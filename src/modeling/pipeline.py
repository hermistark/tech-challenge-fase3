"""Model pipelines for the Phase 3 classification task."""

from __future__ import annotations

from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

from src.preprocessing.features import build_preprocessor


def build_random_forest_pipeline(frame):
    """Create a leakage-safe preprocessing and Random Forest pipeline."""
    return Pipeline(
        steps=[
            ("preprocessor", build_preprocessor(frame)),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=15,
                    class_weight="balanced",
                    n_jobs=-1,
                    random_state=42,
                ),
            ),
        ]
    )
