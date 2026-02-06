import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { fetchChartData, fetchAnalysis, fetchTickers } from '../services/api';
import MarketSelector from '../components/MarketSelector';
import TimeSeriesChart from '../components/TimeSeriesChart';
import HistogramChart from '../components/HistogramChart';
import RegimeChart from '../components/RegimeChart';
import ScenarioChart from '../components/ScenarioChart';
import './Analysis.css';

const Analysis = () => {
  const { ticker: urlTicker } = useParams();
  const [selectedTicker, setSelectedTicker] = useState(urlTicker || 'sp500');
  const [tickers, setTickers] = useState([]);
  const [chartData, setChartData] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadTickers = async () => {
      try {
        const data = await fetchTickers();
        setTickers(data);
      } catch (err) {
        console.error('Error loading tickers:', err);
      }
    };
    loadTickers();
  }, []);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [charts, analysis] = await Promise.all([
          fetchChartData(selectedTicker),
          fetchAnalysis(selectedTicker),
        ]);
        setChartData(charts);
        setAnalysisData(analysis);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (selectedTicker) {
      loadData();
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
    return <div className="error">Error loading data. Is the API server running? ({error})</div>;
  }

  if (!chartData) {
    return <div className="error">No analysis data available</div>;
  }

  // Transform chart data for components
  const timeSeriesData = chartData.returns.map(d => ({
    date: d.date,
    return: d.ret,
    is_outlier: d.is_outlier,
  }));

  const regimeData = chartData.returns
    .filter(d => d.regime !== null)
    .map(d => ({
      date: d.date,
      return: d.ret,
      regime: d.regime,
    }));

  const histogramData = {
    bins: chartData.histogram.map(h => h.bin_center),
    frequencies: chartData.histogram.map(h => h.count),
    normal_pdf: chartData.histogram.map(h => h.normal_expected),
  };

  const scenarioData = chartData.scenario_impacts;

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
          <TimeSeriesChart data={timeSeriesData} />
          <p className="chart-description">
            Daily returns with outliers (top/bottom 1%) highlighted in orange.
            Extreme days are rare but visually prominent.
          </p>
        </div>

        <div className="chart-card">
          <h2>Return Distribution</h2>
          <HistogramChart data={histogramData} />
          <p className="chart-description">
            Actual distribution (blue bars) compared to normal distribution (orange line).
            Fat tails indicate higher probability of extreme events than normal distribution predicts.
          </p>
        </div>

        <div className="chart-card">
          <h2>Returns by Market Regime</h2>
          <RegimeChart data={regimeData} />
          <p className="chart-description">
            Green: uptrend (price above 200-day MA). Red: downtrend (price below 200-day MA).
            Outliers cluster during downtrends.
          </p>
        </div>

        <div className="chart-card">
          <h2>Impact of Missing Best Days</h2>
          <ScenarioChart scenarios={scenarioData} />
          <p className="chart-description">
            Missing just a handful of the best days significantly reduces long-term returns.
            This demonstrates the outsized impact of extreme positive days.
          </p>
        </div>
      </section>

      {analysisData && (
        <section className="stats-summary">
          <h2>Outlier Statistics</h2>
          <div className="stats-grid">
            {analysisData.outlier_stats.map((stats) => (
              <div key={stats.quantile} className="stat-card">
                <h3>Quantile {(stats.quantile * 100).toFixed(1)}%</h3>
                <div className="stat-details">
                  <div className="stat-row">
                    <span>Lower Threshold:</span>
                    <span>{(stats.threshold_low * 100).toFixed(2)}%</span>
                  </div>
                  <div className="stat-row">
                    <span>Upper Threshold:</span>
                    <span>{(stats.threshold_high * 100).toFixed(2)}%</span>
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

          <h2>Regime Performance</h2>
          <div className="stats-grid">
            {analysisData.regime_performance.map((regime) => (
              <div key={regime.regime} className="stat-card">
                <h3>{regime.regime === 'uptrend' ? 'Uptrend' : 'Downtrend'}</h3>
                <div className="stat-details">
                  <div className="stat-row">
                    <span>Trading Days:</span>
                    <span>{regime.trading_days.toLocaleString()}</span>
                  </div>
                  <div className="stat-row">
                    <span>Annualized Return:</span>
                    <span>{(regime.annualized_return * 100).toFixed(2)}%</span>
                  </div>
                  <div className="stat-row">
                    <span>Sharpe Ratio:</span>
                    <span>{regime.sharpe_ratio.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

export default Analysis;
