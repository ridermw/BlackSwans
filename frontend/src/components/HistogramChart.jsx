import React from 'react';
import Plot from 'react-plotly.js';

const HistogramChart = ({ data }) => {
  if (!data || !data.bins || !data.frequencies) {
    return <div>No histogram data available</div>;
  }

  const traces = [
    {
      x: data.bins,
      y: data.frequencies,
      type: 'bar',
      name: 'Actual Distribution',
      marker: { color: '#1f77b4', opacity: 0.7 },
      hovertemplate: 'Return: %{x:.1f}%<br>Frequency: %{y:.0f}<extra></extra>'
    },
    {
      x: data.bins,
      y: data.normal_pdf,
      type: 'scatter',
      mode: 'lines',
      name: 'Normal Distribution',
      line: { color: '#ff7f0e', width: 3, dash: 'dash' },
      hovertemplate: 'Return: %{x:.1f}%<br>Expected: %{y:.0f}<extra></extra>'
    }
  ];

  const layout = {
    title: 'Return Distribution vs Normal',
    xaxis: { title: 'Daily Return (%)' },
    yaxis: { title: 'Frequency' },
    showlegend: true,
    height: 400,
    margin: { l: 60, r: 40, t: 60, b: 60 },
    bargap: 0.05
  };

  return (
    <div className="chart-container">
      <Plot
        data={traces}
        layout={layout}
        config={{ responsive: true }}
        style={{ width: '100%' }}
      />
    </div>
  );
};

export default HistogramChart;
