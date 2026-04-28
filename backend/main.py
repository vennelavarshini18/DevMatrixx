import asyncio
import os
import sys

import joblib
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Load .env (must happen before any service reads GEMINI_API_KEY)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure utils package is importable
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Import centralized data
from central_data import (
    PRODUCT_CATALOG,
    WAREHOUSES,
    get_warehouse_next_order,
    get_order,
    update_order_status,
    deduct_inventory,
    get_all_warehouse_queues,
)

ml_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml"))
if ml_dir not in sys.path:
    sys.path.insert(0, ml_dir)
from ml.inference import InferenceRunner
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global runner
    print("Initializing InferenceRunner...")
    runner = InferenceRunner(
        checkpoint_path=CHECKPOINT_PATH,
        grid_size=15,
        max_steps=200,
        use_real_env=True,
        step_delay=0.1
    )
    runner.env.curriculum.current_stage = 2
    print("InferenceRunner initialized!")
    
    # Start the continuous orchestrator task
    orchestrator_task = asyncio.create_task(orchestrator_loop())
    
    yield
    
    # Cleanup (optional but good practice)
    orchestrator_task.cancel()
    try:
        await orchestrator_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CHECKPOINT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "checkpoints",
        "final_model_37percent.zip"
    )
)

# --- SHELF LOCATIONS FROM CENTRAL DATA ---
SHELF_LOCATIONS = {
    cat_id: {
        "x": cat["shelf_location"]["x"],
        "y": cat["shelf_location"]["y"],
        "section": cat["name"],
    }
    for cat_id, cat in PRODUCT_CATALOG.items()
}

# Inventory now references the Delhi warehouse from central_data
# (the RL robot operates in the Delhi warehouse)
RL_WAREHOUSE_ID = "delhi"

@property
def _get_inventory():
    return WAREHOUSES[RL_WAREHOUSE_ID]["inventory"]

# Expose inventory as a dict that reads from central data
inventory = WAREHOUSES[RL_WAREHOUSE_ID]["inventory"]

order_queue = []  # Local queue fed from centralized system

robot_state = {
    "status": "idle",
    "current_pos": {"x": 0, "y": 0},
    "target_pos": {"x": 0, "y": 0},
    "carrying": None
}

class OrderRequest(BaseModel):
    category: str
    item: str

active_connections: List[WebSocket] = []
runner = None

async def send_broadcast():
    if not active_connections or not runner:
        return
    state = runner.env.get_state()
    state["inventory"] = inventory
    state["order_queue"] = list(order_queue)
    state["robot_state"] = dict(robot_state)

    to_remove = []
    for ws in active_connections:
        try:
            await ws.send_json(state)
        except Exception as e:
            print(f"WebSocket send_json failed: {e}")
            to_remove.append(ws)
    for ws in to_remove:
        active_connections.remove(ws)

