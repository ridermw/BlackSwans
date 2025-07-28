"""
validate_outliers.py (refactored)
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

import argparse
import logging
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import scipy.stats

try:
    import yfinance as yf
except ImportError:
    yf = None

# configure logging
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

# constants
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CASH = 0.0

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


def _load_csv(path: Path) -> pd.DataFrame:
    """Load CSV with robust date parsing.

    If a ``Date`` column is present it is parsed and set as index.
    Otherwise the existing index is converted to datetime.
    The DataFrame is then sorted by the datetime index.
    """
    df = pd.read_csv(path)
    for col in ("Date", "date", "DATE"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
            df.set_index(col, inplace=True)
            break
    else:
        df.index = pd.to_datetime(df.index)
    return df.sort_index()


def fetch_price_data(
    ticker: str,
    start: str,
    end: str,
    csv_path: Optional[str] = None,
    overwrite: bool = False,
) -> pd.DataFrame:
    """Load historical price data with caching.

    If a local CSV is supplied or cached data exists covering the date
    range, use it; otherwise download via yfinance and cache.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = f"{ticker.replace('^', '_')}_{start}_to_{end}.csv"
    cache_path = DATA_DIR / cache_file

    def _from_csv(path: Path) -> pd.DataFrame:
        df = _load_csv(path)
        if "Close" not in df.columns and "Adj Close" in df.columns:
            df["Close"] = df["Adj Close"]
        # ── ensure numeric dtype ────────────────╮
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df = df.sort_index().loc[start:end, ["Close"]]
        df.dropna(subset=["Close"], inplace=True)
        return df


    # explicit CSV override
    if csv_path:
        csv_file = Path(csv_path)
        if csv_file.exists():
            logging.info(f"Loading prices from {csv_file}")
            return _from_csv(csv_file)
        else:
            logging.warning(f"CSV path {csv_file} not found, proceeding to cache or download.")

    # load from cache
    if cache_path.exists() and not overwrite:
        df = _from_csv(cache_path)
        if not df.empty:
            logging.info(f"Loaded cached data from {cache_path}")
            return df

    # download fresh
    if yf is None:
        raise RuntimeError("yfinance not installed and no CSV provided.")
    logging.info(f"Downloading {ticker} from {start} to {end}")
    data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    if data.empty:
        raise ValueError(f"No data for {ticker} from {start} to {end}")
    data = data.rename(columns={"Adj Close": "Close"})
    data.index.name = "Date"
    data.to_csv(cache_path)
    return data[["Close"]]


def compute_daily_returns(prices: pd.Series) -> pd.Series:
    """Calculate daily percentage returns from price series.

    Accepts either a Series or single-column DataFrame.
    """
    # ensure we have a Series
    if isinstance(prices, pd.DataFrame):
        # prefer column named 'Close' or fallback to first column
        prices = prices['Close'] if 'Close' in prices else prices.iloc[:, 0]

    # coerce any stray strings → NaN, then drop
    prices = pd.to_numeric(prices, errors='coerce').dropna()

    # use pct_change with no fill_method
    returns = prices.pct_change(fill_method=None).dropna()
    returns.name = "Return"
    return returns

def calculate_outlier_stats(returns: pd.Series, quantile: float) -> OutlierStats:
    """Identify and compute statistics for extreme quantile return days."""
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
        lows.min(), highs.max(),
    )


def annualised_return(returns: pd.Series) -> float:
    """Compute compound annual growth rate (CAGR) from daily returns."""
    if returns.empty:
        return float("nan")
    cumulative = (1 + returns).prod()
    years = len(returns) / 252
    return cumulative ** (1 / years) - 1 if years > 0 else float("nan")


def scenario_returns(
    returns: pd.Series,
    best_n: int,
    worst_n: int,
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Simulate missing best/worst return days."""
    r = returns.copy()
    sorted_idx = r.sort_values()
    worst_idx = sorted_idx.index[:worst_n]
    best_idx = sorted_idx.index[-best_n:]
    miss_best = r.copy(); miss_best.loc[best_idx] = CASH
    miss_worst = r.copy(); miss_worst.loc[worst_idx] = CASH
    miss_both = r.copy(); miss_both.loc[best_idx.union(worst_idx)] = CASH
    return r, miss_best, miss_worst, miss_both


def moving_average_regime(prices: pd.Series, window: int) -> pd.Series:
    """Classify market regime by rolling moving average."""
    # coerce either Series or single-column DataFrame into a 1-D Series
    if isinstance(prices, pd.DataFrame):
        series = prices['Close'] if 'Close' in prices.columns else prices.iloc[:, 0]
    else:
        series = prices

    # ensure numeric and drop any NaNs before computing MA
    series = pd.to_numeric(series, errors='coerce').dropna()

    sma = series.rolling(window).mean()
    # > yields a Series of booleans; astype(int) keeps it 1-D
    regime = (series > sma).astype(int)
    regime.iloc[: window - 1] = np.nan
    return regime


def outlier_regime_counts(
    returns: pd.Series,
    regimes: pd.Series,
    quantile: float
) -> Tuple[int, int]:
    """Count outliers occurring in each regime."""
    threshold_low = returns.quantile(1 - quantile)
    threshold_high = returns.quantile(quantile)
    outliers = returns[(returns <= threshold_low) | (returns >= threshold_high)]
    regs = regimes.loc[outliers.index]
    return int((regs == 0).sum()), int((regs == 1).sum())


def regime_performance(returns: pd.Series, regimes: pd.Series) -> pd.DataFrame:
    """Summarize returns by market regime."""
    stats = []
    valid = regimes.dropna().index
    for label, val in [("downtrend", 0), ("uptrend", 1)]:
        mask = regimes.loc[valid] == val
        r = returns.loc[valid][mask]
        stats.append({
            "regime": label,
            "count": len(r),
            "pct_of_total": len(r) / len(valid) if valid.size else np.nan,
            "mean": r.mean(),
            "median": r.median(),
            "std": r.std(ddof=0),
            "annualised_return": annualised_return(r),
        })
    return pd.DataFrame(stats)


def save_dataframe(df: pd.DataFrame, path: Path):
    """Save DataFrame to a CSV file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path)


