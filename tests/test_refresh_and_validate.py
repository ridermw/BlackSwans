"""Tests for refresh safety behavior."""

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

import scripts.refresh_and_validate as refresh


def _prices(dates=("2025-01-31", "2026-05-22"), close=(100, 120)):
    data = pd.DataFrame({"Close": close}, index=pd.to_datetime(list(dates)))
    data.index.name = "Date"
    return data


def test_refresh_success_preserves_until_new_csv_valid(monkeypatch, tmp_path):
    old_csv = tmp_path / "_GSPC_1928-09-04_to_2025-01-31.csv"
    old_csv.write_text("Date,Close\n2025-01-31,100\n")
    mock_yf = MagicMock()
    mock_yf.download.return_value = _prices()

    monkeypatch.setattr(refresh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(refresh, "TICKER_REGISTRY", {"sp500": refresh.TICKER_REGISTRY["sp500"]})
    monkeypatch.setattr(refresh, "yf", mock_yf)

    results = refresh.refresh_data()

    result = results["sp500"]
    assert result["status"] == refresh.SUCCESS
    assert result["end"] == "2026-05-22"
    assert not old_csv.exists()
    assert (tmp_path / "_GSPC_1928-09-04_to_2026-05-22.csv").exists()


def test_refresh_rejects_data_regression_and_keeps_old_csv(monkeypatch, tmp_path):
    old_csv = tmp_path / "_GSPC_1928-09-04_to_2026-05-22.csv"
    old_csv.write_text("Date,Close\n2026-05-22,120\n")
    mock_yf = MagicMock()
    mock_yf.download.return_value = _prices(dates=("2025-01-30", "2025-01-31"), close=(99, 100))

    monkeypatch.setattr(refresh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(refresh, "TICKER_REGISTRY", {"sp500": refresh.TICKER_REGISTRY["sp500"]})
    monkeypatch.setattr(refresh, "yf", mock_yf)

    results = refresh.refresh_data()

    result = results["sp500"]
    assert result["status"] == refresh.REFRESH_FAILED
    assert result["error_type"] == "DataRegression"
    assert old_csv.exists()
    assert not (tmp_path / "_GSPC_1928-09-04_to_2025-01-31.csv").exists()


def test_refresh_rejects_missing_close_and_keeps_old_csv(monkeypatch, tmp_path):
    old_csv = tmp_path / "_GSPC_1928-09-04_to_2025-01-31.csv"
    old_csv.write_text("Date,Close\n2025-01-31,100\n")
    bad_data = pd.DataFrame({"Open": [100, 101]}, index=pd.to_datetime(["2026-05-21", "2026-05-22"]))
    mock_yf = MagicMock()
    mock_yf.download.return_value = bad_data

    monkeypatch.setattr(refresh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(refresh, "TICKER_REGISTRY", {"sp500": refresh.TICKER_REGISTRY["sp500"]})
    monkeypatch.setattr(refresh, "yf", mock_yf)

    results = refresh.refresh_data()

    result = results["sp500"]
    assert result["status"] == refresh.REFRESH_FAILED
    assert old_csv.exists()
    assert "Close" in result["error"]


def test_refresh_records_empty_data_failure(monkeypatch, tmp_path):
    mock_yf = MagicMock()
    mock_yf.download.return_value = pd.DataFrame()

    monkeypatch.setattr(refresh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(refresh, "TICKER_REGISTRY", {"sp500": refresh.TICKER_REGISTRY["sp500"]})
    monkeypatch.setattr(refresh, "yf", mock_yf)

    results = refresh.refresh_data()

    assert results["sp500"]["status"] == refresh.REFRESH_FAILED
    assert results["sp500"]["error_type"] == "EmptyData"
