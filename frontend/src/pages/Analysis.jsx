import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { fetchAnalysis, fetchTickers, fetchClaims } from '../services/api';
import MarketSelector from '../components/MarketSelector';
import TimeSeriesChart from '../components/TimeSeriesChart';
import HistogramChart from '../components/HistogramChart';
import RegimeChart from '../components/RegimeChart';
import ScenarioChart from '../components/ScenarioChart';
import './Analysis.css';

const Analysis = () => {
  const { ticker: urlTicker } = useParams();
  const [selectedTicker, setSelectedTicker] = useState(urlTicker || '^GSPC');
  const [tickers, setTickers] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [tickersData, claimsData] = await Promise.all([
          fetchTickers(),
          fetchClaims()
        ]);
        setTickers(tickersData);
        setClaims(claimsData);
      } catch (err) {
        console.error('Error loading initial data:', err);
      }
    };

    loadInitialData();
  }, []);

  useEffect(() => {
    const loadAnalysis = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchAnalysis(selectedTicker);
        setAnalysis(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (selectedTicker) {
      loadAnalysis();
    }
  }, [selectedTicker]);

  const handleTickerChange = (newTicker) => {
    setSelectedTicker(newTicker);
    window.history.pushState({}, '', `/analysis/${newTicker}`);
  };

  if (loading) {
    return <div className="loading">Loading analysis...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  if (!analysis) {
    return <div className="error">No analysis data available</div>;
  }

  const claim2 = claims.find(c => c.id === 2);

  return (
    <div className="analysis-page">
      <header className="page-header">
        <h1>Market Analysis Dashboard</h1>
        <MarketSelector
          tickers={tickers}
          selectedTicker={selectedTicker}
          onTickerChange={handleTickerChange}
        />
      </header>

      <section className="charts-section">
        <div className="chart-card">
          <h2>Daily Returns Time Series</h2>
          <TimeSeriesChart data={analysis.returns_timeseries} />
          <p className="chart-description">
            Daily returns with outliers (top/bottom 1%) highlighted in orange.
            Extreme days are rare but visually prominent.
          </p>
        </div>

        <div className="chart-card">
          <h2>Return Distribution</h2>
          <HistogramChart data={analysis.histogram_data} />
          <p className="chart-description">
            Actual distribution (blue bars) compared to normal distribution (orange line).
            Fat tails indicate higher probability of extreme events than normal distribution predicts.
          </p>
        </div>

        <div className="chart-card">
          <h2>Returns by Market Regime</h2>
          <RegimeChart data={analysis.regime_data} />
          <p className="chart-description">
            Green: uptrend (price above 200-day MA). Red: downtrend (price below 200-day MA).
            Outliers cluster during downtrends.
          </p>
        </div>

        <div className="chart-card">
          <h2>Impact of Missing Best Days</h2>
          <ScenarioChart
            data={analysis.scenario_returns}
            scenarios={claim2?.metrics?.scenarios}
          />
          <p className="chart-description">
            Missing just a handful of the best days significantly reduces long-term returns.
            This demonstrates the outsized impact of extreme positive days.
          </p>
        </div>
      </section>

      <section className="stats-summary">
        <h2>Outlier Statistics</h2>
        <div className="stats-grid">
          {analysis.outlier_stats && Object.entries(analysis.outlier_stats).map(([key, stats]) => (
            <div key={key} className="stat-card">
              <h3>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</h3>
              <div className="stat-details">
                <div className="stat-row">
                  <span>Lower Threshold:</span>
                  <span>{stats.threshold_low?.toFixed(2)}%</span>
                </div>
                <div className="stat-row">
                  <span>Upper Threshold:</span>
                  <span>{stats.threshold_high?.toFixed(2)}%</span>
                </div>
                <div className="stat-row">
                  <span>Extreme Negative Days:</span>
                  <span>{stats.count_low}</span>
                </div>
                <div className="stat-row">
                  <span>Extreme Positive Days:</span>
                  <span>{stats.count_high}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default Analysis;
