# Black Swans Architecture

## Overview

The Black Swans project is a comprehensive financial analysis platform that validates and extends Mebane Faber's 2011 research on extreme market events and their impact on long-term returns. The project consists of three integrated layers:

1. **Core Package** (`src/blackswans/`) — Analysis engine with modular architecture
2. **FastAPI Backend** (`api/`) — REST API for analysis and validation
3. **React Frontend** (`frontend/`) — Interactive dashboard with Plotly charts

**Current Version:** 0.2.0 | **Data Coverage:** 12 indices through Dec 31, 2010 | **Status:** Production Ready

---

## System Architecture

```
┌─────────────────────────────────────────┐
│         React Dashboard (frontend/)      │
│  ├─ Overview Page (/) — 4 Faber Claims  │
│  ├─ Analysis Page (/analysis/:ticker)   │
│  └─ 6 Components + Plotly Charts        │
└────────────────┬────────────────────────┘
                 │ HTTP (Axios)
                 ↓
┌─────────────────────────────────────────┐
│      FastAPI Backend (api/)             │
│  ├─ /api/health — Health check          │
│  ├─ /api/tickers — Available tickers    │
│  ├─ /api/analysis/{ticker} — Run        │
│  └─ /api/validation/{ticker} — Validate │
└────────────────┬────────────────────────┘
                 │ Python imports
                 ↓
┌─────────────────────────────────────────┐
│    Core Package (src/blackswans/)       │
│  ├─ CLI Interface (cli.py)              │
│  ├─ Data Pipeline (data/)               │
│  ├─ Analysis Modules (analysis/)        │
│  ├─ Visualization (visualization/)      │
│  └─ Output Writers (io/)                │
└─────────────────────────────────────────┘
```

---

## Core Package Architecture: `src/blackswans/`

### Module Structure (7 modules)

```
src/blackswans/
├── __init__.py                   # Version, imports
├── cli.py                        # CLI entry point
├── validate_claims.py            # 4-claim validation orchestrator
│
├── data/
│   ├── __init__.py
│   ├── loaders.py               # fetch_price_data()
│   └── transforms.py            # compute_daily_returns()
│
├── analysis/
│   ├── __init__.py
│   ├── outliers.py              # calculate_outlier_stats()
│   ├── scenarios.py             # scenario_returns(), annualised_return()
│   ├── regimes.py               # moving_average_regime(), regime_performance()
│   └── statistics.py            # Statistical tests (7 functions)
│
├── visualization/
│   ├── __init__.py
│   └── plots.py                 # make_plots()
│
└── io/
    ├── __init__.py
    └── writers.py               # save_dataframe()
```

### Data Pipeline

#### 1. Data Fetching & Caching (`data/loaders.py`)
- **`fetch_price_data(ticker, start, end, csv=None, overwrite=False)`**
  - Downloads daily OHLCV data from Yahoo Finance via yfinance
  - Caches locally in `data/` as CSV: `{ticker}_{start}_to_{end}.csv`
  - Validates cache date coverage; re-downloads if incomplete
  - Supports optional pre-downloaded CSV input
  - Fallback: "Close" column with fallback to "Adj Close"
  - Returns pandas DataFrame with Date index and Close column

#### 2. Return Computation (`data/transforms.py`)
- **`compute_daily_returns(prices, method='pct_change')`**
  - Converts price series to daily percentage returns
  - Uses `pct_change(fill_method=None)` to avoid pandas deprecation warnings
  - Drops NaN values before analysis
  - Accepts both Series and DataFrame inputs
  - Returns clean returns series ready for analysis

### Analysis Functions

#### Outlier Detection (`analysis/outliers.py`)
- **`calculate_outlier_stats(returns, quantile=0.99)`**
  - Identifies extreme returns in both tails using quantiles
  - Returns `OutlierStats` dataclass with comprehensive statistics
  - For quantile=0.99: identifies top 1% (high) and bottom 1% (low) returns
  - Stats include: thresholds, counts, means, medians, stds, min/max

#### Return Scenarios (`analysis/scenarios.py`)
- **`scenario_returns(returns, best_n=10, worst_n=10)`**
  - Simulates four scenarios by zeroing selected days' returns:
    1. Baseline (all days included)
    2. Missing best N days (exclude gains)
    3. Missing worst N days (exclude losses)
    4. Missing both best and worst N days
  - Returns tuple of four modified return series

