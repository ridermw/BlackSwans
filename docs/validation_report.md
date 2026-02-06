# Validation Report: Faber's "Where the Black Swans Hide" (2011)

**Date**: 2026-02-06
**Dataset**: S&P 500 (^GSPC), September 1928 – December 2010
**Trading Days**: 20,673
**Data Source**: Yahoo Finance (cached CSV)

---

## Executive Summary

All four core claims from Faber's 2011 paper are **statistically confirmed** using formal hypothesis tests and sensitivity analysis across multiple parameter combinations.

| Claim | Verdict | Key Evidence |
|-------|---------|-------------|
| 1. Fat-tailed returns | **CONFIRMED** | Excess kurtosis = 17.6, Jarque-Bera p ≈ 0 |
| 2. Outsized influence of extremes | **CONFIRMED** | Missing 10 best days: CAGR drops 1.4% (95% CI: [1.2%, 1.6%]) |
| 3. Outliers cluster in bear markets | **CONFIRMED** | 70.7% of outliers in downtrends, chi-squared p ≈ 10⁻⁵² |
| 4. Trend-following avoids worst volatility | **CONFIRMED** | Max drawdown: -25.7% (strategy) vs -86.2% (buy-hold) |

---

## Claim 1: Market Returns Are Fat-Tailed

**Hypothesis**: Daily S&P 500 returns are not normally distributed; they exhibit heavier tails than a Gaussian distribution.

### Test Results

| Test | Statistic | p-value | Result |
|------|-----------|---------|--------|
| Kolmogorov-Smirnov | 0.0962 | ≈ 10⁻¹⁶⁷ | Reject normality |
| Jarque-Bera | 266,869 | ≈ 0 | Reject normality |

### Descriptive Statistics

| Metric | Value | Normal Expected |
|--------|-------|-----------------|
| Excess kurtosis | **17.6** | 0 |
| Skewness | -0.07 | 0 |
| Largest positive return (sigma) | **+13.7σ** | ~3-4σ max |
| Largest negative return (sigma) | **-16.9σ** | ~3-4σ max |

### Interpretation

The excess kurtosis of 17.6 is enormously fat-tailed. Under a normal distribution, a 13.7-sigma event has a probability of approximately 10⁻⁴², yet we observe it in ~80 years of data. The returns distribution has dramatically heavier tails than Gaussian, consistent with Faber's claim and well-established financial literature.

**Verdict: CONFIRMED** with overwhelming statistical significance.

---

## Claim 2: A Small Number of Extreme Days Have Outsized Influence

**Hypothesis**: Removing a tiny fraction of trading days materially changes long-term returns.

### Scenario Analysis

| Miss N Days | % of Total | CAGR (all) | CAGR (miss best) | CAGR (miss worst) | Impact |
|-------------|-----------|------------|-------------------|-------------------|--------|
| 5 | 0.024% | 5.12% | 4.34% | 6.00% | ±0.8% |
| **10** | **0.048%** | **5.12%** | **3.71%** | **6.62%** | **±1.4%** |
| 20 | 0.097% | 5.12% | 2.64% | 7.76% | ±2.5% |
| 50 | 0.242% | 5.12% | 0.18% | 10.48% | ±4.9% |

### Bootstrap Confidence Interval (Miss Best 10)

- **Point estimate**: 1.41% CAGR reduction
- **95% CI**: [1.19%, 1.63%]
- **Standard error**: 0.11%

### Interpretation

Missing just 10 days (0.048% of all trading days) reduces the annualized return by 1.4 percentage points — a statistically significant effect with a tight confidence interval that excludes zero. Missing 50 days reduces CAGR from 5.1% to 0.2%, essentially eliminating all returns from an 82-year investment.

The effect is symmetric: missing the worst 50 days doubles the CAGR to 10.5%.

**Verdict: CONFIRMED** — a tiny number of days drive a disproportionate share of returns.

---

## Claim 3: Outliers Cluster During Bear Markets

**Hypothesis**: Extreme return days occur disproportionately when the market is below its moving average (downtrend).

### Main Result (200-day MA, 99th percentile)

