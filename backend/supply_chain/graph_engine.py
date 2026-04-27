"""
WareFlow Supply Chain — Graph Routing Engine (Expanded)

Builds a NetworkX graph of 22 Indian city hubs connected by 50+ highway edges.
Provides Dijkstra shortest-path routing with dynamic risk-weighted rerouting
when Person 2's disruption predictor flags a weather event.

NEW: Includes warehouse selection via Dijkstra — finds the best warehouse
for a customer based on distance, risk, queue depth, and stock.

Usage:
    from graph_engine import calculate_optimal_route, find_best_warehouse, get_graph_info
"""

import math
import networkx as nx
from typing import Tuple, List, Optional, Dict, Any

# Import centralized data
import sys, os
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from central_data import CITY_COORDS, HIGHWAY_EDGES, WAREHOUSES


# ─── BUILD THE GRAPH ────────────────────────────────────────────────────────

G = nx.Graph()

# Add nodes with coordinate attributes
for city, coords in CITY_COORDS.items():
    G.add_node(city, lat=coords["lat"], lng=coords["lng"])

# Add edges with base travel time weights
for src, dst, hours in HIGHWAY_EDGES:
    # NetworkX handles undirected graphs — skip duplicate edges gracefully
    if not G.has_edge(src, dst):
        G.add_edge(src, dst, weight=hours)

print(f"[GRAPH] Built graph: {G.number_of_nodes()} cities, {G.number_of_edges()} highways")


# ─── HAVERSINE DISTANCE ────────────────────────────────────────────────────

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the Haversine distance between two lat/lng points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _find_nearest_city(lat: float, lng: float) -> str:
    """Find the nearest city in the graph to a given coordinate."""
    best_city = None
    best_dist = float("inf")
    for city, coords in CITY_COORDS.items():
        d = _haversine_km(lat, lng, coords["lat"], coords["lng"])
        if d < best_dist:
            best_dist = d
            best_city = city
    return best_city


# ─── CORE ROUTING FUNCTION ──────────────────────────────────────────────────

def calculate_optimal_route(
    source: str,
    destination: str,
    risk_score: float = 0.0,
    affected_edge: Optional[Tuple[str, str]] = None,
    affected_city: Optional[str] = None
) -> Tuple[List[str], float]:
    """
    Calculates the shortest path using Dijkstra's algorithm.
    
    If P2's disruption predictor reports a high risk_score (> 0.7),
    we penalize highway edges to force Dijkstra to find an alternative.
    We can penalize either a specific edge or all edges touching a city.
    
    Args:
        source: Starting city name (e.g., "Lucknow")
        destination: Ending city name (e.g., "Delhi")
        risk_score: P2's disruption risk score (0.0 - 1.0)
        affected_edge: Tuple of (city_a, city_b) for a specific disrupted highway
        affected_city: Name of a city where ALL incident highways are disrupted
        
    Returns:
        Tuple of (route_list, eta_hours)
    """
    # Create a working copy — never mutate the base graph
    H = G.copy()

    # Apply risk penalty to the affected city (dramatic reroute)
    if risk_score > 0.7 and affected_city:
        if H.has_node(affected_city):
            # Penalize all edges connected to this city
            for u, v in H.edges(affected_city):
                original_weight = H[u][v]["weight"]
                penalty_multiplier = 1 + (3 * risk_score)  # Extra aggressive for city-wide storm
                H[u][v]["weight"] = original_weight * penalty_multiplier
                print(f"[GRAPH] Penalizing city edge {u}<->{v}: "
                      f"{original_weight:.1f}h -> {H[u][v]['weight']:.1f}h "
                      f"(risk={risk_score:.2f})")

    # Apply risk penalty to a specific affected edge (legacy/granular)
    elif risk_score > 0.7 and affected_edge:
        node_a, node_b = affected_edge
        if H.has_edge(node_a, node_b):
            original_weight = H[node_a][node_b]["weight"]
            penalty_multiplier = 1 + (2 * risk_score)
            H[node_a][node_b]["weight"] = original_weight * penalty_multiplier
            print(f"[GRAPH] Penalizing specific edge {node_a}<->{node_b}: "
                  f"{original_weight:.1f}h -> {H[node_a][node_b]['weight']:.1f}h "
                  f"(risk={risk_score:.2f})")

    try:
        route = nx.dijkstra_path(H, source=source, target=destination, weight="weight")
        eta = nx.dijkstra_path_length(H, source=source, target=destination, weight="weight")
        return route, round(eta, 1)
    except nx.NetworkXNoPath:
        print(f"[GRAPH] No path found from {source} to {destination}")
        return [], 0.0
    except nx.NodeNotFound as e:
        print(f"[GRAPH] City not found in graph: {e}")
        return [], 0.0


