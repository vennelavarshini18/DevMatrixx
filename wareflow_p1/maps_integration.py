"""
Task 3 — Google Maps Distance Matrix API Integration.

Provides real driving distances between a customer location and warehouse
coordinates using the Google Maps Distance Matrix API. Falls back to
Euclidean/Haversine distance if the API key is missing or the call fails.
"""

import os
import math
from typing import List, Tuple

import httpx


GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"


def haversine_km(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Calculate the Haversine distance between two lat/lng points in km.

    This is the geodesic fallback when the Google Maps API is unavailable.

    Args:
        coord1: (latitude, longitude) of point 1.
        coord2: (latitude, longitude) of point 2.

    Returns:
        Distance in kilometres.
    """
    R = 6371.0  # Earth's radius in km
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(R * c, 2)


async def get_real_distances(
    customer_coords: List[float],
    warehouse_coords_list: List[List[float]],
) -> List[float]:
    """Get driving distances from customer to each warehouse.

    Calls the Google Maps Distance Matrix API for accurate driving distances.
    Falls back gracefully to Haversine distance if the API key is missing
    or the request fails, ensuring the system never crashes.

    Args:
        customer_coords: [latitude, longitude] of the customer.
        warehouse_coords_list: List of [lat, lng] for each warehouse.

    Returns:
        List of distances in km, one per warehouse (same order as input).
    """
    api_key = GOOGLE_MAPS_API_KEY or os.environ.get("GOOGLE_MAPS_API_KEY", "")

    # --- Fallback path: no API key ---
    if not api_key:
        print("⚠️  GOOGLE_MAPS_API_KEY not set — using Haversine fallback")
        return [
            haversine_km(tuple(customer_coords), tuple(wh))
            for wh in warehouse_coords_list
        ]

    # --- API path ---
    origin = f"{customer_coords[0]},{customer_coords[1]}"
    destinations = "|".join(f"{wh[0]},{wh[1]}" for wh in warehouse_coords_list)

    params = {
        "origins": origin,
        "destinations": destinations,
        "key": api_key,
        "units": "metric",
        "mode": "driving",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(DISTANCE_MATRIX_URL, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("status") != "OK":
            raise ValueError(f"API returned status: {data.get('status')}")

        distances = []
        for element in data["rows"][0]["elements"]:
            if element["status"] == "OK":
                # Distance value is in meters → convert to km
                dist_km = round(element["distance"]["value"] / 1000.0, 2)
                distances.append(dist_km)
            else:
                # Individual element failed — use Haversine for that warehouse
                idx = len(distances)
                fallback = haversine_km(
                    tuple(customer_coords),
                    tuple(warehouse_coords_list[idx])
                )
                distances.append(fallback)
                print(f"⚠️  Element {idx} failed ({element['status']}), using Haversine: {fallback} km")

        print(f"🗺️  Google Maps distances: {distances} km")
        return distances

    except Exception as e:
        print(f"⚠️  Google Maps API failed: {e} — using Haversine fallback")
        return [
            haversine_km(tuple(customer_coords), tuple(wh))
            for wh in warehouse_coords_list
        ]
