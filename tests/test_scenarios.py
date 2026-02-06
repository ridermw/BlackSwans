"""Tests for blackswans.analysis.scenarios."""

import math

import numpy as np
import pandas as pd
import pytest

from blackswans.analysis.scenarios import annualised_return, scenario_returns, CASH


class TestAnnualisedReturn:
    def test_zero_returns(self):
        """All zero returns should give 0% CAGR."""
        r = pd.Series([0.0] * 252)
        assert annualised_return(r) == pytest.approx(0.0)

    def test_constant_positive(self):
        """252 days of constant daily return should annualise correctly."""
        daily = 0.001  # ~0.1% per day
        r = pd.Series([daily] * 252)
        expected = (1 + daily) ** 252 - 1
        assert annualised_return(r) == pytest.approx(expected, rel=1e-6)

    def test_two_years(self):
        """504 days (2 years) should halve the exponent."""
        daily = 0.001
        r = pd.Series([daily] * 504)
        cumulative = (1 + daily) ** 504
        expected = cumulative ** (1 / 2) - 1
        assert annualised_return(r) == pytest.approx(expected, rel=1e-6)

    def test_empty_returns_nan(self):
        assert math.isnan(annualised_return(pd.Series(dtype=float)))

    def test_negative_total(self):
        """Large negative returns should produce negative CAGR."""
        r = pd.Series([-0.10] * 10)
        assert annualised_return(r) < 0


class TestScenarioReturns:
    def test_shapes(self, returns_series):
        all_r, mb, mw, mboth = scenario_returns(returns_series, 5, 5)
        assert len(all_r) == len(returns_series)
        assert len(mb) == len(returns_series)
        assert len(mw) == len(returns_series)
        assert len(mboth) == len(returns_series)

    def test_miss_best_zeroes_top(self, known_returns):
        _, mb, _, _ = scenario_returns(known_returns, 2, 2)
        # The 2 best days (0.05, 0.04) should be zeroed
        sorted_vals = known_returns.sort_values()
        best_idx = sorted_vals.index[-2:]
        for idx in best_idx:
            assert mb.loc[idx] == CASH

    def test_miss_worst_zeroes_bottom(self, known_returns):
        _, _, mw, _ = scenario_returns(known_returns, 2, 2)
        sorted_vals = known_returns.sort_values()
        worst_idx = sorted_vals.index[:2]
        for idx in worst_idx:
            assert mw.loc[idx] == CASH

    def test_miss_both(self, known_returns):
        _, _, _, mboth = scenario_returns(known_returns, 2, 2)
        sorted_vals = known_returns.sort_values()
        best_idx = sorted_vals.index[-2:]
        worst_idx = sorted_vals.index[:2]
        for idx in best_idx.union(worst_idx):
            assert mboth.loc[idx] == CASH

    def test_original_unchanged(self, known_returns):
        original = known_returns.copy()
        all_r, _, _, _ = scenario_returns(known_returns, 2, 2)
        pd.testing.assert_series_equal(all_r, original)

    def test_miss_best_lowers_return(self, returns_series):
        all_r, mb, _, _ = scenario_returns(returns_series, 10, 10)
        assert annualised_return(mb) < annualised_return(all_r)

    def test_miss_worst_raises_return(self, returns_series):
        all_r, _, mw, _ = scenario_returns(returns_series, 10, 10)
        assert annualised_return(mw) > annualised_return(all_r)
