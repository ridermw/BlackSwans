# Black Swans Validation

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Tests](https://img.shields.io/badge/tests-197%20passing-green)
![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen)
![License: AGPL v3](https://img.shields.io/badge/license-AGPL%20v3-blue)

> Validate and extend the analysis from **"Where the Black Swans Hide & The 10 Best Days Myth"** by Faber & CQR (Aug 2011) — with an interactive dashboard for exploring outlier dynamics across 12 global indices.

Repository: [https://github.com/ridermw/BlackSwans](https://github.com/ridermw/BlackSwans)

## Key Findings

All four core claims from Faber's 2011 paper are **statistically confirmed**:

| Claim | Verdict | Key Evidence |
|-------|---------|-------------|
| Market returns are fat-tailed | **CONFIRMED** | Excess kurtosis = 17.6, Jarque-Bera p ≈ 0 |
| Extreme days have outsized influence | **CONFIRMED** | Missing 10 days: -1.4% CAGR (95% CI: [1.2%, 1.6%]) |
| Outliers cluster in bear markets | **CONFIRMED** | 70.7% in downtrends, p ≈ 10⁻⁵², robust across 12 parameter combos |
| Trend-following reduces worst volatility | **CONFIRMED** | Max drawdown: -26% (strategy) vs -86% (buy-hold) |

See [docs/validation_report.md](docs/validation_report.md) for the full report with statistical evidence.

## Dashboard

An interactive React dashboard provides four pages for exploring the analysis:

| Page | Description |
|------|-------------|
| **Landing** | Thesis verdict with key statistics and claim summaries |
| **Period Comparison** | Pre/post-2011 analysis of all 4 claims (did findings hold after publication?) |
| **Multi-Index** | 12 global indices compared in a sortable table with per-index verdicts |
| **CAGR Research** | Interactive scenario analysis with waterfall charts (miss best/worst N days) |

---

## Installation

```bash
git clone https://github.com/ridermw/BlackSwans.git
cd BlackSwans
pip install -e ".[dev]"
```

## Usage

### Run the analysis (CLI)

```bash
# Using the package CLI
blackswans --ticker ^GSPC --start 1928-09-04 --end 2026-05-22 \
  --csv data/_GSPC_1928-09-04_to_2026-05-22.csv --output-dir output/sp500

# Or using the legacy script
python src/validate_outliers.py --ticker ^GSPC --start 1928-09-04 --end 2026-05-22
```

### Run the full validation (all 4 claims)

```bash
python -m blackswans.validate_claims \
  --csv data/_GSPC_1928-09-04_to_2026-05-22.csv \
  --ticker ^GSPC --start 1928-09-04 --end 2026-05-22 \
  --output-dir output/validation
```

### Start the dashboard

```bash
# Start the dashboard
cd frontend && npm run dev

# In another terminal, start the API
cd api && uvicorn main:app --reload
```

### Run tests

```bash
pytest tests/ -v                                    # 197 tests
pytest tests/ -v --cov=src/blackswans              # with coverage (88%)
```

## Static Deployment

Generate pre-computed JSON and build the frontend for GitHub Pages or any static host:

```bash
python scripts/generate_static_data.py
cd frontend && npm run build
```

## Living Repo — Data Refresh

This repo includes a guarded refresh script for keeping the research dataset current. It names CSV files with the latest actual trading date returned by Yahoo Finance, preserves prior data on failed refreshes, and writes timestamped validation status artifacts.

```bash
# Run locally
python scripts/refresh_and_validate.py                  # data refresh only
python scripts/refresh_and_validate.py --validate       # data + full validation
python scripts/refresh_and_validate.py --dry-run        # preview only
```

## Project Structure

```
BlackSwans/
├── src/
│   ├── blackswans/              # Main package (v0.3.0)
│   │   ├── analysis/
│   │   │   ├── outliers.py      # Outlier identification & stats
│   │   │   ├── scenarios.py     # Scenario returns (miss best/worst days)
│   │   │   ├── regimes.py       # MA regime classification & performance
│   │   │   ├── statistics.py    # Statistical tests (chi-sq, KS, bootstrap)
│   │   │   └── periods.py       # Split-period analysis (pre/post-publication)
│   │   ├── data/
│   │   │   ├── loaders.py       # Data loading & caching
│   │   │   └── transforms.py    # Daily return computation
│   │   ├── visualization/
│   │   │   └── plots.py         # Matplotlib chart generation
│   │   ├── io/writers.py        # CSV output
│   │   ├── cli.py               # CLI entry point
│   │   └── validate_claims.py   # Full 4-claim validation
│   └── validate_outliers.py     # Legacy wrapper
├── api/                         # FastAPI backend (8 endpoints)
│   ├── main.py                  # API application
│   └── models.py                # Pydantic response models
├── frontend/                    # React + Vite dashboard (4 pages)
│   └── src/
│       ├── pages/               # Landing, PeriodComparison, MultiIndex, CagrResearch
│       ├── components/          # Reusable chart and UI components
│       └── services/api.js      # API client with fetchWithFallback
├── scripts/
│   └── generate_static_data.py  # Static JSON generation for GitHub Pages
├── tests/                       # 197 tests (pytest, 88% coverage)
├── data/                        # 12 index CSV files (through 2026-05-22)
├── output/                      # Analysis results
├── docs/
│   ├── audit_report.md          # M0 code & methodology audit
│   ├── validation_report.md     # Full statistical validation
│   └── wiki/                    # Project documentation (synced to GitHub Wiki)
└── pyproject.toml               # Package config
```

## Data

12 market indices analyzed:

| Index | Ticker | Period | File |
|-------|--------|--------|------|
| S&P 500 | ^GSPC | 1928-2026 | `_GSPC_1928-09-04_to_2026-05-22.csv` |
| Nikkei 225 | ^N225 | 1970-2026 | `_N225_1970-01-05_to_2026-05-22.csv` |
| FTSE 100 | ^FTSE | 1984-2026 | `_FTSE_1984-01-03_to_2026-05-22.csv` |
| DAX | ^GDAXI | 1987-2026 | `_GDAXI_1987-12-30_to_2026-05-22.csv` |
| CAC 40 | ^FCHI | 1990-2026 | `_FCHI_1990-03-01_to_2026-05-22.csv` |
| ASX 200 | ^AXJO | 1992-2026 | `_AXJO_1992-11-23_to_2026-05-22.csv` |
| TSX | ^GSPTSE | 1979-2026 | `_GSPTSE_1979-06-29_to_2026-05-22.csv` |
| Hang Seng | ^HSI | 1986-2026 | `_HSI_1986-12-31_to_2026-05-22.csv` |
| MSCI EAFE | EFA | 2001-2026 | `EFA_2001-08-27_to_2026-05-22.csv` |
| MSCI EM | EEM | 2003-2026 | `EEM_2003-04-14_to_2026-05-22.csv` |
| REITs | VNQ | 2004-2026 | `VNQ_2004-09-29_to_2026-05-22.csv` |
| US Bonds | AGG | 2003-2026 | `AGG_2003-09-29_to_2026-05-22.csv` |

Original paper: [SSRN 1908469](https://ssrn.com/abstract=1908469)

## License

GNU Affero General Public License v3.0. See [LICENSE](LICENSE).

## Contact

Maintainer: Matthew Williams
