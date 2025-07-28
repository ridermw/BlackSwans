"""
validate_outliers.py
====================

This script reproduces the key analyses from Mebane Faber's paper
"Where the Black Swans Hide & The 10 Best Days Myth" (2011) and
extends the analysis to arbitrary date ranges.  The goal of the
original paper was to show that a small handful of extreme market
events – both positive and negative – have an outsized influence on
long‑term investment outcomes.  Faber also examined how these
outliers cluster during bear markets and how simple trend‑following
rules can help investors sidestep the worst of the volatility.

The script fetches price data for a chosen equity index, computes
daily returns, identifies the best and worst tails according to
user‑supplied quantiles, and calculates descriptive statistics for
those tails.  It then evaluates several buy/sell scenarios by
zeroing out the returns of selected days (e.g. missing the best
days, worst days, or both) and reports the resulting annualised
returns.  Finally, it classifies each day as being in an uptrend or
downtrend based on a moving average and compares the distribution of
outlier days across these regimes.  Summary statistics and plots are
written to an output directory for further inspection.

Example usage:

    python validate_outliers.py \
        --ticker ^GSPC \
        --start 1928-09-01 \
        --end 2010-12-31 \
        --quantiles 0.99 0.999 \
        --ma-window 200 \
        --output-dir output

Dependencies
------------
The script relies on pandas, numpy, matplotlib, scipy and
yfinance.  Install these packages with `pip install -r requirements.txt`.
Note: The repository includes a ``requirements.txt`` file listing
minimal versions.  The script itself does not need internet
connectivity at runtime if you supply pre‑downloaded CSV files via
``--csv``; otherwise it will attempt to fetch data from Yahoo!
Finance via ``yfinance``.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None  # Will be checked at runtime


def fetch_price_data(
    ticker: str,
    start: str,
    end: str,
    csv_path: Optional[str] = None,
) -> pd.DataFrame:
    """Load historical price data.

    If ``csv_path`` is provided and the file exists, it will be
    loaded instead of hitting the network.  Otherwise the function
    attempts to download daily price history via ``yfinance``.

    Parameters
    ----------
    ticker: str
        The ticker symbol understood by Yahoo Finance (e.g. '^GSPC').
    start: str
        ISO formatted start date (inclusive).
    end: str
        ISO formatted end date (inclusive).
    csv_path: Optional[str]
        Path to a local CSV file containing historical prices with at
        least a ``Date`` column and a ``Close`` or ``Adj Close`` column.

    Returns
    -------
    pd.DataFrame
        DataFrame indexed by datetime with a 'Close' column representing
        daily closing prices.  The index will contain all trading days
        between start and end inclusive.
    """
    if csv_path and os.path.exists(csv_path):
        df = pd.read_csv(csv_path, parse_dates=["Date"]).set_index("Date").sort_index()
        if "Close" not in df.columns and "Adj Close" in df.columns:
            df["Close"] = df["Adj Close"]
        return df[["Close"]].loc[start:end]

    if yf is None:
        raise RuntimeError(
            "yfinance is not installed and no CSV file was provided; "
            "install yfinance or provide --csv path"
        )
    data = yf.download(ticker, start=start, end=end, progress=False)
    if data.empty:
        raise ValueError(f"No data returned for {ticker} between {start} and {end}")
    data = data.rename(columns={"Adj Close": "Close"})
    return data[["Close"]]


def compute_daily_returns(prices: pd.Series) -> pd.Series:
    """Compute percentage daily returns from closing prices.

    Returns a Series aligned to the price index (one less element
    because of the differencing).  Returns are expressed as simple
    returns (e.g. 0.01 = 1% daily change).
    """
    returns = prices.pct_change().dropna()
    returns.name = "Return"
    return returns


@dataclass
class OutlierStats:
    quantile: float
    threshold_low: float
    threshold_high: float
    count_low: int
    count_high: int
    mean_low: float
    mean_high: float
    median_low: float
    median_high: float
    std_low: float
    std_high: float
    min_low: float
    max_high: float


def calculate_outlier_stats(
    returns: pd.Series, quantile: float
) -> OutlierStats:
    """Identify tails of the distribution and compute statistics.

    Parameters
    ----------
    returns: pd.Series
        Series of daily returns.
    quantile: float
        Quantile for identifying extremes (e.g. 0.99 means top 1% and
        bottom 1%).

    Returns
    -------
    OutlierStats
        Structured statistics about the extreme return subsets.
    """
    assert 0 < quantile < 1, "Quantile must be between 0 and 1"
    # Lower tail threshold (e.g. 0.01 for bottom 1%)
    low_threshold = returns.quantile(1 - quantile)
    high_threshold = returns.quantile(quantile)

    low_returns = returns[returns <= low_threshold]
    high_returns = returns[returns >= high_threshold]

    return OutlierStats(
        quantile=quantile,
        threshold_low=low_threshold,
        threshold_high=high_threshold,
        count_low=len(low_returns),
        count_high=len(high_returns),
        mean_low=low_returns.mean(),
        mean_high=high_returns.mean(),
        median_low=low_returns.median(),
        median_high=high_returns.median(),
        std_low=low_returns.std(ddof=0),
        std_high=high_returns.std(ddof=0),
        min_low=low_returns.min(),
        max_high=high_returns.max(),
    )


def annualised_return(returns: pd.Series) -> float:
    """Compute the compound annual growth rate (CAGR) from daily returns.

    Assumes 252 trading days per year.  Handles arbitrary lengths by
    computing the geometric mean and then annualising.
    """
    if returns.empty:
        return float('nan')
    cumulative = (1 + returns).prod()
    years = len(returns) / 252.0
    if years <= 0:
        return float('nan')
    return cumulative ** (1 / years) - 1


def scenario_returns(
    returns: pd.Series,
    best_n: int,
    worst_n: int,
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Construct return series for several exclusion scenarios.

    Four scenarios are returned:

    * all_days     – original return series (baseline)
    * miss_best    – returns with the ``best_n`` highest days set to zero
    * miss_worst   – returns with the ``worst_n`` lowest days set to zero
    * miss_both    – returns with both best and worst days set to zero

    Setting returns to zero approximates the investor being out of the
    market on those days but otherwise invested.  We choose to keep
    the same number of trading periods so that the annualisation is
    comparable across scenarios.
    """
    all_days = returns.copy()

    # Identify best and worst days
    sorted_returns = returns.sort_values()
    worst_idx = sorted_returns.index[:worst_n]
    best_idx = sorted_returns.index[-best_n:]

    miss_best = returns.copy()
    miss_best.loc[best_idx] = 0.0

    miss_worst = returns.copy()
    miss_worst.loc[worst_idx] = 0.0

    miss_both = returns.copy()
    miss_both.loc[best_idx] = 0.0
    miss_both.loc[worst_idx] = 0.0

    return all_days, miss_best, miss_worst, miss_both


