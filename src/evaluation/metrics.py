"""Evaluation helpers for generalization metrics."""

from __future__ import annotations

from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score


def evaluate_classifier(model, features, target) -> dict:
    """Return metrics that remain meaningful under target imbalance."""
    predictions = model.predict(features)
    probabilities = model.predict_proba(features)[:, 1]
    report = classification_report(target, predictions, output_dict=True, zero_division=0)
    return {
        "roc_auc": roc_auc_score(target, probabilities),
        "classification_report": report,
        "confusion_matrix": confusion_matrix(target, predictions).tolist(),
    }
