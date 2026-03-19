import { useState, useEffect, useMemo } from 'react';
import Plot from 'react-plotly.js';
import { fetchMultiIndex } from '../services/api';
import './MultiIndex.css';

/** Format a decimal as a percentage string (e.g. 0.051 → "5.1%") */
const pct = (v) => (v != null ? `${(v * 100).toFixed(1)}%` : '—');

/** Format drawdown (already negative decimal) as a percentage */
const ddPct = (v) => (v != null ? `${(v * 100).toFixed(0)}%` : '—');

/** Derive period string from start_date / end_date (e.g. "1928–2025") */
const periodLabel = (start, end) => {
  if (!start || !end) return '—';
  return `${start.slice(0, 4)}–${end.slice(0, 4)}`;
};

/** Column definitions for the sortable table */
const COLUMNS = [
  { key: 'name',               label: 'Index',         fmt: (v) => v },
  { key: '_period',            label: 'Period',         fmt: (v) => v },
  { key: 'cagr_full',         label: 'CAGR (Full)',    fmt: pct,        numeric: true },
  { key: 'cagr_pre',          label: 'CAGR (Pre)',     fmt: pct,        numeric: true },
  { key: 'cagr_post',         label: 'CAGR (Post)',    fmt: pct,        numeric: true },
  { key: 'kurtosis_full',     label: 'Kurtosis',       fmt: (v) => v != null ? v.toFixed(1) : '—', numeric: true },
  { key: 'clustering_pct_full', label: 'Clustering %', fmt: (v) => v != null ? `${v.toFixed(1)}%` : '—', numeric: true },
  { key: 'tf_max_drawdown',   label: 'Strategy DD',    fmt: ddPct,      numeric: true },
  { key: 'bh_max_drawdown',   label: 'Buy-Hold DD',    fmt: ddPct,      numeric: true },
];

/** Return a CSS class for color-coding a metric value */
const cellClass = (key, row) => {
  if (key === 'clustering_pct_full') {
    return row[key] != null && row[key] > 60 ? 'cell-green' : '';
  }
  if (key === 'kurtosis_full') {
    return row[key] != null && row[key] > 3 ? 'cell-green' : '';
  }
  if (key === 'tf_max_drawdown') {
    // Strategy DD is better (less negative) than buy-hold DD
    if (row.tf_max_drawdown != null && row.bh_max_drawdown != null) {
      return row.tf_max_drawdown > row.bh_max_drawdown ? 'cell-green' : 'cell-red';
    }
  }
  if (key === 'bh_max_drawdown') {
    if (row.tf_max_drawdown != null && row.bh_max_drawdown != null) {
      return row.bh_max_drawdown < row.tf_max_drawdown ? 'cell-red' : '';
    }
  }
  return '';
};

const SortArrow = ({ active, direction }) => {
  if (!active) return <span className="sort-arrow muted">⇅</span>;
  return (
    <span className="sort-arrow active">
      {direction === 'asc' ? '↑' : '↓'}
    </span>
  );
};

