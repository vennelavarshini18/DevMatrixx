"""
validate_model.py
=================
Phase 3 validation script for the Disruption Predictor (Person 2).

Generates 100 fresh test rows, loads the trained LightGBM model, evaluates
RMSE, and produces two publication-quality plots for the pitch deck:
  1. Feature Importance bar chart
  2. Predicted vs. Actual Risk scatter plot

Output:
  backend/visuals/feature_importance.png
  backend/visuals/predicted_vs_actual.png
"""

import os
import sys

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error

# ── paths ────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(SCRIPT_DIR, "..", "models", "disruption_predictor.pkl")
VISUALS_DIR = os.path.join(SCRIPT_DIR, "..", "visuals")

FEATURES = ["base_travel_time", "precipitation_mm", "wind_speed_kmh"]
TARGET = "risk_score"

# ── Pitch-deck color palette ────────────────────────────────────────────
BG_COLOR = "#0f172a"        # Slate 900
CARD_COLOR = "#1e293b"      # Slate 800
ACCENT_GREEN = "#4ade80"    # Emerald 400
ACCENT_BLUE = "#60a5fa"     # Blue 400
ACCENT_PINK = "#f472b6"     # Pink 400
ACCENT_AMBER = "#fbbf24"    # Amber 400
TEXT_COLOR = "#e2e8f0"       # Slate 200
GRID_COLOR = "#334155"       # Slate 700


def generate_test_data(n_rows: int = 100, seed: int = 999) -> pd.DataFrame:
    """Generate fresh test data using the same formula as training data."""
    rng = np.random.default_rng(seed)

    base_travel_time = rng.uniform(1, 12, size=n_rows)
    precipitation_mm = rng.uniform(0, 80, size=n_rows)
    wind_speed_kmh = rng.uniform(0, 100, size=n_rows)

    noise = rng.normal(0, 0.05, size=n_rows)
    risk_score = (
        0.3 * (precipitation_mm / 80.0)
        + 0.1 * (wind_speed_kmh / 100.0)
        + noise
    )
    risk_score = np.clip(risk_score, 0.0, 1.0)

    return pd.DataFrame({
        "base_travel_time": base_travel_time,
        "precipitation_mm": precipitation_mm,
        "wind_speed_kmh": wind_speed_kmh,
        "risk_score": risk_score,
    })


def plot_feature_importance(model, save_path: str) -> None:
    """Create a dark-themed horizontal bar chart of feature importances."""
    importances = model.feature_importances_
    sorted_idx = np.argsort(importances)

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(CARD_COLOR)

    colors = [ACCENT_GREEN, ACCENT_BLUE, ACCENT_PINK]
    bars = ax.barh(
        [FEATURES[i] for i in sorted_idx],
        importances[sorted_idx],
        color=[colors[i % len(colors)] for i in range(len(sorted_idx))],
        edgecolor="none",
        height=0.5,
    )

    # Value labels on bars
    for bar, val in zip(bars, importances[sorted_idx]):
        ax.text(
            bar.get_width() + max(importances) * 0.02,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,}",
            va="center", ha="left",
            color=TEXT_COLOR, fontsize=12, fontweight="bold",
        )

    ax.set_xlabel("Importance (split count)", color=TEXT_COLOR, fontsize=12)
    ax.set_title(
        "LightGBM Feature Importance  --  Disruption Predictor",
        color=TEXT_COLOR, fontsize=14, fontweight="bold", pad=15,
    )
    ax.tick_params(colors=TEXT_COLOR, labelsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(GRID_COLOR)
    ax.spines["left"].set_color(GRID_COLOR)
    ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.5)

    fig.tight_layout()
    fig.savefig(save_path, dpi=200, facecolor=BG_COLOR, bbox_inches="tight")
    plt.close(fig)


def plot_predicted_vs_actual(y_true, y_pred, rmse: float, save_path: str) -> None:
    """Create a dark-themed scatter plot of predicted vs actual risk scores."""
    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(CARD_COLOR)

    # Perfect prediction line
    lim = [0, max(y_true.max(), y_pred.max()) * 1.05]
    ax.plot(lim, lim, "--", color=ACCENT_AMBER, linewidth=1.5, alpha=0.7, label="Perfect prediction")

    # Scatter
    scatter = ax.scatter(
        y_true, y_pred,
        c=y_pred, cmap="cool", alpha=0.8,
        s=60, edgecolors="white", linewidths=0.3,
    )

    ax.set_xlabel("Actual Risk Score", color=TEXT_COLOR, fontsize=13)
    ax.set_ylabel("Predicted Risk Score", color=TEXT_COLOR, fontsize=13)
    ax.set_title(
        f"Predicted vs Actual Risk  |  RMSE = {rmse:.5f}",
        color=TEXT_COLOR, fontsize=14, fontweight="bold", pad=15,
    )
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_aspect("equal")
    ax.tick_params(colors=TEXT_COLOR, labelsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(GRID_COLOR)
    ax.spines["left"].set_color(GRID_COLOR)
    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.4)
    ax.legend(loc="upper left", fontsize=11, facecolor=CARD_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)

    # Colorbar
    cbar = fig.colorbar(scatter, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label("Predicted Risk", color=TEXT_COLOR, fontsize=11)
    cbar.ax.tick_params(colors=TEXT_COLOR)

    fig.tight_layout()
    fig.savefig(save_path, dpi=200, facecolor=BG_COLOR, bbox_inches="tight")
    plt.close(fig)


def main():
    # ── 1. Load model ────────────────────────────────────────────────────
    if not os.path.exists(MODEL_FILE):
        print("[!] Model not found. Run train_model.py first.")
        sys.exit(1)

    model = joblib.load(MODEL_FILE)
    print(f"[OK] Loaded model from {os.path.basename(MODEL_FILE)}")

    # ── 2. Generate fresh test data ──────────────────────────────────────
    df_test = generate_test_data(n_rows=100, seed=999)
    print(f"[OK] Generated {len(df_test)} fresh test rows (seed=999)")

    X_test = df_test[FEATURES]
    y_test = df_test[TARGET]

    # ── 3. Predict & evaluate ────────────────────────────────────────────
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print(f"\n{'='*55}")
    print(f"  VALIDATION RESULTS")
    print(f"  RMSE on 100 fresh test rows : {rmse:.6f}")
    print(f"  Mean Actual Risk            : {y_test.mean():.4f}")
    print(f"  Mean Predicted Risk         : {y_pred.mean():.4f}")
    print(f"  Max Absolute Error          : {np.abs(y_test.values - y_pred).max():.6f}")
    print(f"{'='*55}\n")

    # ── 4. Generate pitch-deck visuals ───────────────────────────────────
    os.makedirs(VISUALS_DIR, exist_ok=True)

    fi_path = os.path.join(VISUALS_DIR, "feature_importance.png")
    plot_feature_importance(model, fi_path)
    print(f"[OK] Feature Importance chart -> {os.path.abspath(fi_path)}")

    pva_path = os.path.join(VISUALS_DIR, "predicted_vs_actual.png")
    plot_predicted_vs_actual(y_test, y_pred, rmse, pva_path)
    print(f"[OK] Predicted vs Actual plot -> {os.path.abspath(pva_path)}")

    print("\n[DONE] All validation artifacts saved to backend/visuals/")


if __name__ == "__main__":
    main()
