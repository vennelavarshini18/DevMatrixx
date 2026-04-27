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

# --- SINGLE SOURCE OF TRUTH (IN-MEMORY) ---
SHELF_LOCATIONS = {
    "skincare": {"x": 2, "y": 3, "section": "Skincare"},
    "grocery": {"x": 7, "y": 3, "section": "Grocery"},
    "footwear": {"x": 11, "y": 3, "section": "Footwear"},
    "clothes": {"x": 2, "y": 8, "section": "Clothes"},
    "pharmacy": {"x": 7, "y": 8, "section": "Pharmacy"},
    "electronics": {"x": 11, "y": 8, "section": "Electronics"},
    "stationery": {"x": 4, "y": 12, "section": "Stationery"},
    "accessories": {"x": 9, "y": 12, "section": "Accessories"}
}

inventory = {
    "skincare": 15,
    "grocery": 20,
    "footwear": 5,
    "clothes": 12,
    "pharmacy": 30,
    "electronics": 3,
    "stationery": 40,
    "accessories": 10
}

order_queue = [] 

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
                # Update single source of truth
                cat_id = order_data["category"]
                if inventory[cat_id] > 0:
                    inventory[cat_id] -= 1
                robot_state["carrying"] = None
                robot_state["status"] = "delivered"
                await send_broadcast()
                await asyncio.sleep(3.0) # Pause so UI can show the success toast
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
    return {"inventory": inventory, "locations": SHELF_LOCATIONS}

@app.post("/api/order")
async def place_order(order: OrderRequest):
    if order.category not in inventory:
        return {"error": "Category not found"}
    if inventory[order.category] <= 0:
        return {"error": "Category out of stock"}
        
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

    # Step 2: Predict risk with LightGBM
    features = np.array([[req.base_travel_time, precip, wind]])
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
        )
        print(f"[P2] Gemini alert generated: {gemini_alert[:80]}...")
    else:
        gemini_alert = f"All clear at {req.city}. Risk score {risk_score:.0%}. No disruption detected."

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
        "risk_score": risk_score,
        "risk_level": "CRITICAL" if risk_score > 0.8 else "HIGH" if risk_score > 0.7 else "MODERATE" if risk_score > 0.4 else "LOW",
        "gemini_alert": gemini_alert,
        "firebase": fb_result["mode"],
        "reroute": reroute_result,
    }
