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

# validate_outliers.py
# Rewritten version with full function docstrings and preserved inline comments for clarity and robustness.

import argparse
import os
from typing import Optional, List, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats

try:
    import yfinance as yf
except ImportError:
    yf = None


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


def _load_csv(path: str) -> pd.DataFrame:
    """Load CSV with robust date parsing.

    If a ``Date`` column is present it is parsed and set as index.
    Otherwise the existing index is converted to datetime.
    The DataFrame is then sorted by the datetime index.

    Parameters
    ----------
    path : str
        Path to a CSV file.

    Returns
    -------
    pd.DataFrame
        DataFrame indexed by datetime, sorted ascending.
    """
    df = pd.read_csv(path)
    for col in ("Date", "date", "DATE"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
            df = df.set_index(col)
            break
    else:
        df.index = pd.to_datetime(df.index)
    return df.sort_index()


def fetch_price_data(ticker: str, start: str, end: str,
                     csv_path: Optional[str] = None,
                     overwrite: bool = False) -> pd.DataFrame:
    """Load historical price data.

    If ``csv_path`` is provided and the file exists, it will be
    loaded instead of hitting the network. Otherwise, the function
    checks for a cached file in ./data, and only downloads if not found
    or if the file does not cover the requested date range. If --overwrite
    is set, always download and overwrite the file.
    Downloaded data is always saved to ./data for future use.

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
    overwrite: bool
        If True, forces re-download even if a cache exists.

    Returns
    -------
    pd.DataFrame
        DataFrame indexed by datetime with a 'Close' column representing
        daily closing prices. The index will contain all trading days
        between start and end inclusive.
    """
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = f"{ticker.replace('^','_')}_{start}_to_{end}.csv"
    cache_path = os.path.join(cache_dir, cache_file)

    def download_and_cache() -> pd.DataFrame:
        if yf is None:
            raise RuntimeError("yfinance not installed and no CSV provided")
        data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
        if data.empty:
            raise ValueError(f"No data for {ticker} from {start} to {end}")
        data = data.rename(columns={"Adj Close": "Close"})
        data.index.name = "Date"
        data.to_csv(cache_path)
        return data[["Close"]]

    # 1) explicit CSV path
    if csv_path and os.path.exists(csv_path):
        df = _load_csv(csv_path)
        if "Close" not in df.columns and "Adj Close" in df.columns:
            df["Close"] = df["Adj Close"]
        if df.index.min() <= pd.to_datetime(start) and df.index.max() >= pd.to_datetime(end):
            return df[["Close"]].loc[start:end]

    # 2) cached file
    if os.path.exists(cache_path) and not overwrite:
        df = _load_csv(cache_path)
        if "Close" not in df.columns and "Adj Close" in df.columns:
            df["Close"] = df["Adj Close"]
        # if covers the range, return it
        if df.index.min() <= pd.to_datetime(start) and df.index.max() >= pd.to_datetime(end):
            return df[["Close"]].loc[start:end]
        # otherwise fall through to full download

    # 3) download fresh
    return download_and_cache()


def compute_daily_returns(prices: pd.Series) -> pd.Series:
    """Calculate daily percentage returns from price series.

    Parameters
    ----------
    prices : pd.Series
        Series of daily closing prices.

    Returns
    -------
    pd.Series
        Daily returns as percentage change, named 'Return'.
    """
    returns = prices.pct_change().dropna()
    returns.name = "Return"
    return returns


def calculate_outlier_stats(returns: pd.Series, quantile: float) -> OutlierStats:
    """Identify and compute statistics for extreme quantile return days.

    Parameters
    ----------
    returns : pd.Series
        Daily return series.
    quantile : float
        Tail quantile (e.g. 0.99 for 1%).

    Returns
    -------
    OutlierStats
        Descriptive statistics for low and high outlier tails.
    """
    low = returns.quantile(1 - quantile)
    high = returns.quantile(quantile)
    lows = returns[returns <= low]
    highs = returns[returns >= high]
    return OutlierStats(
        quantile, low, high,
        len(lows), len(highs),
        lows.mean(), highs.mean(),
        lows.median(), highs.median(),
        lows.std(ddof=0), highs.std(ddof=0),
        lows.min(), highs.max()
    )


def annualised_return(returns: pd.Series) -> float:
    """Compute compound annual growth rate (CAGR) from daily returns.

    Assumes 252 trading days per year and uses geometric mean.

    Parameters
    ----------
    returns : pd.Series
        Series of daily returns.

    Returns
    -------
    float
        Annualised geometric return.
    """
    if returns.empty:
        return float("nan")
    cumulative = (1 + returns).prod()
    years = len(returns) / 252
    return cumulative ** (1 / years) - 1 if years > 0 else float("nan")


def scenario_returns(returns: pd.Series, best_n: int, worst_n: int
                     ) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Simulate missing best/worst return days.

    Returns four series: original, missing best, missing worst, and missing both.

    Parameters
    ----------
    returns : pd.Series
        Original daily returns.
    best_n : int
        Number of top-return days to zero out.
    worst_n : int
        Number of bottom-return days to zero out.

    Returns
    -------
    Tuple[pd.Series, pd.Series, pd.Series, pd.Series]
        (all_days, miss_best, miss_worst, miss_both)
    """
    # Accept both Series and single-column DataFrame
    if isinstance(returns, pd.DataFrame):
        # Use 'Return' column if present, else first column
        if 'Return' in returns.columns:
            returns = returns['Return']
        else:
            returns = returns.iloc[:, 0]

    # Now ensure returns is a Series
    sorted_r = returns.sort_values()
    worst_idx = sorted_r.index[:worst_n]
    best_idx = sorted_r.index[-best_n:]

    miss_best = returns.copy()
    miss_best.loc[best_idx] = 0.0
    miss_worst = returns.copy()
    miss_worst.loc[worst_idx] = 0.0
    miss_both = returns.copy()
    miss_both.loc[best_idx.union(worst_idx)] = 0.0

    return returns, miss_best, miss_worst, miss_both


def moving_average_regime(prices: pd.Series, window: int) -> pd.Series:
    """Classify market regime by rolling moving average.

    Regime is 1 when price > rolling mean, 0 otherwise; NaN for first (window-1) days.

    Parameters
    ----------
    prices : pd.Series or pd.DataFrame
        Price series or single-column DataFrame.
    window : int
        Moving average window length.

    Returns
    -------
    pd.Series
        Regime labels (0 or 1) indexed by date.
    """
    # allow DataFrame input
    if isinstance(prices, pd.DataFrame):
        if 'Close' in prices.columns:
            series = prices['Close']
        else:
            series = prices.iloc[:, 0]
    else:
        series = prices

    sma = series.rolling(window).mean()
    regime = pd.Series(np.where(series > sma, 1, 0), index=series.index)
    regime.iloc[:window - 1] = np.nan
    return regime


def outlier_regime_counts(returns: pd.Series, regimes: pd.Series,
                          quantile: float) -> Tuple[int, int]:
    """Count outliers occurring in each regime.

    Parameters
    ----------
    returns : pd.Series
        Daily return series.
    regimes : pd.Series
        Regime classification (0 or 1).
    quantile : float
        Outlier quantile threshold.

    Returns
    -------
    Tuple[int, int]
        (count in downtrend, count in uptrend)
    """
    low = returns.quantile(1 - quantile)
    high = returns.quantile(quantile)
    outliers = returns[(returns <= low) | (returns >= high)].dropna()
    regime_vals = regimes.loc[outliers.index]
    return int((regime_vals == 0).sum()), int((regime_vals == 1).sum())


def regime_performance(returns: pd.Series, regimes: pd.Series) -> pd.DataFrame:
    """Summarize returns by market regime.

    Parameters
    ----------
    returns : pd.Series
        Daily returns.
    regimes : pd.Series
        Regime classification (0 or 1).

    Returns
    -------
    pd.DataFrame
        Statistics (count, mean, median, std, annualised return, pct days)
        for each regime ('downtrend', 'uptrend').
    """
    results = []
    valid_idx = regimes.dropna().index
    sub_returns = returns.loc[valid_idx]
    sub_regimes = regimes.loc[valid_idx]
    for label, val in [("downtrend", 0), ("uptrend", 1)]:
        mask = sub_regimes == val
        r = sub_returns[mask]
        results.append({
            "regime": label,
            "count": len(r),
            "pct_of_total": len(r) / len(sub_returns) if len(sub_returns) else np.nan,
            "mean": r.mean(),
            "median": r.median(),
            "std": r.std(ddof=0),
            "annualised_return": annualised_return(r)
        })
    return pd.DataFrame(results)


def save_dataframe(df: pd.DataFrame, path: str):
    """Save DataFrame to a CSV file, creating parent dirs as needed.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to save.
    path : str
        Target CSV file path.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path)


