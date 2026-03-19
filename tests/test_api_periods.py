"""Tests for v0.3 period comparison API endpoints."""

import pytest
from fastapi.testclient import TestClient

from api.main import app, DATA_DIR

client = TestClient(app)

# Check if real data files exist for integration tests
HAS_DATA = (DATA_DIR / "_GSPC_1928-09-04_to_2025-01-31.csv").exists()
skip_no_data = pytest.mark.skipif(not HAS_DATA, reason="No CSV data files present")


class TestPeriodComparison:
    @skip_no_data
    def test_basic_response(self):
        resp = client.get("/api/period-comparison/sp500")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "sp500"
        assert data["split_date"] == "2011-01-01"
        assert len(data["periods"]) == 3

    @skip_no_data
    def test_period_keys(self):
        resp = client.get("/api/period-comparison/sp500")
        data = resp.json()
        period_keys = [p["period"] for p in data["periods"]]
        assert set(period_keys) == {"pre", "post", "full"}

    @skip_no_data
    def test_each_period_has_claims(self):
        resp = client.get("/api/period-comparison/sp500")
        data = resp.json()
        for period in data["periods"]:
            assert "fat_tails" in period
            assert "outsized_influence" in period
            assert "clustering" in period
            assert "trend_following" in period
            for claim in ["fat_tails", "outsized_influence", "clustering", "trend_following"]:
                assert "verdict" in period[claim]

    @skip_no_data
    def test_custom_split_date(self):
        resp = client.get("/api/period-comparison/sp500?split_date=2015-01-01")
        assert resp.status_code == 200
        data = resp.json()
        assert data["split_date"] == "2015-01-01"

    def test_invalid_ticker(self):
        resp = client.get("/api/period-comparison/invalid_ticker")
        assert resp.status_code == 404


class TestCagrMatrix:
    @skip_no_data
    def test_basic_response(self):
        resp = client.get("/api/cagr-matrix/sp500")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "sp500"
        assert data["n_days"] == 10
        assert len(data["rows"]) == 3

    @skip_no_data
    def test_cagr_values_present(self):
        resp = client.get("/api/cagr-matrix/sp500")
        data = resp.json()
        for row in data["rows"]:
            assert "cagr_all" in row
            assert "cagr_miss_best" in row
            assert "cagr_miss_worst" in row
            assert "cagr_miss_both" in row
            assert "impact_miss_both" in row
            assert row["cagr_miss_best"] < row["cagr_all"]
            assert row["cagr_miss_worst"] > row["cagr_all"]

    @skip_no_data
    def test_custom_n_days(self):
        resp = client.get("/api/cagr-matrix/sp500?n_days=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["n_days"] == 5

    def test_invalid_ticker(self):
        resp = client.get("/api/cagr-matrix/invalid_ticker")
        assert resp.status_code == 404


class TestMultiIndex:
    @skip_no_data
    def test_basic_response(self):
        resp = client.get("/api/multi-index")
        assert resp.status_code == 200
        data = resp.json()
        assert "indices" in data
        assert len(data["indices"]) >= 1

    @skip_no_data
    def test_index_fields(self):
        resp = client.get("/api/multi-index")
        data = resp.json()
        for idx in data["indices"]:
            assert "ticker" in idx
            assert "name" in idx
            assert "cagr_full" in idx
            assert "kurtosis_full" in idx
            assert "n_trading_days" in idx

    @skip_no_data
    def test_custom_split_date(self):
        resp = client.get("/api/multi-index?split_date=2015-01-01")
        assert resp.status_code == 200
        data = resp.json()
        assert data["split_date"] == "2015-01-01"


class TestExistingEndpoints:
    """Verify existing endpoints still work after changes."""

    def test_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_tickers(self):
        resp = client.get("/api/tickers")
        assert resp.status_code == 200

    @skip_no_data
    def test_analysis(self):
        resp = client.get("/api/analysis/sp500")
        assert resp.status_code == 200

    @skip_no_data
    def test_chart_data(self):
        resp = client.get("/api/chart-data/sp500")
        assert resp.status_code == 200