const MultiIndex = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortKey, setSortKey] = useState('cagr_full');
  const [sortDir, setSortDir] = useState('desc');

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const resp = await fetchMultiIndex();
      setData(resp);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  /* Augment each index row with a derived _period field */
  const indices = useMemo(() => {
    if (!data?.indices) return [];
    return data.indices.map((idx) => ({
      ...idx,
      _period: periodLabel(idx.start_date, idx.end_date),
    }));
  }, [data]);

  /* Sorted rows */
  const sorted = useMemo(() => {
    const col = COLUMNS.find((c) => c.key === sortKey);
    return [...indices].sort((a, b) => {
      let va = a[sortKey];
      let vb = b[sortKey];
      // Treat nulls as the "worst" value
      if (va == null) return 1;
      if (vb == null) return -1;
      if (!col?.numeric) {
        va = String(va).toLowerCase();
        vb = String(vb).toLowerCase();
      }
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [indices, sortKey, sortDir]);

  /* Summary stats */
  const clusteringCount = indices.filter(
    (i) => i.clustering_pct_full != null && i.clustering_pct_full > 60
  ).length;

  const avgKurtosis =
    indices.length > 0
      ? (
          indices.reduce((s, i) => s + (i.kurtosis_full ?? 0), 0) /
          indices.filter((i) => i.kurtosis_full != null).length
        ).toFixed(1)
      : '—';

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  /* ── Charts data ────────────────────────────────── */

  /* CAGR comparison — sorted by full-period CAGR ascending so largest is on top */
  const cagrSorted = useMemo(
    () => [...indices].sort((a, b) => (a.cagr_full ?? 0) - (b.cagr_full ?? 0)),
    [indices]
  );

  const cagrPreTrace = {
    y: cagrSorted.map((i) => i.name),
    x: cagrSorted.map((i) => (i.cagr_pre != null ? i.cagr_pre * 100 : null)),
    type: 'bar',
    orientation: 'h',
    name: `Pre-${data?.split_date?.slice(0, 4) ?? '2011'}`,
    marker: { color: '#3b82f6' },
    hovertemplate: '%{y}<br>CAGR: %{x:.1f}%<extra>Pre</extra>',
  };

  const cagrPostTrace = {
    y: cagrSorted.map((i) => i.name),
    x: cagrSorted.map((i) => (i.cagr_post != null ? i.cagr_post * 100 : null)),
    type: 'bar',
    orientation: 'h',
    name: `Post-${data?.split_date?.slice(0, 4) ?? '2011'}`,
    marker: { color: '#22c55e' },
    hovertemplate: '%{y}<br>CAGR: %{x:.1f}%<extra>Post</extra>',
  };

  const cagrLayout = {
    barmode: 'group',
    height: Math.max(400, indices.length * 50),
    margin: { l: 140, r: 30, t: 40, b: 50 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: '#e0e6ed', size: 12 },
    xaxis: {
      title: { text: 'CAGR (%)', font: { color: '#8896ab' } },
      gridcolor: '#1e293b',
      zerolinecolor: '#1e293b',
      ticksuffix: '%',
    },
    yaxis: {
      automargin: true,
      tickfont: { size: 12 },
    },
    legend: {
      orientation: 'h',
      y: 1.06,
      x: 0.5,
      xanchor: 'center',
      font: { color: '#8896ab' },
    },
  };

  /* Kurtosis bar chart */
  const kurtosisSorted = useMemo(
    () =>
      [...indices]
        .filter((i) => i.kurtosis_full != null)
        .sort((a, b) => b.kurtosis_full - a.kurtosis_full),
    [indices]
  );

  const kurtosisTrace = {
    x: kurtosisSorted.map((i) => i.name),
    y: kurtosisSorted.map((i) => i.kurtosis_full),
    type: 'bar',
    marker: {
      color: kurtosisSorted.map((i) =>
        i.kurtosis_full > 3 ? '#22c55e' : '#ef4444'
      ),
    },
    hovertemplate: '%{x}<br>Excess Kurtosis: %{y:.1f}<extra></extra>',
  };

  const kurtosisLayout = {
    height: 400,
    margin: { l: 60, r: 30, t: 40, b: 100 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: '#e0e6ed', size: 12 },
    xaxis: {
      tickangle: -40,
      tickfont: { size: 11 },
    },
    yaxis: {
      title: { text: 'Excess Kurtosis', font: { color: '#8896ab' } },
      gridcolor: '#1e293b',
      zerolinecolor: '#ef4444',
      zerolinewidth: 2,
    },
    shapes: [
      {
        type: 'line',
        x0: -0.5,
        x1: kurtosisSorted.length - 0.5,
        y0: 0,
        y1: 0,
        line: { color: '#ef4444', width: 2, dash: 'dash' },
      },
    ],
    annotations: [
      {
        x: kurtosisSorted.length - 1,
        y: 0,
        text: 'Normal (0)',
        showarrow: false,
        font: { color: '#ef4444', size: 11 },
        yshift: -14,
        xanchor: 'right',
      },
    ],
  };

  /* ── Loading state ───────────────────────────────── */
  if (loading) {
    return (
      <div className="multi-index">
        <div className="mi-loading">
          <div className="spinner" />
          <p>Loading global index data…</p>
        </div>
      </div>
    );
  }

  /* ── Error state ─────────────────────────────────── */
  if (error) {
    return (
      <div className="multi-index">
        <div className="mi-error">
          <p>Failed to load data: {error}</p>
          <button className="retry-btn" onClick={loadData}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  /* ── Render ──────────────────────────────────────── */
  return (
    <div className="multi-index">
      {/* 1. Page Header */}
      <header className="mi-header">
        <p className="mi-eyebrow">Faber 2011 · Cross-Market Validation</p>
        <h1>Global Evidence: 12 Indices, One Conclusion</h1>
        <p className="mi-subtitle">
          Fat tails and outlier clustering are not unique to the S&amp;P 500 —
          they appear in every major market we tested.
        </p>
      </header>

      {/* 2. Summary Bar */}
      <section className="mi-summary">
        <div className="summary-card">
          <span className="summary-value accent-green">{clusteringCount} of {indices.length}</span>
          <span className="summary-label">indices show &gt;60% clustering</span>
        </div>
        <div className="summary-card">
          <span className="summary-value">{avgKurtosis}</span>
          <span className="summary-label">average excess kurtosis</span>
        </div>
        <div className="summary-card">
          <span className="summary-value accent-green">
            {indices.filter(
              (i) =>
                i.tf_max_drawdown != null &&
                i.bh_max_drawdown != null &&
                i.tf_max_drawdown > i.bh_max_drawdown
            ).length}{' '}
            of {indices.length}
          </span>
          <span className="summary-label">trend strategy beats buy-hold DD</span>
        </div>
      </section>

      {/* 3. Comparison Table */}
      <section className="mi-table-section">
        <h2>Index Comparison</h2>
        <div className="mi-table-wrapper">
          <table className="mi-table">
            <thead>
              <tr>
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className="sortable"
                  >
                    {col.label}
                    <SortArrow
                      active={sortKey === col.key}
                      direction={sortDir}
                    />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr key={row.ticker}>
                  {COLUMNS.map((col) => (
                    <td
                      key={col.key}
                      className={cellClass(col.key, row)}
                    >
                      {col.fmt(row[col.key])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* 4. CAGR Comparison Chart */}
      <section className="mi-chart-section">
        <h2>CAGR Comparison</h2>
        <p className="section-subtitle">
          Pre- vs Post-{data?.split_date?.slice(0, 4) ?? '2011'} compound
          annual growth across all indices
        </p>
        <div className="mi-chart-card">
          <Plot
            data={[cagrPreTrace, cagrPostTrace]}
            layout={cagrLayout}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </div>
      </section>

      {/* 5. Kurtosis Chart */}
      <section className="mi-chart-section">
        <h2>Excess Kurtosis by Index</h2>
        <p className="section-subtitle">
          All indices well above 0 — confirming fat-tailed returns are a
          universal market phenomenon
        </p>
        <div className="mi-chart-card">
          <Plot
            data={[kurtosisTrace]}
            layout={kurtosisLayout}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </div>
      </section>
    </div>
  );
};

export default MultiIndex;