def moving_average_regime(
    prices: pd.Series, window: int
) -> pd.Series:
    """Compute a simple moving average and classify regimes.

    A regime of 1 indicates the price is above its ``window`` day
    moving average (uptrend), while 0 indicates a downtrend.  The
    resulting Series is aligned to the input price index.  Days
    without a valid moving average (first ``window``–1 observations)
    will be marked as NaN.
    """
    sma = prices.rolling(window).mean()
    regime = pd.Series(np.where(prices > sma, 1, 0), index=prices.index)
    regime[: window - 1] = np.nan
    return regime


def outlier_regime_counts(
    returns: pd.Series, regimes: pd.Series, quantile: float
) -> Tuple[int, int]:
    """Count how many outlier days fall within each regime.

    Returns a tuple (count_in_downtrend, count_in_uptrend).
    """
    low_threshold = returns.quantile(1 - quantile)
    high_threshold = returns.quantile(quantile)
    outliers = returns[(returns <= low_threshold) | (returns >= high_threshold)]
    # Drop NaNs in regime (first ``window`` days)
    outliers = outliers.dropna()
    regime_outliers = regimes.loc[outliers.index]
    count_down = int((regime_outliers == 0).sum())
    count_up = int((regime_outliers == 1).sum())
    return count_down, count_up


