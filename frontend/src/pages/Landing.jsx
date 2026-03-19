import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { fetchPeriodComparison, fetchMultiIndex } from '../services/api';
import './Landing.css';

const STAT_CARDS = [
  { value: '4/4', label: 'Claims Confirmed', accent: true },
  { value: '12', label: 'Indices Tested' },
  { value: '97', label: 'Years of Data' },
  { value: '✓', label: 'Post-2011: Still Works', accent: true },
];

const NAV_ITEMS = [
  {
    to: '/period-comparison',
    icon: '📅',
    title: 'Period Comparison',
    desc: 'Pre-2011 vs Post-2011 — see how every claim holds up across the publication boundary.',
    arrow: 'View comparison →',
  },
  {
    to: '/multi-index',
    icon: '🌍',
    title: 'Multi-Index Analysis',
    desc: 'S&P 500, FTSE, DAX, Nikkei, and 8 more — global robustness of Faber\'s thesis.',
    arrow: 'Explore indices →',
  },
  {
    to: '/cagr',
    icon: '📈',
    title: 'CAGR Research',
    desc: 'Compound growth analysis showing the outsized influence of extreme trading days.',
    arrow: 'See research →',
  },
];

/** Format a decimal as a percentage string (e.g. 0.05 → "5.0%") */
const pct = (v) => (v != null ? `${(v * 100).toFixed(1)}%` : '—');

/** Pick CSS class based on verdict string */
const verdictClass = (verdict) =>
  verdict === 'CONFIRMED' ? 'confirmed' : 'rejected';

/**
 * Extract the metrics we need from a single period object.
 * Returns nulls for any missing paths so the table renders gracefully.
 */
const extractRow = (p) => {
  if (!p) return null;
  return {
    label: p.period_label ?? p.period,
    cagr: p.outsized_influence?.metrics?.cagr_all,
    missBest10: p.outsized_influence?.metrics?.impact_miss_best_10,
    missBoth10: p.outsized_influence?.metrics?.impact_miss_both_10,
    kurtosis: p.fat_tails?.metrics?.excess_kurtosis,
    clusterPct: p.clustering?.metrics?.pct_in_downtrend,
    fatTailsVerdict: p.fat_tails?.verdict,
    influenceVerdict: p.outsized_influence?.verdict,
    clusteringVerdict: p.clustering?.verdict,
    trendVerdict: p.trend_following?.verdict,
  };
};

/** Determine the overall verdict across all periods */
const computeOverallVerdict = (periods) => {
  if (!periods?.length) return null;
  const allConfirmed = periods.every((p) =>
    ['fat_tails', 'outsized_influence', 'clustering', 'trend_following'].every(
      (k) => p[k]?.verdict === 'CONFIRMED'
    )
  );
  return allConfirmed ? 'CONFIRMED' : 'MIXED';
};

const Landing = () => {
  const [periodData, setPeriodData] = useState(null);
  const [multiIndexData, setMultiIndexData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [periodResp, multiResp] = await Promise.all([
        fetchPeriodComparison('sp500'),
        fetchMultiIndex(),
      ]);
      setPeriodData(periodResp);
      setMultiIndexData(multiResp);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  /* ── Loading state ───────────────────────────────── */
  if (loading) {
    return (
      <div className="landing">
        <div className="landing-loading">
          <div className="spinner" />
          <p>Loading market data…</p>
        </div>
      </div>
    );
  }

  /* ── Error state ─────────────────────────────────── */
  if (error) {
    return (
      <div className="landing">
        <div className="landing-error">
          <p>Failed to load data: {error}</p>
          <button className="retry-btn" onClick={loadData}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  const periods = periodData?.periods ?? [];
  const rows = periods.map(extractRow).filter(Boolean);
  const overallVerdict = computeOverallVerdict(periods);
  const indexCount = multiIndexData?.indices?.length ?? 12;

  /* ── Render ──────────────────────────────────────── */
  return (
    <div className="landing">
      {/* Hero */}
      <section className="hero">
        <p className="hero-eyebrow">Faber 2011 · Statistical Replication</p>
        <h1>Does Faber's Black Swans Thesis Still&nbsp;Work?</h1>
        <p className="hero-subtitle">
          Rigorous statistical validation across {indexCount} global indices,
          1928–2025
        </p>

        {overallVerdict && (
          <div
            className={`verdict-badge ${overallVerdict === 'CONFIRMED' ? 'confirmed' : 'rejected'}`}
          >
            <span className="badge-icon">
              {overallVerdict === 'CONFIRMED' ? '✅' : '⚠️'}
            </span>
            {overallVerdict === 'CONFIRMED'
              ? 'All Four Claims Confirmed'
              : 'Results Mixed — See Details'}
          </div>
        )}
      </section>

      {/* Key Numbers */}
      <section className="key-numbers">
        <h2>At a Glance</h2>
        <div className="numbers-grid">
          {STAT_CARDS.map((card) => (
            <div className="number-card" key={card.label}>
              <div
                className={`number-value${card.accent ? ' accent-green' : ''}`}
              >
                {card.value}
              </div>
              <div className="number-label">{card.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Split Period Table */}
      {rows.length > 0 && (
        <section className="split-period">
          <h2>Split-Period Comparison</h2>
          <p className="section-subtitle">
            S&amp;P 500 results split at the 2011 publication date
          </p>
          <div className="period-table-wrapper">
            <table className="period-table">
              <thead>
                <tr>
                  <th>Period</th>
                  <th>CAGR</th>
                  <th>Miss 10 Best</th>
                  <th>Miss Both 10</th>
                  <th>Kurtosis</th>
                  <th>Clustering %</th>
                  <th>Fat Tails</th>
                  <th>Influence</th>
                  <th>Clustering</th>
                  <th>Trend</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.label}>
                    <td className="period-label">{r.label}</td>
                    <td className="cell-neutral">{pct(r.cagr)}</td>
                    <td className="cell-neutral">{pct(r.missBest10)}</td>
                    <td className="cell-miss-both">{pct(r.missBoth10)}</td>
                    <td className="cell-neutral">
                      {r.kurtosis != null ? r.kurtosis.toFixed(1) : '—'}
                    </td>
                    <td className="cell-neutral">
                      {r.clusterPct != null ? `${r.clusterPct.toFixed(1)}%` : '—'}
                    </td>
                    <VerdictCell verdict={r.fatTailsVerdict} />
                    <VerdictCell verdict={r.influenceVerdict} />
                    <VerdictCell verdict={r.clusteringVerdict} />
                    <VerdictCell verdict={r.trendVerdict} />
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Navigation Cards */}
      <section className="nav-cards">
        <h2>Explore the Analysis</h2>
        <div className="nav-grid">
          {NAV_ITEMS.map((item) => (
            <Link to={item.to} className="nav-card" key={item.to}>
              <div className="nav-card-icon">{item.icon}</div>
              <h3>{item.title}</h3>
              <p>{item.desc}</p>
              <span className="card-arrow">{item.arrow}</span>
            </Link>
          ))}
        </div>
      </section>

      {/* Disclaimer */}
      <footer className="landing-disclaimer">
        <p>
          This is a research tool, not financial advice. Past performance does
          not guarantee future results. Data sourced from Yahoo Finance and
          validated against Faber's original methodology.
        </p>
      </footer>
    </div>
  );
};

/** Small helper component for verdict table cells */
const VerdictCell = ({ verdict }) => {
  if (!verdict) return <td className="cell-neutral">—</td>;
  return (
    <td>
      <span className={`verdict-chip ${verdictClass(verdict)}`}>
        {verdict}
      </span>
    </td>
  );
};

export default Landing;
