import React, { useState, useEffect, useMemo } from 'react';
import Plot from 'react-plotly.js';
import { fetchPeriodComparison, fetchCagrMatrix } from '../services/api';
import './PeriodComparison.css';

const DEFAULT_TICKER = 'sp500';
const DEFAULT_SPLIT_DATE = '2011-01-01';

const CLAIM_LABELS = {
  fat_tails: 'Fat Tails',
  outsized_influence: 'Outsized Influence',
  clustering: 'Bear Market Clustering',
  trend_following: 'Trend Following',
};

const CLAIM_KEYS = ['fat_tails', 'outsized_influence', 'clustering', 'trend_following'];

/** Format a number to fixed decimals, returning '—' for null/undefined. */
function fmt(value, decimals = 1) {
  if (value == null || Number.isNaN(value)) return '—';
  return Number(value).toFixed(decimals);
}

/** Format a percentage value (already in 0–100 range or as a decimal). */
function pct(value, decimals = 1, scale100 = false) {
  if (value == null || Number.isNaN(value)) return '—';
  const v = scale100 ? value * 100 : value;
  return `${v >= 0 ? '+' : ''}${Number(v).toFixed(decimals)}%`;
}

/** Extract a human-readable metric summary for a claim. */
function claimSummary(claimKey, data) {
  if (!data) return '';
  const m = data.metrics || {};

  switch (claimKey) {
    case 'fat_tails':
      return m.excess_kurtosis != null
        ? `kurtosis: ${fmt(m.excess_kurtosis, 1)}`
        : '';
    case 'outsized_influence':
      if (m.cagr_impact_miss_best != null) {
        return `miss 10 → ${pct(m.cagr_impact_miss_best, 1, true)}`;
      }
      if (m.impact_miss_best != null) {
        return `miss 10 → ${pct(m.impact_miss_best, 1, true)}`;
      }
      return '';
    case 'clustering':
      if (m.pct_downtrend != null) {
        return `${fmt(m.pct_downtrend, 1)}% in downtrends`;
      }
      if (m.outliers_in_downtrend_pct != null) {
        return `${fmt(m.outliers_in_downtrend_pct, 1)}% in downtrends`;
      }
      return '';
    case 'trend_following':
      if (m.strategy_max_drawdown != null && m.buy_hold_max_drawdown != null) {
        return `drawdown: ${fmt(m.strategy_max_drawdown * 100, 0)}% vs ${fmt(m.buy_hold_max_drawdown * 100, 0)}%`;
      }
      if (m.strategy_drawdown != null && m.buyhold_drawdown != null) {
        return `drawdown: ${fmt(m.strategy_drawdown, 0)}% vs ${fmt(m.buyhold_drawdown, 0)}%`;
      }
      return '';
    default:
      return '';
  }
}

