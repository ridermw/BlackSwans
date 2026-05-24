#!/usr/bin/env python3
"""Refresh market data and re-validate Faber's 4 claims.

Downloads the latest price data for all 12 indices via Yahoo Finance,
replaces stale CSV files, runs the full 4-claim validation, and writes
timestamped status files.

Usage:
    python scripts/refresh_and_validate.py                      # data only
    python scripts/refresh_and_validate.py --validate           # data + validation
    python scripts/refresh_and_validate.py --validate --dry-run # preview only
"""

import argparse
import json
import logging
import math
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

from blackswans.data.loaders import load_price_csv
from blackswans.data.transforms import compute_daily_returns
from blackswans.data.tickers import (
    TICKER_REGISTRY,
    csv_filename,
    _end_date_from_filename,
    find_csv,
    get_all_csvs,
)
from blackswans.validate_claims import run_full_validation

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


SUCCESS = "success"
REFRESH_FAILED = "refresh_failed"
VALIDATION_FAILED = "validation_failed"


def _failure(
    code: str,
    status: str,
    message: str,
    old_path: Optional[Path] = None,
    error_type: Optional[str] = None,
) -> dict:
    info = TICKER_REGISTRY[code]
    return {
        "status": status,
        "symbol": info["symbol"],
        "old_file": old_path.name if old_path else None,
        "new_file": None,
        "rows": 0,
        "start": info["start"],
        "end": None,
        "error_type": error_type,
        "error": message,
    }


def _parse_file_end(path: Optional[Path]) -> Optional[date]:
    if path is None:
        return None
    return date.fromisoformat(_end_date_from_filename(path.name))


def _normalise_yfinance_frame(data: pd.DataFrame) -> pd.DataFrame:
    """Return a single-ticker OHLCV frame with a usable Close column."""
    if isinstance(data.columns, pd.MultiIndex):
        level0 = set(data.columns.get_level_values(0))
        if "Close" in level0 or "Adj Close" in level0:
            data = data.copy()
            data.columns = data.columns.get_level_values(0)
        else:
            data = data.copy()
            data.columns = data.columns.get_level_values(-1)

    if "Adj Close" in data.columns:
        data = data.copy()
        data["Close"] = data["Adj Close"]
    if "Close" not in data.columns:
        raise ValueError("downloaded data is missing Close/Adj Close columns")

    data = data.copy()
    data.index = pd.to_datetime(data.index)
    data.index.name = "Date"
    data["Close"] = pd.to_numeric(data["Close"], errors="coerce")
    if data["Close"].dropna().empty:
        raise ValueError("downloaded data has no numeric Close values")
    return data


class NumpyEncoder(json.JSONEncoder):
    """Handle numpy types and NaN/Infinity in JSON serialisation."""

    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            v = float(obj)
            if math.isnan(v) or math.isinf(v):
                return None
            return v
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (pd.Timestamp,)):
            return str(obj)
        return super().default(obj)


# ── Data refresh ──────────────────────────────────────────────────────────

def refresh_data(dry_run: bool = False) -> Dict[str, dict]:
    """Download latest data for all 12 indices.

    Returns a dict of per-ticker refresh results.
    """
    if yf is None:
        raise RuntimeError("yfinance is required — pip install yfinance")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    results: Dict[str, dict] = {}

    for code, info in TICKER_REGISTRY.items():
        symbol = info["symbol"]
        start = info["start"]

        # Find existing CSV (if any)
        old_path = find_csv(code, DATA_DIR)
        old_name = old_path.name if old_path else None

        logger.info(f"[{code}] Downloading {symbol} from {start} to {today} ...")
        if dry_run:
            results[code] = {
                "status": SUCCESS,
                "symbol": symbol, "old_file": old_name,
                "new_file": csv_filename(code, today), "rows": 0,
                "start": start, "end": today,
                "error_type": None,
                "error": None,
            }
            continue

        try:
            data = yf.download(
                symbol, start=start, end=today,
                progress=False, auto_adjust=False,
            )
        except Exception as exc:
            logger.error(f"[{code}] Download failed for {symbol} {start} to {today}: {exc}")
            results[code] = _failure(code, REFRESH_FAILED, str(exc), old_path, type(exc).__name__)
            continue

        if data.empty:
            logger.warning(f"[{code}] No data returned — skipping")
            results[code] = _failure(code, REFRESH_FAILED, "No data returned", old_path, "EmptyData")
            continue

        try:
            data = _normalise_yfinance_frame(data)
        except Exception as exc:
            logger.error(f"[{code}] Downloaded data failed validation: {exc}")
            results[code] = _failure(code, REFRESH_FAILED, str(exc), old_path, type(exc).__name__)
            continue

        actual_end_date = data.index.max().date()
        old_end_date = _parse_file_end(old_path)
        if old_end_date is not None and actual_end_date < old_end_date:
            message = f"download regressed from {old_end_date.isoformat()} to {actual_end_date.isoformat()}"
            logger.error(f"[{code}] {message}")
            results[code] = _failure(code, REFRESH_FAILED, message, old_path, "DataRegression")
            continue

        actual_end = actual_end_date.isoformat()
        new_name = csv_filename(code, actual_end)
        new_path = DATA_DIR / new_name

        try:
            data.to_csv(new_path)
            loaded = load_price_csv(new_path, start, actual_end)
            if loaded.empty:
                raise ValueError("saved CSV reload produced no price rows")
            if old_path and old_path != new_path and old_path.exists():
                logger.info(f"[{code}] Removing old file: {old_name}")
                old_path.unlink()
        except Exception as exc:
            if new_path.exists() and new_path != old_path:
                new_path.unlink()
            logger.error(f"[{code}] Failed to save validated CSV {new_name}: {exc}")
            results[code] = _failure(code, REFRESH_FAILED, str(exc), old_path, type(exc).__name__)
            continue

        logger.info(f"[{code}] Saved {len(data)} rows → {new_name}")

        results[code] = {
            "status": SUCCESS,
            "symbol": symbol,
            "old_file": old_name,
            "new_file": new_name,
            "rows": len(data),
            "start": start,
            "end": actual_end,
            "error_type": None,
            "error": None,
        }

    return results


