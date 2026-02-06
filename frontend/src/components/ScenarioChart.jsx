import React from 'react';
import Plot from 'react-plotly.js';

const ScenarioChart = ({ data, scenarios }) => {
  if (!data) {
    return <div>No scenario data available</div>;
  }

  // If scenarios data is provided, show impact of missing days
  if (scenarios) {
    const daysCounts = Object.keys(scenarios).map(Number).sort((a, b) => a - b);
    const impacts = daysCounts.map(days => Math.abs(scenarios[days]));

    const trace = {
      x: daysCounts,
      y: impacts,
      type: 'bar',
      marker: { color: '#ff7f0e' },
      text: impacts.map(v => `${v.toFixed(2)}%`),
      textposition: 'auto',
      hovertemplate: 'Missing %{x} Days<br>Impact: %{y:.2f}%<extra></extra>'
    };

    const layout = {
      title: 'Impact of Missing Best Days on CAGR',
      xaxis: { title: 'Number of Best Days Missed', type: 'category' },
      yaxis: { title: 'CAGR Impact (%)' },
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
  }

  // Otherwise show standard scenario comparison
  const scenarios_list = [
    { name: 'All Days', value: data.all_days, color: '#1f77b4' },
    { name: 'Miss Best 10', value: data.miss_best_10, color: '#ff7f0e' },
    { name: 'Miss Worst 10', value: data.miss_worst_10, color: '#2ca02c' },
    { name: 'Miss Both', value: data.miss_both, color: '#d62728' }
  ];

  const trace = {
    x: scenarios_list.map(s => s.name),
    y: scenarios_list.map(s => s.value),
    type: 'bar',
    marker: { color: scenarios_list.map(s => s.color) },
    text: scenarios_list.map(s => `${s.value.toFixed(2)}%`),
    textposition: 'auto',
    hovertemplate: '%{x}<br>CAGR: %{y:.2f}%<extra></extra>'
  };

  const layout = {
    title: 'Return Scenarios Comparison',
    xaxis: { title: 'Scenario' },
    yaxis: { title: 'Annualized Return (%)' },
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
