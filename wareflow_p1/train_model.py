"""
Task 2 — Train XGBoost Classifier for Warehouse Selection.

Loads synthetic training data, trains an XGBClassifier, evaluates accuracy
and feature importances, and saves the model + summary report.
"""

import os
import time
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


def train_warehouse_selector(data_path: str = None) -> tuple:
    """Train XGBoost classifier on warehouse assignment data.

    Args:
        data_path: Path to warehouse_training_data.csv.
                   Defaults to same directory as this script.

    Returns:
        Tuple of (trained model, accuracy, feature_importances dict).
    """
    if data_path is None:
        data_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "warehouse_training_data.csv"
        )

    if not os.path.exists(data_path):
        raise FileNotFoundError(
            f"Training data not found at {data_path}. "
            "Run data_generator.py first."
        )

    # Load data
    df = pd.read_csv(data_path)
    feature_cols = ["distance_to_wh1", "distance_to_wh2", "queue_size_wh1", "queue_size_wh2"]
    X = df[feature_cols]
    y = df["label"]

    # Split 80/20
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Train XGBoost
    model = XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        eval_metric="logloss",
    )

    print("🏋️  Training XGBoost classifier...")
    start_time = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - start_time

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    # Feature importances
    importances = dict(zip(feature_cols, model.feature_importances_))
    sorted_importances = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))

    print(f"\n✅ Training complete in {train_time:.2f}s")
    print(f"📊 Test Accuracy: {accuracy:.4f} ({accuracy:.1%})")
    print(f"\n🔍 Feature Importances:")
    for feat, imp in sorted_importances.items():
        bar = "█" * int(imp * 40)
        print(f"   {feat:25s} {imp:.4f} {bar}")

    print(f"\n📋 Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Lucknow (0)", "Delhi (1)"]))

    return model, accuracy, sorted_importances, train_time


def save_model_and_summary(model, accuracy: float, importances: dict, train_time: float):
    """Save trained model as .pkl and write model_summary.txt.

    Args:
        model: Trained XGBClassifier.
        accuracy: Test accuracy score.
        importances: Dict of feature name → importance score.
        train_time: Training duration in seconds.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, "warehouse_selector.pkl")
    summary_path = os.path.join(base_dir, "model_summary.txt")

    # Save model
    joblib.dump(model, model_path)
    print(f"\n💾 Model saved to: {model_path}")

    # Write summary
    lines = [
        "=" * 50,
        "  WareFlow P1 — Warehouse Selector Model Summary",
        "=" * 50,
        "",
        f"Model Type:      XGBClassifier",
        f"Estimators:      100",
        f"Test Accuracy:   {accuracy:.4f} ({accuracy:.1%})",
        f"Training Time:   {train_time:.2f}s",
        f"Training Rows:   10,000",
        f"Features:        4",
        "",
        "Feature Importances (descending):",
        "-" * 40,
    ]
    for feat, imp in importances.items():
        lines.append(f"  {feat:25s} {imp:.4f}")
    lines.append("")
    lines.append("Warehouses: Lucknow (label=0), Delhi (label=1)")
    lines.append("Label Heuristic: score = distance * (1 + 0.1 * queue_size)")
    lines.append("")

    with open(summary_path, "w") as f:
        f.write("\n".join(lines))

    print(f"📝 Summary saved to: {summary_path}")


def main():
    """Generate data (if needed), train model, and save outputs."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_dir, "warehouse_training_data.csv")

    # Auto-generate data if CSV doesn't exist
    if not os.path.exists(data_path):
        print("📦 Training data not found — generating now...")
        from data_generator import generate_training_data
        df = generate_training_data()
        df.to_csv(data_path, index=False)
        print(f"✅ Generated {len(df):,} rows → {data_path}\n")

    print("=" * 50)
    print("  WareFlow P1 — XGBoost Model Training")
    print("=" * 50)

    model, accuracy, importances, train_time = train_warehouse_selector(data_path)
    save_model_and_summary(model, accuracy, importances, train_time)

    print("\n🎉 Task 2 complete — model ready for inference.")


if __name__ == "__main__":
    main()
