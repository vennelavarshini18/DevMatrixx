"""
WareFlow Supply Chain — FastAPI Server (Unified Gateway)

This is THE single API server for the entire WareFlow system.
Runs on port 8001. All order operations, routing, and simulation go through here.

Endpoints:
    === ORDER LIFECYCLE ===
    POST /order/place                → Unified entry point: place order, assign warehouse
    GET  /order/{order_id}/status    → Full order lifecycle tracking
    POST /order/{order_id}/warehouse-complete → RL robot finished, ready for dispatch
    POST /order/{order_id}/start-delivery    → Begin delivery simulation
    GET  /orders/active              → All in-flight orders

    === WAREHOUSES ===
    GET  /warehouses                 → All 10 warehouses with live data
    GET  /supply/warehouse-queues    → Queue depths for all warehouses

    === SUPPLY CHAIN (P3 routing) ===
    GET  /supply/route-status        → Full shipment state (for P4 polling)
    GET  /supply/graph-info          → City nodes + edges (for map rendering)
    POST /supply/trigger-reroute     → P2 calls with risk data to trigger Dijkstra
    POST /supply/trigger-weather-event → Demo: simulates storm + reroute
    POST /supply/start-simulation    → Starts the truck simulation loop
    POST /supply/stop-simulation     → Stops the simulation loop
    POST /supply/reset-shipment      → Resets shipment to initial state

Run with:
    python run_supply_server.py
"""

import asyncio
import sys
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure backend directory is in path for central_data import
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from central_data import (
    place_order as central_place_order,
    assign_order_to_warehouse,
    get_order,
    update_order_status,
    get_active_orders,
    get_all_orders,
    get_warehouse_next_order,
    complete_warehouse_fulfillment,
    update_order_position,
    deduct_inventory,
    get_all_warehouse_queues,
    get_all_warehouses_info,
    reset_all_data,
    WAREHOUSES,
    PRODUCT_CATALOG,
)

