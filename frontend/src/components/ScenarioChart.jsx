import React from 'react';
import Plot from 'react-plotly.js';

const ScenarioChart = ({ scenarios }) => {
  if (!scenarios || Object.keys(scenarios).length === 0) {
    return <div>No scenario data available</div>;
  }

  // scenarios is { "5": 0.78, "10": 1.41, "20": 2.47, "50": 4.94 }
  const daysCounts = Object.keys(scenarios).map(Number).sort((a, b) => a - b);
  const impacts = daysCounts.map(days => Math.abs(scenarios[String(days)]));

  const trace = {
    x: daysCounts,
    y: impacts,
    type: 'bar',
    marker: { color: '#ff7f0e' },
    text: impacts.map(v => `${v.toFixed(2)}pp`),
    textposition: 'auto',
    hovertemplate: 'Missing %{x} Best Days<br>CAGR Impact: %{y:.2f} pp<extra></extra>'
  };

  const layout = {
    title: 'Impact of Missing Best Days on CAGR',
    xaxis: { title: 'Number of Best Days Missed', type: 'category' },
    yaxis: { title: 'CAGR Impact (percentage points)' },
    height: 400,
    margin: { l: 60, r: 40, t: 60, b: 60 }
  };

  return (
    <div className="chart-container">
      <Plot
        data={[trace]}
        layout={layout}
        config={{ responsive: true }}
        style={{ width: '100%' }}
      />
    </div>
  );
};

export default ScenarioChart;
