"""Quick Firebase handshake verification for Person 2."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.firebase_service import push_disruption_to_firebase

result = push_disruption_to_firebase(
    risk_score=0.85,
    gemini_alert="CRITICAL: Agra experiencing 75mm rainfall. Risk score 85% detected. Recommending immediate reroute.",
    precipitation_mm=75.0,
    wind_speed_kmh=90.0,
)

print()
print("=" * 55)
print("  FIREBASE HANDSHAKE VERIFICATION")
print(f"  risk_score  = {result['risk_score']}  (type: {result['risk_score_type']})")
print(f"  gemini_alert type = {result['gemini_alert_type']}")
print(f"  Firebase mode     = {result['mode']}")
print(f"  Status            = {result['status']}")
print("=" * 55)