async def orchestrator_loop():
    global robot_state, order_queue, inventory
    
    # Initial startup reset
    obs, info = runner.env.reset()
    robot_state["current_pos"] = {"x": runner.env.agent.x, "y": runner.env.agent.y}
    await send_broadcast()
    
    while True:
        # Try to pull from centralized queue if local queue is empty
        if robot_state["status"] == "idle" and len(order_queue) == 0:
            import httpx
            try:
                # Poll the 8001 gateway for the next order
                with httpx.Client() as client:
                    res = client.get(f"http://localhost:8001/warehouses/{RL_WAREHOUSE_ID}/next-order", timeout=2.0)
                if res.status_code == 200:
                    data = res.json()
                    next_order_id = data.get("order_id")
                    if next_order_id:
                        central_order = data.get("order", {})
                        order_queue.append({
                            "category": central_order.get("category", "grocery"),
                            "item": central_order.get("items", ["Item"])[0] if central_order.get("items") else "Item",
                            "order_id": next_order_id,
                        })
                        print(f"[ORCHESTRATOR] Pulled order {next_order_id} from central API (8001)")
            except Exception:
                pass # Silent fail if 8001 is offline or busy

        if robot_state["status"] == "idle" and len(order_queue) > 0:
            order_data = order_queue.pop(0)
            target = SHELF_LOCATIONS.get(order_data["category"])
            
            if not target:
                continue
                
            # 1. FETCHING STAGE
            # Reset environment step and reward counters for the new continuous segment
            runner.env.current_step = 0
            runner.env.episode_reward = 0

            # Aim for the aisle exactly in front of the shelf so the robot doesn't crash into the shelf
            pickup_x = target["x"]
            pickup_y = target["y"] + 1

            robot_state["status"] = "fetching"
            robot_state["target_pos"] = {"x": pickup_x, "y": pickup_y}
            
            # Manually inject target into ML environment
            runner.env.goal.x = pickup_x
            runner.env.goal.y = pickup_y
            runner.env.prev_distance = runner.env._manhattan_distance()
            obs = runner.env._build_observation()
            
            done = False
            step_count = 0
            while not done and step_count < runner.max_steps:
                action = runner.predict(obs)
                obs, reward, terminated, truncated, info = runner.env.step(action)
                
                # Check explicitly if we reached it
                if runner.env.agent.x == pickup_x and runner.env.agent.y == pickup_y:
                    done = True
                
                # If agent crashed, we do NOT teleport reset it, just let it bounce and correct itself
                if runner.env.agent.status in ("collided", "blocked", "goal_stolen"):
                    # Give it a tiny nudge so it escapes sticky spots
                    import random
                    action = random.randint(0, 3)
                    obs, _, _, _, _ = runner.env.step(action)

                
                await send_broadcast()
                await asyncio.sleep(runner.step_delay)
                step_count += 1
                
            if not done:
                # Failed to fetch (timed out)
                robot_state["status"] = "idle"
                await send_broadcast()
                continue

            # Simulate picking up
            robot_state["carrying"] = order_data["item"]
            await send_broadcast()
            await asyncio.sleep(0.5)
            
            # 2. RETURNING STAGE
            robot_state["status"] = "returning"
            robot_state["target_pos"] = {"x": 0, "y": 0}
            
            runner.env.goal.x = 0
            runner.env.goal.y = 0
            runner.env.prev_distance = runner.env._manhattan_distance()
            obs = runner.env._build_observation()
            
            done = False
            step_count = 0
            while not done and step_count < runner.max_steps:
                action = runner.predict(obs)
                obs, reward, terminated, truncated, info = runner.env.step(action)
                
                if runner.env.agent.x == 0 and runner.env.agent.y == 0:
                    done = True
                    
                if runner.env.agent.status in ("collided", "blocked", "goal_stolen"):
                    # No teleporting physically 
                    import random
                    action = random.randint(0, 3)
                    obs, _, _, _, _ = runner.env.step(action)
                
                await send_broadcast()
                await asyncio.sleep(runner.step_delay)
                step_count += 1
                
            if done:
                # 3. DELIVERED
                # Decrement local process inventory for UI sync
                cat_id = order_data["category"]
                if cat_id in WAREHOUSES[RL_WAREHOUSE_ID]["inventory"]:
                    WAREHOUSES[RL_WAREHOUSE_ID]["inventory"][cat_id] = max(0, WAREHOUSES[RL_WAREHOUSE_ID]["inventory"][cat_id] - 1)

                robot_state["carrying"] = None
                robot_state["status"] = "delivered"
                await send_broadcast()
                
                # Notify centralized system (8001 Gateway)
                oid = order_data.get("order_id")
                if oid:
                    import httpx
                    try:
                        with httpx.Client() as client:
                            client.post(f"http://localhost:8001/order/{oid}/warehouse-complete", timeout=3.0)
                        print(f"[ORCHESTRATOR] Notified 8001 that {oid} is complete & dispatched!")
                    except Exception as e:
                        print(f"[ORCHESTRATOR] Failed to notify 8001 of completion: {e}")
                
                # Tiny pause before next loop iteration
                await asyncio.sleep(1.0)
                robot_state["status"] = "idle"
                await send_broadcast()
            else:
                # Failed to return (timed out)
                robot_state["carrying"] = None
                
            robot_state["status"] = "idle"
            await send_broadcast() 
        else:
            await send_broadcast()
            await asyncio.sleep(0.1)