| Metric | Value |
|--------|-------|
| Outliers in downtrends | 290 (70.7%) |
| Outliers in uptrends | 120 (29.3%) |
| Downtrend days | 35.2% of total |
| Chi-squared statistic | 230.4 |
| **Chi-squared p-value** | **4.78 × 10⁻⁵²** |
| Z-test statistic | 15.2 |
| Z-test p-value | ≈ 0 |

### Sensitivity Analysis

All 12 parameter combinations (4 MA windows × 3 quantile thresholds) show significant clustering at p < 0.05:

| MA Window | q=0.95 | q=0.99 | q=0.999 |
|-----------|--------|--------|---------|
| 50-day | 63.4% (p≈0) | 72.7% (p≈10⁻⁴³) | 64.3% (p=0.002) |
| 100-day | 62.9% (p≈0) | 73.1% (p≈10⁻⁴⁹) | 57.1% (p=0.017) |
| **200-day** | **61.7% (p≈0)** | **70.7% (p≈10⁻⁵²)** | **66.7% (p≈10⁻⁵)** |
| 300-day | 63.1% (p≈0) | 76.8% (p≈10⁻⁷³) | 73.0% (p≈10⁻⁶) |

### Interpretation

The clustering effect is:
1. **Highly statistically significant** — p-values are astronomically small
2. **Robust to parameter choice** — confirmed across all MA windows and quantile thresholds
3. **Economically meaningful** — 70%+ of outliers occur during 35% of time
4. **Stronger for more extreme outliers** — the 99th percentile clusters more than 95th

The outlier rate in downtrends is approximately 2x higher than in uptrends (confirmed by z-test). This is not an artifact of parameter selection.

**Verdict: CONFIRMED** with extreme statistical significance and full robustness to parameter sensitivity.

---

## Claim 4: Trend-Following Reduces Worst Volatility

**Hypothesis**: A simple strategy (hold when price > 200-day MA, cash otherwise) reduces maximum drawdown and volatility.

### Main Result (200-day MA, 1928-2025)

| Metric | Buy-and-Hold | Trend-Following | Improvement |
|--------|-------------|-----------------|-------------|
| CAGR | 5.86% | 16.57% | +10.71pp |
| Sharpe Ratio | 0.40 | 1.32 | +0.92 |
| Max Drawdown | **-86.2%** | **-25.7%** | **+60.5pp** |
| Volatility | 19.0% | 12.2% | -6.8pp |

### Important Caveats

1. **No transaction costs**: The backtest assumes zero trading costs. A 200-day MA generates approximately 2-10 trades per year; at 0.1% round-trip cost, this represents a 0.2-1% annual drag.
2. **Execution timing**: The regime signal compares today's closing price against the lagged 200-day MA (computed from yesterday's data). The position is determined at the close.
3. **Survivorship bias**: The S&P 500 index composition changes over time.

### Interpretation

Trend-following reduces maximum drawdown from -86% to -26% and volatility from 19% to 12%. The CAGR improvement is substantial (+10.7pp) and the Sharpe ratio more than triples (0.40 → 1.32). The drawdown reduction is the key finding consistent with Faber's claim: trend-following **avoids worst-case volatility**.

The strategy outperforms buy-and-hold on both an absolute and risk-adjusted basis. The primary benefit is tail-risk protection by sitting in cash during extended downtrends.

**Verdict: CONFIRMED** — trend-following reduces maximum drawdown and volatility, consistent with Faber's claim.

---

## Methodology Notes

### Data
- S&P 500 price data from Yahoo Finance, 1928-09-04 to 2025-01-31
- Daily percentage returns computed via `pct_change(fill_method=None)`
- 24,216 trading days (original validation used 20,673 days through 2010-12-31)

### Statistical Tests Used
- **Normality**: Kolmogorov-Smirnov, Jarque-Bera
- **Clustering**: Chi-squared contingency test, two-proportion z-test
- **Confidence intervals**: Non-parametric bootstrap (1,000 resamples)
- **Performance**: CAGR, Sharpe ratio, maximum drawdown, annualized volatility

### Regime Classification
- Binary: uptrend (price > lagged 200-day SMA) vs downtrend (price ≤ lagged 200-day SMA)
- Lagged by 1 day to avoid look-ahead bias
- First 200 days excluded (MA undefined)

### Sensitivity Analysis
- MA windows: 50, 100, 200, 300 days
- Quantile thresholds: 0.95, 0.99, 0.999
- Best/worst day counts: 5, 10, 20, 50

