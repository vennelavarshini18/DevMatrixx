"""
train_model.py
==============
Trains a LightGBM Regressor on the synthetic weather-disruption dataset,
evaluates with RMSE, prints a feature-importance chart, and exports the
trained model to ``backend/models/disruption_predictor.pkl``.
"""

import os
import sys

import joblib
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for saving plots
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split

# ── paths ────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "..", "data", "synthetic_weather_disruption.csv")
MODEL_DIR = os.path.join(SCRIPT_DIR, "..", "models")
MODEL_FILE = os.path.join(MODEL_DIR, "disruption_predictor.pkl")
PLOT_FILE = os.path.join(MODEL_DIR, "feature_importance.png")

FEATURES = ["base_travel_time", "precipitation_mm", "wind_speed_kmh", "traffic_congestion_ratio"]
TARGET = "risk_score"


def main():
    # ── 1. Load data ─────────────────────────────────────────────────────
    if not os.path.exists(DATA_FILE):
        print("[!] Data file not found. Run generate_weather_data.py first.")
        sys.exit(1)

    df = pd.read_csv(DATA_FILE)
    print(f"[i] Loaded {len(df)} rows from {os.path.basename(DATA_FILE)}")

    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # ── 2. Train LightGBM ───────────────────────────────────────────────
    model = LGBMRegressor(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=6,
        random_state=42,
        verbose=-1,
    )
    model.fit(X_train, y_train)

    # ── 3. Evaluate ──────────────────────────────────────────────────────
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    print(f"\n{'='*50}")
    print(f"  RMSE on test set : {rmse:.6f}")
    print(f"{'='*50}\n")

    # ── 4. Feature importance ────────────────────────────────────────────
    importances = model.feature_importances_
    sorted_idx = np.argsort(importances)

    print("Feature Importances (split-based):")
    for idx in sorted_idx:
        bar = "#" * int(importances[idx] / max(importances) * 30)
        print(f"  {FEATURES[idx]:>20s}  {importances[idx]:>6d}  {bar}")

    # Save plot
    os.makedirs(MODEL_DIR, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(
        [FEATURES[i] for i in sorted_idx],
        importances[sorted_idx],
        color=["#4ade80", "#60a5fa", "#f472b6"],
    )
    ax.set_xlabel("Importance (split count)")
    ax.set_title("LightGBM Feature Importance — Disruption Predictor")
    fig.tight_layout()
    fig.savefig(PLOT_FILE, dpi=150)
    print(f"\n[OK] Feature importance plot saved -> {os.path.abspath(PLOT_FILE)}")

    # ── 5. Export model ──────────────────────────────────────────────────
    joblib.dump(model, MODEL_FILE)
    print(f"[OK] Model exported -> {os.path.abspath(MODEL_FILE)}")


if __name__ == "__main__":
    main()
