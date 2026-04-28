"""
generate_weather_data.py
========================
Generates 10,000 rows of synthetic weather+traffic disruption data for
training the disruption-risk prediction model.

Columns
-------
- base_travel_time        : Uniform [1, 12] hours
- precipitation_mm        : Uniform [0, 80] mm
- wind_speed_kmh          : Uniform [0, 100] km/h
- traffic_congestion_ratio: Uniform [1.0, 3.0] (1.0 = free flow, 3.0 = gridlock)
- risk_score (label)      : weighted combination + noise, clamped [0, 1]
"""

import os
import numpy as np
import pandas as pd

SEED = 42
N_ROWS = 10_000
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "synthetic_weather_disruption.csv")


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)

    base_travel_time = rng.uniform(1, 12, size=N_ROWS)
    precipitation_mm = rng.uniform(0, 80, size=N_ROWS)
    wind_speed_kmh = rng.uniform(0, 100, size=N_ROWS)
    traffic_congestion_ratio = rng.uniform(1.0, 3.0, size=N_ROWS)

    noise = rng.normal(0, 0.05, size=N_ROWS)

    # Risk formula:
    #   - Precipitation contributes 25% (heavy rain is dangerous)
    #   - Wind speed contributes 8%
    #   - Traffic congestion contributes 25% (gridlock = high disruption)
    #   - Remaining is noise and base conditions
    risk_score = (
        0.25 * (precipitation_mm / 80.0)
        + 0.08 * (wind_speed_kmh / 100.0)
        + 0.25 * ((traffic_congestion_ratio - 1.0) / 2.0)
        + noise
    )
    risk_score = np.clip(risk_score, 0.0, 1.0)

    df = pd.DataFrame(
        {
            "base_travel_time": base_travel_time,
            "precipitation_mm": precipitation_mm,
            "wind_speed_kmh": wind_speed_kmh,
            "traffic_congestion_ratio": traffic_congestion_ratio,
            "risk_score": risk_score,
        }
    )
    return df


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = generate()
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"[OK] Generated {len(df)} rows  ->  {os.path.abspath(OUTPUT_FILE)}")
    print(df.describe().round(4))


if __name__ == "__main__":
    main()
