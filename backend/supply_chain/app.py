"""
WareFlow Supply Chain — FastAPI Server (Person 3: Route Optimizer)

This is the supply chain API server. It runs on port 8001, completely
independent of the existing RL warehouse server on port 8000.

Endpoints:
    GET  /supply/route-status           → Full shipment state (for P4 polling)
    GET  /supply/graph-info             → City nodes + edges (for P4 map rendering)
    POST /supply/trigger-reroute        → P2 calls this with risk data to trigger Dijkstra
    POST /supply/trigger-weather-event  → Demo button: simulates storm + reroute
    POST /supply/start-simulation       → Starts the truck simulation loop
    POST /supply/stop-simulation        → Stops the simulation loop
    POST /supply/reset-shipment         → Resets shipment to initial state
    GET  /supply/warehouse-queues       → Current warehouse queue depths

Run with:
    python run_supply_server.py
    # or
    uvicorn supply_chain.app:app --port 8001 --reload
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from supply_chain.graph_engine import (
    calculate_optimal_route,
    get_graph_info,
    CITY_COORDS,
)
from supply_chain.firebase_client import (
    initialize_firebase,
    get_active_shipment,
    update_shipment_route,
    update_shipment_position,
    update_shipment_status,
    update_gemini_alert,
    get_warehouse_queues,
    increment_warehouse_queue,
    decrement_warehouse_queue,
    seed_initial_data,
    get_full_database,
    is_mock_mode,
)
from supply_chain.risk_listener import (
    risk_score_listener_loop,
    stop_listener,
    reset_listener_state,
)


# ─── REQUEST MODELS ─────────────────────────────────────────────────────────

class RerouteRequest(BaseModel):
    """P2 sends this when LightGBM detects high disruption risk."""
    source: str = "Lucknow"
    destination: str = "Delhi"
    risk_score: float
    edge_a: Optional[str] = None
    edge_b: Optional[str] = None
    affected_city: Optional[str] = None

class WeatherEventRequest(BaseModel):
    """Demo endpoint payload to simulate a storm on a specific highway."""
    edge_a: str = "Agra"
    edge_b: str = "Delhi"
    risk_score: float = 0.85
    source: str = "Lucknow"
    destination: str = "Delhi"
    gemini_alert: Optional[str] = None  # P2 can pass generated text here

class ResetRequest(BaseModel):
    """Reset shipment with optional custom route."""
    source: str = "Lucknow"
    destination: str = "Delhi"

class OrderPlaceRequest(BaseModel):
    """P4's incoming order payload from the storefront UI."""
    order_id: str
    customer_coords: list[float]
    items: list[str] = []


# ─── APP LIFESPAN ───────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Firebase on startup, start risk listener, clean up on shutdown."""
    is_live = initialize_firebase()
    mode = "LIVE Firebase" if is_live else "MOCK in-memory"
    print(f"\n{'='*60}")
    print(f"  WareFlow Supply Chain Server")
    print(f"  Mode: {mode}")
    print(f"  Port: 8001")
    print(f"{'='*60}\n")

    # Start the Firebase risk_score listener (Person 2 → Person 3 safety net)
    risk_listener_task = asyncio.create_task(risk_score_listener_loop())

    yield

    # Shutdown: stop risk listener and simulation
    stop_listener()
    risk_listener_task.cancel()
    try:
        await risk_listener_task
    except asyncio.CancelledError:
        pass
    global _simulation_running
    _simulation_running = False
    print("\n[SERVER] Supply chain server shutting down.")


# ─── APP INSTANCE ───────────────────────────────────────────────────────────

