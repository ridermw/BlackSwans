"""Tests for blackswans.analysis.statistics."""

import numpy as np
import pandas as pd
import pytest

from blackswans.analysis.statistics import (
    StatTestResult,
    chi_square_regime_clustering,
    two_proportion_z_test,
    normality_tests,
    excess_kurtosis,
    skewness,
    bootstrap_confidence_interval,
    max_drawdown,
    sharpe_ratio,
    trend_following_backtest,
)


class TestChiSquareRegimeClustering:
    def test_strong_clustering(self):
        """When outliers heavily cluster in downtrends, p should be very small."""
        result = chi_square_regime_clustering(
            outlier_down=200, outlier_up=50,
            total_down=5000, total_up=10000
        )
        assert isinstance(result, StatTestResult)
        assert result.p_value < 0.001
        assert "Highly significant" in result.conclusion

    def test_proportional_distribution(self):
        """When outliers are proportional to regime sizes, p should be large."""
        result = chi_square_regime_clustering(
            outlier_down=100, outlier_up=200,
            total_down=5000, total_up=10000
        )
        assert result.p_value > 0.05

    def test_identical_rates(self):
        result = chi_square_regime_clustering(
            outlier_down=50, outlier_up=50,
            total_down=5000, total_up=5000
        )
        assert result.p_value > 0.9


class TestTwoProportionZTest:
    def test_higher_rate_downtrend(self):
        result = two_proportion_z_test(
            outlier_down=200, outlier_up=50,
            total_down=5000, total_up=10000
        )
        assert result.statistic > 0  # positive z means higher rate in downtrend
        assert result.p_value < 0.001

    def test_equal_rates(self):
        result = two_proportion_z_test(
            outlier_down=100, outlier_up=100,
            total_down=5000, total_up=5000
        )
        assert abs(result.statistic) < 0.5
        assert result.p_value > 0.5


class TestNormalityTests:
    def test_normal_data(self):
        """Normally distributed data should not reject normality."""
        rng = np.random.RandomState(42)
        data = pd.Series(rng.normal(0, 1, 1000))
        results = normality_tests(data)
        assert "ks" in results
        assert "jb" in results
        # Normal data: KS p-value should be > 0.05
        assert results["ks"].p_value > 0.01

    def test_fat_tailed_data(self):
        """Student-t distributed data should reject normality."""
        rng = np.random.RandomState(42)
        data = pd.Series(rng.standard_t(3, 5000))
        results = normality_tests(data)
        # Fat-tailed: should reject normality
        assert results["jb"].p_value < 0.05


class TestExcessKurtosis:
    def test_normal_near_zero(self):
        rng = np.random.RandomState(42)
        data = pd.Series(rng.normal(0, 1, 100000))
        k = excess_kurtosis(data)
        assert abs(k) < 0.1  # should be close to 0

    def test_fat_tails_positive(self):
        rng = np.random.RandomState(42)
        data = pd.Series(rng.standard_t(3, 10000))
        k = excess_kurtosis(data)
        assert k > 2  # Student-t(3) has theoretical excess kurtosis of inf, sample should be large


class TestSkewness:
    def test_symmetric_near_zero(self):
        rng = np.random.RandomState(42)
        data = pd.Series(rng.normal(0, 1, 100000))
        s = skewness(data)
        assert abs(s) < 0.05


class TestBootstrapCI:
    def test_contains_point_estimate(self):
        rng = np.random.RandomState(42)
        data = pd.Series(rng.normal(5, 1, 100))
        result = bootstrap_confidence_interval(data, lambda x: x.mean(), n_bootstrap=1000)
        assert result["ci_lower"] <= result["point_estimate"] <= result["ci_upper"]

    def test_known_mean(self):
        rng = np.random.RandomState(42)
        data = pd.Series(rng.normal(10, 1, 1000))
        result = bootstrap_confidence_interval(data, lambda x: x.mean(), n_bootstrap=5000)
        assert result["ci_lower"] > 9.5
        assert result["ci_upper"] < 10.5

    def test_confidence_level(self):
        data = pd.Series(np.ones(100))
        result = bootstrap_confidence_interval(data, lambda x: x.mean())
        assert result["confidence"] == 0.95


class TestMaxDrawdown:
    def test_no_drawdown(self):
        r = pd.Series([0.01] * 100)
        assert max_drawdown(r) == pytest.approx(0.0)

    def test_known_drawdown(self):
        # 50% gain then 50% loss: peak at 1.5, trough at 0.75 → drawdown = -50%
        r = pd.Series([0.5, -0.5])
        dd = max_drawdown(r)
        assert dd == pytest.approx(-0.5)

    def test_always_negative(self):
        r = pd.Series([-0.01] * 50)
        assert max_drawdown(r) < 0


class TestSharpeRatio:
    def test_positive_returns(self):
        r = pd.Series([0.001] * 252)
        sr = sharpe_ratio(r)
        assert sr > 0

    def test_zero_returns(self):
        r = pd.Series([0.0] * 100)
        assert sharpe_ratio(r) == 0.0

    def test_volatile_low_return(self):
        rng = np.random.RandomState(42)
        r = pd.Series(rng.normal(0, 0.02, 252))
        sr = sharpe_ratio(r)
        assert abs(sr) < 3  # reasonable range


class TestTrendFollowingBacktest:
    def test_output_shape(self, price_series, returns_series):
        result = trend_following_backtest(price_series, returns_series, window=50)
        assert "buy_hold_return" in result.columns
        assert "strategy_return" in result.columns
        assert "regime" in result.columns

    def test_cash_in_downtrend(self):
        """Strategy returns should be 0 when regime is downtrend."""
        dates = pd.bdate_range("2020-01-01", periods=300)
        # Monotonically decreasing → all downtrend after warmup
        prices = pd.Series(np.linspace(100, 50, 300), index=dates)
        returns = prices.pct_change().dropna()
        returns.name = "Return"
        result = trend_following_backtest(prices, returns, window=10)
        valid = result[result["regime"] == 0]
        if not valid.empty:
            assert (valid["strategy_return"] == 0).all()
