"""Tests for blackswans.validate_claims module."""

import json

import numpy as np
import pandas as pd
import pytest

from blackswans.validate_claims import (
    run_full_validation,
    validate_claim1_fat_tails,
    validate_claim2_outsized_influence,
    validate_claim3_clustering,
    validate_claim4_trend_following,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def large_price_series():
    """1500-day synthetic price series for reliable statistical results."""
    rng = np.random.RandomState(42)
    dates = pd.bdate_range("2015-01-01", periods=1500)
    daily_returns = rng.normal(0.0004, 0.012, size=1500)
    prices = 100 * np.cumprod(1 + daily_returns)
    return pd.Series(prices, index=dates, name="Close")


@pytest.fixture
def large_returns_series(large_price_series):
    """Daily returns from the 1500-day price series."""
    r = large_price_series.pct_change().dropna()
    r.name = "Return"
    return r


@pytest.fixture
def fat_tailed_returns():
    """Returns with injected outliers to guarantee fat-tailed detection."""
    rng = np.random.RandomState(99)
    dates = pd.bdate_range("2015-01-01", periods=1500)
    base = rng.normal(0.0004, 0.008, size=1500)
    # Inject extreme outliers
    for idx in [50, 200, 400, 600, 800, 1000, 1200]:
        base[idx] = rng.choice([-1, 1]) * rng.uniform(0.08, 0.15)
    return pd.Series(base, index=dates, name="Return")


@pytest.fixture
def fat_tailed_prices(fat_tailed_returns):
    """Price series reconstructed from fat-tailed returns."""
    prices = 100 * np.cumprod(1 + fat_tailed_returns)
    prices.name = "Close"
    return prices


@pytest.fixture
def normal_returns():
    """Nearly Gaussian returns with no outliers (for structure tests)."""
    rng = np.random.RandomState(123)
    dates = pd.bdate_range("2015-01-01", periods=1000)
    values = rng.normal(0.0, 0.005, size=1000)
    return pd.Series(values, index=dates, name="Return")


# ===================================================================
# Claim 1 – Fat Tails
# ===================================================================

class TestClaim1FatTails:
    """Tests for validate_claim1_fat_tails()."""

    REQUIRED_KEYS = {
        "claim",
        "ks_statistic",
        "ks_p_value",
        "ks_conclusion",
        "jb_statistic",
        "jb_p_value",
        "jb_conclusion",
        "excess_kurtosis",
        "skewness",
        "max_return_sigma",
        "min_return_sigma",
        "n_observations",
        "verdict",
    }

    def test_returns_all_required_keys(self, returns_series):
        result = validate_claim1_fat_tails(returns_series)
        assert self.REQUIRED_KEYS.issubset(result.keys())

    def test_verdict_is_valid_string(self, returns_series):
        result = validate_claim1_fat_tails(returns_series)
        assert result["verdict"] in ("CONFIRMED", "NOT CONFIRMED")

    def test_n_observations_matches_input(self, returns_series):
        result = validate_claim1_fat_tails(returns_series)
        assert result["n_observations"] == len(returns_series)

    def test_claim_text(self, returns_series):
        result = validate_claim1_fat_tails(returns_series)
        assert result["claim"] == "Market returns are fat-tailed"

    def test_numeric_types(self, returns_series):
        result = validate_claim1_fat_tails(returns_series)
        for key in ("ks_statistic", "ks_p_value", "jb_statistic", "jb_p_value",
                     "excess_kurtosis", "skewness", "max_return_sigma", "min_return_sigma"):
            assert isinstance(result[key], (int, float, np.floating))

    def test_fat_tailed_data_confirmed(self, fat_tailed_returns):
        """Injected outliers should yield excess kurtosis > 0 and JB p < 0.05."""
        result = validate_claim1_fat_tails(fat_tailed_returns)
        assert result["excess_kurtosis"] > 0
        assert result["jb_p_value"] < 0.05
        assert result["verdict"] == "CONFIRMED"

    def test_sigma_extremes_are_reasonable(self, fat_tailed_returns):
        result = validate_claim1_fat_tails(fat_tailed_returns)
        assert result["max_return_sigma"] > 3
        assert result["min_return_sigma"] < -3

    def test_p_values_in_valid_range(self, returns_series):
        result = validate_claim1_fat_tails(returns_series)
        assert 0 <= result["ks_p_value"] <= 1
        assert 0 <= result["jb_p_value"] <= 1

    def test_verdict_logic_not_confirmed(self, normal_returns):
        """With near-Gaussian data, kurtosis or JB may not trigger CONFIRMED."""
        result = validate_claim1_fat_tails(normal_returns)
        # Verify the structure is still correct regardless of verdict
        assert self.REQUIRED_KEYS.issubset(result.keys())
        assert result["verdict"] in ("CONFIRMED", "NOT CONFIRMED")


# ===================================================================
# Claim 2 – Outsized Influence
# ===================================================================

class TestClaim2OutsizedInfluence:
    """Tests for validate_claim2_outsized_influence()."""

    SCENARIO_KEYS = {
        "n_days", "pct_of_total", "cagr_all", "cagr_miss_best",
        "cagr_miss_worst", "cagr_miss_both", "impact_miss_best",
        "impact_miss_worst",
    }

    CI_KEYS = {
        "point_estimate", "ci_lower", "ci_upper",
        "confidence", "n_bootstrap", "std_error",
    }

    TOP_LEVEL_KEYS = {"claim", "scenarios", "bootstrap_ci_miss_best_10", "verdict"}

    def test_returns_top_level_keys(self, large_returns_series):
        result = validate_claim2_outsized_influence(large_returns_series)
        assert self.TOP_LEVEL_KEYS.issubset(result.keys())

    def test_four_scenarios(self, large_returns_series):
        result = validate_claim2_outsized_influence(large_returns_series)
        assert len(result["scenarios"]) == 4

    def test_scenario_n_days_values(self, large_returns_series):
        result = validate_claim2_outsized_influence(large_returns_series)
        n_values = [s["n_days"] for s in result["scenarios"]]
        assert n_values == [5, 10, 20, 50]

    def test_scenario_keys(self, large_returns_series):
        result = validate_claim2_outsized_influence(large_returns_series)
        for scenario in result["scenarios"]:
            assert self.SCENARIO_KEYS.issubset(scenario.keys())

    def test_bootstrap_ci_keys(self, large_returns_series):
        result = validate_claim2_outsized_influence(large_returns_series)
        ci = result["bootstrap_ci_miss_best_10"]
        assert self.CI_KEYS.issubset(ci.keys())

    def test_bootstrap_ci_ordering(self, large_returns_series):
        result = validate_claim2_outsized_influence(large_returns_series)
        ci = result["bootstrap_ci_miss_best_10"]
        assert ci["ci_lower"] <= ci["point_estimate"] <= ci["ci_upper"]

    def test_impact_increases_with_n(self, large_returns_series):
        """Removing more extreme days should have a larger impact."""
        result = validate_claim2_outsized_influence(large_returns_series)
        impacts = [abs(s["impact_miss_best"]) for s in result["scenarios"]]
        # Each impact should be >= the previous (monotonically non-decreasing)
        for i in range(1, len(impacts)):
            assert impacts[i] >= impacts[i - 1]

    def test_cagr_miss_best_lower_than_full(self, large_returns_series):
        """Missing the best days should reduce CAGR."""
        result = validate_claim2_outsized_influence(large_returns_series)
        for scenario in result["scenarios"]:
            assert scenario["cagr_miss_best"] < scenario["cagr_all"]

    def test_cagr_miss_worst_higher_than_full(self, large_returns_series):
        """Missing the worst days should improve CAGR."""
        result = validate_claim2_outsized_influence(large_returns_series)
        for scenario in result["scenarios"]:
            assert scenario["cagr_miss_worst"] > scenario["cagr_all"]

    def test_pct_of_total_correct(self, large_returns_series):
        result = validate_claim2_outsized_influence(large_returns_series)
        n_total = len(large_returns_series)
        for scenario in result["scenarios"]:
            expected_pct = scenario["n_days"] / n_total * 100
            assert abs(scenario["pct_of_total"] - expected_pct) < 1e-10

    def test_verdict_is_valid(self, large_returns_series):
        result = validate_claim2_outsized_influence(large_returns_series)
        assert result["verdict"] in ("CONFIRMED", "NOT CONFIRMED")

    def test_verdict_confirmed_when_impact_large(self, large_returns_series):
        """With enough data, removing 10 best days should impact CAGR by > 0.5%."""
        result = validate_claim2_outsized_influence(large_returns_series)
        impact_10 = abs(result["scenarios"][1]["impact_miss_best"])
        if impact_10 > 0.005:
            assert result["verdict"] == "CONFIRMED"
        else:
            assert result["verdict"] == "NOT CONFIRMED"

    def test_claim_text(self, large_returns_series):
        result = validate_claim2_outsized_influence(large_returns_series)
        assert result["claim"] == "Extreme days have outsized influence on returns"


# ===================================================================
# Claim 3 – Clustering
# ===================================================================

class TestClaim3Clustering:
    """Tests for validate_claim3_clustering()."""

    RESULT_KEYS = {
        "ma_window", "quantile", "outliers_down", "outliers_up",
        "total_down", "total_up", "pct_outliers_in_downtrend",
        "chi2_statistic", "chi2_p_value", "z_statistic", "z_p_value",
    }

    TOP_LEVEL_KEYS = {
        "claim", "sensitivity_results", "main_case_p_value",
        "main_case_pct_downtrend", "robust_count", "verdict",
    }

    def test_returns_top_level_keys(self, large_returns_series, large_price_series):
        result = validate_claim3_clustering(large_returns_series, large_price_series)
        assert self.TOP_LEVEL_KEYS.issubset(result.keys())

    def test_twelve_sensitivity_results(self, large_returns_series, large_price_series):
        """4 MA windows × 3 quantiles = 12 combinations."""
        result = validate_claim3_clustering(large_returns_series, large_price_series)
        assert len(result["sensitivity_results"]) == 12

    def test_sensitivity_result_keys(self, large_returns_series, large_price_series):
        result = validate_claim3_clustering(large_returns_series, large_price_series)
        for item in result["sensitivity_results"]:
            assert self.RESULT_KEYS.issubset(item.keys())

    def test_ma_windows_and_quantiles(self, large_returns_series, large_price_series):
        result = validate_claim3_clustering(large_returns_series, large_price_series)
        windows = sorted({r["ma_window"] for r in result["sensitivity_results"]})
        quantiles = sorted({r["quantile"] for r in result["sensitivity_results"]})
        assert windows == [50, 100, 200, 300]
        assert quantiles == [0.95, 0.99, 0.999]

    def test_main_case_p_value_is_numeric(self, large_returns_series, large_price_series):
        result = validate_claim3_clustering(large_returns_series, large_price_series)
        assert isinstance(result["main_case_p_value"], (int, float, np.floating))
        assert 0 <= result["main_case_p_value"] <= 1

    def test_main_case_pct_downtrend_range(self, large_returns_series, large_price_series):
        result = validate_claim3_clustering(large_returns_series, large_price_series)
        pct = result["main_case_pct_downtrend"]
        assert 0 <= pct <= 100

    def test_verdict_consistent_with_p_value(self, large_returns_series, large_price_series):
        result = validate_claim3_clustering(large_returns_series, large_price_series)
        if result["main_case_p_value"] < 0.05:
            assert result["verdict"] == "CONFIRMED"
        else:
            assert result["verdict"] == "NOT CONFIRMED"

    def test_outlier_counts_non_negative(self, large_returns_series, large_price_series):
        result = validate_claim3_clustering(large_returns_series, large_price_series)
        for item in result["sensitivity_results"]:
            assert item["outliers_down"] >= 0
            assert item["outliers_up"] >= 0
            assert item["total_down"] >= 0
            assert item["total_up"] >= 0

    def test_chi2_statistic_non_negative(self, large_returns_series, large_price_series):
        result = validate_claim3_clustering(large_returns_series, large_price_series)
        for item in result["sensitivity_results"]:
            assert item["chi2_statistic"] >= 0

    def test_robust_count_format(self, large_returns_series, large_price_series):
        result = validate_claim3_clustering(large_returns_series, large_price_series)
        robust = result["robust_count"]
        assert "12" in robust
        assert "significant at p<0.05" in robust

    def test_claim_text(self, large_returns_series, large_price_series):
        result = validate_claim3_clustering(large_returns_series, large_price_series)
        assert result["claim"] == "Outliers cluster during bear markets"

    def test_higher_quantile_fewer_outliers(self, large_returns_series, large_price_series):
        """0.999 quantile should flag fewer outliers than 0.95 for same MA window."""
        result = validate_claim3_clustering(large_returns_series, large_price_series)
        by_window = {}
        for item in result["sensitivity_results"]:
            by_window.setdefault(item["ma_window"], []).append(item)
        for window, items in by_window.items():
            items_sorted = sorted(items, key=lambda x: x["quantile"])
            total_outliers = [i["outliers_down"] + i["outliers_up"] for i in items_sorted]
            for i in range(1, len(total_outliers)):
                assert total_outliers[i] <= total_outliers[i - 1]


# ===================================================================
# Claim 4 – Trend Following
# ===================================================================

class TestClaim4TrendFollowing:
    """Tests for validate_claim4_trend_following()."""

    RESULT_KEYS = {
        "ma_window", "buy_hold_cagr", "strategy_cagr",
        "buy_hold_sharpe", "strategy_sharpe",
        "buy_hold_max_drawdown", "strategy_max_drawdown",
        "buy_hold_volatility", "strategy_volatility",
    }

    TOP_LEVEL_KEYS = {
        "claim", "backtest_results", "main_case_200dma", "verdict",
    }

    def test_returns_top_level_keys(self, large_returns_series, large_price_series):
        result = validate_claim4_trend_following(large_returns_series, large_price_series)
        assert self.TOP_LEVEL_KEYS.issubset(result.keys())

    def test_four_backtest_results(self, large_returns_series, large_price_series):
        result = validate_claim4_trend_following(large_returns_series, large_price_series)
        assert len(result["backtest_results"]) == 4

    def test_backtest_result_keys(self, large_returns_series, large_price_series):
        result = validate_claim4_trend_following(large_returns_series, large_price_series)
        for item in result["backtest_results"]:
            assert self.RESULT_KEYS.issubset(item.keys())

    def test_ma_windows(self, large_returns_series, large_price_series):
        result = validate_claim4_trend_following(large_returns_series, large_price_series)
        windows = [r["ma_window"] for r in result["backtest_results"]]
        assert windows == [50, 100, 200, 300]

    def test_main_case_is_200dma(self, large_returns_series, large_price_series):
        result = validate_claim4_trend_following(large_returns_series, large_price_series)
        assert result["main_case_200dma"]["ma_window"] == 200

    def test_drawdowns_are_negative(self, large_returns_series, large_price_series):
        """Max drawdown should be ≤ 0 (expressed as negative or zero)."""
        result = validate_claim4_trend_following(large_returns_series, large_price_series)
        for item in result["backtest_results"]:
            assert item["buy_hold_max_drawdown"] <= 0
            assert item["strategy_max_drawdown"] <= 0

    def test_volatilities_positive(self, large_returns_series, large_price_series):
        result = validate_claim4_trend_following(large_returns_series, large_price_series)
        for item in result["backtest_results"]:
            assert item["buy_hold_volatility"] > 0
            assert item["strategy_volatility"] > 0

    def test_verdict_consistent_with_drawdown(self, large_returns_series, large_price_series):
        """Verdict CONFIRMED when strategy drawdown > buy-hold drawdown (less negative)."""
        result = validate_claim4_trend_following(large_returns_series, large_price_series)
        main = result["main_case_200dma"]
        if main["strategy_max_drawdown"] > main["buy_hold_max_drawdown"]:
            assert result["verdict"] == "CONFIRMED"
        else:
            assert result["verdict"] == "NOT CONFIRMED"

    def test_verdict_is_valid(self, large_returns_series, large_price_series):
        result = validate_claim4_trend_following(large_returns_series, large_price_series)
        assert result["verdict"] in ("CONFIRMED", "NOT CONFIRMED")

    def test_claim_text(self, large_returns_series, large_price_series):
        result = validate_claim4_trend_following(large_returns_series, large_price_series)
        assert result["claim"] == "Trend-following reduces worst volatility"

    def test_strategy_volatility_leq_buy_hold(self, large_returns_series, large_price_series):
        """Trend strategy sits in cash during downtrends, so volatility should be ≤ buy-hold."""
        result = validate_claim4_trend_following(large_returns_series, large_price_series)
        for item in result["backtest_results"]:
            assert item["strategy_volatility"] <= item["buy_hold_volatility"] + 1e-10


# ===================================================================
# run_full_validation
# ===================================================================

class TestRunFullValidation:
    """Tests for run_full_validation() orchestrator."""

    @pytest.fixture
    def prices_df(self, large_price_series):
        """DataFrame wrapper expected by run_full_validation."""
        return pd.DataFrame({"Close": large_price_series})

    def test_output_structure(self, prices_df, tmp_path):
        summary = run_full_validation(
            csv_path="unused",
            ticker="TEST",
            start="2015-01-01",
            end="2021-01-01",
            output_dir=str(tmp_path),
            prices_df=prices_df,
        )
        assert "ticker" in summary
        assert "period" in summary
        assert "n_trading_days" in summary
        assert "claims" in summary
        assert "details" in summary

    def test_claims_dict_has_all_four(self, prices_df, tmp_path):
        summary = run_full_validation(
            csv_path="unused",
            ticker="TEST",
            start="2015-01-01",
            end="2021-01-01",
            output_dir=str(tmp_path),
            prices_df=prices_df,
        )
        expected_keys = {
            "1_fat_tails", "2_outsized_influence",
            "3_clustering", "4_trend_following",
        }
        assert expected_keys == set(summary["claims"].keys())

    def test_all_verdicts_are_valid(self, prices_df, tmp_path):
        summary = run_full_validation(
            csv_path="unused",
            ticker="TEST",
            start="2015-01-01",
            end="2021-01-01",
            output_dir=str(tmp_path),
            prices_df=prices_df,
        )
        for verdict in summary["claims"].values():
            assert verdict in ("CONFIRMED", "NOT CONFIRMED")

    def test_details_has_all_claims(self, prices_df, tmp_path):
        summary = run_full_validation(
            csv_path="unused",
            ticker="TEST",
            start="2015-01-01",
            end="2021-01-01",
            output_dir=str(tmp_path),
            prices_df=prices_df,
        )
        expected = {"claim1", "claim2", "claim3", "claim4"}
        assert expected == set(summary["details"].keys())

    def test_ticker_and_period_stored(self, prices_df, tmp_path):
        summary = run_full_validation(
            csv_path="unused",
            ticker="^GSPC",
            start="2015-01-01",
            end="2021-01-01",
            output_dir=str(tmp_path),
            prices_df=prices_df,
        )
        assert summary["ticker"] == "^GSPC"
        assert summary["period"] == "2015-01-01 to 2021-01-01"

    def test_n_trading_days_correct(self, prices_df, tmp_path):
        summary = run_full_validation(
            csv_path="unused",
            ticker="TEST",
            start="2015-01-01",
            end="2021-01-01",
            output_dir=str(tmp_path),
            prices_df=prices_df,
        )
        # Returns drop 1 row from pct_change
        expected = len(prices_df) - 1
        assert summary["n_trading_days"] == expected

    def test_creates_output_files(self, prices_df, tmp_path):
        run_full_validation(
            csv_path="unused",
            ticker="TEST",
            start="2015-01-01",
            end="2021-01-01",
            output_dir=str(tmp_path),
            prices_df=prices_df,
        )
        assert (tmp_path / "validation_summary.json").exists()
        assert (tmp_path / "clustering_sensitivity.csv").exists()
        assert (tmp_path / "backtest_results.csv").exists()
        assert (tmp_path / "scenario_sensitivity.csv").exists()

    def test_json_file_is_valid(self, prices_df, tmp_path):
        run_full_validation(
            csv_path="unused",
            ticker="TEST",
            start="2015-01-01",
            end="2021-01-01",
            output_dir=str(tmp_path),
            prices_df=prices_df,
        )
        with open(tmp_path / "validation_summary.json") as f:
            data = json.load(f)
        assert "claims" in data
        assert "details" in data

    def test_json_numpy_types_serialized(self, prices_df, tmp_path):
        """Numpy types should be converted; loading JSON should not fail."""
        run_full_validation(
            csv_path="unused",
            ticker="TEST",
            start="2015-01-01",
            end="2021-01-01",
            output_dir=str(tmp_path),
            prices_df=prices_df,
        )
        with open(tmp_path / "validation_summary.json") as f:
            raw = f.read()
        # Verify it's parseable and has no numpy repr strings
        data = json.loads(raw)
        assert "numpy" not in raw.lower()
        assert isinstance(data["n_trading_days"], int)

    def test_csv_files_have_rows(self, prices_df, tmp_path):
        run_full_validation(
            csv_path="unused",
            ticker="TEST",
            start="2015-01-01",
            end="2021-01-01",
            output_dir=str(tmp_path),
            prices_df=prices_df,
        )
        clustering = pd.read_csv(tmp_path / "clustering_sensitivity.csv")
        backtest = pd.read_csv(tmp_path / "backtest_results.csv")
        scenarios = pd.read_csv(tmp_path / "scenario_sensitivity.csv")
        assert len(clustering) == 12
        assert len(backtest) == 4
        assert len(scenarios) == 4

    def test_creates_output_dir_if_missing(self, prices_df, tmp_path):
        nested = tmp_path / "deep" / "nested" / "dir"
        run_full_validation(
            csv_path="unused",
            ticker="TEST",
            start="2015-01-01",
            end="2021-01-01",
            output_dir=str(nested),
            prices_df=prices_df,
        )
        assert nested.exists()
        assert (nested / "validation_summary.json").exists()

    def test_details_claim2_excludes_scenarios(self, prices_df, tmp_path):
        """summary['details']['claim2'] should not contain the scenarios list."""
        summary = run_full_validation(
            csv_path="unused",
            ticker="TEST",
            start="2015-01-01",
            end="2021-01-01",
            output_dir=str(tmp_path),
            prices_df=prices_df,
        )
        assert "scenarios" not in summary["details"]["claim2"]

    def test_details_claim3_excludes_sensitivity(self, prices_df, tmp_path):
        summary = run_full_validation(
            csv_path="unused",
            ticker="TEST",
            start="2015-01-01",
            end="2021-01-01",
            output_dir=str(tmp_path),
            prices_df=prices_df,
        )
        assert "sensitivity_results" not in summary["details"]["claim3"]

    def test_details_claim4_excludes_backtest_results(self, prices_df, tmp_path):
        summary = run_full_validation(
            csv_path="unused",
            ticker="TEST",
            start="2015-01-01",
            end="2021-01-01",
            output_dir=str(tmp_path),
            prices_df=prices_df,
        )
        assert "backtest_results" not in summary["details"]["claim4"]
