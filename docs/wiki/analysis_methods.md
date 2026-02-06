# Analysis Methods

## Overview

This document describes the mathematical and statistical methods used in the Black Swans validation project. The analysis implements core techniques from Mebane Faber's 2011 white paper: "Where the Black Swans Hide & The 10 Best Days Myth".

**Reference:** [SSRN 1908469](https://ssrn.com/abstract=1908469)

## Daily Return Calculation

### Formula
```
Daily Return (%) = (P_t - P_{t-1}) / P_{t-1} × 100
```

Where:
- `P_t` = Closing price on day t
- `P_{t-1}` = Closing price on day t-1

### Implementation Notes
- Computed using pandas `pct_change(fill_method=None)`
- Avoids pandas deprecation warnings by explicitly setting `fill_method=None`
- First return (t=1) is NaN and dropped
- No forward-fill or backward-fill applied

## Compound Annual Growth Rate (CAGR)

### Formula
```
CAGR = (∏(1 + r_i))^(1/n) - 1
```

Where:
- `r_i` = Daily return on day i
- `n` = Number of years = (Number of days) / 252
- `∏` = Product operator across all days

### Interpretation
CAGR represents the constant annual return that would yield the same ending value if applied annually. Used to compare scenarios with different return distributions.

### Assumptions
- **Trading Days:** 252 per year (market convention)
- **Compounding:** Daily returns compound continuously into annual returns
- **No Cash Flows:** Assumes buy-and-hold with no deposits/withdrawals

## Quantile-Based Outlier Detection

### Concept
Identifies extreme returns at both tails of the distribution using statistical quantiles.

### Formula
For quantile q (e.g., 0.99):
- **Lower Tail:** Returns ≤ quantile(1 - q) = quantile(0.01)
- **Upper Tail:** Returns ≥ quantile(q) = quantile(0.99)

### Example: q = 0.99
- Identifies bottom 1% worst returns
- Identifies top 1% best returns
- Approximately 2-3 days per year (252 × 0.01 ≈ 2.5)

### Why Quantiles?
- **Robust to outliers:** Not sensitive to extreme values
- **Non-parametric:** Does not assume normal distribution
- **Flexible:** Can adjust tail percentage (0.99 = 1%, 0.999 = 0.1%)
- **Interpretable:** Direct connection to tail risk

## Market Regime Classification

### Moving Average (MA) Crossover

#### Formula
```
MA_t = mean(P_t-window+1, ..., P_t)
Regime_t = 1 if P_t > MA_t else 0
```

Where:
- `MA_t` = Simple moving average of prices over `window` days
- `Regime_t` = 1 (uptrend) if price above MA, 0 (downtrend) if below

### Default Window
200 trading days (~10 months)

### Regimes Defined
| Regime | Label | Condition | Interpretation |
|--------|-------|-----------|-----------------|
| 0 | Downtrend | Price < MA | Bearish environment |
| 1 | Uptrend | Price > MA | Bullish environment |
| NaN | Undefined | First 199 days | Insufficient history |

### Rationale
- **Simple & Interpretable:** No optimization required
- **Widely Tested:** Decades of trend-following research
- **Lag Inherent:** MA lags price moves (conservative signal)
- **200-day Window:** ~1 market year; captures medium-term trends

## Scenario Analysis: Impact of Extreme Days

### Method
Simulates four return scenarios by selectively zeroing out returns on extreme days:

```
1. All Days (Baseline)
   Returns: [r_1, r_2, r_3, ..., r_n]

2. Miss Best N Days
   Returns: [r_1, r_2, 0, ..., r_n] (largest N days set to 0)

3. Miss Worst N Days
   Returns: [r_1, 0, r_3, ..., r_n] (smallest N days set to 0)

4. Miss Both Best & Worst N Days
   Returns: [r_1, 0, 0, ..., r_n] (both sets zeroed out)
```

### Implementation
- Days are ranked by return magnitude
- Top N returns zeroed for "miss best"
- Bottom N returns zeroed for "miss worst"
- CAGR computed for each scenario
- Default: N = 10 days

### Interpretation
This analysis tests Faber's central claim: **A handful of extreme days determine long-term returns.**

Example Results:
- All days: 10% CAGR
- Miss best 10: 8% CAGR → 2% loss from missing gains
- Miss worst 10: 12% CAGR → 2% gain from avoiding losses
- Miss both: 10% CAGR → Extreme days net neutral

## Regime Performance Metrics

### Daily Statistics by Regime
For each regime (uptrend/downtrend), compute:

```
count      = Number of trading days in regime
pct_total  = count / total_days × 100
mean       = Average daily return
median     = Median daily return
std        = Population standard deviation (ddof=0)
cagr       = Annualized return for regime
```

### Interpretation
- **Count & %:** How much time spent in each regime?
- **Mean/Median:** Average performance in each regime
- **Std:** Volatility in each regime
- **CAGR:** Long-term growth by regime

### Example
If downtrends (0% of time) have high negative skew and high std, this suggests:
- Concentrated losses during bear markets
- Potential benefit from avoiding downtrend exposure

## Outlier Clustering Analysis

### Method
For each quantile threshold, count how many outliers occur in each regime:

```python
Regime 0 (Downtrend): Count of outliers with Price < MA
Regime 1 (Uptrend):   Count of outliers with Price > MA
```

### Hypothesis Test (Conceptual)
**H0:** Outliers are randomly distributed across regimes
**H1:** Outliers cluster in downtrends (regime 0)

If observed clustering significantly exceeds random expectation, this supports Faber's "black swans hide during bear markets" thesis.

### Expected Under Random Distribution
If 30% of days are downtrends:
- Expected downtrend outliers = 30% × total_outliers
- Expected uptrend outliers = 70% × total_outliers

If actual downtrend outliers >> 30% of total, clustering is evident.

## Limitations & Assumptions

### Statistical Assumptions
1. **Returns are i.i.d.:** Ignores autocorrelation and volatility clustering
2. **Normal Distribution (for reference):** Most returns are clearly non-normal (fat tails)
3. **No Transaction Costs:** Scenarios ignore realistic costs of regime switching
4. **No Slippage:** Assumes perfect execution at daily close

### Methodological Limitations

#### Quantile Outliers
- **Threshold Dependent:** Results sensitive to chosen quantile (0.99 vs 0.999)
- **Look-ahead Bias:** Quantiles computed on full history, then applied
- **Survivorship:** Only captures events within data range

#### MA Regime
- **Lag:** Moving average lags price by ~half the window
- **Whipsaws:** Can generate false signals in choppy markets
- **Parameter Selection:** 200-day window not optimized per market

#### Scenario Analysis
- **Unrealistic:** Cannot actually "miss" days; requires active trading
- **One-way Test:** Only tests missing best or worst, not hedging costs
- **Hindsight Bias:** Results apply only with perfect foresight

### Data Quality Notes
- **Survivorship Bias:** Historical indices reflect current constituents
- **Delisted Stocks:** Not included in index histories
- **Corporate Actions:** Dividends handled (Adj Close used), but stock splits assumed adjusted
- **Holiday Closures:** Gaps between trading days not specially handled

## Historical Context from Faber (2011)

### Key Findings from Original Paper
1. **Out-sized Impact:** 10 best days account for ~50% of 80-year S&P 500 returns
2. **Timing Problem:** Missing best days is nearly impossible in practice
3. **Regime Effect:** Extreme days cluster during bear markets (downtrends)
4. **Trend Following:** 200-day MA crossover reduces downside volatility

### Extensions in This Analysis
- Extend analysis to 2010 (original: 1926–2010)
- Apply to 11 additional indices (original: S&P 500 only)
- Quantify regime clustering effect
- Test multiple quantile thresholds

## Implemented Enhancements (M2: Statistical Validation)

### Completed in Milestone 2
1. **Statistical Testing:** Chi-square test for outlier clustering (COMPLETED)
   - Tests hypothesis that outliers cluster in downtrends
   - Results show 70.7% of outliers in downtrends, p ≈ 10⁻⁵²
2. **Normality Tests:** Jarque-Bera, KS, Shapiro-Wilk (COMPLETED)
3. **Bootstrap Confidence Intervals:** Non-parametric CI for any statistic (COMPLETED)
4. **Trend Following Backtest:** MA strategy evaluation (COMPLETED)
5. **Performance Metrics:** Sharpe ratio, max drawdown calculation (COMPLETED)

See `docs/validation_report.md` for complete evidence and results.

## Future Enhancements

### Remaining Improvements
1. **Conditional Analysis:** Returns conditioned on prior regime
2. **Rolling Windows:** Test stability of regime classification over time
3. **Cost Analysis:** Model realistic transaction costs for regime switching
4. **Machine Learning:** Alternative regime classification methods (e.g., HMM, GARCH)
5. **Multivariate:** Correlations across international indices
6. **Data Update:** Extend historical data from 2010 to 2025