app = FastAPI(
    title="WareFlow Supply Chain API",
    description="Person 3: Route Optimizer — Graph routing, Firebase sync, shipment simulation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # P4's React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── SIMULATION STATE ───────────────────────────────────────────────────────

_simulation_running = False
_simulation_task: Optional[asyncio.Task] = None


# ─── ENDPOINTS ──────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Health check."""
    return {
        "service": "WareFlow Supply Chain API",
        "status": "ok",
        "mode": "mock" if is_mock_mode() else "live",
        "simulation_running": _simulation_running,
    }


@app.get("/supply/route-status")
async def route_status():
    """
    Returns the full active shipment state from Firebase.
    P4's frontend polls this every 2 seconds to update the dashboard.
    
    Response shape:
    {
        "order_id": "ORD-001",
        "status": "in_transit",
        "current_route": ["Lucknow", "Agra", "Delhi"],
        "risk_score": 0.0,
        "eta_hours": 6.5,
        "gemini_alert": null,
        "position": "Agra"
    }
    """
    shipment = get_active_shipment()
    if not shipment:
        raise HTTPException(status_code=404, detail="No active shipment found")
    return shipment


@app.get("/supply/graph-info")
async def graph_info():
    """
    Returns the city graph structure for P4 to render on Google Maps.
    Includes all city nodes with lat/lng and all highway edges with travel times.
    """
    return get_graph_info()


@app.post("/supply/trigger-reroute")
async def trigger_reroute(req: RerouteRequest):
    """
    Person 2 calls this when their LightGBM model predicts high disruption risk.
    
    Flow:
    1. Receive risk data from P2
    2. Run Dijkstra with penalized edge weights  
    3. Write new route to Firebase
    4. P4's frontend auto-updates via Firebase listener
    """
    if req.risk_score < 0:
        raise HTTPException(status_code=400, detail="risk_score must be >= 0")

    # Get the current route for comparison
    current = get_active_shipment()
    old_route = current.get("current_route", []) if current else []

    # Run risk-weighted Dijkstra
    affected_edge = (req.edge_a, req.edge_b) if req.edge_a and req.edge_b else None
    new_route, new_eta = calculate_optimal_route(
        req.source, req.destination,
        risk_score=req.risk_score,
        affected_edge=affected_edge,
        affected_city=req.affected_city,
    )

    if not new_route:
        raise HTTPException(
            status_code=500,
            detail=f"No viable route from {req.source} to {req.destination}"
        )

    # Write new route to Firebase
    update_shipment_route(new_route, new_eta, req.risk_score)

    # Determine if the route actually changed
    rerouted = old_route != new_route

    return {
        "status": "rerouted" if rerouted else "same_route",
        "old_route": old_route,
        "new_route": new_route,
        "new_eta": new_eta,
        "risk_score": req.risk_score,
        "affected_edge": [req.edge_a, req.edge_b],
    }




@app.post("/order/place")
async def place_order(req: OrderPlaceRequest):
    """
    DEMO ENDPOINT — Simulates Person 4's XGBoost Warehouse Selector.
    Since P4's ML model isn't built yet, this acts as a placeholder
    so the storefront UI's "Place Order" button functions properly.
    """
    import random
    
    # Dummy ML logic: just pick Lucknow or Delhi randomly for the demo
    warehouse = random.choice(["Lucknow", "Delhi"])
    eta = f"{random.uniform(2.5, 8.5):.1f}h"
    
    # Increment the queue depth in Firebase to reflect the new order
    new_queue_pos = increment_warehouse_queue(warehouse)
    
    return {
        "status": "success",
        "warehouse": warehouse,
        "eta": eta,
        "queue_position": new_queue_pos
    }

@app.post("/supply/trigger-weather-event")
async def trigger_weather_event(req: WeatherEventRequest):
    """
    DEMO ENDPOINT — Simulates a weather disruption.
    
    This is the button P2/P4 needs for the live demo:
    1. Injects a high risk_score on a highway edge
    2. Runs Dijkstra reroute
    3. Writes a Gemini-style alert to Firebase (or uses P2's real Gemini text)
    4. P4's dashboard shows the route change + alert card in real time
    """
    # Run reroute
    affected_edge = (req.edge_a, req.edge_b)
    new_route, new_eta = calculate_optimal_route(
        req.source, req.destination,
        risk_score=req.risk_score,
        affected_edge=affected_edge,
    )

    if not new_route:
        raise HTTPException(
            status_code=500,
            detail=f"No viable route from {req.source} to {req.destination}"
        )

    # Write route update
    update_shipment_route(new_route, new_eta, req.risk_score)

    # Write Gemini alert (use P2's text if provided, otherwise use a demo fallback)
    alert_text = req.gemini_alert or (
        f"⚠️ WEATHER ALERT: Severe storm detected on {req.edge_a}–{req.edge_b} highway. "
        f"Risk score: {req.risk_score:.0%}. Shipment rerouted via {' → '.join(new_route)}. "
        f"New ETA: {new_eta} hours."
    )
    update_gemini_alert(alert_text)
    update_shipment_status("rerouting")

    return {
        "status": "weather_event_triggered",
        "disrupted_edge": [req.edge_a, req.edge_b],
        "risk_score": req.risk_score,
        "new_route": new_route,
        "new_eta": new_eta,
        "gemini_alert": alert_text,
    }


@app.post("/supply/reset-shipment")
async def reset_shipment(req: ResetRequest = ResetRequest()):
    """
    Resets the shipment to initial state. 
    Seeds the Firebase database with the agreed-upon schema.
    Useful for demo resets between different demo runs.
    """
    global _simulation_running
    _simulation_running = False

    # Reset the risk listener state so it can detect fresh events
    reset_listener_state()

    # Seed the initial data
    seed_initial_data()

    # Calculate the default route
    route, eta = calculate_optimal_route(req.source, req.destination)
    update_shipment_route(route, eta, 0.0)
    update_shipment_position(req.source)
    update_shipment_status("in_transit")
    update_gemini_alert(None)

    return {
        "status": "reset",
        "route": route,
        "eta": eta,
        "position": req.source,
    }


@app.get("/supply/warehouse-queues")
async def warehouse_queues():
    """
    Returns current pending order counts per warehouse.
    P4 uses this for the warehouse queue panel on the dashboard.
    """
    return get_warehouse_queues()


@app.post("/supply/increment-queue/{wh_id}")
async def increment_queue(wh_id: str):
    """P1 calls this when XGBoost assigns an order to a warehouse."""
    new_count = increment_warehouse_queue(wh_id)
    return {"warehouse": wh_id, "pending": new_count}


@app.post("/supply/decrement-queue/{wh_id}")
async def decrement_queue(wh_id: str):
    """Called when RL robot finishes delivery at a warehouse."""
    new_count = decrement_warehouse_queue(wh_id)
    return {"warehouse": wh_id, "pending": new_count}


# ─── SIMULATION LOOP ────────────────────────────────────────────────────────

async def _shipment_simulation_loop():
    """
    Background async task that advances the truck along the route.
    
    Every 5 seconds:
    1. Read current route and position from Firebase
    2. Find current index in the route array
    3. Move to the next city
    4. Write new position to Firebase
    
    P4's React frontend reads the position in real-time and uses
    linear interpolation between city coordinates to smoothly
    animate the truck marker on the Google Map.
    """
    global _simulation_running
    _simulation_running = True
    print("[SIMULATION] Truck simulation started")

    while _simulation_running:
        try:
            shipment = get_active_shipment()

            if not shipment:
                await asyncio.sleep(5)
                continue

            status = shipment.get("status", "")
            if status not in ("in_transit", "rerouting"):
                await asyncio.sleep(5)
                continue

            current_route = shipment.get("current_route", [])
            current_position = shipment.get("position", "")

            if not current_route or not current_position:
                await asyncio.sleep(5)
                continue

            # Find where we are in the route
            try:
                current_idx = current_route.index(current_position)
            except ValueError:
                # Position not in current route (maybe rerouted) — snap to first city
                current_idx = 0
                update_shipment_position(current_route[0])
                print(f"[SIMULATION] Snapped truck to {current_route[0]} (route changed)")
                await asyncio.sleep(5)
                continue

            # Check if we've reached the destination
            if current_idx >= len(current_route) - 1:
                print(f"[SIMULATION] [DONE] Truck reached destination: {current_position}")
                update_shipment_status("delivered")
                _simulation_running = False
                break

            # Advance to next city
            next_city = current_route[current_idx + 1]
            update_shipment_position(next_city)

            # Also update status back to in_transit if it was rerouting
            if status == "rerouting":
                update_shipment_status("in_transit")

            print(f"[SIMULATION] {current_position} -> {next_city} "
                  f"({current_idx + 1}/{len(current_route) - 1})")

        except Exception as e:
            print(f"[SIMULATION] [ERROR] Error: {e}")

        await asyncio.sleep(5)

    print("[SIMULATION] [STOP] Truck simulation stopped")


@app.post("/supply/start-simulation")
async def start_simulation():
    """Start the truck moving along the route."""
    global _simulation_running, _simulation_task

    if _simulation_running:
        return {"status": "already_running"}

    # Reset position to the start of the current route
    shipment = get_active_shipment()
    if shipment and shipment.get("current_route"):
        start_city = shipment["current_route"][0]
        update_shipment_position(start_city)
        update_shipment_status("in_transit")

    _simulation_task = asyncio.create_task(_shipment_simulation_loop())
    return {"status": "simulation_started"}


@app.post("/supply/stop-simulation")
async def stop_simulation():
    """Stop the truck simulation loop."""
    global _simulation_running
    _simulation_running = False
    return {"status": "simulation_stopped"}


# ─── DEBUG ENDPOINT ─────────────────────────────────────────────────────────

@app.get("/supply/debug/full-db")
async def debug_full_db():
    """
    Returns the entire Firebase database state. 
    Only for development/debugging — remove before production.
    """
    return get_full_database()
