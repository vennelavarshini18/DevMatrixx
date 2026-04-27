"""
WareFlow Supply Chain — Firebase Risk Score Listener (Updated)

Background async task that polls the risk_score from Firebase every 3 seconds.
When the score exceeds 0.7 (and hasn't already been handled), it automatically
triggers a Dijkstra reroute to avoid the disrupted highway segment.

This acts as a SAFETY NET — the primary trigger is P2's direct HTTP call to
/supply/trigger-reroute. This poller catches cases where that call fails.

Updated to work with the expanded 22-city graph.
"""

import asyncio
from typing import Optional, Tuple

from supply_chain.firebase_client import (
    get_active_shipment,
    update_shipment_route,
    update_shipment_status,
)
from supply_chain.graph_engine import calculate_optimal_route, CITY_COORDS


# ─── STATE ──────────────────────────────────────────────────────────────────

_last_handled_risk: float = 0.0
_listener_running: bool = False


# ─── EDGE DETECTION ────────────────────────────────────────────────────────

def _detect_affected_city(current_route: list) -> Optional[str]:
    """
    Heuristic: find the most likely disrupted city on the current route.
    Returns the first intermediate city (not source/destination).
    """
    if len(current_route) < 3:
        return None
    intermediates = current_route[1:-1]
    for city in intermediates:
        if city in CITY_COORDS:
            return city
    return None


# ─── REROUTE FUNCTION ──────────────────────────────────────────────────────

def reroute(
    source: str,
    destination: str,
    risk_score: float,
    affected_city: str,
) -> dict:
    """
    Execute the reroute logic: penalize edges around the affected city
    and find a new optimal path using Dijkstra's algorithm.
    """
    current = get_active_shipment()
    old_route = current.get("current_route", []) if current else []

    new_route, new_eta = calculate_optimal_route(
        source, destination,
        risk_score=risk_score,
        affected_city=affected_city,
    )

    if not new_route:
        print(f"[RISK-LISTENER] ERROR: No viable route from {source} to {destination}")
        return {"rerouted": False, "error": "No viable route"}

    update_shipment_route(new_route, new_eta, risk_score)

    rerouted = old_route != new_route
    if rerouted:
        update_shipment_status("rerouting")
        print(f"[RISK-LISTENER] [OK] REROUTED: {' -> '.join(old_route)} => {' -> '.join(new_route)}")
    else:
        print(f"[RISK-LISTENER] Route unchanged (already optimal): {' → '.join(new_route)}")

    return {
        "rerouted": rerouted,
        "old_route": old_route,
        "new_route": new_route,
        "new_eta": new_eta,
        "affected_city": affected_city,
    }


# ─── POLLING LOOP ──────────────────────────────────────────────────────────

async def risk_score_listener_loop():
    """
    Background async task that polls Firebase risk_score every 3 seconds.
    
    When risk_score crosses the 0.7 threshold (and we haven't already handled
    that exact value), triggers an automatic reroute.
    """
    global _last_handled_risk, _listener_running
    _listener_running = True
    _last_handled_risk = 0.0

    print("[RISK-LISTENER] Firebase risk_score poller started (every 3s)")

    while _listener_running:
        try:
            shipment = get_active_shipment()

            if not shipment:
                await asyncio.sleep(3)
                continue

            risk_score = shipment.get("risk_score", 0.0)
            
            # Ensure it's a float
            if isinstance(risk_score, (int, str)):
                risk_score = float(risk_score)

            # Check if this is a NEW high-risk event we haven't handled
            if risk_score > 0.7 and risk_score != _last_handled_risk:
                current_route = shipment.get("current_route", [])
                source = current_route[0] if current_route else "Lucknow"
                destination = current_route[-1] if current_route else "Delhi"

                affected_city = _detect_affected_city(current_route)

                if affected_city:
                    print(f"[RISK-LISTENER] [WARN] HIGH RISK DETECTED: {risk_score:.2f} "
                          f"(was {_last_handled_risk:.2f}). Auto-rerouting...")

                    result = reroute(source, destination, risk_score, affected_city)
                    _last_handled_risk = risk_score

                    if result.get("rerouted"):
                        print(f"[RISK-LISTENER] [OK] Auto-reroute complete!")
                    else:
                        print(f"[RISK-LISTENER] [INFO] Route already optimal, no change needed")
                else:
                    print(f"[RISK-LISTENER] [WARN] High risk ({risk_score:.2f}) but "
                          f"no intermediate city to reroute around")
                    _last_handled_risk = risk_score

            elif risk_score <= 0.3 and _last_handled_risk > 0.7:
                print(f"[RISK-LISTENER] [OK] Risk cleared ({risk_score:.2f}). Ready for next event.")
                _last_handled_risk = 0.0

        except Exception as e:
            print(f"[RISK-LISTENER] [ERROR] Error in polling loop: {e}")

        await asyncio.sleep(3)

    print("[RISK-LISTENER] [STOP] Firebase risk_score poller stopped")


def stop_listener():
    """Stop the risk listener polling loop."""
    global _listener_running
    _listener_running = False


def reset_listener_state():
    """Reset the listener's tracked state (for testing/demo resets)."""
    global _last_handled_risk
    _last_handled_risk = 0.0
    print("[RISK-LISTENER] State reset — ready for fresh events")