# ── Validation ────────────────────────────────────────────────────────────

def run_validation() -> Dict[str, dict]:
    """Run 4-claim validation on all 12 indices.

    Returns ``{code: validation_summary}`` for each index.
    """
    all_csvs = get_all_csvs(DATA_DIR)
    results: Dict[str, dict] = {}

    for code, (symbol, csv_path, start, end) in all_csvs.items():
        logger.info(f"[{code}] Validating {symbol} ({start} → {end}) ...")
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                summary = run_full_validation(
                    csv_path=str(csv_path),
                    ticker=symbol,
                    start=start,
                    end=end,
                    output_dir=tmpdir,
                )
            results[code] = summary
        except Exception as exc:
            logger.error(f"[{code}] Validation failed: {exc}")
            results[code] = {
                "status": VALIDATION_FAILED,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }

    return results


# ── Status output ─────────────────────────────────────────────────────────

def write_validation_status(
    refresh_info: Dict[str, dict],
    validation_results: Dict[str, dict],
) -> None:
    """Write ``data/validation_status.json`` and ``VALIDATION_STATUS.md``."""
    now = datetime.now(timezone.utc).isoformat()

    # ── JSON ──
    overall = "success"
    if any(r.get("status") != SUCCESS for r in refresh_info.values()):
        overall = "partial"
    if any(v.get("status") == VALIDATION_FAILED or "error" in v for v in validation_results.values()):
        overall = "partial"
    if len(refresh_info) != len(TICKER_REGISTRY) or len(validation_results) != len(TICKER_REGISTRY):
        overall = "partial"

    status = {
        "overall_status": overall,
        "last_data_refresh": now,
        "last_validation_run": now,
        "indices": {},
    }
    for code, info in TICKER_REGISTRY.items():
        entry: dict = {
            "name": info["name"],
            "symbol": info["symbol"],
        }

        ri = refresh_info.get(code)
        if ri:
            entry["status"] = ri.get("status")
            entry["data_file"] = ri.get("new_file")
            entry["data_start"] = ri.get("start")
            entry["data_end"] = ri.get("end")
            entry["rows"] = ri.get("rows")
            if ri.get("error"):
                entry["error_type"] = ri.get("error_type")
                entry["error"] = ri.get("error")
        else:
            entry["status"] = REFRESH_FAILED
            entry["error"] = "Ticker was not refreshed"

        vr = validation_results.get(code)
        if vr and "claims" in vr:
            entry["claims"] = vr["claims"]
            entry["n_trading_days"] = vr.get("n_trading_days")
        elif vr and "error" in vr:
            entry["status"] = VALIDATION_FAILED
            entry["error_type"] = vr.get("error_type")
            entry["error"] = vr["error"]

        status["indices"][code] = entry

    json_path = DATA_DIR / "validation_status.json"
    with open(json_path, "w") as f:
        json.dump(status, f, indent=2, cls=NumpyEncoder)
    logger.info(f"Wrote {json_path}")

    # ── Markdown ──
    lines = [
        "# Validation Status",
        "",
        f"> **Overall status:** {overall}",
        f"> **Last data refresh:** {now}",
        f"> **Last validation run:** {now}",
        "",
        "This file is auto-generated by the data refresh workflow.",
        "",
        "## Claim Verdicts by Index",
        "",
        "| Index | Status | Data Range | Days | Fat Tails | Outsized Influence | Clustering | Trend Following |",
        "|-------|--------|-----------|------|-----------|-------------------|------------|----------------|",
    ]

    for code, entry in status["indices"].items():
        name = entry["name"]
        row_status = entry.get("status", "unknown")
        start = entry.get("data_start", "?")
        end = entry.get("data_end", "?")
        days = entry.get("n_trading_days", "—")
        claims = entry.get("claims", {})
        c1 = _verdict_emoji(claims.get("1_fat_tails"))
        c2 = _verdict_emoji(claims.get("2_outsized_influence"))
        c3 = _verdict_emoji(claims.get("3_clustering"))
        c4 = _verdict_emoji(claims.get("4_trend_following"))
        lines.append(f"| {name} | {row_status} | {start} → {end} | {days} | {c1} | {c2} | {c3} | {c4} |")

    lines.extend(["", "✅ = CONFIRMED · ❌ = NOT CONFIRMED · — = not yet validated", ""])

    md_path = ROOT / "VALIDATION_STATUS.md"
    md_path.write_text("\n".join(lines))
    logger.info(f"Wrote {md_path}")


