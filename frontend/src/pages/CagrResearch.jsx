import React, { useState, useEffect, useMemo } from 'react';
import Plot from 'react-plotly.js';
import { fetchCagrMatrix, fetchTickers } from '../services/api';
import './CagrResearch.css';

const N_DAYS_OPTIONS = [5, 10, 20, 50];
const DEFAULT_N_DAYS = 10;
const DEFAULT_SPLIT_DATE = '2011-01-01';
const DEFAULT_TICKER = 'sp500';

/** Format a decimal as a percentage string: 0.0512 → "5.12%" */
const fmtPct = (v) => {
  if (v == null) return '—';
  return `${(v * 100).toFixed(2)}%`;
};

/** Format with explicit sign: 0.0141 → "+1.41%", -0.012 → "-1.20%" */
const fmtSignedPct = (v) => {
  if (v == null) return '—';
  const pct = (v * 100).toFixed(2);
  return v >= 0 ? `+${pct}%` : `${pct}%`;
};

const PLOTLY_DARK_LAYOUT = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { color: '#94a3b8', family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' },
  xaxis: { gridcolor: '#1e293b', zerolinecolor: '#334155' },
  yaxis: { gridcolor: '#1e293b', zerolinecolor: '#334155', ticksuffix: '%' },
  margin: { t: 40, r: 20, b: 50, l: 60 },
  legend: { orientation: 'h', y: -0.18, x: 0.5, xanchor: 'center', font: { size: 12 } },
};

const PLOTLY_CONFIG = { displayModeBar: false, responsive: true };

