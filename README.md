# Black Swans Validation

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Tests](https://img.shields.io/badge/tests-66%20passing-green)
![License: AGPL v3](https://img.shields.io/badge/license-AGPL%20v3-blue)

> Validate and extend the analysis from **"Where the Black Swans Hide & The 10 Best Days Myth"** by Faber & CQR (Aug 2011).

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

---

## Installation

```bash
git clone https://github.com/ridermw/BlackSwans.git
cd BlackSwans
pip install -e ".[dev]"
```

## Usage

### Run the analysis

```bash
# Using the package CLI
blackswans --ticker ^GSPC --start 1928-09-01 --end 2010-12-31 \
  --csv data/_GSPC_1928-09-01_to_2010-12-31.csv --output-dir output/sp500

# Or using the legacy script
python src/validate_outliers.py --ticker ^GSPC --start 1928-09-01 --end 2010-12-31
```

### Run the full validation (all 4 claims)

```bash
python -m blackswans.validate_claims \
  --csv data/_GSPC_1928-09-01_to_2010-12-31.csv \
  --ticker ^GSPC --start 1928-09-01 --end 2010-12-31 \
  --output-dir output/validation
```

### Run tests

```bash
pytest tests/ -v
```

## Project Structure

```
BlackSwans/
├── src/
│   ├── blackswans/              # Main package
│   │   ├── analysis/
│   │   │   ├── outliers.py      # Outlier identification & stats
│   │   │   ├── scenarios.py     # Scenario returns (miss best/worst days)
│   │   │   ├── regimes.py       # MA regime classification & performance
│   │   │   └── statistics.py    # Statistical tests (chi-sq, KS, bootstrap)
│   │   ├── data/
│   │   │   ├── loaders.py       # Data loading & caching
│   │   │   └── transforms.py    # Daily return computation
│   │   ├── visualization/
│   │   │   └── plots.py         # Matplotlib chart generation
│   │   ├── io/writers.py        # CSV output
│   │   ├── cli.py               # CLI entry point
│   │   └── validate_claims.py   # Full 4-claim validation
│   └── validate_outliers.py     # Legacy wrapper
├── tests/                       # 66 tests (pytest)
├── data/                        # 12 index CSV files (1928-2010)
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
| S&P 500 | ^GSPC | 1928-2010 | `_GSPC_1928-09-01_to_2010-12-31.csv` |
| FTSE 100 | ^FTSE | 1970-2010 | `_FTSE_1970-01-01_to_2010-12-31.csv` |
| DAX | ^GDAXI | 1970-2010 | `_GDAXI_1970-01-01_to_2010-12-31.csv` |
| Nikkei 225 | ^N225 | 1970-2010 | `_N225_1970-01-01_to_2010-12-31.csv` |
| Hang Seng | ^HSI | 1970-2010 | `_HSI_1970-01-01_to_2010-12-31.csv` |
| ASX 200 | ^AXJO | 1970-2010 | `_AXJO_1970-01-01_to_2010-12-31.csv` |
| CAC 40 | ^FCHI | 1970-2010 | `_FCHI_1970-01-01_to_2010-12-31.csv` |
| TSX | ^GSPTSE | 1970-2010 | `_GSPTSE_1970-01-01_to_2010-12-31.csv` |
| MSCI EAFE | EFA | 1970-2010 | `EFA_1970-01-01_to_2010-12-31.csv` |
| MSCI EM | EEM | 1988-2010 | `EEM_1988-01-01_to_2010-12-31.csv` |
| REITs | VNQ | 1970-2010 | `VNQ_1970-01-01_to_2010-12-31.csv` |
| US Bonds | AGG | 1976-2010 | `AGG_1976-01-01_to_2010-12-31.csv` |

Original paper: [SSRN 1908469](https://ssrn.com/abstract=1908469)

## License

GNU Affero General Public License v3.0. See [LICENSE](LICENSE).

## Contact

Maintainer: Matthew Williams
