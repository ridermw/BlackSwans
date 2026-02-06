import React from 'react';
import Plot from 'react-plotly.js';

const RegimeChart = ({ data }) => {
  if (!data || data.length === 0) {
    return <div>No regime data available</div>;
  }

  const uptrendData = data.filter(d => d.regime === 1);
  const downtrendData = data.filter(d => d.regime === 0);

  const traces = [
    {
      x: uptrendData.map(d => d.date),
      y: uptrendData.map(d => d.return * 100),
      type: 'scatter',
      mode: 'markers',
      marker: { color: '#2ca02c', size: 4, opacity: 0.6 },
      name: 'Uptrend (Above MA)',
      hovertemplate: '<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>'
    },
    {
      x: downtrendData.map(d => d.date),
      y: downtrendData.map(d => d.return * 100),
      type: 'scatter',
      mode: 'markers',
      marker: { color: '#d62728', size: 4, opacity: 0.6 },
      name: 'Downtrend (Below MA)',
      hovertemplate: '<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>'
    }
  ];

  const layout = {
    title: 'Returns by Market Regime',
    xaxis: { title: 'Date' },
    yaxis: { title: 'Daily Return (%)' },
    hovermode: 'closest',
    showlegend: true,
    height: 400,
    margin: { l: 60, r: 40, t: 60, b: 60 }
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

export default RegimeChart;
