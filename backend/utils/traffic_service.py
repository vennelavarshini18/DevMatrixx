"""
traffic_service.py
==================
Person 2 — Disruption Predictor: Google Maps Traffic Fetcher

Fetches real-time traffic congestion data from the Google Maps Routes API
for highway segments between WareFlow cities. Returns a congestion ratio
that measures how much slower traffic is compared to free-flow conditions.

Google Maps Routes API docs:
    https://developers.google.com/maps/documentation/routes

Environment Variables Required:
    GOOGLE_MAPS_API_KEY — Google Cloud API key with Routes API enabled

Usage:
    from utils.traffic_service import fetch_traffic_for_segment

    traffic = fetch_traffic_for_segment("Agra", "Delhi")
    # Returns: {"congestion_ratio": 1.8, "duration_seconds": 7200, ...}
"""

import os
import requests
from typing import Dict, Optional, Tuple

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")

# Google Maps Routes API endpoint
ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

# City coordinates for Google Maps lookups
CITY_COORDS = {
    "Lucknow":       (26.8467, 80.9462),
    "Agra":          (27.1767, 78.0081),
    "Delhi":         (28.6139, 77.2090),
    "Kanpur":        (26.4499, 80.3319),
    "Jaipur":        (26.9124, 75.7873),
    "Gwalior":       (26.2183, 78.1828),
    "Varanasi":      (25.3176, 82.9739),
    "Prayagraj":     (25.4358, 81.8463),
    "Patna":         (25.6093, 85.1376),
    "Bhopal":        (23.2599, 77.4126),
    "Indore":        (22.7196, 75.8577),
    "Nagpur":        (21.1458, 79.0882),
    "Mumbai":        (19.0760, 72.8777),
    "Pune":          (18.5204, 73.8567),
    "Hyderabad":     (17.3850, 78.4867),
    "Bangalore":     (12.9716, 77.5946),
    "Chennai":       (13.0827, 80.2707),
    "Kolkata":       (22.5726, 88.3639),
    "Ahmedabad":     (23.0225, 72.5714),
    "Surat":         (21.1702, 72.8311),
    "Nashik":        (19.9975, 73.7898),
    "Visakhapatnam": (17.6868, 83.2185),
}


def _parse_duration(duration_str: str) -> int:
    """Parse Google Maps duration string like '7200s' to integer seconds."""
    if not duration_str:
        return 0
    return int(duration_str.rstrip("s"))


