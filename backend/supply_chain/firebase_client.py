"""
WareFlow Supply Chain — Firebase Realtime Database Client (Person 3)

Centralized Firebase read/write operations for ALL supply chain modules.
P1, P2, and P3 import from this file to avoid duplicate DB connections.

The module provides two modes:
  1. LIVE MODE  — connects to the real Firebase RTDB (requires service account JSON)
  2. MOCK MODE  — uses an in-memory dict when Firebase credentials aren't configured yet.
                  This lets you develop and test all endpoints without Firebase access.

The mode is auto-detected: if the service account file exists → live, otherwise → mock.
"""

import os
import json
from typing import Optional, Dict, Any, List

# ─── ATTEMPT FIREBASE IMPORT ────────────────────────────────────────────────

_FIREBASE_AVAILABLE = False
_firebase_db = None

try:
    import firebase_admin
    from firebase_admin import credentials, db as firebase_db_module
    _FIREBASE_AVAILABLE = True
except ImportError:
    print("[FIREBASE] firebase-admin not installed. Running in MOCK mode.")
    print("[FIREBASE] Install with: pip install firebase-admin")


# ─── MOCK IN-MEMORY DATABASE ────────────────────────────────────────────────
# Used when Firebase credentials aren't set up yet.
# Mimics the exact same schema so all endpoints work identically.

_mock_db: Dict[str, Any] = {
    "warehouses": {
        "lucknow": {"pending": 0, "coords": [26.8467, 80.9462]},
        "delhi": {"pending": 0, "coords": [28.6139, 77.2090]}
    },
    "active_shipment": {
        "order_id": "ORD-001",
        "status": "in_transit",
        "current_route": ["Lucknow", "Agra", "Delhi"],
        "risk_score": 0.0,
        "eta_hours": 6.5,
        "gemini_alert": None,
        "position": "Lucknow"
    }
}

_using_mock = True  # Will be set to False if Firebase initializes successfully


# ─── INITIALIZATION ─────────────────────────────────────────────────────────

def initialize_firebase() -> bool:
    """
    Initialize Firebase connection. Returns True if live Firebase is active,
    False if falling back to mock mode.
    """
    global _using_mock, _firebase_db

    if not _FIREBASE_AVAILABLE:
        print("[FIREBASE] --- Running in MOCK mode (firebase-admin not installed)")
        _using_mock = True
        return False

    from supply_chain.firebase_config import SERVICE_ACCOUNT_PATH, DATABASE_URL

    if not os.path.exists(SERVICE_ACCOUNT_PATH):
        print(f"[FIREBASE] --- Service account not found at: {SERVICE_ACCOUNT_PATH}")
        print("[FIREBASE] --- Running in MOCK mode. Place your firebase-service-account.json there.")
        _using_mock = True
        return False

    if DATABASE_URL == "https://your-project-id-default-rtdb.firebaseio.com/":
        print("[FIREBASE] --- DATABASE_URL not configured in firebase_config.py")
        print("[FIREBASE] --- Running in MOCK mode.")
        _using_mock = True
        return False

    try:
        # Only initialize once
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred, {"databaseURL": DATABASE_URL})

        _firebase_db = firebase_db_module
        _using_mock = False
        print("[FIREBASE] [OK] Connected to live Firebase Realtime Database")
        return True

    except Exception as e:
        print(f"[FIREBASE] [FAIL] Failed to initialize: {e}")
        print("[FIREBASE] [WARN] Falling back to MOCK mode")
        _using_mock = True
        return False


# ─── ACTIVE SHIPMENT OPERATIONS ─────────────────────────────────────────────

def get_active_shipment() -> Optional[Dict[str, Any]]:
    """Read the current active shipment state. Used by P4's GET /supply/route-status."""
    if _using_mock:
        return dict(_mock_db.get("active_shipment", {}))

    ref = _firebase_db.reference("/active_shipment")
    return ref.get()


def update_shipment_route(new_route: List[str], new_eta: float, risk_score: float) -> None:
    """
    Write new route, ETA, and risk score to Firebase.
    Called after Dijkstra reroute completes.
    """
    update_data = {
        "current_route": new_route,
        "eta_hours": new_eta,
        "risk_score": risk_score,
    }

    if _using_mock:
        _mock_db["active_shipment"].update(update_data)
        print(f"[MOCK-DB] Updated route: {new_route}, ETA: {new_eta}h, risk: {risk_score}")
        return

    ref = _firebase_db.reference("/active_shipment")
    ref.update(update_data)
    print(f"[FIREBASE] Updated route: {new_route}, ETA: {new_eta}h, risk: {risk_score}")


