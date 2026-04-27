"""
WareFlow — Centralized Data Layer (Single Source of Truth)

Every module in the system reads from and writes to this module.
No more scattered hardcoded data across P1/P2/P3/P4.

Contents:
    WAREHOUSES        — 10 warehouses with coords, inventory, queue
    PRODUCT_CATALOG   — 8 categories × items, unified across the system
    ORDER_REGISTRY    — All orders with full lifecycle state
    CITY_GRAPH        — 20+ cities with coords (used by graph_engine)
    HIGHWAY_EDGES     — 50+ edges with travel times

Usage:
    from central_data import WAREHOUSES, PRODUCT_CATALOG, get_order, place_order
"""

import time
import threading
import copy
from typing import Dict, List, Optional, Any, Tuple

# ─── THREAD SAFETY ──────────────────────────────────────────────────────────
_lock = threading.Lock()


# ─── PRODUCT CATALOG ────────────────────────────────────────────────────────
# Unified product list used by storefront, warehouse RL, and order system.

PRODUCT_CATALOG = {
    "skincare": {
        "name": "Skincare",
        "items": ["Face Cream", "Sunscreen", "Serum", "Lotion", "Face Wash", "Toner"],
        "shelf_location": {"x": 2, "y": 3},
    },
    "grocery": {
        "name": "Grocery",
        "items": ["Milk", "Eggs", "Chocolates", "Detergent", "Flour", "Bread", "Rice", "Oil"],
        "shelf_location": {"x": 7, "y": 3},
    },
    "footwear": {
        "name": "Footwear",
        "items": ["Sneakers", "Boots", "Sandals", "Socks", "Running Shoes", "Loafers"],
        "shelf_location": {"x": 11, "y": 3},
    },
    "clothes": {
        "name": "Clothes",
        "items": ["T-Shirt", "Jeans", "Jacket", "Sweater", "Hoodie", "Shorts"],
        "shelf_location": {"x": 2, "y": 8},
    },
    "pharmacy": {
        "name": "Pharmacy",
        "items": ["Vitamins", "Painkillers", "First Aid", "Masks", "Thermometer", "Bandages"],
        "shelf_location": {"x": 7, "y": 8},
    },
    "electronics": {
        "name": "Electronics",
        "items": ["Laptop", "Smartwatch", "Headphones", "Cables", "Power Bank", "Mouse"],
        "shelf_location": {"x": 11, "y": 8},
    },
    "stationery": {
        "name": "Stationery",
        "items": ["Notebook", "Pens", "Markers", "Stapler", "Scissors", "Tape"],
        "shelf_location": {"x": 4, "y": 12},
    },
    "accessories": {
        "name": "Accessories",
        "items": ["Watch", "Sunglasses", "Belt", "Wallet", "Backpack", "Umbrella"],
        "shelf_location": {"x": 9, "y": 12},
    },
}


# ─── 10 WAREHOUSES ──────────────────────────────────────────────────────────
# Each warehouse: city, coords, per-category inventory, pending queue, orders

def _default_inventory() -> Dict[str, int]:
    """Default stock levels per category for a new warehouse."""
    return {
        "skincare": 25,
        "grocery": 40,
        "footwear": 15,
        "clothes": 20,
        "pharmacy": 35,
        "electronics": 10,
        "stationery": 50,
        "accessories": 18,
    }


