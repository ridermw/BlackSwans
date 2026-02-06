"""Data loading and caching utilities."""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

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
