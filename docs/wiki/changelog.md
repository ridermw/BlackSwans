# Changelog

## Version 0.1 - 2026-02-06

### Initial M0 Audit Documentation
**Status:** M0 (Maintenance/Documentation Phase)

#### Added
- **Wiki Architecture Documentation** (`docs/wiki/architecture.md`)
  - Single-file architecture overview
  - Data pipeline description
  - Complete function reference and purposes
  - Data structures (OutlierStats dataclass)
  - Full data flow diagram
  - Output files specification

- **Data Dictionary** (`docs/wiki/data_dictionary.md`)
  - Complete reference for 12 input CSV data files
  - Index-by-index metadata (ticker, date range, asset class)
  - Output CSV column specifications
  - Data quality notes and loading behavior
  - Cache strategy documentation

- **Analysis Methods Documentation** (`docs/wiki/analysis_methods.md`)
  - Mathematical formulas for all analyses
  - Daily return calculation
  - CAGR (Compound Annual Growth Rate) formula
  - Quantile-based outlier detection methodology
  - Moving average regime classification
  - Scenario analysis explanation
  - Regime performance metrics
  - Outlier clustering analysis methodology
  - Limitations and assumptions
  - Historical context from Faber (2011) paper

- **Project Wiki Directory** (`docs/wiki/`)
  - Centralized documentation location
  - Foundation for future contributor documentation

#### Project Context
- **Audit Phase:** M0 (Code Audit and Validation)
- **Active Tasks:** M0.1-M0.4 (Code audit, research audit, devil's advocate review)
- **Reference Paper:** Faber, M. "Where the Black Swans Hide & The 10 Best Days Myth" (2011) SSRN 1908469
- **Data Coverage:** 12 market indices with historical data through 2010
- **Primary Analysis:** S&P 500 (1928-2010); validation on international indices

#### Technical Summary
- Single-file Python implementation (~389 lines)
- Dependencies: pandas, numpy, matplotlib, scipy, yfinance
- Output: 4 CSV files + 3 PNG visualizations per analysis
- Caching: Local CSV files in `data/` directory
- Default parameters: MA window=200, quantiles=[0.99, 0.999], N_days=10

#### Known Limitations (Documented)
- Quantile thresholds not optimized per market
- MA window (200 days) not market-specific
- No transaction costs in scenario analysis
- Survivorship bias in historical index data
- Look-ahead bias in full-history quantile calculation

#### Future Enhancement Areas
1. Statistical testing (chi-square for clustering)
2. Conditional regime analysis
3. Rolling window stability testing
4. Realistic transaction cost modeling
5. Machine learning regime alternatives
6. Multivariate index correlation analysis

---

## Version History Notes

### M0 (Current Phase)
- **M0.1:** Run existing script and verify outputs (in_progress)
- **M0.2:** Code audit of validate_outliers.py (completed)
- **M0.3:** Research audit - compare methodology to paper (in_progress)
- **M0.4:** Devil's Advocate review of assumptions (in_progress)
- **M0.5:** Compile audit report from M0.1-0.4 (pending)
- **M0.6:** Initialize project wiki documentation (in_progress)

### Future Phases
- M1: Bug fixes and refinements (post-audit)
- M2: Feature enhancements (new analysis methods)
- M3: Test suite development
- M4: Performance optimization