from supply_chain.graph_engine import (
    calculate_optimal_route,
    find_best_warehouse,
    calculate_delivery_route,
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
    set_active_shipment,
    get_warehouse_queues,
    increment_warehouse_queue,
    decrement_warehouse_queue,
    write_order_to_firebase,
    update_order_in_firebase,
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

class UnifiedOrderRequest(BaseModel):
    """Unified order placement — the SINGLE entry point for all orders."""
    order_id: Optional[str] = None
    customer_coords: list[float]
    items: list[str] = []
    category: str = ""

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
    gemini_alert: Optional[str] = None

class ResetRequest(BaseModel):
    """Reset shipment with optional custom route."""
    source: str = "Lucknow"
    destination: str = "Delhi"


# ─── APP LIFESPAN ───────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Firebase on startup, start risk listener, clean up on shutdown."""
    is_live = initialize_firebase()
    mode = "LIVE Firebase" if is_live else "MOCK in-memory"
    print(f"\n{'='*60}")
    print(f"  WareFlow Unified Supply Chain Server")
    print(f"  Mode: {mode}")
    print(f"  Port: 8001")
    print(f"  Warehouses: {len(WAREHOUSES)}")
    print(f"  Cities: {len(CITY_COORDS)}")
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
    title="WareFlow Unified API",
    description="Centralized gateway: Order placement, warehouse assignment, routing, simulation",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── SIMULATION STATE ───────────────────────────────────────────────────────

_simulation_running = False
_simulation_task: Optional[asyncio.Task] = None
_delivery_tasks: dict = {}  # order_id -> asyncio.Task


# ═══════════════════════════════════════════════════════════════════════════
# UNIFIED ORDER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/order/place")
async def place_order(req: UnifiedOrderRequest):
    """
    UNIFIED ORDER ENTRY POINT — The gateway for the entire system.
    
    Flow:
    1. Create order in central registry
    2. Use Dijkstra + disruptor model to find best warehouse
    3. Assign order to warehouse queue
    4. Update Firebase with shipment state
    5. Return full assignment details to frontend
    """
    import time as _time

    # Step 1: Determine category from items if not provided
    category = req.category
    if not category and req.items:
        # Try to find category by item name
        item_lower = req.items[0].lower()
        for cat_id, cat in PRODUCT_CATALOG.items():
            if any(item_lower in it.lower() for it in cat["items"]):
                category = cat_id
                break
    if not category:
        category = "grocery"  # default

    # Step 2: Create order in central registry
    order = central_place_order(
        customer_coords=req.customer_coords,
        items=req.items,
        category=category,
        order_id=req.order_id,
    )
    order_id = order["order_id"]

    # Step 3: Find best warehouse using Dijkstra + disruptor
    warehouse_result = find_best_warehouse(
        customer_coords=req.customer_coords,
        category=category,
    )

    if "error" in warehouse_result:
        raise HTTPException(
            status_code=500,
            detail=f"No warehouse available: {warehouse_result['error']}"
        )

    wh_id = warehouse_result["warehouse_id"]
    route = warehouse_result["route"]
    eta = warehouse_result["eta_hours"]
    total_eta = warehouse_result["total_eta"]

    # Step 4: Assign to warehouse
    order = assign_order_to_warehouse(order_id, wh_id, route, total_eta)

    # Step 5: Update Firebase
    # Write order to Firebase
    write_order_to_firebase(order)

    # Update active shipment to show this order
    set_active_shipment({
        "order_id": order_id,
        "status": "warehouse_assigned",
        "current_route": route,
        "risk_score": 0.0,
        "eta_hours": total_eta,
        "gemini_alert": None,
        "position": WAREHOUSES[wh_id]["city"],
    })

    # Increment warehouse queue in Firebase
    increment_warehouse_queue(wh_id)

    print(f"[ORDER] ✅ {order_id} → {wh_id} ({warehouse_result['warehouse_city']}) | "
          f"Route: {' → '.join(route)} | ETA: {total_eta}h | Queue: {order['warehouse_queue_position']}")

    return {
        "status": "success",
        "order_id": order_id,
        "warehouse": wh_id,
        "warehouse_city": warehouse_result["warehouse_city"],
        "route": route,
        "eta": f"{total_eta}h",
        "eta_hours": total_eta,
        "delivery_eta_hours": eta,
        "last_mile_hours": warehouse_result.get("last_mile_hours", 0),
        "queue_position": order["warehouse_queue_position"],
        "queue_depth": warehouse_result["queue_depth"],
        "nearest_city": warehouse_result.get("nearest_customer_city", ""),
        "stock": warehouse_result.get("stock", -1),
        "alternatives": warehouse_result.get("alternatives", []),
    }


@app.get("/order/{order_id}/status")
async def order_status(order_id: str):
    """Full order lifecycle tracking."""
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


@app.post("/order/{order_id}/warehouse-complete")
async def warehouse_complete(order_id: str):
    """
    Called when the RL robot finishes picking from shelf and delivers to dispatch.
    Transitions: picking → dispatched.
    """
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    # Deduct inventory
    if order.get("category") and order.get("assigned_warehouse"):
        deduct_inventory(order["assigned_warehouse"], order["category"])

    # Mark as dispatched
    updated = complete_warehouse_fulfillment(order_id)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update order")

    # Decrement warehouse queue in Firebase
    if order.get("assigned_warehouse"):
        decrement_warehouse_queue(order["assigned_warehouse"])

    # Update Firebase order
    update_order_in_firebase(order_id, {"status": "dispatched"})

    print(f"[ORDER] 📦 {order_id} warehouse fulfillment complete → dispatched")

    return {"status": "dispatched", "order_id": order_id}


@app.post("/order/{order_id}/start-delivery")
async def start_delivery(order_id: str):
    """Begin delivery simulation from warehouse to customer's nearest city."""
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    if order["status"] not in ("dispatched", "warehouse_assigned"):
        raise HTTPException(status_code=400, detail=f"Order not ready for delivery (status={order['status']})")

    # Calculate delivery route
    wh_city = WAREHOUSES[order["assigned_warehouse"]]["city"]
    route, eta = calculate_delivery_route(wh_city, order["customer_coords"])

    # Update order
    update_order_status(order_id, "in_transit", route=route, eta_hours=eta, position=wh_city)
    update_order_in_firebase(order_id, {"status": "in_transit", "route": route, "eta_hours": eta})

    # Update active shipment
    set_active_shipment({
        "order_id": order_id,
        "status": "in_transit",
        "current_route": route,
        "risk_score": 0.0,
        "eta_hours": eta,
        "gemini_alert": None,
        "position": wh_city,
    })

    # Start delivery simulation in background
    task = asyncio.create_task(_delivery_simulation(order_id, route))
    _delivery_tasks[order_id] = task

    print(f"[ORDER] 🚛 {order_id} delivery started: {' → '.join(route)} (ETA: {eta}h)")

    return {"status": "delivery_started", "order_id": order_id, "route": route, "eta": eta}


@app.get("/orders/active")
async def active_orders():
    """Get all non-delivered orders."""
    return {"orders": get_active_orders()}


@app.get("/orders/all")
async def all_orders():
    """Get all orders (including delivered)."""
    return {"orders": get_all_orders()}


# ═══════════════════════════════════════════════════════════════════════════
# WAREHOUSE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/warehouses")
async def list_warehouses():
    """Get all 10 warehouses with live queue + inventory data."""
    return get_all_warehouses_info()


@app.get("/warehouses/{wh_id}/inventory")
async def warehouse_inventory(wh_id: str):
    """Get inventory for a specific warehouse."""
    from central_data import get_warehouse_inventory
    inv = get_warehouse_inventory(wh_id)
    if not inv:
        raise HTTPException(status_code=404, detail=f"Warehouse {wh_id} not found")
    return {"warehouse": wh_id, "inventory": inv}


@app.get("/warehouses/{wh_id}/next-order")
async def warehouse_next_order(wh_id: str):
    """Get the next order in a warehouse's queue (for RL robot to pick up)."""
    order_id = get_warehouse_next_order(wh_id)
    if not order_id:
        return {"order": None, "message": "No orders in queue"}
    order = get_order(order_id)
    return {"order": order}


# ═══════════════════════════════════════════════════════════════════════════
# SUPPLY CHAIN ENDPOINTS (P3 ROUTING — backward compatible)
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """Health check."""
    return {
        "service": "WareFlow Unified API",
        "status": "ok",
        "mode": "mock" if is_mock_mode() else "live",
        "simulation_running": _simulation_running,
        "warehouses": len(WAREHOUSES),
        "cities": len(CITY_COORDS),
    }


@app.get("/supply/route-status")
async def route_status():
    """Returns the full active shipment state from Firebase."""
    shipment = get_active_shipment()
    if not shipment:
        raise HTTPException(status_code=404, detail="No active shipment found")
    return shipment


@app.get("/supply/graph-info")
async def graph_info():
    """Returns the city graph structure for frontend map rendering."""
    return get_graph_info()


@app.post("/supply/trigger-reroute")
async def trigger_reroute(req: RerouteRequest):
    """
    Person 2 calls this when their LightGBM model predicts high disruption risk.
    Runs Dijkstra with penalized edge weights and updates Firebase.
    """
    if req.risk_score < 0:
        raise HTTPException(status_code=400, detail="risk_score must be >= 0")

    current = get_active_shipment()
    old_route = current.get("current_route", []) if current else []

    affected_edge = (req.edge_a, req.edge_b) if req.edge_a and req.edge_b else None
    new_route, new_eta = calculate_optimal_route(
        req.source, req.destination,
        risk_score=req.risk_score,
        affected_edge=affected_edge,
        affected_city=req.affected_city,
    )

    if not new_route:
        raise HTTPException(status_code=500, detail=f"No viable route from {req.source} to {req.destination}")

    update_shipment_route(new_route, new_eta, req.risk_score)
    rerouted = old_route != new_route

    return {
        "status": "rerouted" if rerouted else "same_route",
        "old_route": old_route,
        "new_route": new_route,
        "new_eta": new_eta,
        "risk_score": req.risk_score,
        "affected_edge": [req.edge_a, req.edge_b],
    }


@app.post("/supply/trigger-weather-event")
async def trigger_weather_event(req: WeatherEventRequest):
    """DEMO ENDPOINT — Simulates a weather disruption."""
    affected_edge = (req.edge_a, req.edge_b)
    new_route, new_eta = calculate_optimal_route(
        req.source, req.destination,
        risk_score=req.risk_score,
        affected_edge=affected_edge,
    )

    if not new_route:
        raise HTTPException(status_code=500, detail=f"No viable route from {req.source} to {req.destination}")

    update_shipment_route(new_route, new_eta, req.risk_score)

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
    """Resets the shipment to initial state."""
    global _simulation_running
    _simulation_running = False

    reset_listener_state()
    reset_all_data()
    seed_initial_data()

    route, eta = calculate_optimal_route(req.source, req.destination)
    update_shipment_route(route, eta, 0.0)
    update_shipment_position(req.source)
    update_shipment_status("in_transit")
    update_gemini_alert(None)

    return {"status": "reset", "route": route, "eta": eta, "position": req.source}


@app.get("/supply/warehouse-queues")
async def warehouse_queues():
    """Returns current pending order counts per warehouse (all 10)."""
    return get_all_warehouse_queues()


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


# ═══════════════════════════════════════════════════════════════════════════
# PRODUCT CATALOG
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/catalog")
async def get_catalog():
    """Get the unified product catalog."""
    return {"catalog": PRODUCT_CATALOG}


@app.get("/api/inventory")
async def get_inventory():
    """Get aggregated inventory across all warehouses (for storefront display)."""
    from central_data import PRODUCT_CATALOG as PC
    aggregated = {}
    shelf_locations = {}
    for cat_id, cat in PC.items():
        total = sum(
            WAREHOUSES[wh_id].get("inventory", {}).get(cat_id, 0)
            for wh_id in WAREHOUSES
        )
        aggregated[cat_id] = total
        shelf_locations[cat_id] = cat["shelf_location"]

    return {"inventory": aggregated, "locations": shelf_locations}


# ─── For backward compatibility with the old storefront ───
@app.post("/api/order")
async def legacy_order(order: dict):
    """Legacy order endpoint for the storefront's direct RL warehouse orders."""
    category = order.get("category", "")
    item = order.get("item", "")

    # Create in central system and assign to default warehouse (Delhi for RL)
    central_order = central_place_order(
        customer_coords=[28.6, 77.2],  # Default Delhi coords
        items=[item] if item else [],
        category=category,
    )

    # Assign to delhi warehouse (where the RL robot operates)
    assign_order_to_warehouse(central_order["order_id"], "delhi", ["Delhi"], 0.5)
    increment_warehouse_queue("delhi")

    return {"status": "success", "queue_position": central_order.get("warehouse_queue_position", 1)}


# ─── SIMULATION LOOPS ───────────────────────────────────────────────────────

async def _shipment_simulation_loop():
    """Background async task that advances the truck along the route."""
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

            try:
                current_idx = current_route.index(current_position)
            except ValueError:
                current_idx = 0
                update_shipment_position(current_route[0])
                await asyncio.sleep(5)
                continue

            if current_idx >= len(current_route) - 1:
                print(f"[SIMULATION] [DONE] Truck reached destination: {current_position}")
                update_shipment_status("delivered")
                _simulation_running = False
                break

            next_city = current_route[current_idx + 1]
            update_shipment_position(next_city)

            if status == "rerouting":
                update_shipment_status("in_transit")

            print(f"[SIMULATION] {current_position} -> {next_city} "
                  f"({current_idx + 1}/{len(current_route) - 1})")

        except Exception as e:
            print(f"[SIMULATION] [ERROR] Error: {e}")

        await asyncio.sleep(5)

    print("[SIMULATION] [STOP] Truck simulation stopped")


async def _delivery_simulation(order_id: str, route: list):
    """Background task that simulates delivery along a route for a specific order."""
    print(f"[DELIVERY] Starting delivery for {order_id}: {' → '.join(route)}")

    for idx in range(len(route)):
        city = route[idx]
        update_order_position(order_id, city)
        update_shipment_position(city)
        update_order_in_firebase(order_id, {"position": city})

        print(f"[DELIVERY] {order_id}: at {city} ({idx + 1}/{len(route)})")

        if idx < len(route) - 1:
            await asyncio.sleep(5)

    # Mark delivered
    update_order_status(order_id, "delivered")
    update_shipment_status("delivered")
    update_order_in_firebase(order_id, {"status": "delivered"})
    print(f"[DELIVERY] ✅ {order_id} delivered to {route[-1]}")


@app.post("/supply/start-simulation")
async def start_simulation():
    """Start the truck moving along the route."""
    global _simulation_running, _simulation_task

    if _simulation_running:
        return {"status": "already_running"}

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
    """Returns the entire Firebase database state."""
    return get_full_database()
