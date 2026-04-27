"""
weather_service.py
==================
Person 2 — Disruption Predictor: Live Weather Fetcher

Fetches real-time weather data from Open-Meteo (free, no API key required)
for a given set of coordinates. Returns precipitation and wind speed that
are fed into the LightGBM disruption predictor.

Open-Meteo docs: https://open-meteo.com/en/docs

Usage:
    from utils.weather_service import fetch_live_weather

    weather = fetch_live_weather(lat=27.1767, lng=78.0081)
    # Returns: {"precipitation_mm": 12.3, "wind_speed_kmh": 45.6}
"""

import requests
from typing import Dict, Optional

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_live_weather(lat: float, lng: float) -> Dict[str, float]:
    """
    Fetch current weather conditions from Open-Meteo.

    Args:
        lat: Latitude of the location
        lng: Longitude of the location

    Returns:
        Dictionary with:
            - precipitation_mm: Current precipitation (mm)
            - wind_speed_kmh: Current wind speed (km/h)
    """
    params = {
        "latitude": lat,
        "longitude": lng,
        "current_weather": "true",
        "hourly": "precipitation",
        "forecast_days": 1,
    }

    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current_weather", {})
        wind_speed = current.get("windspeed", 0.0)

        # Get the most recent hourly precipitation value
        hourly = data.get("hourly", {})
        precip_values = hourly.get("precipitation", [0.0])
        # Use the first non-zero value, or the latest value
        precipitation = precip_values[0] if precip_values else 0.0

        return {
            "precipitation_mm": float(precipitation),
            "wind_speed_kmh": float(wind_speed),
        }

    except requests.RequestException as e:
        print(f"[WEATHER] Open-Meteo API error: {e}")
        return {
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 0.0,
        }


def fetch_weather_for_city(city_name: str) -> Dict[str, float]:
    """
    Convenience wrapper that maps known WareFlow city names to coordinates
    and fetches weather. Uses the same coordinate data as Person 3's graph engine.
    """
    CITY_COORDS = {
        "Lucknow":   (26.8467, 80.9462),
        "Kanpur":    (26.4499, 80.3319),
        "Agra":      (27.1767, 78.0081),
        "Delhi":     (28.6139, 77.2090),
        "Jaipur":    (26.9124, 75.7873),
        "Varanasi":  (25.3176, 82.9739),
        "Prayagraj": (25.4358, 81.8463),
        "Gwalior":   (26.2183, 78.1828),
    }

    coords = CITY_COORDS.get(city_name)
    if not coords:
        print(f"[WEATHER] Unknown city: {city_name}. Returning zeroes.")
        return {"precipitation_mm": 0.0, "wind_speed_kmh": 0.0}

    return fetch_live_weather(lat=coords[0], lng=coords[1])