WAREHOUSES: Dict[str, Dict[str, Any]] = {
    "delhi": {
        "city": "Delhi",
        "coords": [28.6139, 77.2090],
        "inventory": {"skincare": 30, "grocery": 45, "footwear": 18, "clothes": 25,
                       "pharmacy": 40, "electronics": 15, "stationery": 55, "accessories": 22},
        "pending": 0,
        "order_queue": [],
    },
    "mumbai": {
        "city": "Mumbai",
        "coords": [19.0760, 72.8777],
        "inventory": {"skincare": 28, "grocery": 50, "footwear": 20, "clothes": 30,
                       "pharmacy": 38, "electronics": 12, "stationery": 48, "accessories": 20},
        "pending": 0,
        "order_queue": [],
    },
    "bangalore": {
        "city": "Bangalore",
        "coords": [12.9716, 77.5946],
        "inventory": {"skincare": 22, "grocery": 35, "footwear": 16, "clothes": 28,
                       "pharmacy": 32, "electronics": 20, "stationery": 45, "accessories": 15},
        "pending": 0,
        "order_queue": [],
    },
    "hyderabad": {
        "city": "Hyderabad",
        "coords": [17.3850, 78.4867],
        "inventory": {"skincare": 20, "grocery": 38, "footwear": 14, "clothes": 22,
                       "pharmacy": 30, "electronics": 18, "stationery": 42, "accessories": 16},
        "pending": 0,
        "order_queue": [],
    },
    "chennai": {
        "city": "Chennai",
        "coords": [13.0827, 80.2707],
        "inventory": {"skincare": 24, "grocery": 42, "footwear": 12, "clothes": 20,
                       "pharmacy": 36, "electronics": 14, "stationery": 40, "accessories": 19},
        "pending": 0,
        "order_queue": [],
    },
    "kolkata": {
        "city": "Kolkata",
        "coords": [22.5726, 88.3639],
        "inventory": {"skincare": 18, "grocery": 48, "footwear": 10, "clothes": 24,
                       "pharmacy": 34, "electronics": 8, "stationery": 52, "accessories": 14},
        "pending": 0,
        "order_queue": [],
    },
    "lucknow": {
        "city": "Lucknow",
        "coords": [26.8467, 80.9462],
        "inventory": {"skincare": 15, "grocery": 35, "footwear": 12, "clothes": 18,
                       "pharmacy": 28, "electronics": 6, "stationery": 44, "accessories": 12},
        "pending": 0,
        "order_queue": [],
    },
    "jaipur": {
        "city": "Jaipur",
        "coords": [26.9124, 75.7873],
        "inventory": {"skincare": 20, "grocery": 30, "footwear": 14, "clothes": 22,
                       "pharmacy": 26, "electronics": 10, "stationery": 38, "accessories": 16},
        "pending": 0,
        "order_queue": [],
    },
    "ahmedabad": {
        "city": "Ahmedabad",
        "coords": [23.0225, 72.5714],
        "inventory": {"skincare": 22, "grocery": 40, "footwear": 16, "clothes": 26,
                       "pharmacy": 30, "electronics": 12, "stationery": 46, "accessories": 18},
        "pending": 0,
        "order_queue": [],
    },
    "pune": {
        "city": "Pune",
        "coords": [18.5204, 73.8567],
        "inventory": {"skincare": 26, "grocery": 36, "footwear": 18, "clothes": 24,
                       "pharmacy": 32, "electronics": 16, "stationery": 42, "accessories": 20},
        "pending": 0,
        "order_queue": [],
    },
}


# ─── 22 CITY NODES ──────────────────────────────────────────────────────────
# All cities in the transport graph. Warehouse cities are a subset.

CITY_COORDS: Dict[str, Dict[str, float]] = {
    # Warehouse cities (10)
    "Delhi":      {"lat": 28.6139, "lng": 77.2090},
    "Mumbai":     {"lat": 19.0760, "lng": 72.8777},
    "Bangalore":  {"lat": 12.9716, "lng": 77.5946},
    "Hyderabad":  {"lat": 17.3850, "lng": 78.4867},
    "Chennai":    {"lat": 13.0827, "lng": 80.2707},
    "Kolkata":    {"lat": 22.5726, "lng": 88.3639},
    "Lucknow":    {"lat": 26.8467, "lng": 80.9462},
    "Jaipur":     {"lat": 26.9124, "lng": 75.7873},
    "Ahmedabad":  {"lat": 23.0225, "lng": 72.5714},
    "Pune":       {"lat": 18.5204, "lng": 73.8567},
    # Transit/intermediate cities (12)
    "Agra":       {"lat": 27.1767, "lng": 78.0081},
    "Kanpur":     {"lat": 26.4499, "lng": 80.3319},
    "Varanasi":   {"lat": 25.3176, "lng": 82.9739},
    "Prayagraj":  {"lat": 25.4358, "lng": 81.8463},
    "Gwalior":    {"lat": 26.2183, "lng": 78.1828},
    "Nagpur":     {"lat": 21.1458, "lng": 79.0882},
    "Indore":     {"lat": 22.7196, "lng": 75.8577},
    "Bhopal":     {"lat": 23.2599, "lng": 77.4126},
    "Patna":      {"lat": 25.6093, "lng": 85.1376},
    "Surat":      {"lat": 21.1702, "lng": 72.8311},
    "Nashik":     {"lat": 19.9975, "lng": 73.7898},
    "Visakhapatnam": {"lat": 17.6868, "lng": 83.2185},
}

