/** Static asset base path (Vite public base URL, trailing slash stripped). */
const BASE = import.meta.env.BASE_URL.replace(/\/$/, '');

/**
 * Live API base URL. Defaults to same-origin ('') so requests go to the
 * hosting server.  Override with VITE_API_BASE env var for development
 * against a remote FastAPI instance (e.g. "http://localhost:8000").
 */
const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Fetch with error handling.  Tries the primary URL first; if a fallback
 * is provided and the primary fails, retries against the fallback.
 */
async function fetchWithFallback(primaryUrl, fallbackUrl, label) {
  let response = await fetch(primaryUrl);
  if (response.ok) return response.json();

  if (fallbackUrl) {
    response = await fetch(fallbackUrl);
    if (response.ok) return response.json();
  }

  throw new Error(`Failed to fetch ${label}: ${response.status} ${response.statusText}`);
}

// ---------------------------------------------------------------------------
// Existing v0.1 / v0.2 functions (static JSON data)
// ---------------------------------------------------------------------------

/**
 * Fetch validation status (last-run timestamp and claim verdicts).
 * Returns { last_run, last_data_refresh, indices } or null if not available.
 */
export async function fetchValidationStatus() {
  try {
    const response = await fetch(`${BASE}/data/validation_status.json`);
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

/**
 * Fetch list of available tickers.
 * Returns array of { ticker_code, ticker_symbol, start_date, end_date }.
 */
export async function fetchTickers() {
  const response = await fetch(`${BASE}/data/tickers.json`);
  if (!response.ok) throw new Error(`Failed to fetch tickers: ${response.status}`);
  const data = await response.json();
  return data.tickers;
}

/**
 * Fetch validation results (Faber's 4 claims) for a ticker.
 * Returns claims array shaped for ClaimCard component.
 */
export async function fetchClaims(ticker = 'sp500') {
  const response = await fetch(`${BASE}/data/${ticker}/validation.json`);
  if (!response.ok) throw new Error(`Failed to fetch claims for ${ticker}: ${response.status}`);
  const data = await response.json();

  const claimMeta = [
    { id: 1, title: 'Fat-tailed Returns', description: 'Market returns exhibit significant fat tails (excess kurtosis)' },
    { id: 2, title: 'Outsized Impact of Extreme Days', description: 'A small number of extreme days have disproportionate impact on long-term returns' },
    { id: 3, title: 'Outliers Cluster in Downtrends', description: 'Extreme days occur disproportionately during bear markets' },
    { id: 4, title: 'Trend Following Reduces Drawdowns', description: 'Simple moving average strategies help avoid worst volatility periods' },
  ];

  return data.claim_details.map((claim, i) => {
    const meta = claimMeta[i] || {};
    const details = claim.details || {};

    let metrics = {};
    if (i === 0) {
      metrics = {
        excess_kurtosis: details.excess_kurtosis,
        jarque_bera_stat: details.jb_statistic,
        p_value: details.jb_p_value,
      };
    } else if (i === 1) {
      const scenarios = details.scenarios || [];
      const row10 = scenarios.find(s => s.n_days === 10);
      metrics = {
        days_missed: 10,
        cagr_impact_pct: row10 ? (row10.impact_miss_best * 100).toFixed(2) : null,
      };
    } else if (i === 2) {
      metrics = {
        outliers_in_downtrend_pct: details.main_case_pct_downtrend,
        chi_squared_p_value: details.main_case_p_value,
        robust_count: details.robust_count,
      };
    } else if (i === 3) {
      const main = details.main_case_200dma || {};
      metrics = {
        buyhold_max_drawdown_pct: main.buy_hold_max_drawdown ? (main.buy_hold_max_drawdown * 100).toFixed(1) : null,
        strategy_max_drawdown_pct: main.strategy_max_drawdown ? (main.strategy_max_drawdown * 100).toFixed(1) : null,
        buyhold_sharpe: main.buy_hold_sharpe,
        strategy_sharpe: main.strategy_sharpe,
      };
    }

    return {
      id: meta.id,
      title: meta.title,
      description: meta.description,
      verdict: claim.verdict,
      metrics,
    };
  });
}

/**
 * Fetch chart-ready data for a ticker.
 * Returns { returns, histogram, scenario_impacts }.
 */
export async function fetchChartData(ticker = 'sp500') {
  const response = await fetch(`${BASE}/data/${ticker}/chart-data.json`);
  if (!response.ok) throw new Error(`Failed to fetch chart data for ${ticker}: ${response.status}`);
  return response.json();
}

/**
 * Fetch analysis results (outlier stats, scenarios, regime performance).
 */
export async function fetchAnalysis(ticker = 'sp500') {
  const response = await fetch(`${BASE}/data/${ticker}/analysis.json`);
  if (!response.ok) throw new Error(`Failed to fetch analysis for ${ticker}: ${response.status}`);
  return response.json();
}

// ---------------------------------------------------------------------------
// New v0.3 functions (live API with static-JSON fallback)
// ---------------------------------------------------------------------------

/**
 * Fetch period-comparison data for a ticker split at a given date.
 *
 * Live:   GET {API_BASE}/api/period-comparison/{ticker}?split_date=...
 * Static: GET {BASE}/data/{ticker}/period-comparison.json
 *
 * @param {string} ticker   - Yahoo Finance ticker (e.g. "^GSPC")
 * @param {string} splitDate - ISO date string (e.g. "2011-01-01")
 * @returns {Promise<object>} { ticker, split_date, periods }
 */
export async function fetchPeriodComparison(ticker, splitDate = '2011-01-01') {
  const params = new URLSearchParams({ split_date: splitDate });
  const primaryUrl = `${API_BASE}/api/period-comparison/${encodeURIComponent(ticker)}?${params}`;
  const fallbackUrl = `${BASE}/data/${encodeURIComponent(ticker)}/period-comparison.json`;
  return fetchWithFallback(primaryUrl, fallbackUrl, `period comparison for ${ticker}`);
}

/**
 * Fetch CAGR-matrix data showing impact of removing best/worst N days.
 *
 * Live:   GET {API_BASE}/api/cagr-matrix/{ticker}?split_date=...&n_days=...
 * Static: GET {BASE}/data/{ticker}/cagr-matrix.json
 *
 * @param {string} ticker    - Yahoo Finance ticker
 * @param {string} splitDate - ISO date string
 * @param {number} [nDays=10] - Number of best/worst days to remove
 * @returns {Promise<object>} { ticker, split_date, n_days, rows }
 */
export async function fetchCagrMatrix(ticker, splitDate = '2011-01-01', nDays = 10) {
  const params = new URLSearchParams({ split_date: splitDate, n_days: String(nDays) });
  const primaryUrl = `${API_BASE}/api/cagr-matrix/${encodeURIComponent(ticker)}?${params}`;
  const fallbackUrl = `${BASE}/data/${encodeURIComponent(ticker)}/cagr-matrix.json`;
  return fetchWithFallback(primaryUrl, fallbackUrl, `CAGR matrix for ${ticker}`);
}

/**
 * Fetch multi-index comparison across all supported indices.
 *
 * Live:   GET {API_BASE}/api/multi-index?split_date=...
 * Static: GET {BASE}/data/multi-index.json
 *
 * @param {string} splitDate - ISO date string
 * @returns {Promise<object>} { split_date, indices }
 */
export async function fetchMultiIndex(splitDate = '2011-01-01') {
  const params = new URLSearchParams({ split_date: splitDate });
  const primaryUrl = `${API_BASE}/api/multi-index?${params}`;
  const fallbackUrl = `${BASE}/data/multi-index.json`;
  return fetchWithFallback(primaryUrl, fallbackUrl, 'multi-index comparison');
}
