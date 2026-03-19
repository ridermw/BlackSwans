"""Tests for blackswans.cli — CLI entry point."""

import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from blackswans.cli import main


def _write_synthetic_csv(path: Path, num_days: int = 50) -> Path:
    """Write a minimal price CSV with enough rows for MA and outlier analysis."""
    dates = pd.bdate_range("2020-01-01", periods=num_days)
    prices = [100 + i * 0.5 + ((-1) ** i) * 2 for i in range(num_days)]
    df = pd.DataFrame({"Date": dates, "Close": prices})
    df.to_csv(path, index=False)
    return path


class TestCliHelp:
    def test_help_exits_zero(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["blackswans", "--help"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


class TestCliWithSyntheticCsv:
    def test_runs_full_pipeline(self, tmp_path, monkeypatch):
        csv_path = _write_synthetic_csv(tmp_path / "prices.csv", num_days=250)
        output_dir = tmp_path / "out"
        monkeypatch.setattr(sys, "argv", [
            "blackswans",
            "--ticker", "TEST",
            "--start", "2020-01-01",
            "--end", "2021-06-01",
            "--csv", str(csv_path),
            "--output-dir", str(output_dir),
            "--quantiles", "0.99",
            "--ma-window", "50",
            "--best-count", "5",
            "--worst-count", "5",
        ])
        # Mock make_plots to avoid matplotlib rendering
        with patch("blackswans.cli.make_plots"):
            main()

        assert (output_dir / "outlier_stats.csv").exists()
        assert (output_dir / "return_scenarios.csv").exists()
        assert (output_dir / "regime_performance.csv").exists()
        assert (output_dir / "outlier_regime_counts.csv").exists()

    def test_output_contents_valid(self, tmp_path, monkeypatch):
        csv_path = _write_synthetic_csv(tmp_path / "prices.csv", num_days=250)
        output_dir = tmp_path / "out"
        monkeypatch.setattr(sys, "argv", [
            "blackswans",
            "--ticker", "TEST",
            "--start", "2020-01-01",
            "--end", "2021-06-01",
            "--csv", str(csv_path),
            "--output-dir", str(output_dir),
            "--quantiles", "0.99",
            "--ma-window", "50",
        ])
        with patch("blackswans.cli.make_plots"):
            main()

        stats = pd.read_csv(output_dir / "outlier_stats.csv", index_col=0)
        assert len(stats) >= 1

        scenarios = pd.read_csv(output_dir / "return_scenarios.csv", index_col=0)
        assert "annualised_return" in scenarios.columns
        # Should contain base 'all' plus quantile-based rows
        assert "all" in scenarios.index

    def test_multiple_quantiles(self, tmp_path, monkeypatch):
        csv_path = _write_synthetic_csv(tmp_path / "prices.csv", num_days=250)
        output_dir = tmp_path / "out"
        monkeypatch.setattr(sys, "argv", [
            "blackswans",
            "--ticker", "TEST",
            "--start", "2020-01-01",
            "--end", "2021-06-01",
            "--csv", str(csv_path),
            "--output-dir", str(output_dir),
            "--quantiles", "0.95", "0.99",
            "--ma-window", "50",
        ])
        with patch("blackswans.cli.make_plots"):
            main()

        stats = pd.read_csv(output_dir / "outlier_stats.csv", index_col=0)
        assert len(stats) == 2

    def test_default_args(self, tmp_path, monkeypatch):
        """CLI should work with defaults when given just --csv and --output-dir."""
        csv_path = _write_synthetic_csv(tmp_path / "prices.csv", num_days=250)
        output_dir = tmp_path / "out"
        monkeypatch.setattr(sys, "argv", [
            "blackswans",
            "--csv", str(csv_path),
            "--output-dir", str(output_dir),
        ])
        with patch("blackswans.cli.make_plots"):
            main()

        assert (output_dir / "outlier_stats.csv").exists()

    def test_overwrite_flag_accepted(self, tmp_path, monkeypatch):
        """--overwrite flag should be accepted without error."""
        csv_path = _write_synthetic_csv(tmp_path / "prices.csv", num_days=250)
        output_dir = tmp_path / "out"
        monkeypatch.setattr(sys, "argv", [
            "blackswans",
            "--csv", str(csv_path),
            "--output-dir", str(output_dir),
            "--overwrite",
        ])
        with patch("blackswans.cli.make_plots"):
            main()

        assert (output_dir / "outlier_stats.csv").exists()
