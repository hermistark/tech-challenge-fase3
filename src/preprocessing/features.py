"""Feature selection and preprocessing for the official student-level dataset."""

from __future__ import annotations

from typing import Iterable

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET = "alfabetizado_oficial"
LEAKAGE_COLUMNS = {"VL_PROFICIENCIA_LP", TARGET}


def select_features(frame: pd.DataFrame, excluded: Iterable[str] = ()) -> tuple[pd.DataFrame, pd.Series]:
    """Return model features and target while excluding known leakage columns."""
    if TARGET not in frame.columns:
        raise ValueError(f"Target column not found: {TARGET}")

    excluded_columns = LEAKAGE_COLUMNS | set(excluded)
    feature_columns = [column for column in frame.columns if column not in excluded_columns]
    return frame[feature_columns].copy(), frame[TARGET].astype("int8")


def build_preprocessor(frame: pd.DataFrame) -> ColumnTransformer:
    """Build preprocessing inside sklearn so fit statistics never cross splits."""
    numeric_columns = frame.select_dtypes(include="number").columns.tolist()
    categorical_columns = frame.select_dtypes(exclude="number").columns.tolist()

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_columns),
            ("categorical", categorical_pipeline, categorical_columns),
        ],
        remainder="drop",
    )
