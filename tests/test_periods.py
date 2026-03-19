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
    _claim_summary_for_period,
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


# ---------------------------------------------------------------------------
# Edge-case tests for uncovered lines
# ---------------------------------------------------------------------------

def _make_synthetic(n_days, seed=42, start="2010-01-04"):
    """Return (prices, returns) with *n_days* business days."""
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range(start, periods=n_days)
    daily_ret = rng.normal(0.0003, 0.012, size=n_days)
    prices = pd.Series(
        100 * np.cumprod(1 + daily_ret), index=dates, name="Close"
    )
    returns = prices.pct_change().dropna()
    returns.name = "Return"
    return prices, returns


class TestEdgeCases:
    """Cover lines 156, 218, 238, 257, 328-329, 382-384 in periods.py."""

    # -- Line 218: outsized_influence INSUFFICIENT DATA (n < 20) ----------

    def test_very_short_data_outsized_influence_insufficient(self):
        """With only 10 data points, outsized_influence → INSUFFICIENT DATA."""
        prices, returns = _make_synthetic(10)
        result = _claim_summary_for_period(returns, prices)
        assert result["outsized_influence"]["verdict"] == "INSUFFICIENT DATA"

    # -- Lines 238, 257: clustering & trend_following INSUFFICIENT DATA ----

    def test_short_data_clustering_insufficient(self):
        """With 50 data points, clustering → INSUFFICIENT DATA (need ≥200)."""
        prices, returns = _make_synthetic(50)
        result = _claim_summary_for_period(returns, prices)
        assert result["clustering"]["verdict"] == "INSUFFICIENT DATA"
        assert result["trend_following"]["verdict"] == "INSUFFICIENT DATA"
        # outsized_influence should still work (n ≥ 20)
        assert result["outsized_influence"]["verdict"] != "INSUFFICIENT DATA"

    def test_very_short_data_all_insufficient(self):
        """10 data points: outsized, clustering, trend_following all insufficient."""
        prices, returns = _make_synthetic(10)
        result = _claim_summary_for_period(returns, prices)
        assert result["outsized_influence"]["verdict"] == "INSUFFICIENT DATA"
        assert result["clustering"]["verdict"] == "INSUFFICIENT DATA"
        assert result["trend_following"]["verdict"] == "INSUFFICIENT DATA"
        # fat_tails should still compute (no minimum)
        assert result["fat_tails"]["verdict"] in ("CONFIRMED", "NOT CONFIRMED")

    # -- Line 156: period_cagr_matrix skips periods with too few points ----

    def test_cagr_matrix_skips_short_period(self):
        """Split so pre-period has < 2*n_days points → row skipped."""
        prices, returns = _make_synthetic(300, start="2010-01-04")
        # split_date near start: pre has very few points
        split_date = "2010-01-11"  # ~5 business days into data
        result = period_cagr_matrix(returns, split_date=split_date, n_days=10)
        periods_in_result = set(result["period"].tolist())
        # pre should be skipped (< 20 points), post & full should be present
        assert "pre" not in periods_in_result
        assert "post" in periods_in_result
        assert "full" in periods_in_result

    # -- Line 257 via period_claim_summary (public API) --------------------

    def test_period_claim_summary_short_post_period(self):
        """Post period with < 200 days gives INSUFFICIENT DATA for clustering."""
        prices, returns = _make_synthetic(50, start="2020-01-02")
        # All 50 data points, split so post has < 200 days
        split_date = "2020-01-02"
        result = period_claim_summary(prices, returns, split_date=split_date)
        # post period has all ~49 returns (< 200)
        post = result["post"]
        assert post["n_trading_days"] < 200
        assert post["clustering"]["verdict"] == "INSUFFICIENT DATA"
        assert post["trend_following"]["verdict"] == "INSUFFICIENT DATA"

    # -- Lines 328-329: multi_index_summary CSV not found ------------------

    def test_multi_index_missing_csv(self, tmp_path):
        """Ticker map pointing to non-existent files → empty result list."""
        ticker_map = {
            "MISSING1": {
                "file": "does_not_exist_1.csv",
                "start": "2000-01-03",
                "end": "2020-12-31",
            },
            "MISSING2": {
                "file": "does_not_exist_2.csv",
                "start": "2005-01-03",
                "end": "2020-12-31",
            },
        }
        result = multi_index_summary(
            data_dir=str(tmp_path),
            ticker_map=ticker_map,
            split_date="2011-01-01",
        )
        assert isinstance(result, list)
        assert len(result) == 0

    # -- Lines 382-384: multi_index_summary exception handling -------------

    def test_multi_index_corrupt_csv(self, tmp_path):
        """CSV with bad data triggers exception path, ticker is skipped."""
        bad_csv = tmp_path / "bad_data.csv"
        bad_csv.write_text("not,a,real,csv\nfoo,bar,baz,qux\n")

        ticker_map = {
            "BAD": {
                "file": "bad_data.csv",
                "start": "2000-01-03",
                "end": "2020-12-31",
            },
        }
        result = multi_index_summary(
            data_dir=str(tmp_path),
            ticker_map=ticker_map,
            split_date="2011-01-01",
        )
        assert isinstance(result, list)
        assert len(result) == 0  # bad ticker is skipped

    def test_multi_index_mix_good_and_bad(self, tmp_path):
        """Mix of valid and corrupt CSV: only the valid ticker appears."""
        # Good CSV
        rng = np.random.RandomState(42)
        dates = pd.bdate_range("2000-01-03", "2020-12-31")
        prices = 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, len(dates)))
        df = pd.DataFrame({"Date": dates, "Close": prices})
        df.to_csv(tmp_path / "good.csv", index=False)

        # Bad CSV
        (tmp_path / "corrupt.csv").write_text("garbage\n\n\n")

        ticker_map = {
            "GOOD": {
                "file": "good.csv",
                "start": "2000-01-03",
                "end": "2020-12-31",
            },
            "CORRUPT": {
                "file": "corrupt.csv",
                "start": "2000-01-03",
                "end": "2020-12-31",
            },
        }
        result = multi_index_summary(
            data_dir=str(tmp_path),
            ticker_map=ticker_map,
            split_date="2011-01-01",
        )
        assert len(result) == 1
        assert result[0]["ticker"] == "GOOD"

    # -- Split date at boundary --------------------------------------------

    def test_split_date_at_first_data_point(self, long_prices, long_returns):
        """Split at first data point: pre is empty, post has everything."""
        first_date = str(long_returns.index.min().date())
        result = split_returns_by_date(long_returns, split_date=first_date)
        assert len(result["pre"]) == 0
        assert len(result["post"]) == len(long_returns)

    def test_split_date_at_last_data_point(self, long_prices, long_returns):
        """Split at last data point: pre has all but last, post has 1."""
        last_date = str(long_returns.index.max().date())
        result = split_returns_by_date(long_returns, split_date=last_date)
        assert len(result["post"]) == 1
        assert len(result["pre"]) == len(long_returns) - 1

    # -- Empty pre or post period ------------------------------------------

    def test_split_before_all_data(self, long_prices, long_returns):
        """Split date before all data: pre empty, post = full."""
        result = split_returns_by_date(long_returns, split_date="1990-01-01")
        assert len(result["pre"]) == 0
        assert len(result["post"]) == len(long_returns)

    def test_split_after_all_data(self, long_prices, long_returns):
        """Split date after all data: pre = full, post empty."""
        result = split_returns_by_date(long_returns, split_date="2030-01-01")
        assert len(result["pre"]) == len(long_returns)
        assert len(result["post"]) == 0
