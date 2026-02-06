# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a financial research project that validates and extends the analysis from **"Where the Black Swans Hide & The 10 Best Days Myth"** by Mebane Faber (2011). The project examines how extreme market events (outliers) influence long-term investment outcomes and how these events cluster during bear markets.

The analysis fetches historical equity index data, identifies outlier days, evaluates multiple return scenarios (e.g., missing the best/worst days), and classifies market regimes using moving averages.

## Development Commands

### Running the Analysis

The main script is `src/validate_outliers.py`. Run it with date range and analysis parameters:

```bash
python src/validate_outliers.py \
  --ticker ^GSPC \
  --start 1928-09-01 \
  --end 2025-07-27 \
  --quantiles 0.99 0.999 \
  --ma-window 200 \
  --best-count 10 \
  --worst-count 10
```

**Key parameters:**
- `--ticker`: Yahoo Finance ticker symbol (e.g., `^GSPC` for S&P 500)
- `--start` / `--end`: Date range in YYYY-MM-DD format
- `--quantiles`: Quantile thresholds for identifying outliers (e.g., 0.99 = top/bottom 1%)
- `--ma-window`: Moving average window for regime classification (default: 200 days)
- `--best-count` / `--worst-count`: Number of best/worst days to exclude in scenario analysis
- `--csv`: Optional path to pre-downloaded CSV data
- `--output-dir`: Output directory (default: `output/`)
- `--overwrite`: Force re-download of cached data

### Installing Dependencies

```bash
pip install -r requirements.txt
```

Dependencies: pandas, numpy, matplotlib, scipy, yfinance

## Code Architecture

### Main Script: `src/validate_outliers.py`

This is a self-contained script (~389 lines) organized into logical sections:

**Data Pipeline:**
1. `fetch_price_data()` - Downloads or loads cached price data from Yahoo Finance
2. `compute_daily_returns()` - Calculates daily percentage returns from prices
3. Data is cached in `data/` directory as CSV files with naming format: `{ticker}_{start}_to_{end}.csv`

**Analysis Functions:**
- `calculate_outlier_stats()` - Identifies extreme quantile days and computes statistics
- `scenario_returns()` - Simulates missing best/worst days by zeroing out returns
- `annualised_return()` - Computes CAGR from daily returns
- `moving_average_regime()` - Classifies uptrend/downtrend using rolling moving average
- `outlier_regime_counts()` - Counts outliers occurring in each regime
- `regime_performance()` - Summarizes returns by market regime

**Output Functions:**
- `save_dataframe()` - Saves analysis results to CSV
- `make_plots()` - Generates diagnostic charts (time series, histograms, regime scatter plots)

### Data Structures

The script uses a `@dataclass OutlierStats` to encapsulate outlier statistics for each quantile threshold, containing:
- Thresholds (low/high)
- Counts, means, medians, standard deviations
- Min/max values for extreme tails

### Output Structure

All results are saved to `output/` (or specified `--output-dir`):
- `outlier_stats.csv` - Statistics for each quantile threshold
- `return_scenarios.csv` - Annualized returns for all/miss_best/miss_worst/miss_both scenarios
- `regime_performance.csv` - Performance metrics by uptrend/downtrend regime
- `outlier_regime_counts.csv` - Distribution of outliers across regimes
- `returns_time_series.png` - Time series plot with outliers highlighted
- `returns_histogram.png` - Distribution of returns with normal PDF overlay
- `returns_by_regime.png` - Scatter plot colored by market regime

The `output/` directory contains subdirectories for different analyses (e.g., `msci_eafe/`, `reit/`).

## Important Implementation Details

### Data Handling
- The script caches downloaded data to avoid repeated API calls
- CSV files are loaded with robust date parsing (handles various column names: "Date", "date", "DATE")
- Price data is coerced to numeric type to handle any string values
- The script prefers "Close" column but falls back to "Adj Close" if needed
- All data is sorted by datetime index after loading

### Return Calculations
- Daily returns are computed using `pct_change(fill_method=None)` to avoid deprecation warnings
- Returns series are cleaned (NaN values dropped) before analysis
- Scenario analysis replaces selected days with `CASH = 0.0` (no return) rather than removing them

### Regime Classification
- Regime is binary: 0 = downtrend (price < MA), 1 = uptrend (price > MA)
- First `window-1` days are marked as NaN since MA cannot be computed
- The function handles both Series and DataFrame inputs by extracting the relevant column

### Quantile Logic
- Quantile parameter (e.g., 0.99) identifies both tails:
  - Lower tail: returns <= quantile(1 - 0.99) = bottom 1%
  - Upper tail: returns >= quantile(0.99) = top 1%

## Code Style

The codebase follows **PEP8** conventions with:
- Type annotations on function signatures
- Comprehensive docstrings
- Structured functions for testability
- Clear separation of concerns (data loading, computation, output)

## Testing

Per CONTRIBUTING.md, contributors should:
- Ensure `validate_outliers.py` runs successfully with changes
- Add unit tests for new features or fixes (test infrastructure not yet present in repo)
- Include test coverage for new analysis methods

## Context from README

The project validates these key claims from the original Faber (2011) paper:
1. Fat-tailed market returns have significant outliers
2. A small number of extreme days have outsized influence on long-term returns
3. Outliers cluster during bear markets (downtrends)
4. Simple trend-following rules can help avoid the worst volatility

**Extension to present day**: The analysis can be updated to include recent crisis periods (2020 COVID-19 crash, 2022 downturn) by changing the `--end` parameter and re-running the script.
