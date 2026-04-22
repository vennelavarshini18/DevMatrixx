"""Seed Firebase Realtime Database with the shared WareFlow schema."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

import firebase_admin
from firebase_admin import credentials, db as firebase_db

def seed():
    cred_path = os.environ.get("FIREBASE_CREDENTIALS", "./serviceAccountKey.json")
    db_url = os.environ.get("FIREBASE_URL", "")

    if not db_url:
        print("ERROR: FIREBASE_URL not set in .env")
        sys.exit(1)

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {"databaseURL": db_url})

    # Shared schema - EXACTLY as defined in the contract
    schema = {
        "warehouses": {
            "lucknow": {"pending": 0, "coords": [26.8, 80.9]},
            "delhi": {"pending": 0, "coords": [28.6, 77.2]},
        },
        "active_shipment": {
            "order_id": "",
            "status": "",
            "current_route": [],
            "risk_score": 0.0,
            "eta_hours": 0,
            "gemini_alert": None,
        },
    }

    ref = firebase_db.reference("/")
    ref.set(schema)
    print("Firebase seeded successfully!")
    print(f"  DB URL: {db_url}")
    print(f"  Warehouses: lucknow, delhi")
    print(f"  Active shipment: initialized (empty)")

if __name__ == "__main__":
    seed()
