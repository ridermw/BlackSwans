import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

// Mock data based on actual S&P 500 validation results
const MOCK_DATA = {
  claims: [
    {
      id: 1,
      title: 'Fat-tailed Returns',
      description: 'Market returns exhibit significant fat tails (excess kurtosis)',
      verdict: 'CONFIRMED',
      metrics: {
        excess_kurtosis: 17.6,
        jarque_bera_stat: 29847.5,
        p_value: 0.0
      }
    },
    {
      id: 2,
      title: 'Outsized Impact of Extreme Days',
      description: 'A small number of extreme days have disproportionate impact on long-term returns',
      verdict: 'CONFIRMED',
      metrics: {
        days_missed: 10,
        cagr_impact: -1.41,
        scenarios: {
          5: -0.78,
          10: -1.41,
          20: -2.47,
          50: -4.94
        }
      }
    },
    {
      id: 3,
      title: 'Outliers Cluster in Downtrends',
      description: 'Extreme days (both positive and negative) occur disproportionately during bear markets',
      verdict: 'CONFIRMED',
      metrics: {
        outliers_in_downtrend_pct: 70.7,
        chi_squared_stat: 239.8,
        p_value: 1e-52
      }
    },
    {
      id: 4,
      title: 'Trend Following Reduces Drawdowns',
      description: 'Simple moving average strategies help avoid worst volatility periods',
      verdict: 'CONFIRMED',
      metrics: {
        buyhold_max_drawdown: -86.0,
        trend_max_drawdown: -26.0,
        reduction_pct: 69.8
      }
    }
  ],

  tickers: [
    { symbol: '^GSPC', name: 'S&P 500', period: '1928-2025' },
    { symbol: '^DJI', name: 'Dow Jones', period: '1915-2025' },
    { symbol: '^IXIC', name: 'NASDAQ', period: '1971-2025' },
    { symbol: '^FTSE', name: 'FTSE 100', period: '1984-2025' }
  ],

  analysis: {
    '^GSPC': {
      returns_timeseries: generateMockTimeSeries(),
      histogram_data: generateMockHistogram(),
      regime_data: generateMockRegimeData(),
      scenario_returns: {
        all_days: 9.82,
        miss_best_10: 8.41,
        miss_worst_10: 11.23,
        miss_both: 9.82
      },
      outlier_stats: {
        quantile_99: {
          threshold_low: -3.5,
          threshold_high: 3.2,
          count_low: 241,
          count_high: 241
        },
        quantile_999: {
          threshold_low: -6.1,
          threshold_high: 5.8,
          count_low: 24,
          count_high: 24
        }
      }
    }
  }
};

// Generate mock time series data
function generateMockTimeSeries() {
  const data = [];
  const startDate = new Date('1928-01-01');
  const endDate = new Date('2025-01-01');
  let currentDate = new Date(startDate);

  while (currentDate <= endDate) {
    // Skip weekends
    if (currentDate.getDay() !== 0 && currentDate.getDay() !== 6) {
      const dayReturn = (Math.random() - 0.5) * 0.02; // Random return around 0
      const isOutlier = Math.random() < 0.01; // 1% chance of outlier

      data.push({
        date: currentDate.toISOString().split('T')[0],
        return: isOutlier ? dayReturn * 5 : dayReturn,
        is_outlier: isOutlier
      });
    }

    currentDate.setDate(currentDate.getDate() + 1);
  }

  return data;
}

// Generate mock histogram data
function generateMockHistogram() {
  const bins = [];
  const frequencies = [];
  const normal_pdf = [];

  for (let i = -10; i <= 10; i += 0.5) {
    bins.push(i);
    // Create histogram with fat tails
    const freq = Math.exp(-Math.pow(i, 2) / 4) * 1000 * (1 + Math.abs(i) / 20);
    frequencies.push(freq);
    // Normal distribution overlay
    normal_pdf.push(Math.exp(-Math.pow(i, 2) / 2) * 1000);
  }

  return { bins, frequencies, normal_pdf };
}

// Generate mock regime data
function generateMockRegimeData() {
  const data = [];
  const startDate = new Date('1928-01-01');

  for (let i = 0; i < 5000; i++) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + i);

    const regime = Math.random() > 0.4 ? 1 : 0; // 60% uptrend, 40% downtrend
    const returnVal = (Math.random() - 0.5) * 0.03;

    data.push({
      date: date.toISOString().split('T')[0],
      return: returnVal,
      regime: regime
    });
  }

  return data;
}

// API functions with fallback to mock data
export async function fetchClaims() {
  try {
    const response = await axios.get(`${API_BASE_URL}/claims`, { timeout: 2000 });
    return response.data;
  } catch (error) {
    console.warn('API unavailable, using mock data:', error.message);
    return MOCK_DATA.claims;
  }
}

export async function fetchTickers() {
  try {
    const response = await axios.get(`${API_BASE_URL}/tickers`, { timeout: 2000 });
    return response.data;
  } catch (error) {
    console.warn('API unavailable, using mock data:', error.message);
    return MOCK_DATA.tickers;
  }
}

export async function fetchAnalysis(ticker) {
  try {
    const response = await axios.get(`${API_BASE_URL}/analysis/${ticker}`, { timeout: 2000 });
    return response.data;
  } catch (error) {
    console.warn('API unavailable, using mock data:', error.message);
    return MOCK_DATA.analysis[ticker] || MOCK_DATA.analysis['^GSPC'];
  }
}

export async function fetchReturnsTimeSeries(ticker) {
  try {
    const response = await axios.get(`${API_BASE_URL}/returns/${ticker}`, { timeout: 2000 });
    return response.data;
  } catch (error) {
    console.warn('API unavailable, using mock data:', error.message);
    const analysis = MOCK_DATA.analysis[ticker] || MOCK_DATA.analysis['^GSPC'];
    return analysis.returns_timeseries;
  }
}
