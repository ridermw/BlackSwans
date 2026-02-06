# Milestone 0: Audit Report

**Date**: 2026-02-06
**Auditors**: Tester, Code Reviewer, Researcher, Devil's Advocate
**Compiled by**: Team Lead

---

## Executive Summary

The existing `src/validate_outliers.py` script is **functional and reproducible** but has **one critical bug** (regime CAGR calculation), **missing statistical rigor** (no significance tests), and **several methodological concerns** that must be addressed before the analysis can be considered a valid replication of Faber (2011).

**Decision**: Fix the critical bug first, then refactor into a package, then add statistical tests. The code is clean enough that refactoring won't be painful.

---

## M0.1: Script Execution (Tester)

**Status**: PASS

- Script runs without errors for S&P 500, FTSE, and Nikkei 225
- Outputs are **reproducible** — re-running produces identical results (differences only in floating-point precision at the 15th+ decimal place)
- All 3 output types generated correctly: CSVs (4 per index) and PNGs (3 per index)
- **Warning**: Pandas FutureWarning about DatetimeIndex sorting in `pd.concat` (line 321). Non-blocking but should be fixed.

**Conclusion**: The script works as designed. No execution bugs.

---

## M0.2: Code Audit (Code Reviewer)

**Status**: PASS (no critical bugs in core math)

### Functions Verified Correct:
- `compute_daily_returns()` — `pct_change(fill_method=None)` is correct, NaN handling is proper
- `calculate_outlier_stats()` — quantile logic correctly captures both tails with inclusive boundaries
- `annualised_return()` — CAGR formula is mathematically correct (252 trading days standard)
- `scenario_returns()` — sort/slice logic correctly identifies best/worst days, handles overlap
- `moving_average_regime()` — regime classification works, first `window-1` days properly set to NaN
- `outlier_regime_counts()` — index alignment is correct, NaN regime days gracefully excluded

### Minor Issues Found:
1. **Cache coverage validation** (line 143): `fetch_price_data()` doesn't verify cached data covers the full requested date range. Could silently return incomplete data if cache has partial coverage.
2. **Price == MA edge case**: Days where price exactly equals the 200-day MA are classified as downtrend (0). Acceptable but undocumented.
3. **Outliers in NaN regime period**: Outliers occurring in the first 199 days are silently excluded from regime counts. Acceptable but undocumented.

**Conclusion**: Core calculations are sound. No bugs that would affect analysis results.

---

## M0.3: Research Audit (Researcher)

**Status**: PARTIAL MATCH — one critical discrepancy found