def fetch_traffic_for_segment(
    origin_city: str,
    dest_city: str,
) -> Dict:
    """
    Fetch real-time traffic data from Google Maps Routes API for a highway segment.

    Uses the Routes API computeRoutes endpoint with TRAFFIC_AWARE routing
    to get both the static (no-traffic) duration and the live duration.

    The congestion_ratio = duration / staticDuration:
        1.0  = free flow (no congestion)
        1.5  = moderate congestion (50% slower)
        2.0+ = severe congestion (double or more travel time)

    Args:
        origin_city: Name of the origin city (must be in CITY_COORDS)
        dest_city: Name of the destination city (must be in CITY_COORDS)

    Returns:
        Dict with:
            - congestion_ratio: float (1.0 = free flow, higher = worse)
            - duration_seconds: int (actual travel time with traffic)
            - static_duration_seconds: int (travel time without traffic)
            - segment: str (e.g. "Agra → Delhi")
            - source: str ("google_maps" or "fallback")
    """
    api_key = GOOGLE_MAPS_API_KEY or os.environ.get("GOOGLE_MAPS_API_KEY", "")
    origin_coords = CITY_COORDS.get(origin_city)
    dest_coords = CITY_COORDS.get(dest_city)

    if not origin_coords or not dest_coords:
        print(f"[TRAFFIC] Unknown city pair: {origin_city} → {dest_city}")
        return _fallback_result(origin_city, dest_city)

    if not api_key:
        print("[TRAFFIC] GOOGLE_MAPS_API_KEY not set — using fallback (no congestion)")
        return _fallback_result(origin_city, dest_city)

    # Build the Routes API request
    payload = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": origin_coords[0],
                    "longitude": origin_coords[1],
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": dest_coords[0],
                    "longitude": dest_coords[1],
                }
            }
        },
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters",
    }

    try:
        resp = requests.post(ROUTES_API_URL, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        routes = data.get("routes", [])
        if not routes:
            print(f"[TRAFFIC] No routes returned for {origin_city} → {dest_city}")
            return _fallback_result(origin_city, dest_city)

        route = routes[0]
        duration = _parse_duration(route.get("duration", "0s"))
        static_duration = _parse_duration(route.get("staticDuration", "0s"))
        distance_m = route.get("distanceMeters", 0)

        # Calculate congestion ratio
        if static_duration > 0:
            congestion_ratio = duration / static_duration
        else:
            congestion_ratio = 1.0

        congestion_ratio = max(1.0, congestion_ratio)  # Never below 1.0

        print(f"[TRAFFIC] {origin_city} → {dest_city}: "
              f"duration={duration}s, static={static_duration}s, "
              f"congestion={congestion_ratio:.2f}x, distance={distance_m/1000:.0f}km")

        return {
            "congestion_ratio": round(congestion_ratio, 2),
            "duration_seconds": duration,
            "static_duration_seconds": static_duration,
            "distance_km": round(distance_m / 1000, 1),
            "segment": f"{origin_city} → {dest_city}",
            "source": "google_maps",
        }

    except requests.RequestException as e:
        print(f"[TRAFFIC] Google Maps Routes API error: {e}")
        return _fallback_result(origin_city, dest_city)
    except Exception as e:
        print(f"[TRAFFIC] Unexpected error: {e}")
        return _fallback_result(origin_city, dest_city)


def _fallback_result(origin: str, dest: str) -> Dict:
    """Return a neutral fallback when the API is unavailable."""
    return {
        "congestion_ratio": 1.0,
        "duration_seconds": 0,
        "static_duration_seconds": 0,
        "distance_km": 0,
        "segment": f"{origin} → {dest}",
        "source": "fallback",
    }


def fetch_traffic_for_city(city: str) -> Dict:
    """
    Check traffic on all highway segments touching a city.
    Returns the WORST (highest) congestion ratio among all segments.

    This is used by the DisruptionCard to assess overall traffic risk
    at a specific city on the active route.
    """
    # Known highway connections for each city (subset — main corridors)
    CITY_CONNECTIONS = {
        "Delhi":     ["Agra", "Jaipur", "Lucknow", "Gwalior"],
        "Lucknow":   ["Kanpur", "Agra", "Delhi", "Varanasi"],
        "Agra":      ["Delhi", "Lucknow", "Jaipur", "Gwalior"],
        "Kanpur":    ["Lucknow", "Agra", "Delhi"],
        "Jaipur":    ["Delhi", "Agra", "Ahmedabad"],
        "Mumbai":    ["Pune", "Ahmedabad", "Nashik"],
        "Pune":      ["Mumbai", "Hyderabad", "Bangalore"],
        "Bangalore": ["Pune", "Hyderabad", "Chennai"],
        "Hyderabad": ["Nagpur", "Pune", "Bangalore", "Chennai"],
        "Chennai":   ["Hyderabad", "Bangalore"],
        "Kolkata":   ["Patna", "Nagpur"],
        "Patna":     ["Kolkata", "Varanasi", "Lucknow"],
        "Varanasi":  ["Lucknow", "Patna", "Prayagraj"],
        "Nagpur":    ["Hyderabad", "Bhopal", "Kolkata"],
        "Ahmedabad": ["Jaipur", "Mumbai", "Surat"],
        "Gwalior":   ["Delhi", "Agra", "Bhopal"],
        "Bhopal":    ["Gwalior", "Indore", "Nagpur"],
        "Indore":    ["Bhopal", "Ahmedabad"],
        "Surat":     ["Ahmedabad", "Mumbai"],
        "Nashik":    ["Mumbai", "Pune"],
        "Prayagraj": ["Varanasi", "Lucknow", "Kanpur"],
        "Visakhapatnam": ["Hyderabad", "Kolkata", "Chennai"],
    }

    neighbors = CITY_CONNECTIONS.get(city, [])
    if not neighbors:
        return _fallback_result(city, "Unknown")

    # Check the first 2 connections to limit API calls
    worst = _fallback_result(city, neighbors[0])
    for neighbor in neighbors[:2]:
        result = fetch_traffic_for_segment(city, neighbor)
        if result["congestion_ratio"] > worst["congestion_ratio"]:
            worst = result

    return worst