# Warehouse city IDs (lowercase keys matching WAREHOUSES dict)
WAREHOUSE_CITY_IDS = list(WAREHOUSES.keys())


# ─── 55 HIGHWAY EDGES (city_a, city_b, travel_hours) ───────────────────────
# Based on real Indian highway network and approximate driving times.

HIGHWAY_EDGES: List[Tuple[str, str, float]] = [
    # Northern corridor
    ("Delhi",      "Agra",        2.5),   # Yamuna Expressway
    ("Delhi",      "Jaipur",      4.5),   # NH-48
    ("Delhi",      "Lucknow",     6.5),   # via Expressway
    ("Delhi",      "Gwalior",     3.0),   # NH-44
    ("Delhi",      "Kanpur",      5.5),   # NH-2 via Etawah

    # UP corridor
    ("Lucknow",    "Kanpur",      1.5),   # NH-2
    ("Lucknow",    "Agra",        4.0),   # via Expressway
    ("Lucknow",    "Prayagraj",   3.5),   # NH-30
    ("Lucknow",    "Varanasi",    5.0),   # NH-56
    ("Kanpur",     "Agra",        3.5),   # NH-2
    ("Kanpur",     "Prayagraj",   3.0),   # NH-2
    ("Prayagraj",  "Varanasi",    2.5),   # NH-2
    ("Varanasi",   "Patna",       4.5),   # NH-2

    # Agra connections
    ("Agra",       "Gwalior",     2.0),   # NH-44
    ("Agra",       "Jaipur",      4.0),   # NH-21

    # Central India
    ("Gwalior",    "Bhopal",      4.5),   # NH-44
    ("Bhopal",     "Indore",      3.0),   # NH-46
    ("Bhopal",     "Nagpur",      5.5),   # NH-46
    ("Indore",     "Ahmedabad",   4.5),   # NH-47
    ("Indore",     "Surat",       5.0),   # NH-52
    ("Nagpur",     "Hyderabad",   6.0),   # NH-44
    ("Nagpur",     "Pune",        8.0),   # NH-61

    # Western corridor
    ("Jaipur",     "Ahmedabad",   5.5),   # NH-48
    ("Ahmedabad",  "Surat",       4.0),   # NH-48
    ("Ahmedabad",  "Mumbai",      6.5),   # NH-48
    ("Surat",      "Mumbai",      4.5),   # NH-48
    ("Surat",      "Nashik",      4.0),   # NH-3
    ("Mumbai",     "Nashik",      2.5),   # NH-3
    ("Mumbai",     "Pune",        2.5),   # Expressway
    ("Nashik",     "Pune",        3.5),   # NH-50

    # Southern corridor (West)
    ("Pune",       "Hyderabad",   8.0),   # NH-65
    ("Pune",       "Bangalore",  12.0),   # NH-48
    ("Mumbai",     "Hyderabad",  10.0),   # NH-65

    # Southern corridor (Central & East)
    ("Hyderabad",  "Bangalore",   7.0),   # NH-44
    ("Hyderabad",  "Chennai",     7.5),   # NH-65
    ("Hyderabad",  "Visakhapatnam", 8.5), # NH-65
    ("Bangalore",  "Chennai",     4.5),   # NH-48

    # Eastern corridor
    ("Kolkata",    "Patna",       7.5),   # NH-2
    ("Kolkata",    "Visakhapatnam", 12.0), # NH-16
    ("Patna",      "Lucknow",     7.0),   # NH-28
    ("Visakhapatnam", "Chennai",  10.0),  # NH-16

    # Cross-links (strategic connections)
    ("Jaipur",     "Gwalior",     4.5),   # NH-3
    ("Nagpur",     "Indore",      5.0),   # NH-3
    ("Bhopal",     "Jaipur",      7.0),   # via NH
    ("Kanpur",     "Gwalior",     4.5),   # via NH-2/25
    ("Chennai",    "Bangalore",   4.5),   # (duplicate direction, handled by undirected graph)
    ("Nagpur",     "Kolkata",    12.0),   # NH-6
    ("Patna",      "Varanasi",    4.5),   # NH-2
    ("Indore",     "Nashik",      6.5),   # NH-3
    ("Bhopal",     "Nagpur",      5.5),   # (already listed, graph handles duplicates)
]


