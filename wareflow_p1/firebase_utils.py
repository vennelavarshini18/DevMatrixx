"""
Task 5 — Firebase Utility Functions for WareFlow P1.

Handles Firebase Admin SDK initialization and atomic queue counter
operations (increment/decrement) for warehouse pending orders.
Uses transactions to prevent race conditions on concurrent order placement.
"""

import os
import json

import firebase_admin
from firebase_admin import credentials, db as firebase_db


# ─── Module-level state ───
_firebase_app = None
_firebase_initialized = False


def get_firebase_app():
    """Return the initialised Firebase app, creating it on first call.

    Reads credentials from the FIREBASE_CREDENTIALS environment variable
    (path to service-account JSON) and the database URL from FIREBASE_URL.

    Returns:
        The firebase_admin App instance.

    Raises:
        RuntimeError: If required environment variables are missing.
    """
    global _firebase_app, _firebase_initialized

    if _firebase_initialized:
        return _firebase_app

    cred_path = os.environ.get("FIREBASE_CREDENTIALS", "")
    db_url = os.environ.get("FIREBASE_URL", "")

    if not cred_path:
        raise RuntimeError(
            "FIREBASE_CREDENTIALS env var is not set. "
            "Point it to your Firebase service-account JSON file."
        )
    if not db_url:
        raise RuntimeError(
            "FIREBASE_URL env var is not set. "
            "Set it to your Firebase Realtime Database URL "
            "(e.g. https://your-project.firebaseio.com)."
        )

    if not os.path.exists(cred_path):
        raise RuntimeError(f"Firebase credentials file not found: {cred_path}")

    cred = credentials.Certificate(cred_path)
    _firebase_app = firebase_admin.initialize_app(cred, {"databaseURL": db_url})
    _firebase_initialized = True
    print(f"🔥 Firebase initialized — DB: {db_url}")
    return _firebase_app


def is_firebase_connected() -> bool:
    """Check whether Firebase has been successfully initialised.

    Returns:
        True if Firebase Admin SDK is initialised, False otherwise.
    """
    return _firebase_initialized


# ─── Warehouse data helpers ───

def get_warehouse_coords() -> dict:
    """Read warehouse coordinates from Firebase.

    Returns:
        Dict mapping warehouse ID to [lat, lng] list.
        Example: {"lucknow": [26.8, 80.9], "delhi": [28.6, 77.2]}
    """
    get_firebase_app()
    ref = firebase_db.reference("warehouses")
    data = ref.get() or {}
    return {
        wh_id: wh_data.get("coords", [0, 0])
        for wh_id, wh_data in data.items()
    }


def get_warehouse_queues() -> dict:
    """Read current pending queue sizes from Firebase.

    Returns:
        Dict mapping warehouse ID to pending count.
        Example: {"lucknow": 3, "delhi": 1}
    """
    get_firebase_app()
    ref = firebase_db.reference("warehouses")
    data = ref.get() or {}
    return {
        wh_id: wh_data.get("pending", 0)
        for wh_id, wh_data in data.items()
    }


# ─── Atomic queue counter operations ───

def firebase_increment_queue(wh_id: str) -> int:
    """Atomically increment the pending counter for a warehouse.

    Uses Firebase transactions to prevent race conditions when multiple
    orders arrive simultaneously. Person 4's frontend reads this value
    in real time — it MUST be accurate.

    Args:
        wh_id: Warehouse identifier (e.g. "lucknow" or "delhi").

    Returns:
        The new pending count after increment.
    """
    get_firebase_app()
    ref = firebase_db.reference(f"warehouses/{wh_id}/pending")

    new_value = [None]  # mutable container for closure

    def increment_txn(current_value):
        """Transaction function: atomically read-modify-write."""
        val = (current_value or 0) + 1
        new_value[0] = val
        return val

    ref.transaction(increment_txn)
    print(f"📦 {wh_id} queue incremented → {new_value[0]}")
    return new_value[0]


def firebase_decrement_queue(wh_id: str) -> int:
    """Atomically decrement the pending counter for a warehouse.

    Called when the WareFlow RL robot finishes a delivery (Person 4
    triggers this via a UI button). Will not go below 0.

    Args:
        wh_id: Warehouse identifier (e.g. "lucknow" or "delhi").

    Returns:
        The new pending count after decrement.
    """
    get_firebase_app()
    ref = firebase_db.reference(f"warehouses/{wh_id}/pending")

    new_value = [None]

    def decrement_txn(current_value):
        """Transaction function: atomically read-modify-write, floor at 0."""
        val = max((current_value or 0) - 1, 0)
        new_value[0] = val
        return val

    ref.transaction(decrement_txn)
    print(f"📦 {wh_id} queue decremented → {new_value[0]}")
    return new_value[0]


# ─── Active shipment writer ───

def write_active_shipment(
    order_id: str,
    status: str,
    current_route: list,
    risk_score: float = 0.0,
    eta_hours: float = 0.0,
    gemini_alert=None,
):
    """Write active shipment state to Firebase.

    This is the shared schema that Person 2, 3, and 4 all depend on.
    Keys MUST match the contract exactly.

    Args:
        order_id: Unique order identifier.
        status: One of "pending", "in_transit", "delivered".
        current_route: List of city names along the route.
        risk_score: Initial risk score (Person 2 updates this later).
        eta_hours: Estimated time of arrival in hours.
        gemini_alert: Gemini NL alert string (Person 2 sets this).
    """
    get_firebase_app()
    ref = firebase_db.reference("active_shipment")
    ref.set({
        "order_id": order_id,
        "status": status,
        "current_route": current_route,
        "risk_score": risk_score,
        "eta_hours": eta_hours,
        "gemini_alert": gemini_alert,
    })
    print(f"🚚 Active shipment written: {order_id} → {current_route}")
