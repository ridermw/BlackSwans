"""Data loading and caching utilities."""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from ..sanitize import sanitize_ticker

try:
    import yfinance as yf
except ImportError:
    yf = None

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


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


def load_price_csv(csv_path: Path, start: str, end: str) -> pd.DataFrame:
    """Load price data from a known CSV file path.

    This function is intended for use when the caller has already validated
    the path (e.g. from a hardcoded mapping). It does no caching or
    downloading.
    """
    df = _load_csv(csv_path)
    if "Close" not in df.columns and "Adj Close" in df.columns:
        df["Close"] = df["Adj Close"]
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.sort_index().loc[start:end, ["Close"]]
    df.dropna(subset=["Close"], inplace=True)
    return df


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

    safe_ticker = sanitize_ticker(ticker)
    cache_file = f"{safe_ticker.replace('^', '_')}_{start}_to_{end}.csv"
    cache_path = (DATA_DIR / cache_file).resolve()

    # Validate resolved cache path stays within DATA_DIR
    resolved_data_dir = DATA_DIR.resolve()
    try:
        cache_path.relative_to(resolved_data_dir)
    except ValueError:
        raise ValueError(
            f"Invalid ticker results in path outside data directory: {ticker}"
        )
    # codeql[py/path-injection] — ticker is sanitized by sanitize_ticker()
    # and the resolved path is validated to stay within DATA_DIR above.

    # explicit CSV override (user-provided path, no directory restriction)
    if csv_path:
        csv_file = Path(csv_path)
        if csv_file.exists():
            logging.info(f"Loading prices from {csv_file}")
            return load_price_csv(csv_file, start, end)
        else:
            logging.warning(f"CSV path {csv_file} not found, proceeding to cache or download.")

    # load from cache
    if cache_path.exists() and not overwrite:
        df = load_price_csv(cache_path, start, end)
        if not df.empty:
            actual_start = df.index.min().strftime("%Y-%m-%d")
            actual_end = df.index.max().strftime("%Y-%m-%d")
            if actual_start > start or actual_end < end:
                logging.warning(
                    f"Cached data covers {actual_start} to {actual_end}, "
                    f"requested {start} to {end}. Re-downloading."
                )
            else:
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
