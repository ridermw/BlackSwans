"""Central ticker configuration and CSV discovery.

Single source of truth for all 12 market indices analysed in the project.
Other modules should import from here rather than maintaining their own
ticker maps.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Default data directory (project root / data)
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"

# Canonical registry: lowercase code → metadata.
# ``start`` is the earliest date for which Yahoo Finance has data.
TICKER_REGISTRY: Dict[str, dict] = {
    "sp500":  {"symbol": "^GSPC",   "name": "S&P 500",        "start": "1928-09-04"},
    "nikkei": {"symbol": "^N225",   "name": "Nikkei 225",     "start": "1970-01-05"},
    "ftse":   {"symbol": "^FTSE",   "name": "FTSE 100",       "start": "1984-01-03"},
    "dax":    {"symbol": "^GDAXI",  "name": "DAX",            "start": "1987-12-30"},
    "cac":    {"symbol": "^FCHI",   "name": "CAC 40",         "start": "1990-03-01"},
    "asx":    {"symbol": "^AXJO",   "name": "ASX 200",        "start": "1992-11-23"},
    "tsx":    {"symbol": "^GSPTSE", "name": "TSX Composite",  "start": "1979-06-29"},
    "hsi":    {"symbol": "^HSI",    "name": "Hang Seng",      "start": "1986-12-31"},
    "efa":    {"symbol": "EFA",     "name": "MSCI EAFE",      "start": "2001-08-27"},
    "eem":    {"symbol": "EEM",     "name": "MSCI EM",        "start": "2003-04-14"},
    "reit":   {"symbol": "VNQ",     "name": "REITs (VNQ)",    "start": "2004-09-29"},
    "bonds":  {"symbol": "AGG",     "name": "US Bonds (AGG)", "start": "2003-09-29"},
}

# Mapping from periods.py-style uppercase keys to canonical codes
_PERIODS_KEY_MAP: Dict[str, str] = {
    "SP500": "sp500", "NIKKEI": "nikkei", "FTSE": "ftse", "DAX": "dax",
    "CAC40": "cac", "ASX200": "asx", "TSX": "tsx", "HANGSENG": "hsi",
    "EAFE": "efa", "EM": "eem", "REITS": "reit", "BONDS": "bonds",
}


def _sanitize_symbol(symbol: str) -> str:
    """Convert a Yahoo symbol to its filesystem prefix (``^`` → ``_``)."""
    return symbol.replace("^", "_")


def find_csv(ticker_code: str, data_dir: Optional[Path] = None) -> Optional[Path]:
    """Find the CSV data file for *ticker_code* by globbing *data_dir*.

    Returns the path with the latest end-date in its filename, or ``None``
    if no matching file exists.
    """
    data_dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR
    info = TICKER_REGISTRY.get(ticker_code)
    if info is None:
        return None

    prefix = _sanitize_symbol(info["symbol"])
    start = info["start"]
    # Pattern: {prefix}_{start}_to_*.csv  (e.g. _GSPC_1928-09-04_to_*.csv)
    matches = sorted(data_dir.glob(f"{prefix}_{start}_to_*.csv"))
    return matches[-1] if matches else None


def _end_date_from_filename(filename: str) -> str:
    """Extract the end-date portion from a data CSV filename."""
    # e.g. "_GSPC_1928-09-04_to_2025-01-31.csv" → "2025-01-31"
    return filename.replace(".csv", "").rsplit("_to_", 1)[-1]


def get_all_csvs(
    data_dir: Optional[Path] = None,
) -> Dict[str, Tuple[str, Path, str, str]]:
    """Return ``{code: (symbol, csv_path, start, end)}`` for every ticker
    with an existing CSV in *data_dir*."""
    data_dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR
    result: Dict[str, Tuple[str, Path, str, str]] = {}
    for code, info in TICKER_REGISTRY.items():
        csv_path = find_csv(code, data_dir)
        if csv_path is not None:
            end = _end_date_from_filename(csv_path.name)
            result[code] = (info["symbol"], csv_path, info["start"], end)
    return result


def get_periods_ticker_map(
    data_dir: Optional[Path] = None,
) -> Dict[str, dict]:
    """Build a ``TICKER_MAP`` in the format expected by ``periods.py``.

    Keys are uppercase (``SP500``, ``NIKKEI``, …) and values contain
    ``file``, ``name``, ``start``, ``end``.
    """
    all_csvs = get_all_csvs(data_dir)
    result: Dict[str, dict] = {}
    for upper_key, code in _PERIODS_KEY_MAP.items():
        if code not in all_csvs:
            continue
        symbol, csv_path, start, end = all_csvs[code]
        result[upper_key] = {
            "file": csv_path.name,
            "name": TICKER_REGISTRY[code]["name"],
            "start": start,
            "end": end,
        }
    return result


def csv_filename(ticker_code: str, end_date: str) -> str:
    """Build the canonical CSV filename for a ticker and end date.

    >>> csv_filename("sp500", "2026-04-01")
    '_GSPC_1928-09-04_to_2026-04-01.csv'
    """
    info = TICKER_REGISTRY[ticker_code]
    prefix = _sanitize_symbol(info["symbol"])
    return f"{prefix}_{info['start']}_to_{end_date}.csv"
