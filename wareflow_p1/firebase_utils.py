"""
Task 5 — Firebase Utility Functions for WareFlow P1.

Handles Firebase using REST API to avoid requiring service account credentials.
"""

import os
import requests

# ─── Module-level state ───
_firebase_initialized = False

def get_firebase_app():
    global _firebase_initialized
    db_url = os.environ.get("FIREBASE_DB_URL", os.environ.get("FIREBASE_URL", "https://wareflow-f8b9f-default-rtdb.firebaseio.com"))
    if not db_url.endswith("/"):
        db_url += "/"
    os.environ["FIREBASE_URL"] = db_url
    _firebase_initialized = True
    return db_url

def is_firebase_connected() -> bool:
    try:
        get_firebase_app()
        return True
    except Exception:
        return False

# ─── Warehouse data helpers ───

def get_warehouse_coords() -> dict:
    url = get_firebase_app() + "warehouses.json"
    try:
        data = requests.get(url, timeout=5).json() or {}
        return {wh_id: wh_data.get("coords", [0, 0]) for wh_id, wh_data in data.items()}
    except Exception:
        return {"lucknow": [26.8467, 80.9462], "delhi": [28.6139, 77.2090]}

def get_warehouse_queues() -> dict:
    url = get_firebase_app() + "warehouses.json"
    try:
        data = requests.get(url, timeout=5).json() or {}
        return {wh_id: wh_data.get("pending", 0) for wh_id, wh_data in data.items()}
    except Exception:
        return {"lucknow": 0, "delhi": 0}

# ─── Atomic queue counter operations ───

def firebase_increment_queue(wh_id: str) -> int:
    # Read current
    url = get_firebase_app() + f"warehouses/{wh_id}.json"
    data = requests.get(url).json() or {}
    new_val = data.get("pending", 0) + 1
    # Write back
    requests.patch(url, json={"pending": new_val})
    print(f"📦 {wh_id} queue incremented → {new_val}")
    return new_val

def firebase_decrement_queue(wh_id: str) -> int:
    url = get_firebase_app() + f"warehouses/{wh_id}.json"
    data = requests.get(url).json() or {}
    new_val = max(data.get("pending", 0) - 1, 0)
    requests.patch(url, json={"pending": new_val})
    print(f"📦 {wh_id} queue decremented → {new_val}")
    return new_val

# ─── Active shipment writer ───

def write_active_shipment(
    order_id: str,
    status: str,
    current_route: list,
    risk_score: float = 0.0,
    eta_hours: float = 0.0,
    gemini_alert=None,
):
    url = get_firebase_app() + "active_shipment.json"
    payload = {
        "order_id": order_id,
        "status": status,
        "current_route": current_route,
        "risk_score": risk_score,
        "eta_hours": eta_hours,
        "gemini_alert": gemini_alert,
    }
    requests.put(url, json=payload)
    print(f"🚚 Active shipment written via REST API: {order_id} → {current_route}")
