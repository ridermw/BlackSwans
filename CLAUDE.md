# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a financial research project that validates and extends the analysis from **"Where the Black Swans Hide & The 10 Best Days Myth"** by Mebane Faber (2011). The project examines how extreme market events (outliers) influence long-term investment outcomes and how these events cluster during bear markets.

All four of Faber's core claims have been **statistically confirmed** (see `docs/validation_report.md`).

## Development Commands

### Installing Dependencies

```bash
pip install -e ".[dev]"
```

### Running the Analysis

```bash
# Package CLI
blackswans --ticker ^GSPC --start 1928-09-01 --end 2010-12-31 \
  --csv data/_GSPC_1928-09-01_to_2010-12-31.csv --output-dir output/sp500

# Legacy wrapper (backward compatible)
python src/validate_outliers.py --ticker ^GSPC --start 1928-09-01 --end 2010-12-31
```

### Running Full Validation (all 4 claims)

```bash
python -m blackswans.validate_claims \
  --csv data/_GSPC_1928-09-01_to_2010-12-31.csv \
  --ticker ^GSPC --start 1928-09-01 --end 2010-12-31 \
  --output-dir output/validation
```

### Running Tests

```bash
pytest tests/ -v                                    # 66 tests
pytest tests/ -v --cov=src/blackswans              # with coverage
```

**Key parameters for CLI:**
- `--ticker`: Yahoo Finance ticker symbol (e.g., `^GSPC` for S&P 500)
- `--start` / `--end`: Date range in YYYY-MM-DD format
- `--quantiles`: Quantile thresholds for identifying outliers (e.g., 0.99 = top/bottom 1%)
- `--ma-window`: Moving average window for regime classification (default: 200 days)
- `--best-count` / `--worst-count`: Number of best/worst days to exclude in scenario analysis
- `--csv`: Optional path to pre-downloaded CSV data
- `--output-dir`: Output directory (default: `output/`)
- `--overwrite`: Force re-download of cached data

## Code Architecture

### Package: `src/blackswans/`

The codebase is organized as a Python package with clear module separation:

```
src/blackswans/
├── __init__.py                  # Version (0.2.0)
├── cli.py                       # CLI entry point (main())
├── validate_claims.py           # Full 4-claim validation orchestrator
├── data/
│   ├── loaders.py               # fetch_price_data(), _load_csv()
│   └── transforms.py            # compute_daily_returns()
├── analysis/
│   ├── outliers.py              # OutlierStats dataclass, calculate_outlier_stats()
│   ├── scenarios.py             # scenario_returns(), annualised_return(), CASH constant
│   ├── regimes.py               # moving_average_regime(), regime_performance(), outlier_regime_counts()
│   └── statistics.py            # Statistical tests (chi-sq, z-test, KS, JB, bootstrap, Sharpe, drawdown, backtest)
├── visualization/
│   └── plots.py                 # plot_returns_time_series(), plot_returns_histogram(), plot_returns_by_regime(), make_plots()
└── io/
    └── writers.py               # save_dataframe()
```

### Legacy Wrapper: `src/validate_outliers.py`

Re-exports all public names from the package for backward compatibility. Delegates to `blackswans.cli.main()`.

### Data Pipeline

1. `fetch_price_data()` → loads/downloads price data with caching and date validation
2. `compute_daily_returns()` → calculates daily percentage returns
3. Analysis functions operate on returns Series
4. Results saved as CSV and PNG to output directory

## Important Implementation Details

### Data Handling
- Data cached in `data/` directory as CSV files: `{ticker}_{start}_to_{end}.csv`
- Cache validates date coverage — re-downloads if cached data doesn't cover requested range
- CSV loading handles various date column names: "Date", "date", "DATE"
- Prefers "Close" column, falls back to "Adj Close"

### Return Calculations
- Daily returns: `pct_change(fill_method=None)` (simple returns, not log returns)
- CAGR: `(product of (1+r))^(252/n) - 1` using 252 trading days/year
- Scenario analysis replaces selected days with `CASH = 0.0` (zero return)

### Regime Classification
- Binary: 0 = downtrend (price ≤ lagged MA), 1 = uptrend (price > lagged MA)
- **Lagged MA**: MA is shifted by 1 day to avoid look-ahead bias (today's price vs yesterday's MA)
- First `window` days marked as NaN (MA undefined)
- Regime performance annualized over full period (cash on non-regime days)

### Statistical Tests (statistics.py)
- `chi_square_regime_clustering()` — tests if outliers cluster disproportionately in one regime
- `two_proportion_z_test()` — compares outlier rates between regimes
- `normality_tests()` — KS, Jarque-Bera, Shapiro-Wilk
- `bootstrap_confidence_interval()` — non-parametric CIs for any statistic
- `trend_following_backtest()` — simple buy-above-MA / cash-below-MA strategy
- `sharpe_ratio()`, `max_drawdown()`, `excess_kurtosis()`, `skewness()`

### Quantile Logic
- Quantile parameter (e.g., 0.99) identifies both tails:
  - Lower tail: returns ≤ quantile(1 - 0.99) = bottom 1%
  - Upper tail: returns ≥ quantile(0.99) = top 1%

## Code Style

- **PEP8** conventions
- Type annotations on function signatures
- Docstrings on all public functions
- 66 tests with pytest (100% coverage on core analysis modules)

## Testing

```bash
pytest tests/ -v
```

Test files mirror the package structure:
- `tests/test_transforms.py` — daily return computation
- `tests/test_outliers.py` — outlier identification
- `tests/test_scenarios.py` — scenario returns and CAGR
- `tests/test_regimes.py` — regime classification and performance
- `tests/test_statistics.py` — all statistical tests
- `tests/test_loaders.py` — data loading and caching
- `tests/conftest.py` — shared fixtures with synthetic data

## Key Documents

- `docs/validation_report.md` — Full statistical validation of Faber's 4 claims
- `docs/audit_report.md` — Code and methodology audit findings
- `docs/wiki/` — Architecture, data dictionary, analysis methods, changelog (auto-synced to [GitHub Wiki](https://github.com/ridermw/BlackSwans/wiki))
