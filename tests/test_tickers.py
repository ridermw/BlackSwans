"""Tests for the shared ticker registry module."""

import tempfile
from pathlib import Path

import pytest

from blackswans.data.tickers import (
    TICKER_REGISTRY,
    _PERIODS_KEY_MAP,
    _end_date_from_filename,
    _sanitize_symbol,
    csv_filename,
    find_csv,
    get_all_csvs,
    get_periods_ticker_map,
)


class TestTickerRegistry:
    """Tests for the TICKER_REGISTRY constant."""

    def test_has_12_tickers(self):
        assert len(TICKER_REGISTRY) == 12

    def test_all_entries_have_required_keys(self):
        for code, info in TICKER_REGISTRY.items():
            assert "symbol" in info, f"{code} missing 'symbol'"
            assert "name" in info, f"{code} missing 'name'"
            assert "start" in info, f"{code} missing 'start'"

    def test_sp500_symbol(self):
        assert TICKER_REGISTRY["sp500"]["symbol"] == "^GSPC"

    def test_codes_are_lowercase(self):
        for code in TICKER_REGISTRY:
            assert code == code.lower(), f"Key {code!r} should be lowercase"


class TestHelpers:
    """Tests for utility functions."""

    def test_sanitize_symbol_caret(self):
        assert _sanitize_symbol("^GSPC") == "_GSPC"

    def test_sanitize_symbol_no_caret(self):
        assert _sanitize_symbol("EFA") == "EFA"

    def test_end_date_from_filename(self):
        assert _end_date_from_filename("_GSPC_1928-09-04_to_2025-01-31.csv") == "2025-01-31"

    def test_end_date_from_etf_filename(self):
        assert _end_date_from_filename("EFA_2001-08-27_to_2025-01-31.csv") == "2025-01-31"

    def test_csv_filename(self):
        result = csv_filename("sp500", "2026-04-01")
        assert result == "_GSPC_1928-09-04_to_2026-04-01.csv"

    def test_csv_filename_etf(self):
        result = csv_filename("efa", "2026-04-01")
        assert result == "EFA_2001-08-27_to_2026-04-01.csv"


class TestFindCsv:
    """Tests for find_csv()."""

    def test_find_csv_returns_path(self, tmp_path):
        (tmp_path / "_GSPC_1928-09-04_to_2025-01-31.csv").touch()
        result = find_csv("sp500", tmp_path)
        assert result is not None
        assert result.name == "_GSPC_1928-09-04_to_2025-01-31.csv"

    def test_find_csv_returns_latest(self, tmp_path):
        (tmp_path / "_GSPC_1928-09-04_to_2025-01-31.csv").touch()
        (tmp_path / "_GSPC_1928-09-04_to_2026-04-01.csv").touch()
        result = find_csv("sp500", tmp_path)
        assert result.name == "_GSPC_1928-09-04_to_2026-04-01.csv"

    def test_find_csv_missing_returns_none(self, tmp_path):
        assert find_csv("sp500", tmp_path) is None

    def test_find_csv_unknown_code_returns_none(self, tmp_path):
        assert find_csv("unknown_ticker", tmp_path) is None

    def test_find_csv_etf_style(self, tmp_path):
        (tmp_path / "EFA_2001-08-27_to_2025-01-31.csv").touch()
        result = find_csv("efa", tmp_path)
        assert result is not None
        assert result.name == "EFA_2001-08-27_to_2025-01-31.csv"


class TestGetAllCsvs:
    """Tests for get_all_csvs()."""

    def test_returns_dict_for_matching_files(self, tmp_path):
        (tmp_path / "_GSPC_1928-09-04_to_2025-01-31.csv").touch()
        (tmp_path / "EFA_2001-08-27_to_2025-01-31.csv").touch()
        result = get_all_csvs(tmp_path)
        assert "sp500" in result
        assert "efa" in result
        # Each entry is (symbol, path, start, end)
        sym, path, start, end = result["sp500"]
        assert sym == "^GSPC"
        assert end == "2025-01-31"

    def test_skips_missing_tickers(self, tmp_path):
        # Only sp500 present
        (tmp_path / "_GSPC_1928-09-04_to_2025-01-31.csv").touch()
        result = get_all_csvs(tmp_path)
        assert "sp500" in result
        assert "nikkei" not in result

    def test_empty_dir(self, tmp_path):
        result = get_all_csvs(tmp_path)
        assert len(result) == 0


class TestGetPeriodsTickerMap:
    """Tests for get_periods_ticker_map()."""

    def test_returns_uppercase_keys(self, tmp_path):
        (tmp_path / "_GSPC_1928-09-04_to_2025-01-31.csv").touch()
        result = get_periods_ticker_map(tmp_path)
        assert "SP500" in result
        assert "sp500" not in result

    def test_entry_format(self, tmp_path):
        (tmp_path / "_GSPC_1928-09-04_to_2025-01-31.csv").touch()
        entry = get_periods_ticker_map(tmp_path)["SP500"]
        assert entry["file"] == "_GSPC_1928-09-04_to_2025-01-31.csv"
        assert entry["name"] == "S&P 500"
        assert entry["start"] == "1928-09-04"
        assert entry["end"] == "2025-01-31"

    def test_periods_key_map_covers_all(self):
        """Ensure _PERIODS_KEY_MAP maps to every code in TICKER_REGISTRY."""
        mapped_codes = set(_PERIODS_KEY_MAP.values())
        registry_codes = set(TICKER_REGISTRY.keys())
        assert mapped_codes == registry_codes


class TestIntegrationWithRealData:
    """Integration tests using the actual data/ directory."""

    def test_find_csv_with_real_data(self):
        """Verify find_csv works with the actual data directory."""
        result = find_csv("sp500")
        if result is not None:
            assert "GSPC" in result.name
            assert result.exists()

    def test_get_all_csvs_with_real_data(self):
        """Verify get_all_csvs finds all expected files."""
        result = get_all_csvs()
        # Should find at least the 12 CSVs shipped in data/
        assert len(result) >= 12
        for code in TICKER_REGISTRY:
            assert code in result, f"Missing CSV for {code}"
