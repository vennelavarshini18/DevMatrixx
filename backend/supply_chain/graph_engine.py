"""
WareFlow Supply Chain — Graph Routing Engine (Person 3)

Builds a NetworkX graph of 8 Indian city hubs connected by highway edges.
Provides Dijkstra shortest-path routing with dynamic risk-weighted rerouting
when Person 2's disruption predictor flags a weather event.

Usage:
    from graph_engine import calculate_optimal_route, CITY_COORDS, get_graph_info

    route, eta = calculate_optimal_route("Lucknow", "Delhi")
    route, eta = calculate_optimal_route("Lucknow", "Delhi", risk_score=0.85, affected_edge=("Agra", "Delhi"))
"""

import networkx as nx
from typing import Tuple, List, Optional, Dict, Any


# ─── CITY NODES WITH REAL COORDINATES ───────────────────────────────────────
# These lat/lng values are used by P4's Google Map to place markers.

CITY_COORDS: Dict[str, Dict[str, float]] = {
    "Lucknow":   {"lat": 26.8467, "lng": 80.9462},
    "Kanpur":    {"lat": 26.4499, "lng": 80.3319},
    "Agra":      {"lat": 27.1767, "lng": 78.0081},
    "Delhi":     {"lat": 28.6139, "lng": 77.2090},
    "Jaipur":    {"lat": 26.9124, "lng": 75.7873},
    "Varanasi":  {"lat": 25.3176, "lng": 82.9739},
    "Prayagraj": {"lat": 25.4358, "lng": 81.8463},
    "Gwalior":   {"lat": 26.2183, "lng": 78.1828},
}


# ─── HIGHWAY EDGES WITH BASE TRAVEL TIMES (HOURS) ──────────────────────────
# In production, P1 can replace these with Google Maps Routes API travel times.
# For the demo, static values are accurate enough (based on real driving data).

EDGES: List[Tuple[str, str, float]] = [
    ("Lucknow", "Kanpur",    1.5),   # NH-2, ~80km
    ("Lucknow", "Agra",      4.0),   # via Expressway, ~330km
    ("Lucknow", "Prayagraj", 3.5),   # NH-30, ~200km
    ("Kanpur",  "Agra",      3.5),   # NH-2, ~280km
    ("Kanpur",  "Prayagraj", 3.0),   # NH-2, ~195km
    ("Kanpur",  "Delhi",     5.5),   # NH-2 via Etawah, ~450km (longer highway)
    ("Agra",    "Delhi",     2.5),   # Yamuna Expressway, ~230km
    ("Agra",    "Gwalior",   2.0),   # NH-44, ~120km
    ("Agra",    "Jaipur",    4.0),   # NH-21, ~240km
    ("Gwalior", "Delhi",     3.0),   # NH-44 via Dholpur, ~320km
    ("Delhi",   "Jaipur",    4.5),   # NH-48, ~280km
    ("Prayagraj", "Varanasi", 2.5),  # NH-2, ~120km
]


# ─── BUILD THE GRAPH ────────────────────────────────────────────────────────

G = nx.Graph()

# Add nodes with coordinate attributes
for city, coords in CITY_COORDS.items():
    G.add_node(city, lat=coords["lat"], lng=coords["lng"])

# Add edges with base travel time weights
for src, dst, hours in EDGES:
    G.add_edge(src, dst, weight=hours)


# ─── CORE ROUTING FUNCTION ──────────────────────────────────────────────────

def calculate_optimal_route(
    source: str,
    destination: str,
    risk_score: float = 0.0,
    affected_edge: Optional[Tuple[str, str]] = None
) -> Tuple[List[str], float]:
    """
    Calculates the shortest path using Dijkstra's algorithm.
    
    If P2's disruption predictor reports a high risk_score (> 0.7),
    the affected highway edge gets penalized — its travel time is
    multiplied by (1 + risk_score). This forces Dijkstra to find
    an alternative route that avoids the dangerous segment.
    
    Args:
        source: Starting city name (e.g., "Lucknow")
        destination: Ending city name (e.g., "Delhi")
        risk_score: P2's disruption risk score (0.0 - 1.0)
        affected_edge: Tuple of (city_a, city_b) for the disrupted highway
        
    Returns:
        Tuple of (route_list, eta_hours)
        route_list: Ordered list of city names from source to destination
        eta_hours: Estimated travel time in hours
    """
    # Create a working copy — never mutate the base graph
    H = G.copy()

    # Apply risk penalty to the affected edge
    if risk_score > 0.7 and affected_edge:
        node_a, node_b = affected_edge
        if H.has_edge(node_a, node_b):
            original_weight = H[node_a][node_b]["weight"]
            penalty_multiplier = 1 + (2 * risk_score)  # Aggressive penalty for dramatic reroute
            H[node_a][node_b]["weight"] = original_weight * penalty_multiplier
            print(f"[GRAPH] Penalizing {node_a}↔{node_b}: "
                  f"{original_weight:.1f}h → {original_weight * penalty_multiplier:.1f}h "
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


# ─── INFO ENDPOINT HELPER ───────────────────────────────────────────────────

def get_graph_info() -> Dict[str, Any]:
    """
    Returns the full graph structure for P4's frontend to render.
    Includes all city nodes with coordinates and all edges with travel times.
    """
    nodes = []
    for city, coords in CITY_COORDS.items():
        nodes.append({
            "name": city,
            "lat": coords["lat"],
            "lng": coords["lng"]
        })

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
        "total_highways": len(edges)
    }


# ─── STANDALONE TEST ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  WareFlow Graph Engine — Standalone Test")
    print("=" * 60)

    # Test 1: Normal route
    route, eta = calculate_optimal_route("Lucknow", "Delhi")
    print(f"\n✅ Normal route: {' → '.join(route)}")
    print(f"   ETA: {eta} hours")

    # Test 2: Disrupted route (Agra→Delhi storm)
    route2, eta2 = calculate_optimal_route(
        "Lucknow", "Delhi",
        risk_score=0.85,
        affected_edge=("Agra", "Delhi")
    )
    print(f"\n⚠️  Rerouted (storm on Agra→Delhi): {' → '.join(route2)}")
    print(f"   ETA: {eta2} hours")

    # Test 3: Varanasi to Jaipur (long cross-country)
    route3, eta3 = calculate_optimal_route("Varanasi", "Jaipur")
    print(f"\n🗺️  Cross-country: {' → '.join(route3)}")
    print(f"   ETA: {eta3} hours")

    # Graph info
    info = get_graph_info()
    print(f"\n📊 Graph: {info['total_cities']} cities, {info['total_highways']} highways")
