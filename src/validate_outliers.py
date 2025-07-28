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


def fetch_price_data(ticker: str, start: str, end: str, csv_path: Optional[str] = None) -> pd.DataFrame:
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
        raise RuntimeError("yfinance not installed and no CSV provided")

    data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    if data.empty:
        raise ValueError(f"No data returned for {ticker} from {start} to {end}")
    data = data.rename(columns={"Adj Close": "Close"})
    return data[["Close"]]


def compute_daily_returns(prices: pd.Series) -> pd.Series:
    """Calculate daily percentage returns from price series.

    Parameters
    ----------
    prices : pd.Series
        Series of closing prices

    Returns
    -------
    pd.Series
        Daily returns as percentage change
    """
    returns = prices.pct_change().dropna()
    returns.name = "Return"
    return returns


def calculate_outlier_stats(returns: pd.Series, quantile: float) -> OutlierStats:
    """Identify and compute statistics for extreme quantile return days.

    Parameters
    ----------
    returns : pd.Series
        Daily return values
    quantile : float
        Tail quantile threshold (e.g., 0.99 for 1%)

    Returns
    -------
    OutlierStats
        Summary stats for low and high outlier tails
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
    """Compute the compound annual growth rate (CAGR) from daily returns.

    Assumes 252 trading days per year.  Handles arbitrary lengths by
    computing the geometric mean and then annualising.

    Parameters
    ----------
    returns : pd.Series
        Daily return values

    Returns
    -------
    float
        Annualised geometric return
    """
    if returns.empty:
        return float('nan')
    cumulative = (1 + returns).prod()
    years = len(returns) / 252
    return cumulative ** (1 / years) - 1 if years > 0 else float('nan')


def scenario_returns(returns: pd.Series, best_n: int, worst_n: int) -> Tuple[pd.Series, ...]:
    """Simulate the effect of excluding best/worst days on performance.

    Parameters
    ----------
    returns : pd.Series
        Original return series
    best_n : int
        Number of highest return days to remove
    worst_n : int
        Number of lowest return days to remove

    Returns
    -------
    Tuple[pd.Series, ...]
        Original, miss_best, miss_worst, and miss_both return series
    
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
    # Accept both Series and single-column DataFrame
    if isinstance(returns, pd.DataFrame):
        # Use 'Return' column if present, else use the first column
        if 'Return' in returns.columns:
            returns = returns['Return']
        else:
            returns = returns.iloc[:, 0]

    # Now returns is a Series
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

    return returns, miss_best, miss_worst, miss_both


def moving_average_regime(prices: pd.Series, window: int) -> pd.Series:
    """Compute a simple moving average and classify regimes.

    A regime of 1 indicates the price is above its ``window`` day
    moving average (uptrend), while 0 indicates a downtrend.  The
    resulting Series is aligned to the input price index.  Days
    without a valid moving average (first ``window``–1 observations)
    will be marked as NaN.

    Parameters
    ----------
    prices : pd.Series
        Price series
    window : int
        Number of days for moving average window

    Returns
    -------
    pd.Series
        Regime series with 1 for uptrend, 0 for downtrend
    """
    # Ensure input is a Series (use 'Close' if DataFrame)
    if isinstance(prices, pd.DataFrame):
        if 'Close' in prices.columns:
            prices = prices['Close']
        else:
            prices = prices.iloc[:, 0]

    sma = prices.rolling(window).mean()
    regime = pd.Series(np.where(prices > sma, 1, 0), index=prices.index)
    regime[:window - 1] = np.nan
    return regime


def outlier_regime_counts(returns: pd.Series, regimes: pd.Series, quantile: float) -> Tuple[int, int]:
    """Count outlier days by regime (uptrend vs downtrend).

    Parameters
    ----------
    returns : pd.Series
        Daily return values
    regimes : pd.Series
        Market regime labels (0 or 1)
    quantile : float
        Quantile threshold for outliers

    Returns
    -------
    Tuple[int, int]
        (downtrend outliers, uptrend outliers)
    """
    low = returns.quantile(1 - quantile)
    high = returns.quantile(quantile)
    outliers = returns[(returns <= low) | (returns >= high)].dropna()
    regime_vals = regimes.loc[outliers.index]
    return int((regime_vals == 0).sum()), int((regime_vals == 1).sum())


def regime_performance(returns: pd.Series, regimes: pd.Series) -> pd.DataFrame:
    """Summarize performance by market regime.

    Parameters
    ----------
    returns : pd.Series
        Daily returns
    regimes : pd.Series
        Market regime classification

    Returns
    -------
    pd.DataFrame
        Statistics segmented by uptrend and downtrend periods
    Returns a DataFrame with two rows ('downtrend', 'uptrend') and
    columns for count, mean return, median, standard deviation,
    annualised return, and percentage of total trading days.
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
    """Save DataFrame to CSV.

    Parameters
    ----------
    df : pd.DataFrame
        Data to save
    path : str
        Target file path
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path)


def make_plots(returns: pd.Series, outliers: List[OutlierStats], regimes: pd.Series, output_dir: str):
    """Generate time series, histogram, and scatter plots.

    Parameters
    ----------
    returns : pd.Series
        Daily returns
    outliers : List[OutlierStats]
        Outlier statistics for annotation
    regimes : pd.Series
        Market regimes
    output_dir : str
        Directory to save images
    Produces three plots:
    1. Time series of daily returns highlighting extreme tails.
    2. Histogram of returns with a normal distribution overlay.
    3. Scatter plot of returns coloured by regime (uptrend/downtrend).

    The plots are intended to qualitatively match Faber's figures and
    help the user visualise the distribution and clustering of
    outliers.
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
    """Command-line interface for running outlier analysis."""
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
    args = parser.parse_args()

    prices_df = fetch_price_data(args.ticker, args.start, args.end, args.csv)
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