def write_refresh_only_status(refresh_info: Dict[str, dict]) -> None:
    """Update the JSON status file with fresh data ranges (no validation)."""
    json_path = DATA_DIR / "validation_status.json"

    # Load existing status if present
    existing: dict = {}
    if json_path.exists():
        with open(json_path) as f:
            existing = json.load(f)

    now = datetime.now(timezone.utc).isoformat()
    existing["last_data_refresh"] = now
    existing["overall_status"] = (
        "success"
        if len(refresh_info) == len(TICKER_REGISTRY)
        and all(ri.get("status") == SUCCESS for ri in refresh_info.values())
        else "partial"
    )

    indices = existing.setdefault("indices", {})
    for code, ri in refresh_info.items():
        entry = indices.setdefault(code, {})
        entry["name"] = TICKER_REGISTRY[code]["name"]
        entry["symbol"] = TICKER_REGISTRY[code]["symbol"]
        entry["status"] = ri.get("status")
        entry["data_file"] = ri.get("new_file")
        entry["data_start"] = ri.get("start")
        entry["data_end"] = ri.get("end")
        entry["rows"] = ri.get("rows")
        if ri.get("error"):
            entry["error_type"] = ri.get("error_type")
            entry["error"] = ri.get("error")

    with open(json_path, "w") as f:
        json.dump(existing, f, indent=2, cls=NumpyEncoder)
    logger.info(f"Updated {json_path} (data refresh only)")


def _verdict_emoji(verdict) -> str:
    if verdict == "CONFIRMED":
        return "✅"
    elif verdict and verdict != "CONFIRMED":
        return "❌"
    return "—"


# ── CLI ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Refresh market data and optionally validate claims",
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Run full 4-claim validation after refreshing data",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview what would be downloaded without actually doing it",
    )
    args = parser.parse_args()

    logger.info("=== Data Refresh ===")
    refresh_info = refresh_data(dry_run=args.dry_run)
    failures = {code: r for code, r in refresh_info.items() if r.get("status") != SUCCESS}
    missing = sorted(set(TICKER_REGISTRY) - set(refresh_info))
    logger.info(f"Refreshed {len(refresh_info) - len(failures)} of {len(TICKER_REGISTRY)} indices")

    if args.validate and not args.dry_run:
        logger.info("=== Running Validation ===")
        validation_results = run_validation()
        write_validation_status(refresh_info, validation_results)
        validation_failures = {
            code: result
            for code, result in validation_results.items()
            if result.get("status") == VALIDATION_FAILED or "error" in result
        }

        # Print summary
        print("\n" + "=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        for code, result in validation_results.items():
            if "claims" in result:
                verdicts = " | ".join(
                    f"{k}: {v}" for k, v in result["claims"].items()
                )
                print(f"  {code}: {verdicts}")
            elif "error" in result:
                print(f"  {code}: ERROR — {result['error']}")
        print("=" * 60)
        if failures or missing or validation_failures:
            logger.error(
                "Refresh/validation incomplete: refresh_failures=%s missing=%s validation_failures=%s",
                sorted(failures),
                missing,
                sorted(validation_failures),
            )
            sys.exit(1)
    else:
        write_refresh_only_status(refresh_info)
        if failures or missing:
            logger.error("Refresh incomplete: refresh_failures=%s missing=%s", sorted(failures), missing)
            sys.exit(1)


if __name__ == "__main__":
    main()
