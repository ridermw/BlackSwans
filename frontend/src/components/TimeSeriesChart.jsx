import React from 'react';
import Plot from 'react-plotly.js';

const TimeSeriesChart = ({ data }) => {
  if (!data || data.length === 0) {
    return <div>No data available</div>;
  }

  const regularDays = data.filter(d => !d.is_outlier);
  const outlierDays = data.filter(d => d.is_outlier);

  const traces = [
    {
      x: regularDays.map(d => d.date),
      y: regularDays.map(d => d.return * 100),
      type: 'scatter',
      mode: 'markers',
      marker: { color: '#1f77b4', size: 3, opacity: 0.6 },
      name: 'Regular Days',
      hovertemplate: '<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>'
    },
    {
      x: outlierDays.map(d => d.date),
      y: outlierDays.map(d => d.return * 100),
      type: 'scatter',
      mode: 'markers',
      marker: { color: '#ff7f0e', size: 6, symbol: 'star' },
      name: 'Outliers',
      hovertemplate: '<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>'
    }
  ];

  const layout = {
    title: 'Daily Returns Time Series',
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

export default TimeSeriesChart;
