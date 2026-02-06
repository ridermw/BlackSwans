# Black Swans Architecture

## Overview

The Black Swans project is a single-file financial analysis tool (`src/validate_outliers.py`, ~389 lines) that validates and extends Mebane Faber's 2011 research on extreme market events and their impact on long-term returns.

## Single-File Architecture

The entire analysis pipeline is contained in a self-contained Python script with clear functional separation:

### Data Pipeline
1. **Data Fetching & Caching** (`fetch_price_data`)
   - Downloads daily OHLCV data from Yahoo Finance via yfinance
   - Caches data locally in `data/` as CSV files (format: `{ticker}_{start}_to_{end}.csv`)
   - Loads cached data instead of re-downloading if it exists
   - Supports optional pre-downloaded CSV input
   - Fallback logic: Close column with fallback to Adj Close

2. **Return Computation** (`compute_daily_returns`)
   - Converts price series to daily percentage returns
   - Uses `pct_change(fill_method=None)` to avoid pandas deprecation warnings
   - Drops NaN values before analysis
   - Accepts both Series and DataFrame inputs

### Analysis Functions

#### Outlier Detection
- **`calculate_outlier_stats(returns, quantile)`**
  - Identifies extreme returns in both tails (top and bottom quantiles)
  - Returns `OutlierStats` dataclass with comprehensive statistics
  - For quantile=0.99: identifies top 1% and bottom 1% of returns

#### Return Scenarios
- **`scenario_returns(returns, best_n, worst_n)`**
  - Simulates four scenarios by zeroing out selected days' returns:
    1. All days (baseline)
    2. Missing best N days (exclude gains)
    3. Missing worst N days (exclude losses)
    4. Missing both best and worst N days
  - Returns tuple of four modified return series

#### Return Aggregation
- **`annualised_return(returns)`**
  - Calculates Compound Annual Growth Rate (CAGR)
  - Formula: `CAGR = (∏(1 + r_i))^(1/years) - 1`
  - Assumes 252 trading days per year

#### Regime Classification
- **`moving_average_regime(prices, window)`**
  - Binary regime classification using simple moving average
  - Regime 0: Downtrend (price < MA)
  - Regime 1: Uptrend (price > MA)
  - First `window-1` days marked as NaN (insufficient data)
  - Uses 200-day MA by default

#### Regime Analysis
- **`outlier_regime_counts(returns, regimes, quantile)`**
  - Counts how many outliers occur in each regime
  - Returns tuple: (downtrend_count, uptrend_count)

- **`regime_performance(returns, regimes)`**
  - Computes performance metrics for each regime
  - Returns DataFrame with: count, pct_of_total, mean, median, std, annualised_return

### Output Functions

- **`save_dataframe(df, path)`**
  - Saves DataFrame to CSV
  - Creates parent directories as needed

- **`make_plots(returns, outliers, regimes, output_dir)`**
  - Generates three diagnostic visualizations:
    1. `returns_time_series.png` - Daily returns with outliers highlighted
    2. `returns_histogram.png` - Return distribution with normal PDF overlay
    3. `returns_by_regime.png` - Scatter plot colored by market regime (red=downtrend, green=uptrend)

## Data Structures

### OutlierStats (Dataclass)
Encapsulates statistics for a single quantile threshold:

```
OutlierStats:
  quantile: float          # The quantile threshold (e.g., 0.99)
  threshold_low: float     # Lower tail boundary
  threshold_high: float    # Upper tail boundary
  count_low: int           # Number of extreme low returns
  count_high: int          # Number of extreme high returns
  mean_low: float          # Mean of low tail
  mean_high: float         # Mean of high tail
  median_low: float        # Median of low tail
  median_high: float       # Median of high tail
  std_low: float           # Standard deviation of low tail
  std_high: float          # Standard deviation of high tail
  min_low: float           # Most extreme low return
  max_high: float          # Most extreme high return
```

## Data Flow

```
Input (--ticker, --start, --end)
    ↓
[fetch_price_data] → cache/download from Yahoo Finance
    ↓
[compute_daily_returns] → percentage returns
    ↓
├── [calculate_outlier_stats] → outlier statistics (CSV)
├── [scenario_returns] → scenario analysis (CSV)
├── [moving_average_regime] → regime classification
│   ├── [regime_performance] → regime metrics (CSV)
│   └── [outlier_regime_counts] → regime distribution (CSV)
└── [make_plots] → visualizations (PNG)
```

## Output Files

All outputs saved to `output/{analysis_name}/`:

**CSV Files:**
- `outlier_stats.csv` - Statistics for each quantile
- `return_scenarios.csv` - Annualized returns for all scenarios
- `regime_performance.csv` - Performance by regime (uptrend/downtrend)
- `outlier_regime_counts.csv` - Outlier distribution across regimes

**PNG Files:**
- `returns_time_series.png` - Time series with outliers
- `returns_histogram.png` - Return distribution histogram
- `returns_by_regime.png` - Returns colored by regime

## Key Constants

- `DATA_DIR` - Cache directory for downloaded CSV data
- `CASH` - Placeholder return for zeroed-out days (0.0)
- Default MA window - 200 trading days
- Default quantiles - 0.99 and 0.999 (1% and 0.1% tails)
- Trading days per year - 252

## Implementation Notes

### Error Handling
- Robust CSV loading with flexible column name detection (Date/date/DATE)
- Numeric coercion to handle string price data
- Empty DataFrame handling in return calculations

### Performance Considerations
- Data caching minimizes Yahoo Finance API calls
- In-memory operations on pandas Series/DataFrames
- Efficient numpy operations for statistical calculations