def regime_performance(returns: pd.Series, regimes: pd.Series) -> pd.DataFrame:
    """Compute performance metrics separately for uptrend and downtrend days.

    Returns a DataFrame with two rows ('downtrend', 'uptrend') and
    columns for count, mean return, median, standard deviation,
    annualised return, and percentage of total trading days.
    """
    valid = regimes.dropna().index
    sub_returns = returns.loc[valid]
    sub_regime = regimes.loc[valid]
    results = []
    for label, regime_value in [('downtrend', 0), ('uptrend', 1)]:
        mask = sub_regime == regime_value
        r = sub_returns[mask]
        result = {
            'regime': label,
            'count': len(r),
            'pct_of_total': len(r) / len(sub_returns) if len(sub_returns) > 0 else np.nan,
            'mean': r.mean(),
            'median': r.median(),
            'std': r.std(ddof=0),
            'annualised_return': annualised_return(r),
        }
        results.append(result)
    return pd.DataFrame(results)


def save_dataframe(df: pd.DataFrame, path: str) -> None:
    """Save a DataFrame to CSV with index label.

    Ensures that the parent directory exists.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=True)


def make_plots(
    returns: pd.Series,
    outlier_stats: List[OutlierStats],
    regimes: pd.Series,
    output_dir: str,
) -> None:
    """Generate illustrative charts and save them as PNG files.

    Produces three plots:
    1. Time series of daily returns highlighting extreme tails.
    2. Histogram of returns with a normal distribution overlay.
    3. Scatter plot of returns coloured by regime (uptrend/downtrend).

    The plots are intended to qualitatively match Faber's figures and
    help the user visualise the distribution and clustering of
    outliers.
    """
    import matplotlib.pyplot as plt
    import scipy.stats

    os.makedirs(output_dir, exist_ok=True)

    # Time series plot highlighting extremes
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(returns.index, returns.values, label='Daily return', linewidth=0.5)
    for stats in outlier_stats:
        low_threshold = stats.threshold_low
        high_threshold = stats.threshold_high
        extremes = returns[(returns <= low_threshold) | (returns >= high_threshold)]
        ax.scatter(
            extremes.index,
            extremes.values,
            s=10,
            label=f'Outliers (>{stats.quantile*100:.1f}% tails)',
            alpha=0.7,
        )
    ax.set_title('Daily returns with outliers highlighted')
    ax.set_ylabel('Return')
    ax.set_xlabel('Date')
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, 'returns_time_series.png'))
    plt.close(fig)

    # Histogram with normal overlay
    fig, ax = plt.subplots(figsize=(8, 5))
    n, bins, patches = ax.hist(returns.values, bins=100, density=True, alpha=0.6, label='Empirical')
    mu, sigma = returns.mean(), returns.std(ddof=0)
    x = np.linspace(bins[0], bins[-1], 200)
    y = scipy.stats.norm.pdf(x, mu, sigma)
    ax.plot(x, y, 'r--', label='Normal PDF')
    ax.set_title('Distribution of daily returns')
    ax.set_xlabel('Return')
    ax.set_ylabel('Density')
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, 'returns_histogram.png'))
    plt.close(fig)

    # Scatter by regime
    fig, ax = plt.subplots(figsize=(10, 5))
    valid = regimes.dropna().index
    sub_returns = returns.loc[valid]
    sub_regimes = regimes.loc[valid]
    colours = ['red' if x == 0 else 'green' for x in sub_regimes]
    ax.scatter(sub_returns.index, sub_returns.values, c=colours, s=10, alpha=0.6)
    ax.set_title('Daily returns coloured by market regime')
    ax.set_xlabel('Date')
    ax.set_ylabel('Return')
    ax.axhline(0, color='black', linewidth=0.5)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, 'returns_by_regime.png'))
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ticker', type=str, default='^GSPC', help='Ticker symbol (Yahoo Finance format)')
    parser.add_argument('--start', type=str, default='1928-09-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2010-12-31', help='End date (YYYY-MM-DD)')
    parser.add_argument('--csv', type=str, default=None, help='Path to a local CSV with Date and Close columns')
    parser.add_argument('--quantiles', type=float, nargs='+', default=[0.99, 0.999], help='Quantiles for outlier stats')
    parser.add_argument('--ma-window', type=int, default=200, help='Moving average window length')
    parser.add_argument('--best-count', type=int, default=10, help='Number of best days to remove in scenario analysis')
    parser.add_argument('--worst-count', type=int, default=10, help='Number of worst days to remove in scenario analysis')
    parser.add_argument('--output-dir', type=str, default='output', help='Directory to save results (CSV and PNG)')
    args = parser.parse_args()

    prices_df = fetch_price_data(args.ticker, args.start, args.end, args.csv)
    prices = prices_df['Close']
    returns = compute_daily_returns(prices)

    outlier_stats_list: List[OutlierStats] = []
    for q in args.quantiles:
        stats = calculate_outlier_stats(returns, q)
        outlier_stats_list.append(stats)

    # Prepare outlier statistics table
    outlier_rows = []
    for st in outlier_stats_list:
        outlier_rows.append({
            'quantile': st.quantile,
            'threshold_low': st.threshold_low,
            'threshold_high': st.threshold_high,
            'count_low': st.count_low,
            'count_high': st.count_high,
            'mean_low': st.mean_low,
            'mean_high': st.mean_high,
            'median_low': st.median_low,
            'median_high': st.median_high,
            'std_low': st.std_low,
            'std_high': st.std_high,
            'min_low': st.min_low,
            'max_high': st.max_high,
        })
    outliers_df = pd.DataFrame(outlier_rows).set_index('quantile')
    save_dataframe(outliers_df, os.path.join(args.output_dir, 'outlier_stats.csv'))

    # Scenario analysis
    all_days, miss_best, miss_worst, miss_both = scenario_returns(
        returns, args.best_count, args.worst_count
    )
    scenario_results = []
    for label, series in [
        ('all_days', all_days),
        ('miss_best', miss_best),
        ('miss_worst', miss_worst),
        ('miss_both', miss_both),
    ]:
        scenario_results.append({'scenario': label, 'annualised_return': annualised_return(series)})
    scenarios_df = pd.DataFrame(scenario_results).set_index('scenario')
    save_dataframe(scenarios_df, os.path.join(args.output_dir, 'return_scenarios.csv'))

    # Regime classification
    regimes = moving_average_regime(prices, args.ma_window)
    regime_stats_df = regime_performance(returns, regimes)
    save_dataframe(regime_stats_df.set_index('regime'), os.path.join(args.output_dir, 'regime_performance.csv'))

    # Outlier counts by regime
    regime_outlier_rows = []
    for q in args.quantiles:
        down_count, up_count = outlier_regime_counts(returns, regimes, q)
        regime_outlier_rows.append({
            'quantile': q,
            'outliers_in_downtrend': down_count,
            'outliers_in_uptrend': up_count,
        })
    regime_outliers_df = pd.DataFrame(regime_outlier_rows).set_index('quantile')
    save_dataframe(regime_outliers_df, os.path.join(args.output_dir, 'outlier_regime_counts.csv'))

    # Generate charts
    make_plots(returns, outlier_stats_list, regimes, args.output_dir)

    print(f"Analysis complete. Results saved to '{args.output_dir}'.")


if __name__ == '__main__':
    main()