const PeriodComparison = () => {
  const [splitDate, setSplitDate] = useState(DEFAULT_SPLIT_DATE);
  const [comparisonData, setComparisonData] = useState(null);
  const [cagrData, setCagrData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [comparison, cagr] = await Promise.all([
          fetchPeriodComparison(DEFAULT_TICKER, splitDate),
          fetchCagrMatrix(DEFAULT_TICKER, splitDate),
        ]);
        setComparisonData(comparison);
        setCagrData(cagr);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [splitDate]);

  /** Map period key → period data for easy lookup. */
  const periodMap = useMemo(() => {
    if (!comparisonData?.periods) return {};
    const map = {};
    for (const p of comparisonData.periods) {
      map[p.period] = p;
    }
    return map;
  }, [comparisonData]);

  const periodOrder = ['pre', 'post', 'full'];
  const periodLabels = useMemo(() => {
    const labels = { pre: 'Pre-2011', post: 'Post-2011', full: 'Full Period' };
    if (comparisonData?.periods) {
      for (const p of comparisonData.periods) {
        if (p.period_label) labels[p.period] = p.period_label;
      }
    }
    return labels;
  }, [comparisonData]);

  /** Build Plotly traces for the CAGR chart. */
  const cagrChart = useMemo(() => {
    if (!cagrData?.rows) return null;

    const rows = cagrData.rows;
    const labels = rows.map(r => r.period_label || r.period);
    const allDays = rows.map(r => (r.cagr_all != null ? r.cagr_all * 100 : 0));
    const missBest = rows.map(r => (r.cagr_miss_best != null ? r.cagr_miss_best * 100 : 0));
    const missWorst = rows.map(r => (r.cagr_miss_worst != null ? r.cagr_miss_worst * 100 : 0));

    return {
      data: [
        {
          x: labels,
          y: allDays,
          name: 'All Days',
          type: 'bar',
          marker: { color: '#3b82f6' },
          hovertemplate: '%{x}<br>CAGR: %{y:.2f}%<extra>All Days</extra>',
        },
        {
          x: labels,
          y: missBest,
          name: 'Miss Best 10',
          type: 'bar',
          marker: { color: '#ef4444' },
          hovertemplate: '%{x}<br>CAGR: %{y:.2f}%<extra>Miss Best 10</extra>',
        },
        {
          x: labels,
          y: missWorst,
          name: 'Miss Worst 10',
          type: 'bar',
          marker: { color: '#22c55e' },
          hovertemplate: '%{x}<br>CAGR: %{y:.2f}%<extra>Miss Worst 10</extra>',
        },
      ],
      layout: {
        barmode: 'group',
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { color: '#e0e6ed', family: 'Inter, system-ui, sans-serif' },
        title: {
          text: 'CAGR by Period & Scenario',
          font: { size: 18, color: '#e0e6ed' },
        },
        xaxis: {
          gridcolor: 'rgba(255,255,255,0.06)',
          tickfont: { size: 13 },
        },
        yaxis: {
          title: 'CAGR (%)',
          gridcolor: 'rgba(255,255,255,0.06)',
          zeroline: true,
          zerolinecolor: 'rgba(255,255,255,0.15)',
          ticksuffix: '%',
          tickfont: { size: 12 },
        },
        legend: {
          orientation: 'h',
          y: -0.2,
          x: 0.5,
          xanchor: 'center',
          font: { size: 13 },
        },
        margin: { t: 50, b: 60, l: 60, r: 20 },
        hoverlabel: {
          bgcolor: '#1e293b',
          font: { color: '#e0e6ed' },
        },
      },
      config: {
        displayModeBar: false,
        responsive: true,
      },
    };
  }, [cagrData]);

  /** Determine overall takeaway. */
  const takeaway = useMemo(() => {
    if (!comparisonData?.periods) return null;
    const post = periodMap.post;
    if (!post) return null;

    let confirmed = 0;
    let total = 0;
    for (const key of CLAIM_KEYS) {
      const claim = post[key];
      if (claim) {
        total++;
        if (claim.verdict === 'CONFIRMED') confirmed++;
      }
    }

    if (total === 0) return null;
    const ratio = confirmed / total;

    if (ratio === 1) {
      return {
        icon: '✅',
        headline: 'All claims hold in the modern era.',
        body: `All ${total} of Faber's claims remain statistically confirmed in post-${splitDate.slice(0, 4)} data. The thesis is robust across time periods.`,
        tone: 'positive',
      };
    }
    if (ratio >= 0.5) {
      return {
        icon: '⚠️',
        headline: 'Most claims hold, with some caveats.',
        body: `${confirmed} of ${total} claims are confirmed post-${splitDate.slice(0, 4)}. The core thesis largely persists, though some effects may have weakened.`,
        tone: 'mixed',
      };
    }
    return {
      icon: '❌',
      headline: 'The thesis weakens in the modern era.',
      body: `Only ${confirmed} of ${total} claims are confirmed post-${splitDate.slice(0, 4)}. Market dynamics may have shifted since the original study.`,
      tone: 'negative',
    };
  }, [comparisonData, periodMap, splitDate]);

  // ---- Render ----

  if (loading) {
    return (
      <div className="pc-page">
        <div className="pc-loading">
          <div className="pc-spinner" />
          <span>Loading period comparison…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="pc-page">
        <div className="pc-error">
          Error loading data. Is the API server running?
          <span className="pc-error-detail">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="pc-page">
      {/* ---- Header ---- */}
      <header className="pc-header">
        <h1>Period Comparison: Does It Still Work?</h1>
        <p className="pc-subtitle">
          Faber published his paper in 2011. We split the data at a configurable date
          to test whether each claim holds <em>before</em>, <em>after</em>, and across the
          <em> full</em> sample.
        </p>
      </header>

      {/* ---- Period selector ---- */}
      <div className="pc-controls">
        <label className="pc-date-label" htmlFor="split-date">
          Split Date
        </label>
        <input
          id="split-date"
          className="pc-date-input"
          type="date"
          value={splitDate}
          onChange={(e) => setSplitDate(e.target.value)}
        />
      </div>

      {/* ---- Claims comparison grid ---- */}
      <section className="pc-claims-section">
        <h2 className="pc-section-title">Claims Comparison</h2>

        {/* Desktop table */}
        <div className="pc-table-wrapper">
          <table className="pc-table">
            <thead>
              <tr>
                <th className="pc-th-claim">Claim</th>
                {periodOrder.map((key) => (
                  <th key={key}>{periodLabels[key]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {CLAIM_KEYS.map((claimKey) => (
                <tr key={claimKey}>
                  <td className="pc-td-claim">{CLAIM_LABELS[claimKey]}</td>
                  {periodOrder.map((pKey) => {
                    const period = periodMap[pKey];
                    const claim = period?.[claimKey];
                    const verdict = claim?.verdict;
                    const confirmed = verdict === 'CONFIRMED';
                    const summary = claimSummary(claimKey, claim);
                    return (
                      <td
                        key={pKey}
                        className={`pc-td-result ${confirmed ? 'pc-confirmed' : 'pc-not-confirmed'}`}
                      >
                        <span className="pc-verdict-icon">{confirmed ? '✅' : '❌'}</span>
                        <span className="pc-verdict-text">
                          {confirmed ? 'CONFIRMED' : 'NOT CONFIRMED'}
                        </span>
                        {summary && <span className="pc-metric-detail">({summary})</span>}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mobile cards (visible on small screens) */}
        <div className="pc-mobile-cards">
          {CLAIM_KEYS.map((claimKey) => (
            <div key={claimKey} className="pc-mobile-claim-card">
              <h3 className="pc-mobile-claim-title">{CLAIM_LABELS[claimKey]}</h3>
              {periodOrder.map((pKey) => {
                const period = periodMap[pKey];
                const claim = period?.[claimKey];
                const verdict = claim?.verdict;
                const confirmed = verdict === 'CONFIRMED';
                const summary = claimSummary(claimKey, claim);
                return (
                  <div
                    key={pKey}
                    className={`pc-mobile-result ${confirmed ? 'pc-confirmed' : 'pc-not-confirmed'}`}
                  >
                    <span className="pc-mobile-period">{periodLabels[pKey]}</span>
                    <span className="pc-verdict-icon">{confirmed ? '✅' : '❌'}</span>
                    <span className="pc-verdict-text">
                      {confirmed ? 'CONFIRMED' : 'NOT CONFIRMED'}
                    </span>
                    {summary && <span className="pc-metric-detail">({summary})</span>}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </section>

      {/* ---- CAGR Impact Chart ---- */}
      {cagrChart && (
        <section className="pc-chart-section">
          <h2 className="pc-section-title">CAGR Impact Analysis</h2>
          <div className="pc-chart-card">
            <Plot
              data={cagrChart.data}
              layout={cagrChart.layout}
              config={cagrChart.config}
              useResizeHandler
              style={{ width: '100%', height: '420px' }}
            />
          </div>

          {/* CAGR detail table */}
          {cagrData?.rows && (
            <div className="pc-table-wrapper pc-cagr-table-wrapper">
              <table className="pc-table pc-cagr-table">
                <thead>
                  <tr>
                    <th>Period</th>
                    <th>All Days</th>
                    <th>Miss Best 10</th>
                    <th>Miss Worst 10</th>
                    <th>Impact (Best)</th>
                    <th>Impact (Worst)</th>
                  </tr>
                </thead>
                <tbody>
                  {cagrData.rows.map((row) => (
                    <tr key={row.period}>
                      <td className="pc-td-claim">{row.period_label || row.period}</td>
                      <td>{pct(row.cagr_all, 2, true)}</td>
                      <td>{pct(row.cagr_miss_best, 2, true)}</td>
                      <td>{pct(row.cagr_miss_worst, 2, true)}</td>
                      <td className="pc-impact-negative">
                        {pct(row.impact_miss_best, 2, true)}
                      </td>
                      <td className="pc-impact-positive">
                        {pct(row.impact_miss_worst, 2, true)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* ---- Takeaway ---- */}
      {takeaway && (
        <section className={`pc-takeaway pc-takeaway--${takeaway.tone}`}>
          <span className="pc-takeaway-icon">{takeaway.icon}</span>
          <div className="pc-takeaway-body">
            <h3>{takeaway.headline}</h3>
            <p>{takeaway.body}</p>
          </div>
        </section>
      )}
    </div>
  );
};

export default PeriodComparison;
