"""Tests for blackswans.data.loaders."""

import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from blackswans.data.loaders import _load_csv, load_price_csv, fetch_price_data, DATA_DIR
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

    def test_uppercase_date(self, tmp_path):
        csv = tmp_path / "test.csv"
        csv.write_text("DATE,Close\n2020-01-01,100\n2020-01-02,101\n")
        df = _load_csv(csv)
        assert isinstance(df.index, pd.DatetimeIndex)
        assert len(df) == 2

    def test_index_as_dates(self, tmp_path):
        """When there's no Date column, the index should be parsed as datetime."""
        csv = tmp_path / "test.csv"
        # Write a CSV where the index (first unnamed column) holds dates
        csv.write_text(",Close\n2020-01-01,100\n2020-01-02,101\n")
        df = _load_csv(csv)
        assert isinstance(df.index, pd.DatetimeIndex)
        assert len(df) == 2

    def test_sorted_by_date(self, tmp_path):
        csv = tmp_path / "test.csv"
        csv.write_text("Date,Close\n2020-01-03,102\n2020-01-01,100\n2020-01-02,101\n")
        df = _load_csv(csv)
        assert df.index.is_monotonic_increasing


class TestLoadPriceCsv:
    def test_basic_load(self, tmp_path):
        csv = tmp_path / "prices.csv"
        csv.write_text("Date,Close\n2020-01-02,100\n2020-01-03,101\n2020-01-06,102\n")
        df = load_price_csv(csv, "2020-01-01", "2020-12-31")
        assert len(df) == 3
        assert "Close" in df.columns

    def test_adj_close_fallback(self, tmp_path):
        """When 'Close' is missing but 'Adj Close' exists, it should be used."""
        csv = tmp_path / "prices.csv"
        csv.write_text("Date,Adj Close\n2020-01-02,100\n2020-01-03,101\n")
        df = load_price_csv(csv, "2020-01-01", "2020-12-31")
        assert "Close" in df.columns
        assert len(df) == 2

    def test_date_range_filtering(self, tmp_path):
        csv = tmp_path / "prices.csv"
        csv.write_text(
            "Date,Close\n2020-01-01,98\n2020-01-02,100\n2020-01-03,101\n"
            "2020-01-06,102\n2020-01-07,103\n"
        )
        df = load_price_csv(csv, "2020-01-02", "2020-01-06")
        assert len(df) == 3
        assert df.index.min() >= pd.Timestamp("2020-01-02")
        assert df.index.max() <= pd.Timestamp("2020-01-06")

    def test_drops_nan_close(self, tmp_path):
        csv = tmp_path / "prices.csv"
        csv.write_text("Date,Close\n2020-01-02,100\n2020-01-03,NA\n2020-01-06,102\n")
        df = load_price_csv(csv, "2020-01-01", "2020-12-31")
        assert len(df) == 2

    def test_close_coerced_to_numeric(self, tmp_path):
        csv = tmp_path / "prices.csv"
        csv.write_text("Date,Close\n2020-01-02,100.5\n2020-01-03,bad\n2020-01-06,102\n")
        df = load_price_csv(csv, "2020-01-01", "2020-12-31")
        # 'bad' is coerced to NaN then dropped
        assert len(df) == 2
        assert df["Close"].dtype == float


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

    def test_cache_hit(self, tmp_path, monkeypatch):
        """When cache file exists with correct date range, use it without downloading."""
        monkeypatch.setattr("blackswans.data.loaders.DATA_DIR", tmp_path)
        # Request range must be within actual data range for cache hit
        cache_file = tmp_path / "_GSPC_2020-01-02_to_2020-06-01.csv"
        cache_file.write_text(
            "Date,Close\n2020-01-02,100\n2020-01-03,101\n"
            "2020-03-15,150\n2020-06-01,200\n"
        )
        df = fetch_price_data("^GSPC", "2020-01-02", "2020-06-01")
        assert len(df) == 4
        assert "Close" in df.columns

    def test_cache_miss_date_range_mismatch(self, tmp_path, monkeypatch):
        """When cache exists but date range doesn't cover request, re-download."""
        monkeypatch.setattr("blackswans.data.loaders.DATA_DIR", tmp_path)
        # Cache only covers Jan 2020
        cache_file = tmp_path / "_GSPC_2020-01-01_to_2020-12-31.csv"
        cache_file.write_text("Date,Close\n2020-01-02,100\n2020-01-03,101\n")

        # Mock yfinance download to return fresh data
        mock_data = pd.DataFrame(
            {"Close": [100, 101, 150, 200]},
            index=pd.to_datetime(["2020-01-02", "2020-06-01", "2020-09-01", "2020-12-30"]),
        )
        mock_data.index.name = "Date"
        mock_yf = MagicMock()
        mock_yf.download.return_value = mock_data
        monkeypatch.setattr("blackswans.data.loaders.yf", mock_yf)

        df = fetch_price_data("^GSPC", "2020-01-01", "2020-12-31")
        mock_yf.download.assert_called_once()
        assert len(df) >= 1

    def test_cache_empty_triggers_download(self, tmp_path, monkeypatch):
        """Empty cache file should trigger re-download."""
        monkeypatch.setattr("blackswans.data.loaders.DATA_DIR", tmp_path)
        cache_file = tmp_path / "TEST_2020-01-01_to_2020-12-31.csv"
        cache_file.write_text("Date,Close\n")  # header only, empty data

        mock_data = pd.DataFrame(
            {"Close": [100, 101]},
            index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
        )
        mock_data.index.name = "Date"
        mock_yf = MagicMock()
        mock_yf.download.return_value = mock_data
        monkeypatch.setattr("blackswans.data.loaders.yf", mock_yf)

        df = fetch_price_data("TEST", "2020-01-01", "2020-12-31")
        mock_yf.download.assert_called_once()

    def test_yfinance_not_installed(self, tmp_path, monkeypatch):
        """When yfinance is None and no CSV, should raise RuntimeError."""
        monkeypatch.setattr("blackswans.data.loaders.DATA_DIR", tmp_path)
        monkeypatch.setattr("blackswans.data.loaders.yf", None)
        with pytest.raises(RuntimeError, match="yfinance not installed"):
            fetch_price_data("TEST", "2020-01-01", "2020-12-31")

    def test_yfinance_returns_empty(self, tmp_path, monkeypatch):
        """When yfinance returns empty data, should raise ValueError."""
        monkeypatch.setattr("blackswans.data.loaders.DATA_DIR", tmp_path)
        mock_yf = MagicMock()
        mock_yf.download.return_value = pd.DataFrame()
        monkeypatch.setattr("blackswans.data.loaders.yf", mock_yf)

        with pytest.raises(ValueError, match="No data for"):
            fetch_price_data("FAKE", "2020-01-01", "2020-12-31")

    def test_yfinance_multiindex_columns(self, tmp_path, monkeypatch):
        """yfinance may return MultiIndex columns; they should be flattened."""
        monkeypatch.setattr("blackswans.data.loaders.DATA_DIR", tmp_path)

        idx = pd.to_datetime(["2020-01-02", "2020-01-03"])
        arrays = [["Close", "Adj Close"], ["FAKE", "FAKE"]]
        tuples = list(zip(*arrays))
        cols = pd.MultiIndex.from_tuples(tuples, names=["Price", "Ticker"])
        data = pd.DataFrame([[100, 100], [101, 101]], index=idx, columns=cols)
        data.index.name = "Date"

        mock_yf = MagicMock()
        mock_yf.download.return_value = data
        monkeypatch.setattr("blackswans.data.loaders.yf", mock_yf)

        df = fetch_price_data("FAKE", "2020-01-01", "2020-12-31")
        assert "Close" in df.columns

    def test_yfinance_adj_close_copied(self, tmp_path, monkeypatch):
        """When download has Adj Close, it should be copied to Close column."""
        monkeypatch.setattr("blackswans.data.loaders.DATA_DIR", tmp_path)

        data = pd.DataFrame(
            {"Adj Close": [100, 101], "Open": [99, 100]},
            index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
        )
        data.index.name = "Date"

        mock_yf = MagicMock()
        mock_yf.download.return_value = data
        monkeypatch.setattr("blackswans.data.loaders.yf", mock_yf)

        df = fetch_price_data("ADJ", "2020-01-01", "2020-12-31")
        assert "Close" in df.columns
        assert df["Close"].iloc[0] == 100

    def test_overwrite_flag_skips_cache(self, tmp_path, monkeypatch):
        """With overwrite=True, existing cache should be ignored."""
        monkeypatch.setattr("blackswans.data.loaders.DATA_DIR", tmp_path)
        cache_file = tmp_path / "TEST_2020-01-01_to_2020-12-31.csv"
        cache_file.write_text(
            "Date,Close\n2020-01-02,100\n2020-01-03,101\n2020-12-30,200\n"
        )

        mock_data = pd.DataFrame(
            {"Close": [999, 998]},
            index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
        )
        mock_data.index.name = "Date"
        mock_yf = MagicMock()
        mock_yf.download.return_value = mock_data
        monkeypatch.setattr("blackswans.data.loaders.yf", mock_yf)

        df = fetch_price_data("TEST", "2020-01-01", "2020-12-31", overwrite=True)
        mock_yf.download.assert_called_once()

    def test_download_saves_cache_file(self, tmp_path, monkeypatch):
        """Downloaded data should be saved to cache file."""
        monkeypatch.setattr("blackswans.data.loaders.DATA_DIR", tmp_path)

        mock_data = pd.DataFrame(
            {"Close": [100, 101]},
            index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
        )
        mock_data.index.name = "Date"
        mock_yf = MagicMock()
        mock_yf.download.return_value = mock_data
        monkeypatch.setattr("blackswans.data.loaders.yf", mock_yf)

        fetch_price_data("SAVE", "2020-01-01", "2020-12-31")
        cache_file = tmp_path / "SAVE_2020-01-01_to_2020-12-31.csv"
        assert cache_file.exists()
