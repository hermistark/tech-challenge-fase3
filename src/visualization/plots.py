"""Reusable plots for EDA and model evaluation."""

from __future__ import annotations

import matplotlib.pyplot as plt
import seaborn as sns


def plot_target_balance(target, ax=None):
    """Plot class counts for the literacy target."""
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    sns.countplot(x=target, ax=ax)
    ax.set_xlabel("alfabetizado_oficial")
    ax.set_ylabel("Quantidade de registros")
    ax.set_title("Distribuicao do target")
    return ax