---

## Extended Validation: 1928-2025

The original validation used data through December 2010 (matching Faber's paper). We re-validated all four claims using an extended dataset through January 2025, adding 15 years of market events including the COVID-2020 crash, 2022 downturn, and 2023-2024 rally.

### Comparison: 1928-2010 vs 1928-2025

| Metric | 1928-2010 (20,674 days) | 1928-2025 (24,216 days) | Change |
|--------|------------------------|------------------------|--------|
| **Claim 1: Fat tails** | | | |
| Excess kurtosis | 17.60 | 17.27 | Slightly lower (COVID added extreme days but also more normal days) |
| Jarque-Bera p-value | ≈ 0 | ≈ 0 | Unchanged |
| **Claim 2: Outsized influence** | | | |
| CAGR impact (miss 10 best) | 1.41pp (CI: [1.19%, 1.63%]) | 1.21pp (CI: [1.03%, 1.39%]) | Diluted slightly by more data, still highly significant |
| **Claim 3: Clustering** | | | |
| % outliers in downtrends | 70.7% | 72.2% | *Strengthened* |
| Chi-squared p-value | 4.7 × 10⁻⁵² | 2.5 × 10⁻⁷⁸ | *Strengthened* (26 more orders of magnitude) |
| **Claim 4: Trend-following** | | | |
| Strategy CAGR | 16.1% | 16.6% | Stable |
| Buy-hold CAGR | 4.9% | 5.9% | Higher (2010-2025 was a strong bull market) |
| Strategy max drawdown | -25.7% | -25.7% | Unchanged (worst drawdown still from historical period) |
| Buy-hold max drawdown | -86.2% | -86.2% | Unchanged |
| Strategy Sharpe | 1.27 | 1.32 | Slightly improved |

### Cross-Index Validation (2025 Data)

All four claims are confirmed across all major international indices:

| Index | Days | Fat Tails | Outsized | Clustering p-value | % Downtrend | Trend-Following |
|-------|------|-----------|----------|-------------------|-------------|----------------|
| S&P 500 | 24,216 | CONFIRMED | CONFIRMED | 2.5 × 10⁻⁷⁸ | 72.2% | CONFIRMED |
| Nikkei 225 | 13,546 | CONFIRMED | CONFIRMED | 7.4 × 10⁻⁵² | 81.2% | CONFIRMED |
| FTSE 100 | 10,377 | CONFIRMED | CONFIRMED | 2.7 × 10⁻⁶⁷ | 88.4% | CONFIRMED |
| DAX | 9,377 | CONFIRMED | CONFIRMED | 3.1 × 10⁻⁶⁶ | 88.0% | CONFIRMED |
| Hang Seng | 9,398 | CONFIRMED | CONFIRMED | 1.4 × 10⁻²³ | 74.7% | CONFIRMED |

### Key Finding

All four claims are **robustly confirmed** with the extended data across all markets tested. The clustering result (Claim 3) actually *strengthened* significantly — the COVID-2020 crash produced extreme outlier days that clustered heavily during the bear market phase, adding further evidence for Faber's thesis. The S&P 500 p-value dropped from 10⁻⁵² to 10⁻⁷⁸. FTSE and DAX show the strongest clustering (88% of outliers in downtrends).

---

## Conclusion

Faber's four core claims are all **statistically confirmed** with rigorous hypothesis testing:

1. **Fat tails**: Excess kurtosis of 17.6 and extreme sigma values (up to 16.9σ) decisively reject normality.
2. **Outsized influence**: Missing 10 days (0.05% of data) changes CAGR by 1.4pp — a statistically significant effect.
3. **Clustering**: 70.7% of outliers occur during downtrends (which represent 35% of time), confirmed at p ≈ 10⁻⁵². This result is robust across all 12 parameter combinations tested.
4. **Trend-following**: Maximum drawdown drops from -86% to -26% under a simple 200-day MA rule.

The analysis extends Faber's descriptive findings with formal statistical significance tests, bootstrap confidence intervals, and comprehensive sensitivity analysis. The clustering result is particularly robust — all parameter combinations are significant — suggesting it reflects a genuine feature of market dynamics rather than a statistical artifact.
