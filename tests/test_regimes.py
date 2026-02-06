"""Tests for blackswans.analysis.regimes."""

import math

import numpy as np
import pandas as pd
import pytest

from blackswans.analysis.regimes import (
    moving_average_regime,
    outlier_regime_counts,
    regime_performance,
)
from blackswans.analysis.scenarios import annualised_return


class TestMovingAverageRegime:
    def test_first_window_days_nan(self, price_series):
        regime = moving_average_regime(price_series, window=50)
        assert regime.iloc[:50].isna().all()
        assert not regime.iloc[50:].isna().any()

    def test_uptrend(self):
        """Monotonically increasing prices should be all uptrend after warmup."""
        prices = pd.Series(range(1, 302), dtype=float)
        regime = moving_average_regime(prices, window=10)
        valid = regime.dropna()
        assert (valid == 1).all()

    def test_downtrend(self):
        """Monotonically decreasing prices should be all downtrend after warmup."""
        prices = pd.Series(range(301, 0, -1), dtype=float)
        regime = moving_average_regime(prices, window=10)
        valid = regime.dropna()
        assert (valid == 0).all()

    def test_binary_values(self, price_series):
        regime = moving_average_regime(price_series, window=50)
        valid = regime.dropna()
        assert set(valid.unique()) <= {0, 1}

    def test_accepts_dataframe(self, price_dataframe):
        regime = moving_average_regime(price_dataframe, window=50)
        assert len(regime) == len(price_dataframe)

    def test_lagged_ma(self):
        """Verify the MA is lagged (uses yesterday's MA, not today's)."""
        # Create a series where price drops sharply on last day
        prices = pd.Series([100.0] * 20 + [50.0], dtype=float)
        regime = moving_average_regime(prices, window=5)
        # The last day should be 0 (downtrend) because 50 < MA of ~100
        assert regime.iloc[-1] == 0


class TestOutlierRegimeCounts:
    def test_counts_sum(self, returns_series, regime_series):
        down, up = outlier_regime_counts(returns_series, regime_series, 0.95)
        # Total outliers in both regimes should be > 0
        assert down + up > 0

    def test_all_uptrend(self):
        """When all regime = 1, all outliers should be in uptrend."""
        dates = pd.bdate_range("2020-01-01", periods=100)
        returns = pd.Series(np.random.RandomState(0).normal(0, 0.02, 100), index=dates)
        regimes = pd.Series(1, index=dates, dtype=float)
        down, up = outlier_regime_counts(returns, regimes, 0.90)
        assert down == 0
        assert up > 0

    def test_nan_regime_excluded(self):
        """Outliers in NaN regime period should not be counted."""
        dates = pd.bdate_range("2020-01-01", periods=20)
        returns = pd.Series([-0.1, 0.1] * 10, index=dates)
        regimes = pd.Series([np.nan] * 10 + [1] * 10, index=dates, dtype=float)
        down, up = outlier_regime_counts(returns, regimes, 0.90)
        # Only outliers in the second half (regime=1) should be counted
        assert down == 0


class TestRegimePerformance:
    def test_output_shape(self, returns_series, regime_series):
        df = regime_performance(returns_series, regime_series)
        assert len(df) == 2
        assert set(df["regime"]) == {"downtrend", "uptrend"}

    def test_columns(self, returns_series, regime_series):
        df = regime_performance(returns_series, regime_series)
        expected_cols = {"regime", "count", "pct_of_total", "mean", "median", "std", "annualised_return"}
        assert expected_cols == set(df.columns)

    def test_pct_sums_to_one(self, returns_series, regime_series):
        df = regime_performance(returns_series, regime_series)
        assert df["pct_of_total"].sum() == pytest.approx(1.0)

    def test_counts_sum(self, returns_series, regime_series):
        df = regime_performance(returns_series, regime_series)
        total = df["count"].sum()
        valid_regime_days = regime_series.dropna().size
        assert total == valid_regime_days

    def test_annualised_return_reasonable(self, returns_series, regime_series):
        """Regime CAGR should be between -50% and +50% for reasonable data."""
        df = regime_performance(returns_series, regime_series)
        for _, row in df.iterrows():
            cagr = row["annualised_return"]
            if not math.isnan(cagr):
                assert -0.5 < cagr < 0.5

    def test_full_period_annualisation(self):
        """Regime returns should be annualised over the full period, not just regime days."""
        dates = pd.bdate_range("2020-01-01", periods=252)
        # Half uptrend, half downtrend
        returns = pd.Series(0.001, index=dates)
        regimes = pd.Series([1] * 126 + [0] * 126, index=dates, dtype=float)
        df = regime_performance(returns, regimes)
        # Each regime's CAGR should be less than full-period CAGR
        full_cagr = annualised_return(returns)
        for _, row in df.iterrows():
            assert row["annualised_return"] < full_cagr