def update_shipment_position(city_name: str) -> None:
    """
    Write the truck's current city position to Firebase.
    Called every 5s by the simulation loop.
    P4 reads this to animate the truck marker.
    """
    if _using_mock:
        _mock_db["active_shipment"]["position"] = city_name
        return

    ref = _firebase_db.reference("/active_shipment")
    ref.update({"position": city_name})


def update_gemini_alert(alert_text: Optional[str]) -> None:
    """
    Write Gemini-generated alert text to Firebase.
    Called by P2's disruption predictor when risk > 0.7.
    Note: Firebase ignores None in update(), so we use empty string to clear.
    """
    # Firebase RTDB ignores None in update() — use empty string as "no alert" sentinel
    safe_text = alert_text if alert_text else ""

    if _using_mock:
        _mock_db["active_shipment"]["gemini_alert"] = alert_text  # mock can handle None
        print(f"[MOCK-DB] Gemini alert: {alert_text}")
        return

    ref = _firebase_db.reference("/active_shipment/gemini_alert")
    ref.set(safe_text)
    print(f"[FIREBASE] Gemini alert set: {safe_text[:50] if safe_text else '(cleared)'}")


def update_shipment_status(status: str) -> None:
    """Update the shipment status (e.g., 'in_transit', 'delivered', 'rerouting')."""
    if _using_mock:
        _mock_db["active_shipment"]["status"] = status
        return

    ref = _firebase_db.reference("/active_shipment")
    ref.update({"status": status})


# ─── WAREHOUSE QUEUE OPERATIONS ─────────────────────────────────────────────

def get_warehouse_queues() -> Dict[str, int]:
    """
    Read pending order counts for all warehouses.
    Returns: {"lucknow": 3, "delhi": 1}
    """
    if _using_mock:
        queues = {}
        for wh_id, data in _mock_db.get("warehouses", {}).items():
            queues[wh_id] = data.get("pending", 0)
        return queues

    ref = _firebase_db.reference("/warehouses")
    data = ref.get() or {}
    return {wh_id: info.get("pending", 0) for wh_id, info in data.items()}


def increment_warehouse_queue(wh_id: str) -> int:
    """
    Increment the pending order count for a warehouse.
    Called by P1 when XGBoost assigns an order.
    Returns the new pending count.
    """
    if _using_mock:
        if wh_id in _mock_db.get("warehouses", {}):
            _mock_db["warehouses"][wh_id]["pending"] += 1
            new_val = _mock_db["warehouses"][wh_id]["pending"]
            print(f"[MOCK-DB] {wh_id} queue: {new_val}")
            return new_val
        return 0

    ref = _firebase_db.reference(f"/warehouses/{wh_id}/pending")
    current = ref.get() or 0
    ref.set(current + 1)
    return current + 1


def decrement_warehouse_queue(wh_id: str) -> int:
    """
    Decrement the pending order count for a warehouse.
    Called when RL robot finishes delivery.
    Returns the new pending count (never goes below 0).
    """
    if _using_mock:
        if wh_id in _mock_db.get("warehouses", {}):
            current = _mock_db["warehouses"][wh_id]["pending"]
            _mock_db["warehouses"][wh_id]["pending"] = max(0, current - 1)
            new_val = _mock_db["warehouses"][wh_id]["pending"]
            print(f"[MOCK-DB] {wh_id} queue: {new_val}")
            return new_val
        return 0

    ref = _firebase_db.reference(f"/warehouses/{wh_id}/pending")
    current = ref.get() or 0
    new_val = max(0, current - 1)
    ref.set(new_val)
    return new_val


# ─── SEED / RESET ───────────────────────────────────────────────────────────

def seed_initial_data() -> None:
    """
    Write the agreed-upon initial schema to Firebase.
    Safe to call multiple times — it overwrites to a known good state.
    """
    import time
    from supply_chain.firebase_config import INITIAL_SCHEMA

    # Deep copy + generate a fresh order ID to make each reset visually distinct
    schema = json.loads(json.dumps(INITIAL_SCHEMA))
    schema["active_shipment"]["order_id"] = f"ORD-{int(time.time())}"

    if _using_mock:
        _mock_db.update(schema)
        print("[MOCK-DB] [OK] Database seeded with initial schema")
        return

    # Atomically set the entire root to the clean schema
    ref = _firebase_db.reference("/")
    ref.set(schema)
    print("[FIREBASE] [OK] Database fully reset with initial schema")


def get_full_database() -> Dict[str, Any]:
    """Read the entire database state. Useful for debugging."""
    if _using_mock:
        return dict(_mock_db)

    ref = _firebase_db.reference("/")
    return ref.get() or {}


def is_mock_mode() -> bool:
    """Check if we're running in mock mode."""
    return _using_mock
