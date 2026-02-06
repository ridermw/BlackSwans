"""Validate Faber's 4 claims with statistical tests.

Produces structured output for the validation report.
"""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .data.loaders import fetch_price_data
from .data.transforms import compute_daily_returns
from .analysis.outliers import calculate_outlier_stats
from .analysis.scenarios import annualised_return, scenario_returns
from .analysis.regimes import (
    moving_average_regime,
    outlier_regime_counts,
    regime_performance,
)
from .analysis.statistics import (
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
from .io.writers import save_dataframe

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)


def validate_claim1_fat_tails(returns: pd.Series) -> dict:
    """Claim 1: Market returns are fat-tailed (not normally distributed)."""
    results = normality_tests(returns)
    kurt = excess_kurtosis(returns)
    skew = skewness(returns)

    # How many sigma are the largest outliers?
    mu, sigma = returns.mean(), returns.std()
    max_sigma = (returns.max() - mu) / sigma
    min_sigma = (returns.min() - mu) / sigma

    return {
        "claim": "Market returns are fat-tailed",
        "ks_statistic": results["ks"].statistic,
        "ks_p_value": results["ks"].p_value,
        "ks_conclusion": results["ks"].conclusion,
        "jb_statistic": results["jb"].statistic,
        "jb_p_value": results["jb"].p_value,
        "jb_conclusion": results["jb"].conclusion,
        "excess_kurtosis": kurt,
        "skewness": skew,
        "max_return_sigma": max_sigma,
        "min_return_sigma": min_sigma,
        "n_observations": len(returns),
        "verdict": "CONFIRMED" if kurt > 0 and results["jb"].p_value < 0.05 else "NOT CONFIRMED",
    }


def validate_claim2_outsized_influence(returns: pd.Series) -> dict:
    """Claim 2: A small number of extreme days have outsized influence."""
    full_cagr = annualised_return(returns)
    n_days = len(returns)

    rows = []
    for n in [5, 10, 20, 50]:
        _, mb, mw, mboth = scenario_returns(returns, n, n)
        cagr_miss_best = annualised_return(mb)
        cagr_miss_worst = annualised_return(mw)
        cagr_miss_both = annualised_return(mboth)
        rows.append({
            "n_days": n,
            "pct_of_total": n / n_days * 100,
            "cagr_all": full_cagr,
            "cagr_miss_best": cagr_miss_best,
            "cagr_miss_worst": cagr_miss_worst,
            "cagr_miss_both": cagr_miss_both,
            "impact_miss_best": full_cagr - cagr_miss_best,
            "impact_miss_worst": cagr_miss_worst - full_cagr,
        })

    # Bootstrap CI for the "miss 10 best" scenario impact
    def miss_best_10_impact(data):
        _, mb, _, _ = scenario_returns(data, 10, 10)
        return annualised_return(data) - annualised_return(mb)

    ci = bootstrap_confidence_interval(returns, miss_best_10_impact, n_bootstrap=1000, seed=42)

    # Verdict: confirmed if missing even 10 days materially changes CAGR
    impact_10 = rows[1]["impact_miss_best"]  # n=10 row
    verdict = "CONFIRMED" if abs(impact_10) > 0.005 else "NOT CONFIRMED"

    return {
        "claim": "Extreme days have outsized influence on returns",
        "scenarios": rows,
        "bootstrap_ci_miss_best_10": ci,
        "verdict": verdict,
    }


def validate_claim3_clustering(
    returns: pd.Series,
    prices: pd.Series,
) -> dict:
    """Claim 3: Extreme days cluster during bear markets."""
    results = []

    for window in [50, 100, 200, 300]:
        regimes = moving_average_regime(prices, window)
        valid = regimes.dropna()
        total_down = int((valid == 0).sum())
        total_up = int((valid == 1).sum())

        for q in [0.95, 0.99, 0.999]:
            down, up = outlier_regime_counts(returns, regimes, q)
            chi2 = chi_square_regime_clustering(down, up, total_down, total_up)
            z_test = two_proportion_z_test(down, up, total_down, total_up)

            total_outliers = down + up
            pct_down = down / total_outliers * 100 if total_outliers > 0 else 0

            results.append({
                "ma_window": window,
                "quantile": q,
                "outliers_down": down,
                "outliers_up": up,
                "total_down": total_down,
                "total_up": total_up,
                "pct_outliers_in_downtrend": pct_down,
                "chi2_statistic": chi2.statistic,
                "chi2_p_value": chi2.p_value,
                "z_statistic": z_test.statistic,
                "z_p_value": z_test.p_value,
            })

    # Overall verdict: check if p < 0.05 for the main case (200-day MA, 0.99 quantile)
    main_case = [r for r in results if r["ma_window"] == 200 and r["quantile"] == 0.99][0]
    robust = sum(1 for r in results if r["chi2_p_value"] < 0.05)

    return {
        "claim": "Outliers cluster during bear markets",
        "sensitivity_results": results,
        "main_case_p_value": main_case["chi2_p_value"],
        "main_case_pct_downtrend": main_case["pct_outliers_in_downtrend"],
        "robust_count": f"{robust}/{len(results)} parameter combinations significant at p<0.05",
        "verdict": "CONFIRMED" if main_case["chi2_p_value"] < 0.05 else "NOT CONFIRMED",
    }