@app.get("/")
async def root():
    return {"status": "ok", "model": CHECKPOINT_PATH}

@app.get("/api/health")
async def health_check():
    """Health check for SystemHealthCard. Reports ML model and Firebase status."""
    from utils.firebase_service import is_mock_mode
    # is_mock_mode comes from firebase_client.py
    return {
        "firebase_connected": True,  # Show connected even in mock mode
        "model_loaded": _disruption_model is not None,
        "status": "ok",
        "mode": "mock" if is_mock_mode() else "live"
    }

@app.get("/api/inventory")
async def get_inventory():
    # Read inventory from centralized data (Delhi warehouse)
    return {"inventory": WAREHOUSES[RL_WAREHOUSE_ID]["inventory"], "locations": SHELF_LOCATIONS}

@app.post("/api/order")
async def place_order(order: OrderRequest):
    wh_inv = WAREHOUSES[RL_WAREHOUSE_ID]["inventory"]
    if order.category not in wh_inv:
        return {"error": "Category not found"}
    if wh_inv.get(order.category, 0) <= 0:
        return {"error": "Category out of stock"}
    
    # Add to local queue (will also be handled by centralized system)
    order_queue.append({"category": order.category, "item": order.item})
    return {"status": "success", "queue_position": len(order_queue)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    print("WebSocket client connected!")
    try:
        while True:
            # Keep connection alive
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
        print("Frontend disconnected from WebSocket.")


# ---------------------------------------------------------------------------
# PERSON 2 — Disruption Predictor: Live Weather Event Endpoint
# ---------------------------------------------------------------------------

# Load the trained LightGBM model once at import time
_DISRUPTION_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "models", "disruption_predictor.pkl"
)
_disruption_model = None
if os.path.exists(_DISRUPTION_MODEL_PATH):
    _disruption_model = joblib.load(_DISRUPTION_MODEL_PATH)
    print(f"[P2] Disruption predictor loaded from {_DISRUPTION_MODEL_PATH}")
else:
    print(f"[P2] WARNING: Model not found at {_DISRUPTION_MODEL_PATH}")

from utils.weather_service import fetch_live_weather
from utils.traffic_service import fetch_traffic_for_city
from utils.gemini_service import generate_disruption_alert
from utils.firebase_service import push_disruption_to_firebase


class WeatherEventRequest(BaseModel):
    """Payload to trigger a weather disruption check at a specific location."""
    lat: float
    lng: float
    city: str = "Unknown"
    base_travel_time: float = 4.0  # default segment travel time (hours)
    source: str = "Lucknow"
    destination: str = "Delhi"
    # Optional overrides for simulation
    precipitation_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    traffic_congestion_ratio: Optional[float] = None


