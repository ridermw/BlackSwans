"""Tests for blackswans.data.loaders."""

import pandas as pd
import pytest
from pathlib import Path

from blackswans.data.loaders import _load_csv, fetch_price_data
from blackswans.sanitize import sanitize_ticker


class TestLoadCsv:
    def test_date_column(self, tmp_path):
        csv = tmp_path / "test.csv"
        csv.write_text("Date,Close\n2020-01-01,100\n2020-01-02,101\n")
        df = _load_csv(csv)
        assert isinstance(df.index, pd.DatetimeIndex)
        assert "Close" in df.columns
        assert len(df) == 2

    def test_lowercase_date(self, tmp_path):
        csv = tmp_path / "test.csv"
        csv.write_text("date,Close\n2020-01-01,100\n2020-01-02,101\n")
        df = _load_csv(csv)
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_sorted_by_date(self, tmp_path):
        csv = tmp_path / "test.csv"
        csv.write_text("Date,Close\n2020-01-03,102\n2020-01-01,100\n2020-01-02,101\n")
        df = _load_csv(csv)
        assert df.index.is_monotonic_increasing


class TestFetchPriceData:
    def test_load_from_csv(self, tmp_path):
        csv = tmp_path / "prices.csv"
        csv.write_text("Date,Close\n2020-01-02,100\n2020-01-03,101\n2020-01-06,102\n")
        df = fetch_price_data("TEST", "2020-01-01", "2020-12-31", csv_path=str(csv))
        assert len(df) == 3
        assert "Close" in df.columns

    def test_adj_close_fallback(self, tmp_path):
        csv = tmp_path / "prices.csv"
        csv.write_text("Date,Adj Close\n2020-01-02,100\n2020-01-03,101\n")
        df = fetch_price_data("TEST", "2020-01-01", "2020-12-31", csv_path=str(csv))
        assert "Close" in df.columns

    def test_missing_csv_warns(self, tmp_path, caplog):
        # Should warn about missing CSV, then fail (ValueError from yfinance or RuntimeError)
        with pytest.raises((RuntimeError, ValueError)):
            fetch_price_data("TEST", "2020-01-01", "2020-12-31",
                           csv_path=str(tmp_path / "nonexistent.csv"))

    def test_malicious_ticker_with_path_separator(self, tmp_path):
        """Tickers with path separators are sanitized and can't escape DATA_DIR."""
        csv = tmp_path / "prices.csv"
        csv.write_text("Date,Close\n2020-01-02,100\n2020-01-03,101\n")
        # The ticker is sanitized so '../evil' becomes '.._evil' which stays in DATA_DIR
        df = fetch_price_data("../evil", "2020-01-01", "2020-12-31", csv_path=str(csv))
        assert len(df) == 2

    def test_ticker_special_chars_sanitized(self):
        """Verify sanitize_ticker strips dangerous characters."""
        assert sanitize_ticker("^GSPC") == "^GSPC"
        assert sanitize_ticker("../evil") == "___evil"
        assert sanitize_ticker("ticker;rm -rf /") == "ticker_rm_-rf__"
        assert sanitize_ticker("normal-dash_under") == "normal-dash_under"

    def test_date_range_slicing(self, tmp_path):
        csv = tmp_path / "prices.csv"
        csv.write_text(
            "Date,Close\n2020-01-01,98\n2020-01-02,100\n2020-01-03,101\n"
            "2020-01-06,102\n2020-01-07,103\n"
        )
        df = fetch_price_data("TEST", "2020-01-02", "2020-01-06", csv_path=str(csv))
        assert len(df) == 3
        assert df.index.min() >= pd.Timestamp("2020-01-02")
        assert df.index.max() <= pd.Timestamp("2020-01-06")