- **`annualised_return(returns)`**
  - Calculates Compound Annual Growth Rate (CAGR)
  - Formula: `CAGR = (∏(1 + r_i))^(1/years) - 1`
  - Assumes 252 trading days per year
  - Used for all performance metrics

#### Regime Classification (`analysis/regimes.py`)
- **`moving_average_regime(prices, window=200)`**
  - Binary regime classification using simple moving average
  - Regime 0: Downtrend (price ≤ lagged MA)
  - Regime 1: Uptrend (price > lagged MA)
  - **Lagged MA:** Uses shift(1) to avoid look-ahead bias
  - First `window-1` days marked as NaN (insufficient data)
  - Returns Series of 0s, 1s, and NaN values

- **`regime_performance(returns, regimes)`**
  - Computes performance metrics for each regime
  - Returns DataFrame with: count, pct_of_total, mean, median, std, annualised_return
  - Cash (0.0) applied on non-regime days for annualization

- **`outlier_regime_counts(returns, regimes, quantile=0.99)`**
  - Counts outliers occurring in each regime
  - Returns tuple: (downtrend_count, uptrend_count, total_count)

#### Statistical Tests (`analysis/statistics.py`)
- **`chi_square_regime_clustering(returns, regimes, quantile=0.99)`**
  - Tests if outliers cluster disproportionately in one regime
  - Uses chi-squared goodness-of-fit test
  - Returns: chi2_stat, p_value, contingency table

- **`two_proportion_z_test(prop1, n1, prop2, n2)`**
  - Compares outlier rates between regimes
  - Returns: z_statistic, p_value

- **`normality_tests(returns)`**
  - Jarque-Bera test (omnibus)
  - Kolmogorov-Smirnov test
  - Shapiro-Wilk test
  - Returns dict with all test statistics and p-values

- **`bootstrap_confidence_interval(data, statistic_fn, n_bootstrap=10000, ci=0.95)`**
  - Non-parametric confidence intervals for any statistic
  - Resamples data with replacement, computes statistic each time
  - Returns (lower_bound, upper_bound) at specified CI level

- **`trend_following_backtest(prices, ma_window=200)`**
  - Simple MA-based strategy: hold when price > MA, cash otherwise
  - Returns performance metrics including CAGR and max drawdown

- **`sharpe_ratio(returns, risk_free_rate=0.02)`**
- **`max_drawdown(returns)`**
- **`excess_kurtosis(returns)`**
- **`skewness(returns)`**

### Validation (`validate_claims.py`)
- **`validate_faber_claims(ticker, start, end, csv=None, output_dir='output/')`**
  - Orchestrates all 4 claim validations with logging
  - Generates comprehensive validation report
  - Returns dict with all statistical test results
  - Saves `docs/validation_report.md`

### Output Functions (`visualization/plots.py`, `io/writers.py`)
- **`make_plots(returns, outliers, regimes, output_dir)`**
  - Generates three diagnostic visualizations:
    1. `returns_time_series.png` — Daily returns with outliers highlighted
    2. `returns_histogram.png` — Return distribution with normal PDF overlay
    3. `returns_by_regime.png` — Scatter plot colored by regime (red=downtrend, green=uptrend)

- **`save_dataframe(df, path)`**
  - Saves DataFrame to CSV
  - Creates parent directories as needed
  - Called for: outlier_stats, scenarios, regime_performance

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

---

## FastAPI Backend Architecture: `api/`

Provides REST API endpoints for programmatic access to analysis and validation functions.

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Server health check; returns `{"status": "ok"}` |
| `/api/tickers` | GET | List available tickers with date ranges and data file paths |
| `/api/analysis/{ticker}` | GET | Run outlier analysis with optional parameters |
| `/api/validation/{ticker}` | GET | Run full 4-claim validation |

### Analysis Endpoint Parameters
- `start` (string, optional): Start date (YYYY-MM-DD), defaults to data file start
- `end` (string, optional): End date (YYYY-MM-DD), defaults to data file end
- `ma_window` (int, optional): Moving average window, default 200
- `quantiles` (string, optional): Comma-separated quantiles, default "0.99,0.999"

### Response Models (Pydantic)
- `TickerInfo` — Ticker metadata (code, symbol, data file, date range)
- `OutlierResult` — Outlier stats for a single quantile
- `ScenarioResult` — Scenario analysis results
- `RegimeResult` — Regime performance metrics
- `AnalysisResponse` — Complete analysis output
- `ValidationResponse` — Full 4-claim validation with verdicts

