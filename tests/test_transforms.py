"""Tests for blackswans.data.transforms."""

import numpy as np
import pandas as pd
import pytest

from blackswans.data.transforms import compute_daily_returns


class TestComputeDailyReturns:
    def test_basic_returns(self):
        prices = pd.Series([100.0, 110.0, 99.0], name="Close")
        r = compute_daily_returns(prices)
        assert len(r) == 2
        assert r.iloc[0] == pytest.approx(0.10)
        assert r.iloc[1] == pytest.approx(-0.10, abs=1e-4)

    def test_from_dataframe(self, price_dataframe):
        r = compute_daily_returns(price_dataframe)
        assert r.name == "Return"
        assert len(r) == len(price_dataframe) - 1
        assert not r.isna().any()

    def test_from_series(self, price_series):
        r = compute_daily_returns(price_series)
        assert len(r) == len(price_series) - 1

    def test_drops_nan(self):
        prices = pd.Series([100.0, np.nan, 110.0, 121.0])
        r = compute_daily_returns(prices)
        assert not r.isna().any()
        # NaN is dropped before pct_change, so series becomes [100, 110, 121]
        # giving 2 returns: 10% and 10%
        assert len(r) == 2

    def test_single_price(self):
        prices = pd.Series([100.0])
        r = compute_daily_returns(prices)
        assert len(r) == 0

    def test_empty_series(self):
        r = compute_daily_returns(pd.Series(dtype=float))
        assert len(r) == 0