def make_plots(returns: pd.Series, outliers: List[OutlierStats], regimes: pd.Series, output_dir: str):
    """Generate and save diagnostic plots of returns and regimes.

    Parameters
    ----------
    returns : pd.Series
        Daily returns.
    outliers : List[OutlierStats]
        Outlier statistics.
    regimes : pd.Series
        Market regime labels.
    output_dir : str
        Directory to write plot image files.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Plot 1: returns time series with outliers
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(returns.index, returns.values, linewidth=0.5)
    for stat in outliers:
        extreme = returns[(returns <= stat.threshold_low) | (returns >= stat.threshold_high)].dropna()
        # Ensure index and values are 1D arrays of the same length and not empty
        x = np.asarray(extreme.index)
        y = np.asarray(extreme.values)
        if x.ndim == 1 and y.ndim == 1 and len(x) == len(y) and len(x) > 0:
            ax.scatter(x, y, s=10, alpha=0.7, label=f">{stat.quantile*100:.1f}% tails")
    ax.set_title("Daily Returns with Outliers")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "returns_time_series.png"))
    plt.close(fig)

    # Plot 2: histogram + normal PDF
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(returns, bins=100, density=True, alpha=0.6)
    x = np.linspace(returns.min(), returns.max(), 200)
    y = scipy.stats.norm.pdf(x, returns.mean(), returns.std(ddof=0))
    ax.plot(x, y, 'r--')
    ax.set_title("Histogram of Returns")
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "returns_histogram.png"))
    plt.close(fig)

    # Plot 3: scatter by regime
    fig, ax = plt.subplots(figsize=(10, 5))
    valid = regimes.dropna().index
    # Ensure valid is aligned with returns and colormap, and all are numpy arrays of the same length
    valid_returns = returns.loc[valid]
    valid_regimes = regimes.loc[valid]
    x = np.asarray(valid)
    y = np.asarray(valid_returns)
    colormap = np.array(['red' if x == 0 else 'green' for x in valid_regimes])
    # Only plot if lengths match and not empty
    if x.ndim == 1 and y.ndim == 1 and len(x) == len(y) == len(colormap) and len(x) > 0:
        ax.scatter(x, y, c=colormap, s=10, alpha=0.6)
    ax.axhline(0, color='black', linewidth=0.5)
    ax.set_title("Returns by Market Regime")
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "returns_by_regime.png"))
    plt.close(fig)


def main():
    """Command-line interface for running outlier analysis.

    Parses arguments, orchestrates data loading, analysis, and plotting.

    Command-line arguments mirror docstring at top of file.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticker', type=str, default='^GSPC')
    parser.add_argument('--start', type=str, default='1928-09-01')
    parser.add_argument('--end', type=str, default='2010-12-31')
    parser.add_argument('--csv', type=str, default=None)
    parser.add_argument('--quantiles', type=float, nargs='+', default=[0.99, 0.999])
    parser.add_argument('--ma-window', type=int, default=200)
    parser.add_argument('--best-count', type=int, default=10)
    parser.add_argument('--worst-count', type=int, default=10)
    parser.add_argument('--output-dir', type=str, default='output')
    parser.add_argument('--overwrite', action='store_true', help='Force download and overwrite any cached data')
    args = parser.parse_args()

    prices_df = fetch_price_data(args.ticker, args.start, args.end, args.csv, overwrite=args.overwrite)
    prices = prices_df['Close']
    returns = compute_daily_returns(prices)

    outlier_stats = [calculate_outlier_stats(returns, q) for q in args.quantiles]
    outliers_df = pd.DataFrame([s.__dict__ for s in outlier_stats]).set_index("quantile")
    save_dataframe(outliers_df, os.path.join(args.output_dir, "outlier_stats.csv"))

    all_days, miss_best, miss_worst, miss_both = scenario_returns(returns, args.best_count, args.worst_count)
    scenarios = [
        {"scenario": "all_days", "annualised_return": annualised_return(all_days)},
        {"scenario": "miss_best", "annualised_return": annualised_return(miss_best)},
        {"scenario": "miss_worst", "annualised_return": annualised_return(miss_worst)},
        {"scenario": "miss_both", "annualised_return": annualised_return(miss_both)}
    ]
    save_dataframe(pd.DataFrame(scenarios).set_index("scenario"), os.path.join(args.output_dir, "return_scenarios.csv"))

    regimes = moving_average_regime(prices, args.ma_window)
    save_dataframe(regime_performance(returns, regimes).set_index("regime"), os.path.join(args.output_dir, "regime_performance.csv"))

    regime_outliers = [
        {"quantile": q, "outliers_in_downtrend": d, "outliers_in_uptrend": u}
        for q in args.quantiles
        for d, u in [outlier_regime_counts(returns, regimes, q)]
    ]
    save_dataframe(pd.DataFrame(regime_outliers).set_index("quantile"), os.path.join(args.output_dir, "outlier_regime_counts.csv"))

    make_plots(returns, outlier_stats, regimes, args.output_dir)
    print(f"✅ Analysis complete. Results saved to '{args.output_dir}'")


if __name__ == '__main__':
    main()
