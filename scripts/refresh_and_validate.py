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
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

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
    find_csv,
    get_all_csvs,
)
from blackswans.validate_claims import run_full_validation

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


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

    Returns a dict of ``{code: {symbol, old_file, new_file, rows, start, end}}``.
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

        logger.info(f"[{code}] Downloading {symbol} from {start} to {today} …")
        if dry_run:
            results[code] = {
                "symbol": symbol, "old_file": old_name,
                "new_file": csv_filename(code, today), "rows": 0,
                "start": start, "end": today,
            }
            continue

        try:
            data = yf.download(
                symbol, start=start, end=today,
                progress=False, auto_adjust=False,
            )
        except Exception as exc:
            logger.error(f"[{code}] Download failed: {exc}")
            continue

        if data.empty:
            logger.warning(f"[{code}] No data returned — skipping")
            continue

        # Flatten MultiIndex columns produced by newer yfinance versions
        if isinstance(data.columns, pd.MultiIndex):
            data = data.droplevel("Ticker", axis=1)
            data.columns.name = None

        if "Adj Close" in data.columns:
            data["Close"] = data["Adj Close"]

        data.index.name = "Date"

        # Name file using the actual last trading day, not today
        actual_end = data.index.max().strftime("%Y-%m-%d")
        new_name = csv_filename(code, actual_end)
        new_path = DATA_DIR / new_name

        # Remove old CSV if the name changed
        if old_path and old_path != new_path and old_path.exists():
            logger.info(f"[{code}] Removing old file: {old_name}")
            old_path.unlink()

        data.to_csv(new_path)
        logger.info(f"[{code}] Saved {len(data)} rows → {new_name}")

        results[code] = {
            "symbol": symbol,
            "old_file": old_name,
            "new_file": new_name,
            "rows": len(data),
            "start": start,
            "end": actual_end,
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
        logger.info(f"[{code}] Validating {symbol} ({start} → {end}) …")
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
            results[code] = {"error": str(exc)}

    return results


# ── Status output ─────────────────────────────────────────────────────────

def write_validation_status(
    refresh_info: Dict[str, dict],
    validation_results: Dict[str, dict],
) -> None:
    """Write ``data/validation_status.json`` and ``VALIDATION_STATUS.md``."""
    now = datetime.now(timezone.utc).isoformat()

    # ── JSON ──
    status = {
        "last_run": now,
        "indices": {},
    }
    for code, info in TICKER_REGISTRY.items():
        entry: dict = {
            "name": info["name"],
            "symbol": info["symbol"],
        }

        ri = refresh_info.get(code)
        if ri:
            entry["data_file"] = ri.get("new_file")
            entry["data_start"] = ri.get("start")
            entry["data_end"] = ri.get("end")
            entry["rows"] = ri.get("rows")

        vr = validation_results.get(code)
        if vr and "claims" in vr:
            entry["claims"] = vr["claims"]
            entry["n_trading_days"] = vr.get("n_trading_days")
        elif vr and "error" in vr:
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
        f"> **Last run:** {now}",
        "",
        "This file is auto-generated by the weekly/monthly data refresh workflow.",
        "",
        "## Claim Verdicts by Index",
        "",
        "| Index | Data Range | Days | Fat Tails | Outsized Influence | Clustering | Trend Following |",
        "|-------|-----------|------|-----------|-------------------|------------|----------------|",
    ]

    for code, entry in status["indices"].items():
        name = entry["name"]
        start = entry.get("data_start", "?")
        end = entry.get("data_end", "?")
        days = entry.get("n_trading_days", "—")
        claims = entry.get("claims", {})
        c1 = _verdict_emoji(claims.get("1_fat_tails"))
        c2 = _verdict_emoji(claims.get("2_outsized_influence"))
        c3 = _verdict_emoji(claims.get("3_clustering"))
        c4 = _verdict_emoji(claims.get("4_trend_following"))
        lines.append(f"| {name} | {start} → {end} | {days} | {c1} | {c2} | {c3} | {c4} |")

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

    indices = existing.setdefault("indices", {})
    for code, ri in refresh_info.items():
        entry = indices.setdefault(code, {})
        entry["name"] = TICKER_REGISTRY[code]["name"]
        entry["symbol"] = TICKER_REGISTRY[code]["symbol"]
        entry["data_file"] = ri.get("new_file")
        entry["data_start"] = ri.get("start")
        entry["data_end"] = ri.get("end")
        entry["rows"] = ri.get("rows")

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
    logger.info(f"Refreshed {len(refresh_info)} indices")

    if args.validate and not args.dry_run:
        logger.info("=== Running Validation ===")
        validation_results = run_validation()
        write_validation_status(refresh_info, validation_results)

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
    else:
        write_refresh_only_status(refresh_info)


if __name__ == "__main__":
    main()