### What Matches the Paper:
- Same index (S&P 500)
- Same 200-day MA regime classification
- Same quantile approach (0.99, 0.999)
- Same scenario methodology (zeroing out returns)
- Regime split: 64.8% uptrend / 35.2% downtrend (matches paper's ~65%/35%)
- Outlier clustering: 70.7% in downtrends (matches paper's "60-80%" range)
- Outlier statistics close to paper when adjusted for date range differences

### What Doesn't Match:

#### BUG: Regime Performance Annualization Is Wrong
- **Script output**: Uptrend CAGR = 25.9%, Downtrend CAGR = -25.1%
- **Paper reports**: Uptrend CAGR ≈ 10.3%, Downtrend CAGR ≈ -4.5%
- **Root cause**: `regime_performance()` calls `annualised_return(r)` where `r` is only the days in that regime. The function computes `years = len(r) / 252`, which is the number of *regime-specific* trading days divided by 252 — not the total calendar period. This artificially inflates/deflates the CAGR because it compresses 80 years of regime-specific returns into 53 years (uptrend) or 29 years (downtrend).
- **Fix**: Either use total calendar years for annualization, or compute CAGR differently for regime subsets.
- **Severity**: CRITICAL — this is the most prominent numerical discrepancy with the paper.

#### Missing: Quantile-Based Scenario Outputs
- Paper shows scenario returns for missing 1% and 0.1% of best/worst days
- Script only outputs 10-day scenarios (the `--best-count 10 --worst-count 10` default)
- The quantile analysis exists but isn't connected to the scenario output

#### Missing: International Markets
- Paper analyzes 15 global markets
- Script supports any ticker but has only been run for 12 indices

### Extended Date Range:
- Paper covers 1928-2010
- Current outputs use 1928-2025 (extended without documentation)
- Should maintain separate "replication" (1928-2010) and "extension" (2010-2025) runs

**Conclusion**: Core methodology is correctly implemented. The regime CAGR bug must be fixed. Scenario analysis should be extended to cover quantile-based counts.

---

## M0.4: Devil's Advocate Review

**Status**: 11 concerns identified, 3 critical

### Critical Concerns (Must Address):

1. **No Statistical Significance Tests**
   - No p-values, confidence intervals, or hypothesis tests anywhere
   - Cannot distinguish signal from noise
   - Outlier clustering (290 vs 120) could be random — needs chi-squared test
   - Must add: bootstrap CIs, chi-squared, KS test, Jarque-Bera
   - This is the single most important gap in the analysis

2. **Look-Ahead Bias in Regime Classification**
   - Current code: `regime = (price[T] > MA(prices[T-199:T]))` — MA includes today's price
   - Should be: `regime = (price[T] > MA(prices[T-200:T-1]))` — using yesterday's MA
   - Overstates regime classification effectiveness
   - Impact on clustering statistics is likely small but should be quantified

3. **Simple vs Log Returns**
   - Code uses simple returns for scenarios but geometric compounding for CAGR
   - Mixing arithmetic zeroing with geometric annualization creates inconsistency
   - For extreme outliers (±20%), log vs simple returns differ by 2-4%
   - Should document rationale or switch to log returns

### Important Concerns (Should Address):

4. **Arbitrary "10 Best/Worst Days"** — Need sensitivity analysis (5, 10, 20, 50 days)
5. **200-day MA Window Not Justified** — Test 50, 100, 200, 300 day windows
6. **Binary Regime Oversimplified** — Consider 3-state (up/sideways/down)
7. **Yahoo Finance vs Academic Data** — Different source than paper (Global Financial Data)

### Minor Concerns (Nice to Have):

8. Transaction costs ignored (paper acknowledges this)
9. Survivorship bias in index composition
10. No bootstrapped robustness testing
11. "Missing N days" assumes surgical precision (unrealistic)

### Devil's Advocate Verdict:
The core finding (outliers cluster in bear markets) is likely **real** and consistent with known volatility clustering. However, the **magnitude and actionability are unproven** without statistical tests. The analysis currently amounts to exploratory data analysis without formal hypothesis testing.

---

## Prioritized Issue List

| Priority | Issue | Category | Milestone |
|----------|-------|----------|-----------|
| P0 | Fix regime CAGR annualization bug | Bug | M1.1 |
| P0 | Add statistical significance tests | Missing feature | M2.1 |
| P1 | Fix look-ahead bias in MA regime | Bug | M1.1 |
| P1 | Add quantile-based scenario outputs | Missing feature | M1.1 |
| P1 | MA window sensitivity analysis | Validation | M2.4 |
| P1 | N best/worst days sensitivity | Validation | M2.3 |
| P2 | Document simple vs log returns choice | Documentation | M1.6 |
| P2 | Fix pandas FutureWarning | Maintenance | M1.1 |
| P2 | Add cache coverage validation | Robustness | M1.1 |
| P2 | 3-state regime classification | Enhancement | M2.4 |
| P3 | Data quality audit vs academic sources | Validation | M2 |
| P3 | Transaction cost modeling | Enhancement | M2.6 |
| P3 | Bootstrapped robustness testing | Validation | M2 |

---

## Decision: Fix First, Then Refactor

**Rationale**: The codebase is clean (389 lines, well-structured functions, good separation of concerns). The regime CAGR bug is isolated to one function. The look-ahead bias fix is a one-line change. These fixes should be applied first so that:

1. We have a correct baseline before refactoring
2. We can verify refactored code produces the same (corrected) results
3. The fix is small and low-risk

**Plan**:
1. **M1.1**: Fix P0/P1 bugs on `feature/fix/audit-findings` branch
2. **M1.3**: Refactor into package on `feature/backend/modularize` branch
3. **M1.4**: Add tests on `feature/test/core-modules` branch (tests validate refactored code produces same results as fixed script)
4. **M1.2**: Update data to 2025

---

## Appendix: Output Comparison Summary

| Index | outlier_stats | return_scenarios | regime_performance | outlier_regime_counts |
|-------|:---:|:---:|:---:|:---:|
| S&P 500 | FP precision | FP precision | FP precision | Exact match |
| FTSE | FP precision | FP precision | FP precision | Exact match |
| Nikkei | FP precision | Exact match | Exact match | Exact match |

FP precision = floating-point precision differences only (15th+ decimal place). Not meaningful.