### Implementation
- `api/main.py` (281 lines) — FastAPI app, endpoint handlers, error handling
- `api/models.py` (90 lines) — Pydantic models for responses
- CORS enabled for development (all origins allowed)
- Ticker mapping to `data/` CSV files with automatic date parsing
- All endpoints call corresponding `blackswans` package functions

### Running
```bash
pip install -e ".[api]"
uvicorn api.main:app --reload
# Open http://localhost:8000 for interactive docs
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### Available Tickers (12 total)
- S&P 500 (sp500, ^GSPC)
- Nikkei 225 (nikkei, ^N225)
- FTSE 100 (ftse, ^FTSE)
- DAX (dax, ^GDAXI)
- CAC 40 (cac, ^FCHI)
- ASX 200 (asx, ^AXJO)
- TSX Composite (tsx, ^GSPTSE)
- Hang Seng (hsi, ^HSI)
- MSCI EAFE (eafe, EFA)
- MSCI Emerging Markets (eem, EEM)
- REITs (reit, VNQ)
- Aggregate Bonds (bonds, AGG)

---

## React Frontend Architecture: `frontend/`

Interactive dashboard for exploring analysis results and validating Faber's claims.

### Technology Stack
- **Framework:** React 19
- **Build Tool:** Vite (dev server + optimized production builds)
- **Routing:** React Router v7
- **Charts:** Plotly.js via react-plotly.js
- **HTTP Client:** Axios
- **CSS:** Custom stylesheets with financial theme

### Pages (2)

#### 1. Overview Page (`/`)
- Summary of all 4 Faber claims from the paper
- Displays validation verdict (CONFIRMED/DISPROVEN) for each claim
- Shows key evidence supporting each verdict
- Component: ClaimCard (6 instances, one per major result)

#### 2. Analysis Page (`/analysis/:ticker`)
- Detailed analysis for selected market index
- MarketSelector dropdown to choose from 12 available tickers
- Four interactive Plotly charts showing different analysis aspects

### Components (6)

#### 1. ClaimCard (`ClaimCard.jsx`)
- Displays single claim verdict with styling
- Shows claim number, title, verdict badge, and evidence summary
- Color-coded: blue background for overview context

#### 2. MarketSelector (`MarketSelector.jsx`)
- Dropdown to select from 12 available tickers
- Updates route to /analysis/:ticker on selection
- Current selection highlighted

#### 3. TimeSeriesChart (`TimeSeriesChart.jsx`)
- Daily returns over full time period
- Outlier days highlighted in contrasting color
- Plotly scatter plot with hover details
- Axes: Date (x), Daily return % (y)

#### 4. HistogramChart (`HistogramChart.jsx`)
- Return distribution as histogram
- Overlaid normal distribution curve (red) for comparison
- Shows fat tails visually
- Plotly histogram with density estimation

#### 5. RegimeChart (`RegimeChart.jsx`)
- Daily returns colored by market regime
- Green: Uptrend days (price > 200-day MA)
- Red: Downtrend days (price ≤ 200-day MA)
- Gray: Days before MA warmup (first 199 days)
- Plotly scatter plot with color encoding

#### 6. ScenarioChart (`ScenarioChart.jsx`)
- Bar chart comparing scenario returns (CAGR)
- Four scenarios:
  1. Baseline (all days)
  2. Missing best 10 days
  3. Missing worst 10 days
  4. Missing both best and worst 10 days
- Plotly bar chart with value labels

### API Integration

#### `services/api.js`
- Axios-based HTTP client for backend calls
- Comprehensive mock data fallback for offline development
- Mock data based on actual S&P 500 validation results
- Graceful degradation: shows mock data if API unavailable

#### Request/Response Flow
```
User selects ticker in MarketSelector
    ↓
Route changes to /analysis/:ticker
    ↓
Analysis component mounts, calls api.getAnalysis(ticker)
    ↓
Axios requests http://localhost:8000/api/analysis/{ticker}
    ↓
FastAPI backend returns AnalysisResponse (JSON)
    ↓
