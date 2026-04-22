"""
Task 1 — Synthetic Data Generator for Warehouse Selector ML Model.

Generates 10,000 rows of training data with distance and queue features
for two warehouses, plus a heuristic label indicating optimal assignment.
"""

import numpy as np
import pandas as pd
import os


def generate_training_data(n_samples: int = 10_000, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic warehouse assignment training data.

    Features:
        - distance_to_wh1: Driving distance (km) to warehouse 1 (Lucknow)
        - distance_to_wh2: Driving distance (km) to warehouse 2 (Delhi)
        - queue_size_wh1:  Current pending orders at warehouse 1
        - queue_size_wh2:  Current pending orders at warehouse 2

    Label heuristic:
        score_i = distance_to_wh_i * (1 + 0.1 * queue_size_wh_i)
        label = 0 if score1 < score2 else 1
        (Pick warehouse 1 unless warehouse 2 scores 3+ lower after queue penalty)

    Args:
        n_samples: Number of rows to generate.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with features and 'label' column.
    """
    rng = np.random.RandomState(seed)

    distance_to_wh1 = rng.uniform(5, 200, size=n_samples)
    distance_to_wh2 = rng.uniform(5, 200, size=n_samples)
    queue_size_wh1 = rng.randint(0, 15, size=n_samples)
    queue_size_wh2 = rng.randint(0, 15, size=n_samples)

    # Composite cost score: distance penalised by queue congestion
    score1 = distance_to_wh1 * (1 + 0.1 * queue_size_wh1)
    score2 = distance_to_wh2 * (1 + 0.1 * queue_size_wh2)

    # Label: 0 = assign to wh1 (Lucknow), 1 = assign to wh2 (Delhi)
    # Pick wh1 unless wh2 scores 3+ lower (i.e., wh2 is meaningfully better)
    label = np.where(score1 <= score2, 0, np.where((score2 + 3) < score1, 1, 0))

    df = pd.DataFrame({
        "distance_to_wh1": np.round(distance_to_wh1, 2),
        "distance_to_wh2": np.round(distance_to_wh2, 2),
        "queue_size_wh1": queue_size_wh1,
        "queue_size_wh2": queue_size_wh2,
        "label": label,
    })

    return df


def main():
    """Generate and save training data to CSV."""
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "warehouse_training_data.csv")

    print("=" * 50)
    print("  WareFlow P1 — Synthetic Data Generator")
    print("=" * 50)

    df = generate_training_data()

    print(f"\n📊 Generated {len(df):,} samples")
    print(f"   Features: {list(df.columns[:-1])}")
    print(f"   Label distribution:")
    print(f"     Warehouse 1 (Lucknow): {(df['label'] == 0).sum():,} ({(df['label'] == 0).mean():.1%})")
    print(f"     Warehouse 2 (Delhi):   {(df['label'] == 1).sum():,} ({(df['label'] == 1).mean():.1%})")
    print(f"\n📈 Feature statistics:")
    print(df.describe().round(2).to_string())

    df.to_csv(output_path, index=False)
    print(f"\n✅ Saved to: {output_path}")


if __name__ == "__main__":
    main()