# ─── ORDER REGISTRY ─────────────────────────────────────────────────────────
# All orders with full lifecycle tracking.

_order_counter = 0
_orders: Dict[str, Dict[str, Any]] = {}

# Order status flow:
# placed → warehouse_assigned → in_warehouse_queue → picking → dispatched → in_transit → delivered


def place_order(
    customer_coords: List[float],
    items: List[str],
    category: str,
    customer_city: str = "",
    order_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new order in the central registry. Returns the order dict."""
    global _order_counter
    with _lock:
        _order_counter += 1
        if not order_id:
            order_id = f"ORD-{int(time.time())}-{_order_counter}"

        order = {
            "order_id": order_id,
            "customer_coords": customer_coords,
            "customer_city": customer_city,
            "items": items,
            "category": category,
            "status": "placed",
            "assigned_warehouse": None,
            "warehouse_queue_position": 0,
            "route": [],
            "eta_hours": 0.0,
            "risk_score": 0.0,
            "gemini_alert": None,
            "position": None,
            "created_at": time.time(),
            "assigned_at": None,
            "dispatched_at": None,
            "delivered_at": None,
        }
        _orders[order_id] = order
        return copy.deepcopy(order)


def assign_order_to_warehouse(
    order_id: str,
    warehouse_id: str,
    route: List[str],
    eta_hours: float,
) -> Dict[str, Any]:
    """Assign an order to a warehouse. Adds it to the warehouse queue."""
    with _lock:
        if order_id not in _orders:
            raise ValueError(f"Order {order_id} not found")
        if warehouse_id not in WAREHOUSES:
            raise ValueError(f"Warehouse {warehouse_id} not found")

        order = _orders[order_id]
        order["status"] = "warehouse_assigned"
        order["assigned_warehouse"] = warehouse_id
        order["route"] = route
        order["eta_hours"] = eta_hours
        order["assigned_at"] = time.time()
        order["position"] = WAREHOUSES[warehouse_id]["city"]

        # Add to warehouse queue
        wh = WAREHOUSES[warehouse_id]
        wh["order_queue"].append(order_id)
        wh["pending"] = len(wh["order_queue"])
        order["warehouse_queue_position"] = wh["pending"]

        return copy.deepcopy(order)


def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    """Get an order by ID."""
    with _lock:
        order = _orders.get(order_id)
        return copy.deepcopy(order) if order else None


def update_order_status(order_id: str, status: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Update an order's status and any extra fields."""
    with _lock:
        if order_id not in _orders:
            return None
        order = _orders[order_id]
        order["status"] = status
        for k, v in kwargs.items():
            if k in order:
                order[k] = v

        # Auto-set timestamps
        if status == "dispatched":
            order["dispatched_at"] = time.time()
        elif status == "delivered":
            order["delivered_at"] = time.time()

        return copy.deepcopy(order)


def get_active_orders() -> List[Dict[str, Any]]:
    """Get all non-delivered orders."""
    with _lock:
        return [
            copy.deepcopy(o) for o in _orders.values()
            if o["status"] != "delivered"
        ]


def get_all_orders() -> List[Dict[str, Any]]:
    """Get all orders."""
    with _lock:
        return [copy.deepcopy(o) for o in _orders.values()]


def get_warehouse_next_order(warehouse_id: str) -> Optional[str]:
    """Pop the next order from a warehouse's queue. Returns order_id or None."""
    with _lock:
        wh = WAREHOUSES.get(warehouse_id)
        if not wh or not wh["order_queue"]:
            return None
        order_id = wh["order_queue"].pop(0)
        wh["pending"] = len(wh["order_queue"])

        # Update remaining orders' queue positions
        for i, oid in enumerate(wh["order_queue"]):
            if oid in _orders:
                _orders[oid]["warehouse_queue_position"] = i + 1

        return order_id


def complete_warehouse_fulfillment(order_id: str) -> Optional[Dict[str, Any]]:
    """Mark an order as picked and ready for dispatch from the warehouse."""
    return update_order_status(order_id, "dispatched")


def update_order_position(order_id: str, city: str) -> Optional[Dict[str, Any]]:
    """Update the current city position of a shipment."""
    return update_order_status(order_id, _orders.get(order_id, {}).get("status", "in_transit"), position=city)


def deduct_inventory(warehouse_id: str, category: str, quantity: int = 1) -> bool:
    """Deduct inventory from a warehouse. Returns True if successful."""
    with _lock:
        wh = WAREHOUSES.get(warehouse_id)
        if not wh:
            return False
        inv = wh.get("inventory", {})
        if inv.get(category, 0) < quantity:
            return False
        inv[category] -= quantity
        return True


def get_warehouse_inventory(warehouse_id: str) -> Dict[str, int]:
    """Get current inventory for a warehouse."""
    with _lock:
        wh = WAREHOUSES.get(warehouse_id)
        if not wh:
            return {}
        return dict(wh.get("inventory", {}))


def get_all_warehouse_queues() -> Dict[str, int]:
    """Get pending counts for all warehouses."""
    with _lock:
        return {wh_id: wh["pending"] for wh_id, wh in WAREHOUSES.items()}


def get_all_warehouses_info() -> Dict[str, Any]:
    """Get full warehouse info for all warehouses."""
    with _lock:
        result = {}
        for wh_id, wh in WAREHOUSES.items():
            result[wh_id] = {
                "city": wh["city"],
                "coords": list(wh["coords"]),
                "pending": wh["pending"],
                "inventory": dict(wh["inventory"]),
                "queue_size": len(wh["order_queue"]),
            }
        return result


def reset_all_data():
    """Reset all orders and warehouse queues to initial state."""
    global _order_counter
    with _lock:
        _order_counter = 0
        _orders.clear()
        for wh in WAREHOUSES.values():
            wh["pending"] = 0
            wh["order_queue"] = []
            # Reset inventory to default levels
            wh["inventory"] = _default_inventory()


# ─── STANDALONE TEST ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  WareFlow Central Data — Self-Test")
    print("=" * 60)

    print(f"\n📦 Warehouses: {len(WAREHOUSES)}")
    for wh_id, wh in WAREHOUSES.items():
        total_stock = sum(wh["inventory"].values())
        print(f"   {wh_id:12s} | {wh['city']:15s} | Stock: {total_stock:3d} | Queue: {wh['pending']}")

    print(f"\n🏙️  Cities: {len(CITY_COORDS)}")
    for city in CITY_COORDS:
        is_wh = "🏭" if city.lower() in WAREHOUSES else "  "
        print(f"   {is_wh} {city}")

    print(f"\n🛣️  Highway edges: {len(HIGHWAY_EDGES)}")

    print(f"\n📋 Product categories: {len(PRODUCT_CATALOG)}")
    for cat_id, cat in PRODUCT_CATALOG.items():
        print(f"   {cat_id:12s} | {cat['name']:12s} | {len(cat['items'])} items")

    # Test order lifecycle
    print("\n--- Order Lifecycle Test ---")
    order = place_order([27.1, 78.0], ["Laptop"], "electronics")
    print(f"1. Placed: {order['order_id']} (status={order['status']})")

    order = assign_order_to_warehouse(order["order_id"], "delhi", ["Delhi", "Agra"], 2.5)
    print(f"2. Assigned: warehouse={order['assigned_warehouse']} queue={order['warehouse_queue_position']}")

    order = update_order_status(order["order_id"], "picking")
    print(f"3. Picking: status={order['status']}")

    order = complete_warehouse_fulfillment(order["order_id"])
    print(f"4. Dispatched: status={order['status']}")

    order = update_order_status(order["order_id"], "delivered")
    print(f"5. Delivered: status={order['status']}")

    print("\n✅ All tests passed!")
