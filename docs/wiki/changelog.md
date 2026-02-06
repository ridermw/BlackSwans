# Changelog

All notable changes to the BlackSwans project are documented here. Follows semantic versioning and milestone-based development.

---

## Version 0.2.0 - 2026-02-06
**Status:** Production Ready | All 4 Faber claims validated with statistical rigor

### M0: Audit & Documentation (Complete)
**Commit:** `50b666e` (combined with M1)

#### Findings
- **Code Quality:** Script reproducible across 3+ indices; no critical math bugs identified
- **Critical Bug Found:** Regime CAGR annualization bug (fixed in M1) — uptrend CAGR overstated
- **Look-Ahead Bias:** MA quantile calculation using full-history data (documented, not critical)
- **Audit Report:** Comprehensive findings in `docs/audit_report.md`

#### Documentation Created
- `docs/wiki/architecture.md` — Package architecture and data pipeline
- `docs/wiki/data_dictionary.md` — 12 input CSV indices with metadata
- `docs/wiki/analysis_methods.md` — Mathematical formulas for all analyses
- `docs/wiki/` — Central wiki documentation foundation

---

## Version 0.2.0 - M1: Refactor & Package (Complete)
**Commit:** `50b666e` (combined with M0)

### Package Restructuring
- **Modularized:** Single script → `src/blackswans/` package with 7 modules
- **Architecture:**
  ```
  src/blackswans/
  ├── cli.py                 # CLI entry point
  ├── validate_claims.py     # 4-claim validation orchestrator
  ├── data/
  │   ├── loaders.py        # Data fetching & caching
  │   └── transforms.py     # Return computation
  ├── analysis/
  │   ├── outliers.py       # Outlier detection
  │   ├── scenarios.py      # Scenario analysis
  │   ├── regimes.py        # Regime classification
  │   └── statistics.py     # Statistical tests (M2)
  ├── visualization/
  │   └── plots.py          # Plotting functions
  └── io/
      └── writers.py        # File output
  ```
- **Backward Compatibility:** `src/validate_outliers.py` remains as wrapper

