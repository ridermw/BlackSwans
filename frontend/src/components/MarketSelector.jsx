import React from 'react';
import './MarketSelector.css';

const MarketSelector = ({ tickers, selectedTicker, onTickerChange }) => {
  if (!tickers || tickers.length === 0) {
    return null;
  }

  return (
    <div className="market-selector">
      <label htmlFor="ticker-select">Select Market:</label>
      <select
        id="ticker-select"
        value={selectedTicker}
        onChange={(e) => onTickerChange(e.target.value)}
        className="ticker-dropdown"
      >
        {tickers.map((ticker) => (
          <option key={ticker.symbol} value={ticker.symbol}>
            {ticker.name} ({ticker.symbol}) - {ticker.period}
          </option>
        ))}
      </select>
    </div>
  );
};

export default MarketSelector;
