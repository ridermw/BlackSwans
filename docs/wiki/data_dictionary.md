# Data Dictionary

## Input Data Files

The `data/` directory contains 12 cached CSV files from Yahoo Finance, each representing a market index or asset class analyzed using historical data through January 31, 2025.

### Equity Indices

#### 1. S&P 500 (`_GSPC_1928-09-04_to_2025-01-31.csv`)
- **Ticker:** ^GSPC
- **Asset Class:** Large-cap U.S. equities
- **Date Range:** Sept 4, 1928 – Jan 31, 2025
- **Rows:** ~24,217
- **Source:** Yahoo Finance
- **Columns:** Date (index), Close (float)
- **Notes:** Longest historical record; primary analysis index for original Faber paper

#### 2. MSCI EAFE (`EFA_2001-08-27_to_2025-01-31.csv`)
- **Ticker:** EFA
- **Asset Class:** Developed markets (Europe, Australasia, Far East)
- **Date Range:** Aug 27, 2001 – Jan 31, 2025
- **Rows:** ~5,893
- **Source:** Yahoo Finance
- **Columns:** Date (index), Close (float)
- **Notes:** Emerging vs. developed market comparison

#### 3. MSCI Emerging Markets (`EEM_2003-04-14_to_2025-01-31.csv`)
- **Ticker:** EEM
- **Asset Class:** Emerging market equities
- **Date Range:** Apr 14, 2003 – Jan 31, 2025
- **Rows:** ~5,487
- **Source:** Yahoo Finance
- **Columns:** Date (index), Close (float)
- **Notes:** Higher volatility profile; captures extreme outlier events

#### 4. REITs (`VNQ_2004-09-29_to_2025-01-31.csv`)
- **Ticker:** VNQ
- **Asset Class:** Real estate investment trusts (U.S. residential & commercial)
- **Date Range:** Sept 29, 2004 – Jan 31, 2025
- **Rows:** ~5,119
- **Source:** Yahoo Finance
- **Columns:** Date (index), Close (float)
- **Notes:** Alternative asset class for comparison

#### 5. Aggregate Bonds (`AGG_2003-09-29_to_2025-01-31.csv`)
- **Ticker:** AGG
- **Asset Class:** U.S. bonds (investment grade)
- **Date Range:** Sept 29, 2003 – Jan 31, 2025
- **Rows:** ~5,371
- **Source:** Yahoo Finance
- **Columns:** Date (index), Close (float)
- **Notes:** Lower volatility; typically inversely correlated with equities

### International Equity Indices

#### 6. ASX 200 (Australia) (`_AXJO_1992-11-23_to_2025-01-31.csv`)
- **Ticker:** ^AXJO
- **Asset Class:** Australian equities
- **Date Range:** Nov 23, 1992 – Jan 31, 2025
- **Rows:** ~8,137
- **Source:** Yahoo Finance

#### 7. CAC 40 (France) (`_FCHI_1990-03-01_to_2025-01-31.csv`)
- **Ticker:** ^FCHI
- **Asset Class:** French equities
- **Date Range:** Mar 1, 1990 – Jan 31, 2025
- **Rows:** ~8,868
- **Source:** Yahoo Finance

#### 8. FTSE 100 (UK) (`_FTSE_1984-01-03_to_2025-01-31.csv`)
- **Ticker:** ^FTSE
- **Asset Class:** British equities
- **Date Range:** Jan 3, 1984 – Jan 31, 2025
- **Rows:** ~10,378
- **Source:** Yahoo Finance

#### 9. DAX (Germany) (`_GDAXI_1987-12-30_to_2025-01-31.csv`)
- **Ticker:** ^GDAXI
- **Asset Class:** German equities
- **Date Range:** Dec 30, 1987 – Jan 31, 2025
- **Rows:** ~9,378
- **Source:** Yahoo Finance

#### 10. Nikkei 225 (Japan) (`_N225_1970-01-05_to_2025-01-31.csv`)
- **Ticker:** ^N225
- **Asset Class:** Japanese equities
- **Date Range:** Jan 5, 1970 – Jan 31, 2025
- **Rows:** ~13,547
- **Source:** Yahoo Finance

#### 11. Hang Seng (Hong Kong) (`_HSI_1986-12-31_to_2025-01-28.csv`)
- **Ticker:** ^HSI
- **Asset Class:** Hong Kong equities
- **Date Range:** Dec 31, 1986 – Jan 28, 2025
- **Rows:** ~9,399
- **Source:** Yahoo Finance