def make_plots(
    returns: pd.Series,
    outliers: List[OutlierStats],
    regimes: pd.Series,
    output_dir: Path,
):
    """Generate and save diagnostic plots of returns and regimes."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # returns time series with outliers
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(returns.index, returns.values, linewidth=0.5)
    for stats in outliers:
        extreme = returns[(returns <= stats.threshold_low) | (returns >= stats.threshold_high)]
        if not extreme.empty:
            ax.scatter(extreme.index, extreme.values, s=10, alpha=0.7,
                       label=f">{stats.quantile*100:.1f}% tails")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "returns_time_series.png")
    plt.close(fig)

    # histogram + normal PDF
    clean = returns.dropna()
    fig, ax = plt.subplots(figsize=(8,5))
    if clean.size > 0:
        ax.hist(
            clean,
            bins=100,
            density=True,
            alpha=0.6,
            edgecolor='black',
            linewidth=0.5
        )
        x = np.linspace(clean.min(), clean.max(), 200)
        y = scipy.stats.norm.pdf(x, clean.mean(), clean.std(ddof=0))
        ax.plot(x, y, '--')
    ax.set_title("Histogram of Returns")
    fig.tight_layout()
    fig.savefig(output_dir / "returns_histogram.png")
    plt.close(fig)


    # scatter by regime
    fig, ax = plt.subplots(figsize=(10, 5))
    data = pd.concat([returns, regimes], axis=1).dropna()
    if not data.empty:
        colors = ['red' if r == 0 else 'green' for r in data.iloc[:, 1]]
        ax.scatter(data.index, data.iloc[:, 0], c=colors, s=10, alpha=0.6)
        # --- add these two lines for a legend ---
        down = mpatches.Patch(color='red',   label='Downtrend')
        up   = mpatches.Patch(color='green', label='Uptrend')
        ax.legend(handles=[down, up], loc='upper right')
    ax.axhline(0, linewidth=0.5)
    ax.set_title("Returns by Market Regime")
    fig.tight_layout()
    fig.savefig(output_dir / "returns_by_regime.png")
    plt.close(fig)


def main():
    """Command-line interface for running outlier analysis."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticker', type=str, default='^GSPC')
    parser.add_argument('--start', type=str, default='1928-09-01')
    parser.add_argument('--end', type=str, default='2010-12-31')
    parser.add_argument('--csv', type=str)
    parser.add_argument('--quantiles', type=float, nargs='+', default=[0.99, 0.999])
    parser.add_argument('--ma-window', type=int, default=200)
    parser.add_argument('--best-count', type=int, default=10)
    parser.add_argument('--worst-count', type=int, default=10)
    parser.add_argument('--output-dir', type=str, default='output')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    prices_df = fetch_price_data(args.ticker, args.start, args.end, args.csv, overwrite=args.overwrite)
    returns = compute_daily_returns(prices_df['Close'])

    # outlier stats
    stats = [calculate_outlier_stats(returns, q) for q in args.quantiles]
    df_stats = pd.DataFrame([vars(s) for s in stats]).set_index('quantile')
    save_dataframe(df_stats, output_dir / 'outlier_stats.csv')

    # scenario returns
    scenarios = scenario_returns(returns, args.best_count, args.worst_count)
    summary = [annualised_return(s) for s in scenarios]
    df_scenarios = pd.DataFrame({
        'scenario': ['all', 'miss_best', 'miss_worst', 'miss_both'],
        'annualised_return': summary
    }).set_index('scenario')
    save_dataframe(df_scenarios, output_dir / 'return_scenarios.csv')

    # regimes
    regimes = moving_average_regime(prices_df['Close'], args.ma_window)
    df_regime = regime_performance(returns, regimes).set_index('regime')
    save_dataframe(df_regime, output_dir / 'regime_performance.csv')

    # outlier regime counts
    counts = [
        {'quantile': q, 'down': outlier_regime_counts(returns, regimes, q)[0],
         'up': outlier_regime_counts(returns, regimes, q)[1]}
        for q in args.quantiles
    ]
    df_counts = pd.DataFrame(counts).set_index('quantile')
    save_dataframe(df_counts, output_dir / 'outlier_regime_counts.csv')

    make_plots(returns, stats, regimes, output_dir)
    logging.info(f"Analysis complete. Results in {output_dir}")


if __name__ == '__main__':
    main()
