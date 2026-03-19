"""Tests for split-period analysis module.

TDD: these tests are written before the implementation.
"""

import numpy as np
import pandas as pd
import pytest

from blackswans.analysis.periods import (
    split_returns_by_date,
    period_cagr_matrix,
    period_claim_summary,
    multi_index_summary,
    PERIOD_LABELS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def long_prices():
    """Synthetic price series spanning 2000-01-03 to 2020-12-31."""
    rng = np.random.RandomState(99)
    dates = pd.bdate_range("2000-01-03", "2020-12-31")
    daily_ret = rng.normal(0.0003, 0.012, size=len(dates))
    prices = 100 * np.cumprod(1 + daily_ret)
    return pd.Series(prices, index=dates, name="Close")


@pytest.fixture
def long_returns(long_prices):
    r = long_prices.pct_change().dropna()
    r.name = "Return"
    return r


# ---------------------------------------------------------------------------
# split_returns_by_date
# ---------------------------------------------------------------------------

class TestSplitReturnsByDate:
    def test_returns_three_periods(self, long_returns):
        """Should return dict with pre, post, and full periods."""
        result = split_returns_by_date(long_returns, split_date="2011-01-01")
        assert set(result.keys()) == {"pre", "post", "full"}

    def test_pre_period_ends_before_split(self, long_returns):
        result = split_returns_by_date(long_returns, split_date="2011-01-01")
        assert result["pre"].index.max() < pd.Timestamp("2011-01-01")

    def test_post_period_starts_at_or_after_split(self, long_returns):
        result = split_returns_by_date(long_returns, split_date="2011-01-01")
        assert result["post"].index.min() >= pd.Timestamp("2011-01-01")

    def test_full_equals_original_length(self, long_returns):
        result = split_returns_by_date(long_returns, split_date="2011-01-01")
        assert len(result["full"]) == len(long_returns)

    def test_pre_plus_post_equals_full(self, long_returns):
        result = split_returns_by_date(long_returns, split_date="2011-01-01")
        assert len(result["pre"]) + len(result["post"]) == len(result["full"])

    def test_custom_split_date(self, long_returns):
        result = split_returns_by_date(long_returns, split_date="2015-06-15")
        assert result["pre"].index.max() < pd.Timestamp("2015-06-15")
        assert result["post"].index.min() >= pd.Timestamp("2015-06-15")


# ---------------------------------------------------------------------------
# period_cagr_matrix
# ---------------------------------------------------------------------------

class TestPeriodCagrMatrix:
    def test_returns_dataframe(self, long_returns):
        result = period_cagr_matrix(long_returns, split_date="2011-01-01")
        assert isinstance(result, pd.DataFrame)

    def test_has_required_columns(self, long_returns):
        result = period_cagr_matrix(long_returns, split_date="2011-01-01")
        assert "period" in result.columns
        assert "cagr_all" in result.columns
        assert "cagr_miss_best" in result.columns
        assert "cagr_miss_worst" in result.columns

    def test_has_three_periods(self, long_returns):
        result = period_cagr_matrix(long_returns, split_date="2011-01-01")
        assert len(result) == 3

    def test_scenario_counts(self, long_returns):
        """Default n_days=[5, 10, 20, 50]; matrix uses n=10."""
        result = period_cagr_matrix(long_returns, split_date="2011-01-01", n_days=10)
        # All values should be finite floats
        for col in ["cagr_all", "cagr_miss_best", "cagr_miss_worst"]:
            assert result[col].notna().all()

    def test_miss_best_reduces_cagr(self, long_returns):
        """Missing best days should lower CAGR."""
        result = period_cagr_matrix(long_returns, split_date="2011-01-01", n_days=10)
        for _, row in result.iterrows():
            assert row["cagr_miss_best"] < row["cagr_all"]

    def test_miss_worst_increases_cagr(self, long_returns):
        """Missing worst days should raise CAGR."""
        result = period_cagr_matrix(long_returns, split_date="2011-01-01", n_days=10)
        for _, row in result.iterrows():
            assert row["cagr_miss_worst"] > row["cagr_all"]

    def test_custom_n_days(self, long_returns):
        r5 = period_cagr_matrix(long_returns, split_date="2011-01-01", n_days=5)
        r50 = period_cagr_matrix(long_returns, split_date="2011-01-01", n_days=50)
        # Larger n_days → bigger CAGR impact
        full5 = r5[r5["period"] == "full"].iloc[0]
        full50 = r50[r50["period"] == "full"].iloc[0]
        impact5 = full5["cagr_all"] - full5["cagr_miss_best"]
        impact50 = full50["cagr_all"] - full50["cagr_miss_best"]
        assert impact50 > impact5


# ---------------------------------------------------------------------------
# period_claim_summary
# ---------------------------------------------------------------------------

class TestPeriodClaimSummary:
    def test_returns_dict_with_periods(self, long_prices, long_returns):
        result = period_claim_summary(long_prices, long_returns, split_date="2011-01-01")
        assert isinstance(result, dict)
        assert set(result.keys()) == {"pre", "post", "full"}

    def test_each_period_has_four_claims(self, long_prices, long_returns):
        result = period_claim_summary(long_prices, long_returns, split_date="2011-01-01")
        for period_key in ["pre", "post", "full"]:
            claims = result[period_key]
            assert "fat_tails" in claims
            assert "outsized_influence" in claims
            assert "clustering" in claims
            assert "trend_following" in claims

    def test_each_claim_has_verdict(self, long_prices, long_returns):
        result = period_claim_summary(long_prices, long_returns, split_date="2011-01-01")
        claim_keys = ["fat_tails", "outsized_influence", "clustering", "trend_following"]
        for period_key in ["pre", "post", "full"]:
            for claim_key in claim_keys:
                assert claim_key in result[period_key]
                assert "verdict" in result[period_key][claim_key]

    def test_each_period_has_metadata(self, long_prices, long_returns):
        result = period_claim_summary(long_prices, long_returns, split_date="2011-01-01")
        for period_key in ["pre", "post", "full"]:
            claims = result[period_key]
            assert "n_trading_days" in claims
            assert "start_date" in claims
            assert "end_date" in claims
            assert claims["n_trading_days"] > 0


# ---------------------------------------------------------------------------
# multi_index_summary
# ---------------------------------------------------------------------------

class TestMultiIndexSummary:
    def test_returns_list(self, tmp_path):
        """Create two fake CSVs, run multi_index_summary."""
        for name, start_year in [("_TEST1_2000-01-03_to_2020-12-31", 2000),
                                  ("_TEST2_2005-01-03_to_2020-12-31", 2005)]:
            rng = np.random.RandomState(42)
            dates = pd.bdate_range(f"{start_year}-01-03", "2020-12-31")
            prices = 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, len(dates)))
            df = pd.DataFrame({"Date": dates, "Close": prices})
            df.to_csv(tmp_path / f"{name}.csv", index=False)

        ticker_map = {
            "TEST1": {"file": f"_TEST1_2000-01-03_to_2020-12-31.csv",
                       "start": "2000-01-03", "end": "2020-12-31"},
            "TEST2": {"file": f"_TEST2_2005-01-03_to_2020-12-31.csv",
                       "start": "2005-01-03", "end": "2020-12-31"},
        }

        result = multi_index_summary(
            data_dir=str(tmp_path),
            ticker_map=ticker_map,
            split_date="2011-01-01",
        )
        assert isinstance(result, list)
        assert len(result) == 2

    def test_each_entry_has_ticker_and_cagr(self, tmp_path):
        rng = np.random.RandomState(42)
        dates = pd.bdate_range("2000-01-03", "2020-12-31")
        prices = 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, len(dates)))
        df = pd.DataFrame({"Date": dates, "Close": prices})
        df.to_csv(tmp_path / "_IDX_2000-01-03_to_2020-12-31.csv", index=False)

        ticker_map = {
            "IDX": {"file": "_IDX_2000-01-03_to_2020-12-31.csv",
                     "start": "2000-01-03", "end": "2020-12-31"},
        }

        result = multi_index_summary(
            data_dir=str(tmp_path),
            ticker_map=ticker_map,
            split_date="2011-01-01",
        )
        entry = result[0]
        assert entry["ticker"] == "IDX"
        assert "cagr_full" in entry
        assert "cagr_pre" in entry
        assert "cagr_post" in entry
        assert "kurtosis_full" in entry
        assert "clustering_pct_full" in entry


# ---------------------------------------------------------------------------
# PERIOD_LABELS constant
# ---------------------------------------------------------------------------

class TestPeriodLabels:
    def test_default_labels(self):
        assert "pre" in PERIOD_LABELS
        assert "post" in PERIOD_LABELS
        assert "full" in PERIOD_LABELS
