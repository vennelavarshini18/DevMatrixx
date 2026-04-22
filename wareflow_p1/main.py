"""
Task 4 — FastAPI Application for WareFlow Person 1 (Warehouse Selector).

Exposes:
    POST /order/place  → ML-powered warehouse assignment (ENTRY POINT for all modules)
    GET  /health       → Firebase + model status (Person 4 polls this on startup)

This is the gateway that unblocks Person 2, 3, and 4's modules.
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager

import joblib
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import OrderRequest, OrderResponse, HealthResponse, ErrorResponse
from maps_integration import get_real_distances
from firebase_utils import (
    get_firebase_app,
    is_firebase_connected,
    get_warehouse_coords,
    get_warehouse_queues,
    firebase_increment_queue,
    write_active_shipment,
)


# ─── Load environment variables ───
load_dotenv()

# ─── Module-level state ───
_model = None
_model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "warehouse_selector.pkl")

# Warehouse IDs in fixed order (must match training feature order)
WAREHOUSE_IDS = ["lucknow", "delhi"]

# Intermediate route cities between warehouses
ROUTE_INTERMEDIATES = {
    "lucknow": ["Lucknow", "Kanpur", "Agra", "Delhi"],
    "delhi": ["Delhi"],
}

# Average speed assumption for ETA estimation (km/h)
AVG_SPEED_KMH = 60.0


def load_model():
    """Load the trained XGBoost model from disk.

    Returns:
        The loaded model, or None if the file doesn't exist.
    """
    global _model
    if os.path.exists(_model_path):
        _model = joblib.load(_model_path)
        print(f"🤖 Model loaded: {_model_path}")
    else:
        print(f"⚠️  Model file not found: {_model_path}")
        print("   Run train_model.py first to generate warehouse_selector.pkl")
        _model = None
    return _model


# ─── Lifespan ───

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialise Firebase and load ML model on startup."""
    # Startup
    print("=" * 50)
    print("  WareFlow P1 — Warehouse Selector API")
    print("=" * 50)

    # Load ML model
    load_model()

    # Initialise Firebase (graceful — don't crash if creds are missing)
    try:
        get_firebase_app()
    except RuntimeError as e:
        print(f"⚠️  Firebase init skipped: {e}")

    yield

    # Shutdown (nothing to clean up)
    print("👋 WareFlow P1 shutting down.")


# ─── FastAPI app ───

app = FastAPI(
    title="WareFlow P1 — Warehouse Selector",
    description="ML-powered warehouse assignment for the Supply Chain Intelligence layer",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Endpoints ───

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check — Person 4 polls this on startup.

    Returns Firebase connection status and model load status so the
    frontend knows whether the backend is ready to accept orders.
    """
    return HealthResponse(
        status="ok" if (_model is not None and is_firebase_connected()) else "degraded",
        firebase_connected=is_firebase_connected(),
        model_loaded=_model is not None,
        model_path=_model_path if _model is not None else None,
    )


@app.post("/order/place", response_model=OrderResponse, responses={500: {"model": ErrorResponse}})
async def place_order(order: OrderRequest):
    """Place an order — the ENTRY POINT that unblocks all other modules.

    Processing logic (in order):
      1. Get real driving distances from customer to each warehouse
      2. Read current queue sizes from Firebase
      3. Run ML model prediction on [dist_wh1, dist_wh2, queue_wh1, queue_wh2]
      4. Assign order to predicted warehouse
      5. Write active shipment state to Firebase
      6. Increment the assigned warehouse's pending queue
      7. Return assignment result for Person 4's confirmation card

    Args:
        order: OrderRequest with order_id, customer_coords, and items.

    Returns:
        OrderResponse with warehouse, eta, and queue_position.
    """
    # ── Guard: model must be loaded ──
    if _model is None:
        raise HTTPException(
            status_code=500,
            detail="warehouse_selector.pkl not loaded. Run train_model.py first.",
        )

    # ── Guard: Firebase must be connected ──
    if not is_firebase_connected():
        raise HTTPException(
            status_code=500,
            detail="Firebase is not connected. Check FIREBASE_CREDENTIALS and FIREBASE_URL.",
        )

    try:
        # Step 1: Get warehouse coordinates from Firebase
        wh_coords = get_warehouse_coords()
        coords_list = [wh_coords.get(wh_id, [0, 0]) for wh_id in WAREHOUSE_IDS]

        # Step 2: Get real driving distances
        distances = await get_real_distances(order.customer_coords, coords_list)

        # Step 3: Read current queue sizes from Firebase
        queues = get_warehouse_queues()
        queue_sizes = [queues.get(wh_id, 0) for wh_id in WAREHOUSE_IDS]

        # Step 4: Build feature vector and predict
        features = np.array([[
            distances[0],   # distance_to_wh1
            distances[1],   # distance_to_wh2
            queue_sizes[0], # queue_size_wh1
            queue_sizes[1], # queue_size_wh2
        ]])
        prediction = int(_model.predict(features)[0])
        assigned_wh = WAREHOUSE_IDS[prediction]

        # Step 5: Calculate ETA
        assigned_distance = distances[prediction]
        eta_hours = round(assigned_distance / AVG_SPEED_KMH, 1)

        # Step 6: Write active shipment to Firebase
        route = ROUTE_INTERMEDIATES.get(assigned_wh, [assigned_wh, "Delhi"])
        write_active_shipment(
            order_id=order.order_id,
            status="pending",
            current_route=route,
            risk_score=0.0,
            eta_hours=eta_hours,
            gemini_alert=None,
        )

        # Step 7: Increment queue atomically
        new_queue = firebase_increment_queue(assigned_wh)

        print(f"✅ Order {order.order_id} → {assigned_wh} (ETA: {eta_hours}h, Queue: {new_queue})")

        return OrderResponse(
            warehouse=assigned_wh,
            eta=f"{eta_hours} hrs",
            queue_position=new_queue,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Order placement failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/order/complete")
async def complete_order(wh_id: str):
    """Mark a delivery as complete — decrements the warehouse queue.

    Called by Person 4's UI when the RL robot finishes a delivery.

    Args:
        wh_id: Warehouse identifier ("lucknow" or "delhi").

    Returns:
        Updated queue count.
    """
    if wh_id not in WAREHOUSE_IDS:
        raise HTTPException(status_code=400, detail=f"Unknown warehouse: {wh_id}")

    if not is_firebase_connected():
        raise HTTPException(status_code=500, detail="Firebase not connected")

    from firebase_utils import firebase_decrement_queue
    new_count = firebase_decrement_queue(wh_id)
    return {"warehouse": wh_id, "pending": new_count}