#### 12. TSX (Canada) (`_GSPTSE_1979-06-29_to_2025-01-31.csv`)
- **Ticker:** ^GSPTSE
- **Asset Class:** Canadian equities
- **Date Range:** Jun 29, 1979 – Jan 31, 2025
- **Rows:** ~11,448
- **Source:** Yahoo Finance

## Output Data Files

Generated in `output/{analysis_name}/` directories for each market analysis.

### 1. outlier_stats.csv
**Purpose:** Extreme value statistics by quantile threshold

**Columns:**
| Column Name | Type | Description |
|-------------|------|-------------|
| quantile | float | Quantile threshold (e.g., 0.99 = 1% tail) |
| threshold_low | float | Lower tail boundary return value |
| threshold_high | float | Upper tail boundary return value |
| count_low | int | Number of returns in lower tail |
| count_high | int | Number of returns in upper tail |
| mean_low | float | Mean return of lower tail |
| mean_high | float | Mean return of upper tail |
| median_low | float | Median return of lower tail |
| median_high | float | Median return of upper tail |
| std_low | float | Standard deviation of lower tail |
| std_high | float | Standard deviation of upper tail |
| min_low | float | Most extreme (minimum) return |
| max_high | float | Most extreme (maximum) return |

**Example Interpretation:**
For quantile=0.99: rows show statistics for the worst 1% and best 1% of trading days.

### 2. return_scenarios.csv
**Purpose:** Annualized returns under different day-exclusion scenarios

**Columns:**
| Column Name | Type | Description |
|-------------|------|-------------|
| scenario | string | Scenario name |
| annualised_return | float | CAGR for scenario |

**Scenarios:**
| Scenario | Description |
|----------|-------------|
| all | Baseline: all days included |
| miss_best | Exclude N best days (gain loss) |
| miss_worst | Exclude N worst days (avoid loss) |
| miss_both | Exclude both best and worst N days |

**Interpretation:** Demonstrates the outsized impact of extreme days on long-term returns.

### 3. regime_performance.csv
**Purpose:** Market performance by regime (uptrend vs. downtrend)

**Columns:**
| Column Name | Type | Description |
|-------------|------|-------------|
| regime | string | "downtrend" or "uptrend" |
| count | int | Number of trading days in regime |
| pct_of_total | float | Percentage of total days |
| mean | float | Average daily return |
| median | float | Median daily return |
| std | float | Standard deviation of daily returns |
| annualised_return | float | CAGR for regime |

**Interpretation:** Shows whether market regimes have different risk/return profiles.

### 4. outlier_regime_counts.csv
**Purpose:** Distribution of outliers across market regimes

**Columns:**
| Column Name | Type | Description |
|-------------|------|-------------|
| quantile | float | Quantile threshold |
| down | int | Outliers occurring in downtrends |
| up | int | Outliers occurring in uptrends |

**Interpretation:** Tests hypothesis that extreme days cluster during bear markets (downtrends).

## Data Quality Notes

### CSV Loading Behavior
- **Date Parsing:** Flexible column detection (Date/date/DATE automatically set as index)
- **Numeric Conversion:** Coerces Close prices to float; drops rows with NaN
- **Sorting:** All data automatically sorted by datetime index
- **Column Preference:** Prefers "Close" column, falls back to "Adj Close" if needed

### Return Calculation Assumptions
- Daily returns: `r_t = (P_t - P_{t-1}) / P_{t-1}`
- Uses 252 trading days per year
- NaN values in returns series dropped before analysis
- No forward-fill; uses `pct_change(fill_method=None)`

### Regime Classification
- Moving Average Window: Default 200 trading days
- Regime 0 = Price < MA (Downtrend)
- Regime 1 = Price > MA (Uptrend)
- First 199 days (window-1) marked as NaN (insufficient data)

## Data Sources & Licensing

All data sourced from Yahoo Finance via `yfinance` Python library.
- **Source:** Yahoo Finance Historical Data API
- **License:** Individual usage rights per Yahoo Finance terms
- **Update Frequency:** Daily (script re-run with new --end date)
- **Survivorship Bias:** Data reflects indices as of download date; historical constituent changes not tracked

## Cache Strategy

Downloaded CSV files cached in `data/` directory to minimize API calls:
- **Cache Filename:** `{ticker}_{start}_to_{end}.csv`
- **Example:** `_GSPC_1928-09-04_to_2025-01-31.csv`
- **Overwrite Option:** Use `--overwrite` flag to force re-download
