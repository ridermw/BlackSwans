"""Statistical significance tests for validating Faber's claims."""

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd
import scipy.stats


@dataclass
class StatTestResult:
    """Container for a statistical test result."""
    test_name: str
    statistic: float
    p_value: float
    conclusion: str


def chi_square_regime_clustering(
    outlier_down: int,
    outlier_up: int,
    total_down: int,
    total_up: int,
) -> StatTestResult:
    """Chi-squared test for whether outliers cluster in one regime.

    H0: outliers are distributed proportionally across regimes
    H1: outliers cluster disproportionately in one regime

    Parameters
    ----------
    outlier_down : number of outliers in downtrend regime
    outlier_up : number of outliers in uptrend regime
    total_down : total trading days in downtrend regime
    total_up : total trading days in uptrend regime
    """
    total_outliers = outlier_down + outlier_up
    total_days = total_down + total_up
    non_outlier_down = total_down - outlier_down
    non_outlier_up = total_up - outlier_up

    observed = np.array([[outlier_down, outlier_up],
                         [non_outlier_down, non_outlier_up]])
    chi2, p, dof, expected = scipy.stats.chi2_contingency(observed)

    pct_down = outlier_down / total_outliers * 100 if total_outliers else 0
    if p < 0.001:
        conclusion = f"Highly significant clustering (p<0.001): {pct_down:.1f}% of outliers in downtrends"
    elif p < 0.05:
        conclusion = f"Significant clustering (p={p:.4f}): {pct_down:.1f}% of outliers in downtrends"
    else:
        conclusion = f"No significant clustering (p={p:.4f})"

    return StatTestResult("chi_square_regime_clustering", chi2, p, conclusion)


def two_proportion_z_test(
    outlier_down: int,
    outlier_up: int,
    total_down: int,
    total_up: int,
) -> StatTestResult:
    """Two-proportion z-test for outlier rate difference between regimes.

    Tests whether the outlier rate (outliers/total_days) differs between
    downtrend and uptrend regimes.
    """
    p1 = outlier_down / total_down if total_down > 0 else 0
    p2 = outlier_up / total_up if total_up > 0 else 0
    total_outliers = outlier_down + outlier_up
    total_days = total_down + total_up
    p_pooled = total_outliers / total_days if total_days > 0 else 0

    se = np.sqrt(p_pooled * (1 - p_pooled) * (1 / total_down + 1 / total_up))
    if se == 0:
        return StatTestResult("two_proportion_z_test", 0.0, 1.0, "Cannot compute: zero standard error")

    z = (p1 - p2) / se
    p_value = 2 * (1 - scipy.stats.norm.cdf(abs(z)))

    rate_ratio = p1 / p2 if p2 > 0 else float("inf")
    conclusion = (
        f"Outlier rate {rate_ratio:.2f}x higher in downtrends "
        f"(p={p_value:.4f}, z={z:.2f})"
    )
    return StatTestResult("two_proportion_z_test", z, p_value, conclusion)


def normality_tests(returns: pd.Series) -> dict:
    """Run multiple normality tests on a returns series.

    Returns a dict with results from Kolmogorov-Smirnov and Jarque-Bera tests.
    """
    clean = returns.dropna()
    mu, sigma = clean.mean(), clean.std(ddof=0)

    # KS test against normal
    ks_stat, ks_p = scipy.stats.kstest(clean, 'norm', args=(mu, sigma))
    ks_result = StatTestResult(
        "kolmogorov_smirnov",
        ks_stat,
        ks_p,
        f"{'Reject' if ks_p < 0.05 else 'Fail to reject'} normality (KS stat={ks_stat:.4f})"
    )

    # Jarque-Bera test
    jb_stat, jb_p = scipy.stats.jarque_bera(clean)
    jb_result = StatTestResult(
        "jarque_bera",
        jb_stat,
        jb_p,
        f"{'Reject' if jb_p < 0.05 else 'Fail to reject'} normality (JB stat={jb_stat:.1f})"
    )

    # Shapiro-Wilk (only for small samples, scipy limit is 5000)
    sw_result = None
    if len(clean) <= 5000:
        sw_stat, sw_p = scipy.stats.shapiro(clean)
        sw_result = StatTestResult(
            "shapiro_wilk",
            sw_stat,
            sw_p,
            f"{'Reject' if sw_p < 0.05 else 'Fail to reject'} normality (SW stat={sw_stat:.4f})"
        )

    return {
        "ks": ks_result,
        "jb": jb_result,
        "sw": sw_result,
    }


def excess_kurtosis(returns: pd.Series) -> float:
    """Compute excess kurtosis (kurtosis - 3) of returns.

    Normal distribution has excess kurtosis of 0.
    Fat-tailed distributions have positive excess kurtosis.
    """
    return float(scipy.stats.kurtosis(returns.dropna(), fisher=True))


def skewness(returns: pd.Series) -> float:
    """Compute skewness of returns."""
    return float(scipy.stats.skew(returns.dropna()))


def bootstrap_confidence_interval(
    data: pd.Series,
    statistic_func: Callable,
    n_bootstrap: int = 10000,
    confidence: float = 0.95,
    seed: Optional[int] = 42,
) -> dict:
    """Bootstrap confidence interval for any statistic.

    Parameters
    ----------
    data : input data series
    statistic_func : function that takes a Series and returns a scalar
    n_bootstrap : number of bootstrap resamples
    confidence : confidence level (e.g. 0.95 for 95% CI)
    seed : random seed for reproducibility
    """
    rng = np.random.RandomState(seed)
    n = len(data)
    values = np.array(data)
    boot_stats = np.empty(n_bootstrap)

    for i in range(n_bootstrap):
        sample = rng.choice(values, size=n, replace=True)
        boot_stats[i] = statistic_func(pd.Series(sample))

    alpha = 1 - confidence
    lower = np.percentile(boot_stats, 100 * alpha / 2)
    upper = np.percentile(boot_stats, 100 * (1 - alpha / 2))
    point_estimate = statistic_func(data)

    return {
        "point_estimate": point_estimate,
        "ci_lower": lower,
        "ci_upper": upper,
        "confidence": confidence,
        "n_bootstrap": n_bootstrap,
        "std_error": boot_stats.std(),
    }


def max_drawdown(returns: pd.Series) -> float:
    """Compute maximum drawdown from a returns series."""
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return float(drawdown.min())


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Annualised Sharpe ratio from daily returns."""
    excess = returns - risk_free_rate / 252
    if excess.std() == 0:
        return 0.0
    return float(excess.mean() / excess.std() * np.sqrt(252))


def trend_following_backtest(
    prices: pd.Series,
    returns: pd.Series,
    window: int = 200,
) -> pd.DataFrame:
    """Simple trend-following backtest: invested when price > MA, cash otherwise.

    Returns a DataFrame with columns: date, strategy_return, buy_hold_return, regime.
    """
    from .regimes import moving_average_regime

    regimes = moving_average_regime(prices, window)
    valid = regimes.dropna().index
    aligned_returns = returns.reindex(valid).fillna(0)
    aligned_regimes = regimes.reindex(valid)

    # Strategy: hold when uptrend (regime=1), cash when downtrend (regime=0)
    strategy_returns = aligned_returns * aligned_regimes

    result = pd.DataFrame({
        "buy_hold_return": aligned_returns,
        "strategy_return": strategy_returns,
        "regime": aligned_regimes,
    })
    return result