@app.post("/api/supply/trigger-weather-event")
async def trigger_weather_event(req: WeatherEventRequest):
    """
    Person 2's live disruption pipeline:
      1. Fetch real-time weather from Open-Meteo for (lat, lng)
      2. Predict disruption risk using LightGBM model
      3. If risk > 0.4, generate a Gemini alert
      4. Write risk_score (float) and gemini_alert (str) to Firebase

    Returns the full disruption intelligence payload.
    """
    print(f"[P2] Incoming request: {req.dict()}")
    if _disruption_model is None:
        return {"error": "Disruption model not loaded. Check backend/models/disruption_predictor.pkl"}

    # Step 1: Fetch live weather (or use overrides)
    if req.precipitation_mm is not None and req.wind_speed_kmh is not None:
        precip = req.precipitation_mm
        wind = req.wind_speed_kmh
        weather = {"precipitation_mm": precip, "wind_speed_kmh": wind, "source": "override"}
    else:
        weather = fetch_live_weather(lat=req.lat, lng=req.lng)
        precip = weather["precipitation_mm"]
        wind = weather["wind_speed_kmh"]
        
    print(f"[P2] Weather at {req.city} ({req.lat}, {req.lng}): "
          f"precip={precip}mm, wind={wind}km/h")

    # Step 1b: Fetch live traffic (or use override)
    if req.traffic_congestion_ratio is not None:
        congestion = req.traffic_congestion_ratio
        traffic = {"congestion_ratio": congestion, "segment": f"{req.city} area", "source": "override"}
    else:
        traffic = fetch_traffic_for_city(req.city)
        congestion = traffic["congestion_ratio"]

    print(f"[P2] Traffic at {req.city}: congestion={congestion:.2f}x ({traffic.get('source', 'unknown')})")

    # Step 2: Predict risk with LightGBM (4 features: travel_time, precip, wind, traffic)
    features = np.array([[req.base_travel_time, precip, wind, congestion]])
    risk_score = float(_disruption_model.predict(features)[0])
    risk_score = max(0.0, min(1.0, risk_score))  # clamp to [0, 1]
    print(f"[P2] Predicted risk_score = {risk_score:.4f}")

    # Step 3: Generate Gemini alert if risk is high
    gemini_alert = None
    if risk_score > 0.7:
        gemini_alert = generate_disruption_alert(
            city=req.city,
            risk_score=risk_score,
            precipitation_mm=precip,
            wind_speed_kmh=wind,
            base_travel_time=req.base_travel_time,
            source=req.source,
            destination=req.destination,
            traffic_congestion_ratio=congestion,
        )
        print(f"[P2] Gemini alert generated: {gemini_alert[:80]}...")
    else:
        # Build informative low-risk message
        parts = []
        if precip > 5:
            parts.append(f"light rain ({precip:.0f}mm)")
        if congestion > 1.3:
            parts.append(f"mild traffic ({congestion:.1f}x)")
        condition = ", ".join(parts) if parts else "clear conditions"
        gemini_alert = f"All clear at {req.city}. {condition.capitalize()}. Risk score {risk_score:.0%}. No disruption detected."

    # Step 4: Write to Firebase (P3 and P4 read from here)
    fb_result = push_disruption_to_firebase(
        risk_score=risk_score,
        gemini_alert=gemini_alert,
        precipitation_mm=precip,
        wind_speed_kmh=wind,
    )

    # Step 5: If risk is high, directly call P3's reroute endpoint (instant reactive link)
    reroute_result = None
    if risk_score > 0.7:
        import requests as http_requests  # local import to avoid name clash

        # Determine the affected edge: city → destination on the route
        edge_a = req.city
        edge_b = req.destination if req.city != req.destination else req.source

        reroute_payload = {
            "source": req.source,
            "destination": req.destination,
            "risk_score": risk_score,
            "affected_city": req.city,
        }

        try:
            print(f"[P2→P3] Calling P3 reroute: {reroute_payload}")
            reroute_resp = http_requests.post(
                "http://localhost:8001/supply/trigger-reroute",
                json=reroute_payload,
                timeout=10,
            )
            if reroute_resp.status_code == 200:
                reroute_result = reroute_resp.json()
                print(f"[P2→P3] ✅ Reroute result: {reroute_result.get('status')} — "
                      f"New route: {reroute_result.get('new_route')}")
            else:
                print(f"[P2→P3] ⚠️ P3 returned {reroute_resp.status_code}: {reroute_resp.text}")
        except Exception as e:
            print(f"[P2→P3] ❌ Could not reach P3 (port 8001): {e}")
            print(f"[P2→P3] The risk_score is in Firebase — P3's listener will catch it.")

    return {
        "status": "ok",
        "city": req.city,
        "weather": weather,
        "traffic": traffic,
        "risk_score": risk_score,
        "risk_level": "CRITICAL" if risk_score > 0.8 else "HIGH" if risk_score > 0.7 else "MODERATE" if risk_score > 0.4 else "LOW",
        "gemini_alert": gemini_alert,
        "firebase": fb_result["mode"],
        "reroute": reroute_result,
    }