# ─── WAREHOUSE SELECTION (DIJKSTRA + DISRUPTOR) ────────────────────────────

def find_best_warehouse(
    customer_coords: List[float],
    category: str = "",
    risk_scores: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Find the best warehouse for a customer using Dijkstra + disruptor model.
    
    Scoring formula per warehouse:
        score = dijkstra_distance_hours + (queue_penalty * queue_depth) + risk_penalty
    
    Checks:
        1. Distance via Dijkstra from nearest city to warehouse city
        2. Risk factors on the route (disruptor model — penalized edges)
        3. Queue depth at the warehouse
        4. Stock availability for the requested category
    
    Args:
        customer_coords: [lat, lng] of the customer
        category: Product category to check stock for (optional)
        risk_scores: Dict of {city_name: risk_score} for penalized cities
        
    Returns:
        Dict with warehouse_id, route, eta, score, alternatives
    """
    customer_lat, customer_lng = customer_coords
    nearest_city = _find_nearest_city(customer_lat, customer_lng)
    
    QUEUE_PENALTY = 0.5  # hours per pending order
    
    results = []
    
    for wh_id, wh in WAREHOUSES.items():
        wh_city = wh["city"]
        
        # Skip if out of stock for the requested category
        if category and wh.get("inventory", {}).get(category, 0) <= 0:
            continue
        
        # Calculate Dijkstra route from nearest city to warehouse city
        # Then from warehouse city to nearest city (delivery route)
        try:
            # Create a risk-weighted copy if we have risk data
            if risk_scores:
                H = G.copy()
                for city, rscore in risk_scores.items():
                    if rscore > 0.4 and H.has_node(city):
                        for u, v in H.edges(city):
                            H[u][v]["weight"] = H[u][v]["weight"] * (1 + 2 * rscore)
                delivery_route = nx.dijkstra_path(H, source=wh_city, target=nearest_city, weight="weight")
                delivery_eta = nx.dijkstra_path_length(H, source=wh_city, target=nearest_city, weight="weight")
            else:
                delivery_route = nx.dijkstra_path(G, source=wh_city, target=nearest_city, weight="weight")
                delivery_eta = nx.dijkstra_path_length(G, source=wh_city, target=nearest_city, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
        
        # Add last-mile estimate (nearest city → customer door)
        city_coords = CITY_COORDS[nearest_city]
        last_mile_km = _haversine_km(
            customer_lat, customer_lng,
            city_coords["lat"], city_coords["lng"]
        )
        last_mile_hours = last_mile_km / 40.0  # 40 km/h average for last mile
        
        # Total score: delivery time + queue wait + last mile
        queue_depth = wh["pending"]
        total_eta = delivery_eta + last_mile_hours + (queue_depth * QUEUE_PENALTY)
        
        results.append({
            "warehouse_id": wh_id,
            "warehouse_city": wh_city,
            "delivery_route": delivery_route,
            "delivery_eta_hours": round(delivery_eta, 1),
            "last_mile_hours": round(last_mile_hours, 1),
            "queue_depth": queue_depth,
            "total_score": round(total_eta, 1),
            "stock": wh.get("inventory", {}).get(category, 0) if category else -1,
        })
    
    if not results:
        return {"error": "No warehouse available for this order"}
    
    # Sort by total score (lower is better)
    results.sort(key=lambda x: x["total_score"])
    
    best = results[0]
    return {
        "warehouse_id": best["warehouse_id"],
        "warehouse_city": best["warehouse_city"],
        "route": best["delivery_route"],
        "eta_hours": best["delivery_eta_hours"],
        "last_mile_hours": best["last_mile_hours"],
        "total_eta": best["total_score"],
        "queue_depth": best["queue_depth"],
        "nearest_customer_city": nearest_city,
        "stock": best["stock"],
        "alternatives": results[1:4],  # Top 3 alternatives
    }


def calculate_delivery_route(
    warehouse_city: str,
    customer_coords: List[float],
    risk_scores: Optional[Dict[str, float]] = None,
) -> Tuple[List[str], float]:
    """
    Calculate the delivery route from warehouse to customer's nearest city.
    Uses Dijkstra + risk-weighted edges (disruptor model).
    
    Returns: (route, eta_hours)
    """
    customer_lat, customer_lng = customer_coords
    nearest_city = _find_nearest_city(customer_lat, customer_lng)
    
    if warehouse_city == nearest_city:
        return [warehouse_city], 0.5  # Same city — just last-mile delivery
    
    # Apply risk penalties if available
    H = G.copy()
    if risk_scores:
        for city, rscore in risk_scores.items():
            if rscore > 0.4 and H.has_node(city):
                for u, v in H.edges(city):
                    H[u][v]["weight"] = H[u][v]["weight"] * (1 + 2 * rscore)
    
    try:
        route = nx.dijkstra_path(H, source=warehouse_city, target=nearest_city, weight="weight")
        eta = nx.dijkstra_path_length(H, source=warehouse_city, target=nearest_city, weight="weight")
        return route, round(eta, 1)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return [warehouse_city], 0.0


# ─── INFO ENDPOINT HELPER ───────────────────────────────────────────────────

def get_graph_info() -> Dict[str, Any]:
    """
    Returns the full graph structure for P4's frontend to render.
    Includes all city nodes with coordinates and all edges with travel times.
    Also flags which cities are warehouse cities.
    """
    nodes = []
    for city, coords in CITY_COORDS.items():
        wh_id = city.lower()
        is_warehouse = wh_id in WAREHOUSES
        node = {
            "name": city,
            "lat": coords["lat"],
            "lng": coords["lng"],
            "is_warehouse": is_warehouse,
        }
        if is_warehouse:
            node["pending"] = WAREHOUSES[wh_id]["pending"]
        nodes.append(node)

    edges = []
    for src, dst, data in G.edges(data=True):
        edges.append({
            "from": src,
            "to": dst,
            "hours": data["weight"]
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "total_cities": len(nodes),
        "total_highways": len(edges),
        "total_warehouses": sum(1 for n in nodes if n["is_warehouse"]),
    }


# ─── STANDALONE TEST ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  WareFlow Graph Engine — Standalone Test")
    print("=" * 60)

    # Test 1: Normal route
    route, eta = calculate_optimal_route("Lucknow", "Delhi")
    print(f"\n[OK] Normal route: {' -> '.join(route)}")
    print(f"   ETA: {eta} hours")

    # Test 2: Disrupted route (Agra->Delhi storm)
    route2, eta2 = calculate_optimal_route(
        "Lucknow", "Delhi",
        risk_score=0.85,
        affected_edge=("Agra", "Delhi")
    )
    print(f"\n[WARNING] Rerouted (storm on Agra->Delhi): {' -> '.join(route2)}")
    print(f"   ETA: {eta2} hours")

    # Test 3: Long cross-country route
    route3, eta3 = calculate_optimal_route("Chennai", "Delhi")
    print(f"\n[MAP] Cross-country: {' -> '.join(route3)}")
    print(f"   ETA: {eta3} hours")

    # Test 4: Mumbai to Kolkata
    route4, eta4 = calculate_optimal_route("Mumbai", "Kolkata")
    print(f"\n[MAP] Mumbai-Kolkata: {' -> '.join(route4)}")
    print(f"   ETA: {eta4} hours")

    # Test 5: Warehouse selection
    print("\n--- Warehouse Selection Test ---")
    result = find_best_warehouse([27.1, 78.0], category="electronics")
    print(f"Best warehouse: {result['warehouse_id']} ({result['warehouse_city']})")
    print(f"Route: {' -> '.join(result['route'])}")
    print(f"ETA: {result['eta_hours']}h (+ {result['last_mile_hours']}h last mile)")
    print(f"Total score: {result['total_eta']}")
    if result.get("alternatives"):
        print(f"Alternatives: {[a['warehouse_id'] for a in result['alternatives']]}")

    # Graph info
    info = get_graph_info()
    print(f"\n[GRAPH] Graph: {info['total_cities']} cities, {info['total_highways']} highways, {info['total_warehouses']} warehouses")