Components parse response and render Plotly charts
```

### File Structure
```
frontend/
├── src/
│   ├── App.jsx             # Main router component
│   ├── App.css             # Global styles
│   ├── main.jsx            # React entry point
│   ├── index.css           # Base styles
│   │
│   ├── pages/
│   │   ├── Overview.jsx    # /
│   │   ├── Overview.css
│   │   ├── Analysis.jsx    # /analysis/:ticker
│   │   └── Analysis.css
│   │
│   ├── components/
│   │   ├── ClaimCard.jsx
│   │   ├── ClaimCard.css
│   │   ├── MarketSelector.jsx
│   │   ├── MarketSelector.css
│   │   ├── TimeSeriesChart.jsx
│   │   ├── HistogramChart.jsx
│   │   ├── RegimeChart.jsx
│   │   └── ScenarioChart.jsx
│   │
│   ├── services/
│   │   └── api.js          # Axios client + mock data
│   │
│   └── assets/             # Images, icons
│
├── package.json            # Dependencies and scripts
├── vite.config.js          # Vite configuration
├── eslint.config.js        # ESLint rules
└── README.md               # Build instructions
```

### Running Locally
```bash
cd frontend
npm install
npm run dev       # Development server on http://localhost:5173
npm run build     # Production build to dist/
npm run preview   # Preview production build
npm run lint      # ESLint checks
```

### Styling
- Financial theme with blues and teals
- Color scheme for regime classification: green (uptrend), red (downtrend)
- Responsive layout for desktop and tablet
- CSS Grid for component layout
- Plotly.js default styling with custom color overrides

---

## Data Flow (End-to-End)

### CLI Usage
```
$ blackswans --ticker ^GSPC --start 1928-09-01 --end 2010-12-31
    ↓
cli.py: parse arguments → validate inputs
    ↓
validate_claims.py: orchestrate analysis
    ↓
data/loaders.py: fetch_price_data() → CSV from Yahoo Finance or cache
    ↓
data/transforms.py: compute_daily_returns()
    ↓
analysis/*.py: run all analyses and statistical tests
    ↓
visualization/plots.py: make_plots()
    ↓
io/writers.py: save_dataframe() → CSV files
    ↓
Output: CSVs (4) + PNGs (3) to output/
```

### API Usage
```
GET /api/analysis/sp500?quantiles=0.99
    ↓
api/main.py: parse path and query params
    ↓
Import blackswans modules
    ↓
Fetch ticker data file path, parse dates
    ↓
Run analyses same as CLI
    ↓
api/models.py: wrap results in Pydantic models
    ↓
Return JSON response to client
```

### Frontend Usage
```
User opens browser to http://localhost:5173
    ↓
React Router loads Overview page
    ↓
ClaimCard components render with mock data
    ↓
User clicks market selector
    ↓
Route changes to /analysis/:ticker
    ↓
Analysis page mounts
    ↓
JavaScript fetch/axios to http://localhost:8000/api/analysis/sp500
    ↓
Charts render with API or mock data
    ↓
User interacts with Plotly charts (zoom, hover, etc.)
```

---

## Key Implementation Details

### Data Handling
- **Caching:** CSV files stored in `data/` directory with naming: `{ticker}_{start}_to_{end}.csv`
- **Cache Validation:** Checks cached data covers requested date range before using
- **Column Flexibility:** Handles various CSV column names (Date, date, DATE; Close, Adj Close)

### Return Calculations
- **Daily Returns:** `pct_change(fill_method=None)` — simple returns, not log returns
- **CAGR:** `(product of (1 + r))^(252/n_trading_days) - 1`
- **Trading Days:** Standard 252 per year

### Regime Classification
- **Binary Classification:** 0 = downtrend, 1 = uptrend
- **Lagged MA:** Today's price compared to yesterday's MA (shift by 1) to avoid look-ahead bias
- **Warmup Period:** First `window-1` days marked as NaN (insufficient data for MA)

### Quantile Logic
- **Bidirectional:** Quantile Q identifies both tails
  - Lower tail: returns ≤ quantile(1-Q)
  - Upper tail: returns ≥ quantile(Q)
- **Example:** For Q=0.99, identifies both bottom 1% and top 1%

---

## Testing

**Test Coverage:** 66 tests, 100% on core analysis modules

Test Modules:
- `tests/test_transforms.py` — Return computation
- `tests/test_outliers.py` — Outlier identification
- `tests/test_scenarios.py` — Scenario analysis and CAGR
- `tests/test_regimes.py` — Regime classification and performance
- `tests/test_loaders.py` — Data loading and caching
- `tests/test_statistics.py` — Statistical tests (21 tests)

Run tests:
```bash
pytest tests/ -v                          # All tests
pytest tests/ -v --cov=src/blackswans    # With coverage
```

Note: API and frontend components lack automated tests (TODO)
