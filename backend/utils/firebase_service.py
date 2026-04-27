"""
firebase_service.py
===================
Person 2 — Disruption Predictor: Firebase Writer

Thin wrapper that P2 uses to write disruption intelligence to Firebase.
Delegates to Person 3's centralized firebase_client.py so we never create
duplicate database connections.

The data contract with Person 3 (Route Optimizer):
    - risk_score  : float   (0.0 - 1.0) — P3 triggers reroute when > 0.7
    - gemini_alert: str     — displayed on P4's dashboard card

Usage:
    from utils.firebase_service import push_disruption_to_firebase

    push_disruption_to_firebase(
        risk_score=0.85,
        gemini_alert="CRITICAL: Agra experiencing 72mm rainfall...",
        precipitation_mm=72.3,
        wind_speed_kmh=88.0,
    )
"""

import os
import sys

# Make sure supply_chain package is importable
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from supply_chain.firebase_client import (
    get_active_shipment,
    update_gemini_alert,
    update_shipment_route,
    is_mock_mode,
)


def push_disruption_to_firebase(
    risk_score: float,
    gemini_alert: str,
    precipitation_mm: float = 0.0,
    wind_speed_kmh: float = 0.0,
) -> dict:
    """
    Write disruption intelligence to Firebase Realtime Database.

    This writes to the /active_shipment node so that:
      - Person 3 can read risk_score and trigger Dijkstra reroute
      - Person 4 can display the gemini_alert on the dashboard

    Data type contract (verified):
      - risk_score     -> float  (required for P3's comparison > 0.7)
      - gemini_alert   -> str    (required for P4's text display)

    Args:
        risk_score: LightGBM predicted disruption risk (0.0 - 1.0)
        gemini_alert: Natural language alert from Gemini
        precipitation_mm: Raw precipitation value for logging
        wind_speed_kmh: Raw wind speed value for logging

    Returns:
        Dict confirming what was written and the Firebase mode.
    """
    # ── Type enforcement (Firebase handshake guarantee) ───────────────────
    assert isinstance(risk_score, float), f"risk_score must be float, got {type(risk_score)}"
    assert isinstance(gemini_alert, str), f"gemini_alert must be str, got {type(gemini_alert)}"
    assert 0.0 <= risk_score <= 1.0, f"risk_score must be 0-1, got {risk_score}"

    # ── Write to Firebase ────────────────────────────────────────────────
    # Update the shipment's risk_score via the route update path
    current = get_active_shipment()
    current_route = current.get("current_route", []) if current else []
    current_eta = current.get("eta_hours", 0.0) if current else 0.0

    # Write risk_score (P3 reads this to decide on reroute)
    update_shipment_route(current_route, current_eta, float(risk_score))

    # Write gemini_alert (P4 displays this on the dashboard)
    update_gemini_alert(str(gemini_alert))

    mode = "MOCK" if is_mock_mode() else "LIVE"
    print(f"[P2->FIREBASE] [{mode}] risk_score={risk_score:.4f} (float), "
          f"alert={gemini_alert[:50]}... (str)")

    return {
        "status": "written",
        "mode": mode,
        "risk_score": risk_score,
        "risk_score_type": "float",
        "gemini_alert_type": "str",
        "precipitation_mm": precipitation_mm,
        "wind_speed_kmh": wind_speed_kmh,
    }
