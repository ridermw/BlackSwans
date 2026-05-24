#!/usr/bin/env python3
"""Check that refreshed data metadata agrees across generated artifacts."""

import json
from pathlib import Path

from blackswans.data.tickers import TICKER_REGISTRY, get_all_csvs

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STATIC_DIR = ROOT / "frontend" / "public" / "data"


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _assert_equal(actual, expected, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def main() -> None:
    csvs = get_all_csvs(DATA_DIR)
    missing = sorted(set(TICKER_REGISTRY) - set(csvs))
    if missing:
        raise AssertionError(f"Missing CSVs for expected tickers: {', '.join(missing)}")

    csv_dates = {
        code: {"symbol": symbol, "start": start, "end": end}
        for code, (symbol, _path, start, end) in csvs.items()
    }

    status_path = DATA_DIR / "validation_status.json"
    if status_path.exists():
        status = _load_json(status_path)
        indices = status.get("indices", {})
        for code, meta in csv_dates.items():
            entry = indices.get(code)
            if entry is None:
                raise AssertionError(f"validation_status.json missing {code}")
            _assert_equal(entry.get("data_start"), meta["start"], f"{code} status start date")
            _assert_equal(entry.get("data_end"), meta["end"], f"{code} status end date")

    tickers_path = STATIC_DIR / "tickers.json"
    if tickers_path.exists():
        tickers = _load_json(tickers_path).get("tickers", [])
        by_code = {row["ticker_code"]: row for row in tickers}
        _assert_equal(set(by_code), set(TICKER_REGISTRY), "static tickers set")
        for code, meta in csv_dates.items():
            row = by_code[code]
            _assert_equal(row.get("start_date"), meta["start"], f"{code} static start date")
            _assert_equal(row.get("end_date"), meta["end"], f"{code} static end date")

            ticker_dir = STATIC_DIR / code
            for filename in [
                "analysis.json",
                "validation.json",
                "chart-data.json",
                "period-comparison.json",
                "cagr-matrix.json",
            ]:
                path = ticker_dir / filename
                if not path.exists():
                    raise AssertionError(f"Missing static artifact: {path}")

            for filename in ["analysis.json", "chart-data.json"]:
                data = _load_json(ticker_dir / filename)
                _assert_equal(data.get("start_date"), meta["start"], f"{code} {filename} start")
                _assert_equal(data.get("end_date"), meta["end"], f"{code} {filename} end")

    multi_index_path = STATIC_DIR / "multi-index.json"
    if multi_index_path.exists():
        indices = _load_json(multi_index_path).get("indices", [])
        _assert_equal(len(indices), len(TICKER_REGISTRY), "multi-index count")

    print(f"Data invariants OK for {len(csv_dates)} tickers")


if __name__ == "__main__":
    main()
