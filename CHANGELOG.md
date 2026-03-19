# Changelog

## [0.3.0] - 2025-03-19

### Added
- **Frontend Dashboard**: Complete dark-themed professional UI
  - Landing page with thesis verdict and key statistics
  - Period Comparison page: pre/post-2011 claims analysis
  - Multi-Index page: 12 global indices comparison with sortable table
  - CAGR Research page: interactive scenario analysis with waterfall charts
- **Split-Period Analysis** (`periods.py`): New module for pre/post-publication analysis
- **3 New API Endpoints**: period-comparison, cagr-matrix, multi-index
- **Static JSON Generation**: `generate_static_data.py` for GitHub Pages deployment
- **Playwright E2E Tests**: 17 end-to-end test specifications
- **129 New Tests**: Coverage boost from 58% to 88% (197 total)
  - validate_claims.py: 15% → 81%
  - cli.py: 0% → 98%
  - loaders.py: 67% → 94%
  - periods.py: 92% → 99%

### Changed
- Frontend redesigned with professional dark theme (#0a0e17)
- API service rewritten with fetchWithFallback pattern
- App shell redesigned with 5-route navigation

## [0.2.0] - 2025-02-06

### Added
- Initial frontend with React + Vite + Plotly
- FastAPI backend with validation endpoints
- 4-claim validation framework
- 68 unit tests

## [0.1.0] - 2025-01-15

### Added
- Core analysis modules (outliers, scenarios, regimes, statistics)
- CLI interface
- Data loaders with caching
