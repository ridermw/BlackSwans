import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

/**
 * Fetch list of available tickers from backend.
 * Returns array of { ticker_code, ticker_symbol, start_date, end_date }.
 */
export async function fetchTickers() {
  const response = await api.get('/tickers');
  return response.data.tickers;
}

/**
 * Fetch validation results (Faber's 4 claims) for a ticker.
 * Returns claims array shaped for ClaimCard component.
 */
export async function fetchClaims(ticker = 'sp500') {
  const response = await api.get(`/validation/${ticker}`);
  const data = response.data;

  // Transform backend ValidationResponse into frontend claim cards
  const claimMeta = [
    { id: 1, title: 'Fat-tailed Returns', description: 'Market returns exhibit significant fat tails (excess kurtosis)' },
    { id: 2, title: 'Outsized Impact of Extreme Days', description: 'A small number of extreme days have disproportionate impact on long-term returns' },
    { id: 3, title: 'Outliers Cluster in Downtrends', description: 'Extreme days occur disproportionately during bear markets' },
    { id: 4, title: 'Trend Following Reduces Drawdowns', description: 'Simple moving average strategies help avoid worst volatility periods' },
  ];

  return data.claim_details.map((claim, i) => {
    const meta = claimMeta[i] || {};
    const details = claim.details || {};

    // Extract key metrics per claim
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
  const response = await api.get(`/chart-data/${ticker}`);
  return response.data;
}

/**
 * Fetch analysis results (outlier stats, scenarios, regime performance).
 */
export async function fetchAnalysis(ticker = 'sp500') {
  const response = await api.get(`/analysis/${ticker}`);
  return response.data;
}