### Bug Fixes
- **Regime CAGR Bug:** Fixed annualization to use full period (cash on non-regime days)
  - Uptrend CAGR: 25.9% → 16.1% (now closer to paper's 10.3%)
- **Look-Ahead Bias:** MA now lagged by 1 day (shift(1)) for unbiased regime classification
- **Pandas Warnings:** Fixed FutureWarning in `make_plots()` concat operation
- **Cache Validation:** Added date coverage checks to `fetch_price_data()`

### Testing
- **Test Suite:** 66 tests across 6 modules (100% coverage on core analysis)
- **Test Files:**
  - `tests/test_transforms.py` — Daily return computation
  - `tests/test_outliers.py` — Outlier identification & stats
  - `tests/test_scenarios.py` — Scenario returns & CAGR
  - `tests/test_regimes.py` — Regime classification & performance
  - `tests/test_loaders.py` — Data loading & caching
  - `tests/test_statistics.py` — Statistical tests (added in M2)

### Configuration
- `pyproject.toml` — Package config with `[dev]` and `[api]` extras
- `.gitignore` — Excludes cache, tests, build artifacts

---

## Version 0.2.0 - M2: Statistical Validation (Complete)
**Commit:** `b8b6f10`

### New Modules
- `src/blackswans/analysis/statistics.py` — 7 statistical test functions
  - `chi_square_regime_clustering()` — Tests outlier clustering in regimes
  - `two_proportion_z_test()` — Compares outlier rates between regimes
  - `normality_tests()` — Jarque-Bera, Kolmogorov-Smirnov, Shapiro-Wilk
  - `bootstrap_confidence_interval()` — Non-parametric CIs for any statistic
  - `trend_following_backtest()` — MA strategy evaluation
  - `sharpe_ratio()`, `max_drawdown()`, `excess_kurtosis()`, `skewness()`

- `src/blackswans/validate_claims.py` — Full 4-claim validation
  - Orchestrates all tests with logging
  - Generates `docs/validation_report.md`

### Validation Results (S&P 500, 1928-2010, 20,673 trading days)

| Claim | Verdict | Evidence |
|-------|---------|----------|
| 1. Fat-tailed returns | **CONFIRMED** | Excess kurtosis = 17.6, Jarque-Bera p ≈ 0 |
| 2. Outsized influence of extremes | **CONFIRMED** | Missing 10 best days → -1.4% CAGR (95% CI: [-1.6%, -1.2%]) |
| 3. Outliers cluster in downtrends | **CONFIRMED** | 70.7% in downtrends, chi-squared p ≈ 10⁻⁵² (robust across 12 parameter sets) |
| 4. Trend-following avoids volatility | **CONFIRMED** | Max drawdown -25.7% (strategy) vs -86.2% (buy-hold) |

### Documentation
- `docs/validation_report.md` — Complete evidence with mathematical formulas, test statistics, sensitivity analysis

---

## Version 0.2.0 - M3: FastAPI Backend (Complete)
**Commit:** `c383eb9`

### API Endpoints
1. **GET `/api/health`** — Server health check
2. **GET `/api/tickers`** — List available tickers with date ranges
3. **GET `/api/analysis/{ticker}`** — Run outlier analysis with optional parameters
   - Query params: `start`, `end`, `ma_window`, `quantiles`
4. **GET `/api/validation/{ticker}`** — Run full 4-claim validation

### API Features
- FastAPI with automatic Swagger UI (`/docs`) and ReDoc (`/redoc`)
- Pydantic models for type-safe request/response serialization
- CORS enabled for frontend development
- Ticker mapping to CSV data files with auto-parsed date ranges
- 12 available tickers (S&P 500, Nikkei, FTSE, DAX, CAC, ASX, TSX, Hang Seng, EAFE, EM, REITs, Bonds)

### Configuration
- `api/README.md` — Complete API documentation
- `api/main.py` — FastAPI application (281 lines)
- `api/models.py` — Pydantic response models (90 lines)
- `pyproject.toml` — Added `[api]` extra with FastAPI & uvicorn

### Running
```bash
pip install -e ".[api]"
uvicorn api.main:app --reload
# Available at http://localhost:8000 with docs at /docs
```

---

## Version 0.2.0 - M4: React Dashboard (Complete)
**Commit:** `3c89950`

### Frontend Architecture
- **Framework:** React 19 + Vite + React Router v7
- **Charts:** Plotly.js for interactive visualizations
- **Build:** `npm run build` produces optimized production bundle

### Pages (2)
1. **Overview** (`/`) — Summary of all 4 Faber claims with validation verdicts
   - ClaimCard component for each claim displaying verdict and key evidence

2. **Analysis** (`/analysis/:ticker`) — Per-ticker detailed analysis dashboard
   - Market selector dropdown to choose from 12 tickers
   - Four chart types for comprehensive visualization

### Components (6)
1. **ClaimCard** — Displays claim verdict (CONFIRMED/DISPROVEN) with evidence
2. **MarketSelector** — Dropdown for ticker selection across 12 available indices
3. **TimeSeriesChart** — Daily returns with highlighted outlier days
4. **HistogramChart** — Return distribution with normal overlay for comparison
5. **RegimeChart** — Returns colored by regime (uptrend=green, downtrend=red)
6. **ScenarioChart** — Impact visualization comparing scenarios (baseline, missing best 10 days, missing worst, missing both)

### API Integration
- `services/api.js` — Axios-based API client with comprehensive mock data fallback
- Mock data based on actual S&P 500 validation results
- Graceful degradation when backend is unavailable
- All data types match real API responses

### Styling
- Clean, financial-themed CSS styling
- Responsive layout for desktop and tablet
- Color scheme: blue/red for regime classification, teal for highlights

### Running
```bash
cd frontend
npm install
npm run dev       # Development server on http://localhost:5173
npm run build     # Production build
```

---

## Security Fixes

### PR #8: Path Injection Vulnerabilities (CodeQL)
**Commit:** `39e06b1`
- Fixed path traversal vulnerabilities in file I/O operations
- Sanitized user inputs in CLI and API
- CodeQL scan passed with 0 critical issues

### PR #9: GitHub Actions YAML Syntax
**Commit:** `7f81b9e`
- Fixed syntax errors in `sync-wiki.yml` workflow

---

## CI/CD & Automation

### GitHub Actions Workflows (3 total)

1. **codeql.yml** — Security scanning
   - Runs CodeQL analysis on Python code
   - Identifies potential vulnerabilities

2. **deploy.yml** — Frontend deployment
   - Builds React app with `npm run build`
   - Auto-deploys to GitHub Pages

3. **sync-wiki.yml** — Wiki synchronization
   - Auto-syncs `docs/wiki/` to GitHub Wiki
   - Triggered on changes to wiki files

---

## Known Limitations & TODOs

### Data
- **Stale Data:** Historical data only through Dec 31, 2010 (needs 2025 update)
- **TODO:** Update all 12 CSV files with current market data

### Bugs & Issues
- **Regime CAGR Bug:** Fixed in M1 (was annualizing only regime days, now full-period)
- **Look-Ahead Bias:** Documented limitation in quantile calculation across full history

### Missing Features
- **No API Tests:** Frontend/API integration not covered by pytest suite
- **No Frontend Tests:** React components lack unit tests
- **No Comparison Page:** Can't compare multiple tickers side-by-side
- **No Parameter Controls:** UI doesn't allow real-time MA window/quantile adjustment
- **No Data Export:** Results can't be downloaded (CSV/Excel)

---

## Architecture Summary (Current)

### Package: `src/blackswans/`
- **Version:** 0.2.0
- **CLI:** `blackswans --ticker ^GSPC --start 1928-09-01 --end 2010-12-31 --output-dir output/`
- **7 Core Modules** with clear separation of concerns
- **66 Tests** with 100% coverage on analysis modules

### Backend: FastAPI (`api/`)
- **4 REST Endpoints** for analysis and validation
- **Pydantic Models** for type safety
- **12 Tickers** with auto-parsed date ranges

### Frontend: React (`frontend/`)
- **2 Pages** (Overview, Analysis)
- **6 Reusable Components** with Plotly charts
- **Mock Data Fallback** for offline development
- **Built with Vite** for fast development

### Testing
- **66 Tests** across 6 modules
- **100% Coverage** on core analysis (`src/blackswans/analysis/`, `data/`)
- **No API/Frontend Tests** yet

---

## Key Documents

- `docs/audit_report.md` — M0 audit findings and recommendations
- `docs/validation_report.md` — M2 statistical validation with full evidence
- `docs/wiki/architecture.md` — Current package architecture (needs M3/M4 update)
- `docs/wiki/data_dictionary.md` — All 12 CSV input files
- `docs/wiki/analysis_methods.md` — Mathematical formulas for all analyses
- `CLAUDE.md` — Developer guide with CLI commands and code style

---

## Release Notes

### v0.2.0 (2026-02-06) — Production Ready
- All 4 Faber claims statistically validated
- Package architecture complete with 66 tests
- FastAPI backend with 4 endpoints
- React dashboard with 6 components and 2 pages
- Security fixes for path injection vulnerabilities
- GitHub Actions CI/CD with automated wiki sync

**Next Priority:** Update historical data through 2025 and add API/frontend test coverage
