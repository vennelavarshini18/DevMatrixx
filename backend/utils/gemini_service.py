"""
gemini_service.py
=================
Person 2 — Disruption Predictor: Gemini Alert Generator

Uses Google Gemini to generate professional, logistics-grade natural language
alerts when the LightGBM model detects disruption risk > 0.7.

The prompt is engineered to produce actionable intelligence that Person 3
(Route Optimizer) and Person 4 (Dashboard) can consume immediately.

Environment Variables Required:
    GEMINI_API_KEY  — Google AI Studio API key

Usage:
    from utils.gemini_service import generate_disruption_alert

    alert = generate_disruption_alert(
        city="Agra",
        risk_score=0.85,
        precipitation_mm=72.3,
        wind_speed_kmh=88.0,
        base_travel_time=4.0,
    )
"""

import os
from typing import Optional

# ── Attempt Gemini import ────────────────────────────────────────────────
_GEMINI_AVAILABLE = False

try:
    import google.generativeai as genai
    _GEMINI_AVAILABLE = True
except ImportError:
    pass


def _get_gemini_model():
    """Initialize and return Gemini model. Returns None if unavailable."""
    if not _GEMINI_AVAILABLE:
        print("[GEMINI] google-generativeai not installed. Using fallback alerts.")
        return None

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[GEMINI] GEMINI_API_KEY not set. Using fallback alerts.")
        return None

    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def generate_disruption_alert(
    city: str,
    risk_score: float,
    precipitation_mm: float,
    wind_speed_kmh: float,
    base_travel_time: float,
    source: str = "Lucknow",
    destination: str = "Delhi",
    traffic_congestion_ratio: float = 1.0,
) -> str:
    """
    Generate a professional logistics disruption alert using Google Gemini.

    If Gemini is unavailable (no API key or package not installed), returns
    a deterministic fallback alert with the same data so the pipeline
    never breaks.

    Args:
        city: City where the disruption is detected (e.g. "Agra")
        risk_score: LightGBM predicted risk score (0.0 - 1.0)
        precipitation_mm: Current precipitation in mm
        wind_speed_kmh: Current wind speed in km/h
        base_travel_time: Base travel time on the affected segment (hours)
        source: Shipment origin city
        destination: Shipment destination city
        traffic_congestion_ratio: Traffic congestion multiplier (1.0 = normal)

    Returns:
        A professional alert string for Firebase / dashboard display.
    """
    # Determine severity tier
    if risk_score >= 0.8:
        severity = "CRITICAL"
        urgency = "Immediate reroute required"
    elif risk_score >= 0.7:
        severity = "HIGH"
        urgency = "Reroute strongly recommended"
    else:
        severity = "MODERATE"
        urgency = "Monitor closely"

    # Determine weather and traffic cause
    causes = []
    if precipitation_mm > 50:
        causes.append(f"{precipitation_mm:.1f}mm rainfall (heavy)")
    elif precipitation_mm > 20:
        causes.append(f"{precipitation_mm:.1f}mm rainfall (moderate)")
    if wind_speed_kmh > 60:
        causes.append(f"{wind_speed_kmh:.1f} km/h winds (dangerous)")
    elif wind_speed_kmh > 40:
        causes.append(f"{wind_speed_kmh:.1f} km/h winds (elevated)")
    if traffic_congestion_ratio > 2.0:
        causes.append(f"{traffic_congestion_ratio:.1f}x severe traffic congestion on {source}–{destination} segment")
    elif traffic_congestion_ratio > 1.3:
        causes.append(f"{traffic_congestion_ratio:.1f}x traffic congestion on {source}–{destination} segment")
        
    cause_text = " and ".join(causes) if causes else "adverse conditions"

    # Estimated delay
    delay_hours = round(base_travel_time * risk_score, 1)

    # ── Try Gemini first ─────────────────────────────────────────────────
    model = _get_gemini_model()

    if model:
        prompt = f"""You are WareFlow Disruption Intelligence, an AI logistics risk analyst.

Generate a concise, professional supply chain disruption alert (2-3 sentences max).

CONTEXT:
- Shipment route: {source} to {destination}
- Disruption location: {city}
- Severity: {severity} (Risk Score: {risk_score:.2f})
- Weather cause: {cause_text}
- Estimated delay if no action taken: {delay_hours} hours
- Action required: {urgency}

RULES:
- Start with "WARNING:" or "CRITICAL:" based on severity
- Include the city name and specific weather cause
- State the risk score as a percentage
- Recommend immediate reroute if risk > 0.7
- End with estimated delay impact
- Be direct and actionable — this is a real-time logistics alert, not a weather report
- Do NOT use emojis or markdown formatting
- Keep it under 60 words"""

        try:
            response = model.generate_content(prompt)
            alert_text = response.text.strip()
            # Sanitize: remove any markdown artifacts Gemini might add
            alert_text = alert_text.replace("**", "").replace("*", "").replace("#", "")
            return alert_text
        except Exception as e:
            print(f"[GEMINI] API call failed: {e}. Using fallback.")

    # ── Deterministic fallback ───────────────────────────────────────────
    return (
        f"{severity}: {city} is experiencing {cause_text}. "
        f"Risk score {risk_score:.0%} detected on the {source}-{destination} corridor. "
        f"{urgency} to avoid an estimated {delay_hours}-hour delay."
    )