const CagrResearch = () => {
  const [tickers, setTickers] = useState([]);
  const [selectedTicker, setSelectedTicker] = useState(DEFAULT_TICKER);
  const [nDays, setNDays] = useState(DEFAULT_N_DAYS);
  const [splitDate, setSplitDate] = useState(DEFAULT_SPLIT_DATE);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /* ── Load tickers on mount ───────────────────────────────── */
  useEffect(() => {
    const load = async () => {
      try {
        const t = await fetchTickers();
        setTickers(t);
      } catch (err) {
        console.error('Error loading tickers:', err);
      }
    };
    load();
  }, []);

  /* ── Load CAGR matrix when params change ─────────────────── */
  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await fetchCagrMatrix(selectedTicker, splitDate, nDays);
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [selectedTicker, splitDate, nDays]);

  /* ── Derived data ────────────────────────────────────────── */
  const rows = data?.rows ?? [];

  const periodLabels = useMemo(
    () => rows.map((r) => r.period_label),
    [rows],
  );

  /* Full-period row for insight callout */
  const fullRow = rows.find((r) => r.period === 'full');

  /* ── CAGR grouped bar chart traces ───────────────────────── */
  const barTraces = useMemo(() => {
    if (!rows.length) return [];
    return [
      {
        name: 'All Days',
        x: periodLabels,
        y: rows.map((r) => +(r.cagr_all * 100).toFixed(2)),
        type: 'bar',
        marker: { color: '#60a5fa' },
        text: rows.map((r) => `${(r.cagr_all * 100).toFixed(2)}%`),
        textposition: 'outside',
        textfont: { size: 12, color: '#60a5fa' },
      },
      {
        name: `Miss Best ${nDays}`,
        x: periodLabels,
        y: rows.map((r) => +(r.cagr_miss_best * 100).toFixed(2)),
        type: 'bar',
        marker: { color: '#ef4444' },
        text: rows.map((r) => `${(r.cagr_miss_best * 100).toFixed(2)}%`),
        textposition: 'outside',
        textfont: { size: 12, color: '#ef4444' },
      },
      {
        name: `Miss Worst ${nDays}`,
        x: periodLabels,
        y: rows.map((r) => +(r.cagr_miss_worst * 100).toFixed(2)),
        type: 'bar',
        marker: { color: '#22c55e' },
        text: rows.map((r) => `${(r.cagr_miss_worst * 100).toFixed(2)}%`),
        textposition: 'outside',
        textfont: { size: 12, color: '#22c55e' },
      },
      {
        name: `Miss Both ${nDays}`,
        x: periodLabels,
        y: rows.map((r) => +(r.cagr_miss_both * 100).toFixed(2)),
        type: 'bar',
        marker: { color: '#8b5cf6' },
        text: rows.map((r) => `${(r.cagr_miss_both * 100).toFixed(2)}%`),
        textposition: 'outside',
        textfont: { size: 12, color: '#8b5cf6' },
      },
    ];
  }, [rows, periodLabels, nDays]);

  /* ── Impact waterfall traces ─────────────────────────────── */
  const waterfallTraces = useMemo(() => {
    if (!rows.length) return [];
    const labels = [];
    const values = [];
    const colors = [];

    rows.forEach((r) => {
      labels.push(`${r.period_label} — Miss Best`);
      const bestImpact = -(r.impact_miss_best * 100);
      values.push(+bestImpact.toFixed(2));
      colors.push('#ef4444');

      labels.push(`${r.period_label} — Miss Worst`);
      const worstImpact = +(r.impact_miss_worst * 100);
      values.push(+worstImpact.toFixed(2));
      colors.push('#22c55e');

      labels.push(`${r.period_label} — Miss Both`);
      const bothImpact = -(r.impact_miss_both * 100);
      values.push(+bothImpact.toFixed(2));
      colors.push('#8b5cf6');
    });

    return [
      {
        type: 'bar',
        x: labels,
        y: values,
        marker: { color: colors },
        text: values.map((v) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`),
        textposition: 'outside',
        textfont: { size: 11, color: colors },
      },
    ];
  }, [rows]);

  /* ── Trading-day percentage for insight ──────────────────── */
  const tradingDaysPct = fullRow
    ? ((nDays / fullRow.n_trading_days) * 100).toFixed(3)
    : '0.05';

  /* ── Render ──────────────────────────────────────────────── */
  return (
    <div className="cagr-page">
      <header className="page-header">
        <h1>CAGR Impact: The Cost of Missing Extreme Days</h1>
        <p className="subtitle">
          How missing the best or worst trading days reshapes long-term compound returns
        </p>
      </header>

      {/* ── Controls ─────────────────────────────────────────── */}
      <div className="cagr-controls">
        <div className="control-group">
          <label htmlFor="cagr-ticker">Index</label>
          <select
            id="cagr-ticker"
            value={selectedTicker}
            onChange={(e) => setSelectedTicker(e.target.value)}
          >
            {tickers.length > 0
              ? tickers.map((t) => (
                  <option key={t.ticker_code} value={t.ticker_code}>
                    {t.ticker_code.toUpperCase()} — {t.ticker_symbol}
                  </option>
                ))
              : <option value={DEFAULT_TICKER}>SP500</option>
            }
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="cagr-ndays">Days Removed (N)</label>
          <select
            id="cagr-ndays"
            value={nDays}
            onChange={(e) => setNDays(Number(e.target.value))}
          >
            {N_DAYS_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n} days
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="cagr-split">Split Date</label>
          <input
            id="cagr-split"
            type="date"
            value={splitDate}
            onChange={(e) => setSplitDate(e.target.value)}
          />
        </div>
      </div>

      {/* ── Loading / Error ──────────────────────────────────── */}
      {loading && (
        <div className="loading">
          <span className="loading-spinner" />
          Loading CAGR data…
        </div>
      )}

      {error && (
        <div className="error">
          Error loading data: {error}
        </div>
      )}

      {/* ── The Money Table ──────────────────────────────────── */}
      {!loading && !error && rows.length > 0 && (
        <>
          <div className="money-table-card">
            <h2>Miss Best / Worst {nDays} Days: CAGR Impact</h2>
            <div className="money-table-wrapper">
              <table className="money-table">
                <thead>
                  <tr>
                    <th>Period</th>
                    <th>Trading Days</th>
                    <th>All Days</th>
                    <th>Miss Best {nDays}</th>
                    <th>Miss Worst {nDays}</th>
                    <th>Impact (Best)</th>
                    <th>Impact (Worst)</th>
                    <th>Miss Both {nDays}</th>
                    <th>Impact (Both)</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.period}>
                      <td>
                        {r.period_label}
                        <br />
                        <span className="days-count">
                          {r.start_date} → {r.end_date}
                        </span>
                      </td>
                      <td>{r.n_trading_days.toLocaleString()}</td>
                      <td className="cagr-all">{fmtPct(r.cagr_all)}</td>
                      <td className="cagr-miss-best">{fmtPct(r.cagr_miss_best)}</td>
                      <td className="cagr-miss-worst">{fmtPct(r.cagr_miss_worst)}</td>
                      <td className="impact-negative">
                        {fmtSignedPct(-r.impact_miss_best)}
                      </td>
                      <td className="impact-positive">
                        {fmtSignedPct(r.impact_miss_worst)}
                      </td>
                      <td className="cagr-miss-both">{fmtPct(r.cagr_miss_both)}</td>
                      <td className="impact-both">
                        {fmtSignedPct(-r.impact_miss_both)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* ── Charts ─────────────────────────────────────────── */}
          <div className="cagr-charts-grid">
            {/* Grouped Bar Chart */}
            <div className="cagr-chart-card">
              <h2>CAGR Comparison by Period</h2>
              <Plot
                data={barTraces}
                layout={{
                  ...PLOTLY_DARK_LAYOUT,
                  barmode: 'group',
                  title: { text: '' },
                  yaxis: {
                    ...PLOTLY_DARK_LAYOUT.yaxis,
                    title: { text: 'CAGR (%)', font: { color: '#94a3b8' } },
                  },
                }}
                config={PLOTLY_CONFIG}
                useResizeHandler
                style={{ width: '100%', height: 400 }}
              />
              <p className="chart-description">
                Blue bars show baseline returns. Red shows the reduced CAGR when the
                best {nDays} days are missed. Green shows the improved CAGR when the
                worst {nDays} days are avoided. Purple shows the net effect of
                missing both the best and worst {nDays} days.
              </p>
            </div>

            {/* Waterfall / Diverging Bar Chart */}
            <div className="cagr-chart-card">
              <h2>CAGR Impact: Diverging View</h2>
              <Plot
                data={waterfallTraces}
                layout={{
                  ...PLOTLY_DARK_LAYOUT,
                  title: { text: '' },
                  yaxis: {
                    ...PLOTLY_DARK_LAYOUT.yaxis,
                    title: {
                      text: 'Impact on CAGR (pp)',
                      font: { color: '#94a3b8' },
                    },
                  },
                  xaxis: {
                    ...PLOTLY_DARK_LAYOUT.xaxis,
                    tickangle: -25,
                    tickfont: { size: 11 },
                  },
                  shapes: [
                    {
                      type: 'line',
                      x0: -0.5,
                      x1: rows.length * 3 - 0.5,
                      y0: 0,
                      y1: 0,
                      line: { color: '#475569', width: 1, dash: 'dot' },
                    },
                  ],
                }}
                config={PLOTLY_CONFIG}
                useResizeHandler
                style={{ width: '100%', height: 400 }}
              />
              <p className="chart-description">
                Negative bars (red) show the CAGR penalty from missing the best days.
                Positive bars (green) show the CAGR benefit of avoiding the worst days.
                Purple bars show the net impact of missing both extremes.
              </p>
            </div>
          </div>

          {/* ── Key Insight Callout ────────────────────────────── */}
          {fullRow && (
            <div className="insight-callout">
              <h3>💡 Faber's Key Insight</h3>
              <p>
                Missing just{' '}
                <span className="highlight">{nDays} days</span>{' '}
                ({tradingDaysPct}% of trading days) reduces your annualized return by{' '}
                <span className="highlight-red">
                  {(fullRow.impact_miss_best * 100).toFixed(2)} percentage points
                </span>.
                Avoiding the worst {nDays} days adds{' '}
                <span className="highlight-green">
                  {(fullRow.impact_miss_worst * 100).toFixed(2)} percentage points
                </span>.
              </p>
              <p>
                <strong>The punchline:</strong> missing <em>both</em> the best and worst {nDays} days
                yields a{' '}
                <span className="highlight-purple">
                  {fmtPct(fullRow.cagr_miss_both)} CAGR
                </span>
                {fullRow.cagr_miss_both > fullRow.cagr_all ? (
                  <> — <strong>higher than buy-and-hold</strong> ({fmtPct(fullRow.cagr_all)})</>
                ) : (
                  <> vs buy-and-hold ({fmtPct(fullRow.cagr_all)})</>
                )}.
                {' '}This proves worst days hurt more than best days help. Since both
                cluster in bear markets, trend-following avoids them both — a net win.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default CagrResearch;
