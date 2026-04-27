"""
Firebase configuration for the WareFlow Supply Chain module.

HOW TO SET UP:
1. Go to Firebase Console → Project Settings → Service Accounts
2. Click "Generate new private key" → download the JSON file
3. Place it in this directory (backend/supply_chain/)
4. Update SERVICE_ACCOUNT_PATH below with the filename
5. Update DATABASE_URL with your project's Realtime Database URL
"""

import os
from central_data import WAREHOUSES

# Path to your Firebase service account JSON key file
# Download from: Firebase Console → Project Settings → Service Accounts → Generate New Private Key
SERVICE_ACCOUNT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "firebase-service-account.json"  # <-- rename your downloaded file to this
)

# Your Firebase Realtime Database URL
# Find it at: Firebase Console → Realtime Database → Copy the URL at the top
DATABASE_URL = "https://wareflow-f8b9f-default-rtdb.firebaseio.com/"

# --- Initial Firebase Schema ---
# This is the agreed-upon schema that ALL 4 persons must follow.
# P3 seeds this data on first run if the database is empty.
# Now supports 10 warehouses from centralized data.

INITIAL_SCHEMA = {
    "warehouses": {
        wh_id: {
            "pending": 0,
            "coords": wh["coords"],
            "city": wh["city"],
        }
        for wh_id, wh in WAREHOUSES.items()
    },
    "active_shipment": {
        "order_id": "ORD-001",
        "status": "in_transit",
        "current_route": ["Lucknow", "Agra", "Delhi"],
        "risk_score": 0.0,
        "eta_hours": 6.5,
        "gemini_alert": None,
        "position": "Lucknow"
    },
    "orders": {},
}
