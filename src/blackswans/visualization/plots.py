"""Diagnostic chart generation."""

from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import scipy.stats

from ..analysis.outliers import OutlierStats


def plot_returns_time_series(
    returns: pd.Series,
    outliers: List[OutlierStats],
    output_dir: Path,
) -> None:
    """Plot returns time series with outlier days highlighted."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(returns.index, returns.values, linewidth=0.5)
    for stats in outliers:
        extreme = returns[(returns <= stats.threshold_low) | (returns >= stats.threshold_high)]
        if not extreme.empty:
            ax.scatter(extreme.index, extreme.values, s=10, alpha=0.7,
                       label=f">{stats.quantile*100:.1f}% tails")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "returns_time_series.png")
    plt.close(fig)


def plot_returns_histogram(returns: pd.Series, output_dir: Path) -> None:
    """Plot histogram of returns with normal PDF overlay."""
    clean = returns.dropna()
    fig, ax = plt.subplots(figsize=(8, 5))
    if clean.size > 0:
        ax.hist(clean, bins=100, density=True, alpha=0.6, edgecolor='black', linewidth=0.5)
        x = np.linspace(clean.min(), clean.max(), 200)
        y = scipy.stats.norm.pdf(x, clean.mean(), clean.std(ddof=0))
        ax.plot(x, y, '--')
    ax.set_title("Histogram of Returns")
    fig.tight_layout()
    fig.savefig(output_dir / "returns_histogram.png")
    plt.close(fig)


def plot_returns_by_regime(
    returns: pd.Series,
    regimes: pd.Series,
    output_dir: Path,
) -> None:
    """Scatter plot of returns colored by market regime."""
    fig, ax = plt.subplots(figsize=(10, 5))
    data = pd.DataFrame({"return": returns, "regime": regimes}).dropna()
    if not data.empty:
        colors = ['red' if r == 0 else 'green' for r in data["regime"]]
        ax.scatter(data.index, data["return"], c=colors, s=10, alpha=0.6)
        down = mpatches.Patch(color='red', label='Downtrend')
        up = mpatches.Patch(color='green', label='Uptrend')
        ax.legend(handles=[down, up], loc='upper right')
    ax.axhline(0, linewidth=0.5)
    ax.set_title("Returns by Market Regime")
    fig.tight_layout()
    fig.savefig(output_dir / "returns_by_regime.png")
    plt.close(fig)


def make_plots(
    returns: pd.Series,
    outliers: List[OutlierStats],
    regimes: pd.Series,
    output_dir: Path,
) -> None:
    """Generate and save all diagnostic plots."""
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_returns_time_series(returns, outliers, output_dir)
    plot_returns_histogram(returns, output_dir)
    plot_returns_by_regime(returns, regimes, output_dir)