def validate_claim4_trend_following(
    returns: pd.Series,
    prices: pd.Series,
) -> dict:
    """Claim 4: Simple trend-following can help avoid worst volatility."""
    results = []

    for window in [50, 100, 200, 300]:
        bt = trend_following_backtest(prices, returns, window)
        bh = bt["buy_hold_return"]
        st = bt["strategy_return"]

        bh_cagr = annualised_return(bh)
        st_cagr = annualised_return(st)
        bh_sharpe = sharpe_ratio(bh)
        st_sharpe = sharpe_ratio(st)
        bh_dd = max_drawdown(bh)
        st_dd = max_drawdown(st)
        bh_vol = float(bh.std() * np.sqrt(252))
        st_vol = float(st.std() * np.sqrt(252))

        results.append({
            "ma_window": window,
            "buy_hold_cagr": bh_cagr,
            "strategy_cagr": st_cagr,
            "buy_hold_sharpe": bh_sharpe,
            "strategy_sharpe": st_sharpe,
            "buy_hold_max_drawdown": bh_dd,
            "strategy_max_drawdown": st_dd,
            "buy_hold_volatility": bh_vol,
            "strategy_volatility": st_vol,
        })

    # Main case: 200-day MA
    main = [r for r in results if r["ma_window"] == 200][0]
    verdict = (
        "CONFIRMED" if main["strategy_max_drawdown"] > main["buy_hold_max_drawdown"]
        else "NOT CONFIRMED"
    )

    return {
        "claim": "Trend-following reduces worst volatility",
        "backtest_results": results,
        "main_case_200dma": main,
        "verdict": verdict,
    }


def run_full_validation(
    csv_path: str,
    ticker: str = "^GSPC",
    start: str = "1928-09-01",
    end: str = "2010-12-31",
    output_dir: str = "output/validation",
    prices_df: "Optional[pd.DataFrame]" = None,
) -> dict:
    """Run complete validation of all 4 claims.

    If *prices_df* is supplied it is used directly, skipping file I/O.
    """
    # codeql[py/path-injection] — output_dir is either a hardcoded default,
    # a CLI argument from the local user, or sanitised by the API layer
    # before reaching this function.
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if prices_df is None:
        logging.info(f"Loading data: {ticker} {start} to {end}")
        prices_df = fetch_price_data(ticker, start, end, csv_path=csv_path)
    prices = prices_df["Close"]
    returns = compute_daily_returns(prices)

    logging.info("Validating Claim 1: Fat tails...")
    c1 = validate_claim1_fat_tails(returns)

    logging.info("Validating Claim 2: Outsized influence...")
    c2 = validate_claim2_outsized_influence(returns)

    logging.info("Validating Claim 3: Clustering in bear markets...")
    c3 = validate_claim3_clustering(returns, prices)

    logging.info("Validating Claim 4: Trend-following effectiveness...")
    c4 = validate_claim4_trend_following(returns, prices)

    # Save claim 3 sensitivity analysis as CSV
    df_clustering = pd.DataFrame(c3["sensitivity_results"])
    save_dataframe(df_clustering, out / "clustering_sensitivity.csv")

    # Save claim 4 backtest results as CSV
    df_backtest = pd.DataFrame(c4["backtest_results"])
    save_dataframe(df_backtest, out / "backtest_results.csv")

    # Save claim 2 scenarios as CSV
    df_scenarios = pd.DataFrame(c2["scenarios"])
    save_dataframe(df_scenarios, out / "scenario_sensitivity.csv")

    # Summary
    summary = {
        "ticker": ticker,
        "period": f"{start} to {end}",
        "n_trading_days": len(returns),
        "claims": {
            "1_fat_tails": c1["verdict"],
            "2_outsized_influence": c2["verdict"],
            "3_clustering": c3["verdict"],
            "4_trend_following": c4["verdict"],
        },
        "details": {
            "claim1": c1,
            "claim2": {k: v for k, v in c2.items() if k != "scenarios"},
            "claim3": {k: v for k, v in c3.items() if k != "sensitivity_results"},
            "claim4": {k: v for k, v in c4.items() if k != "backtest_results"},
        },
    }

    # Save summary as JSON (convert numpy types)
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    with open(out / "validation_summary.json", "w") as f:
        json.dump(summary, f, indent=2, cls=NumpyEncoder)

    logging.info(f"Validation complete. Results in {out}")
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate Faber's 4 claims")
    parser.add_argument("--csv", type=str, required=True)
    parser.add_argument("--ticker", type=str, default="^GSPC")
    parser.add_argument("--start", type=str, default="1928-09-01")
    parser.add_argument("--end", type=str, default="2010-12-31")
    parser.add_argument("--output-dir", type=str, default="output/validation")
    args = parser.parse_args()

    summary = run_full_validation(
        csv_path=args.csv,
        ticker=args.ticker,
        start=args.start,
        end=args.end,
        output_dir=args.output_dir,
    )

    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    for claim_key, verdict in summary["claims"].items():
        print(f"  {claim_key}: {verdict}")
    print("=" * 60)
