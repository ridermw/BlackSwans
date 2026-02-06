"""Tests for blackswans.analysis.outliers."""

import numpy as np
import pandas as pd
import pytest

from blackswans.analysis.outliers import OutlierStats, calculate_outlier_stats


class TestCalculateOutlierStats:
    def test_symmetric_distribution(self):
        """With a symmetric distribution, thresholds should be roughly mirror images."""
        rng = np.random.RandomState(0)
        returns = pd.Series(rng.normal(0, 0.01, size=10000))
        stats = calculate_outlier_stats(returns, 0.99)
        assert stats.quantile == 0.99
        assert stats.threshold_low < 0
        assert stats.threshold_high > 0
        assert abs(stats.threshold_low + stats.threshold_high) < 0.005
        assert stats.count_low > 0
        assert stats.count_high > 0

    def test_counts_match_quantile(self):
        """Each tail should contain approximately (1-q)% of data."""
        rng = np.random.RandomState(1)
        returns = pd.Series(rng.normal(0, 0.01, size=10000))
        stats = calculate_outlier_stats(returns, 0.99)
        # ~1% in each tail = ~100 each, allow some margin
        assert 80 <= stats.count_low <= 120
        assert 80 <= stats.count_high <= 120

    def test_extremes(self):
        """min_low should be the most negative, max_high the most positive."""
        returns = pd.Series([-0.10, -0.05, 0.0, 0.05, 0.10])
        stats = calculate_outlier_stats(returns, 0.80)
        assert stats.min_low == -0.10
        assert stats.max_high == 0.10

    def test_known_values(self, known_returns):
        stats = calculate_outlier_stats(known_returns, 0.90)
        assert stats.threshold_low <= known_returns.quantile(0.10)
        assert stats.threshold_high >= known_returns.quantile(0.90)
        assert stats.count_low >= 1
        assert stats.count_high >= 1

    def test_dataclass_fields(self):
        returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.0])
        stats = calculate_outlier_stats(returns, 0.80)
        assert isinstance(stats, OutlierStats)
        assert hasattr(stats, "mean_low")
        assert hasattr(stats, "std_high")
