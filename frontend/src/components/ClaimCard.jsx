import React from 'react';
import './ClaimCard.css';

const ClaimCard = ({ claim }) => {
  const getVerdictClass = (verdict) => {
    switch (verdict) {
      case 'CONFIRMED':
        return 'verdict-confirmed';
      case 'REJECTED':
        return 'verdict-rejected';
      case 'PARTIAL':
        return 'verdict-partial';
      default:
        return 'verdict-unknown';
    }
  };

  const renderMetrics = () => {
    if (!claim.metrics) return null;

    return (
      <div className="metrics">
        {Object.entries(claim.metrics).map(([key, value]) => {
          // Skip nested objects like scenarios
          if (typeof value === 'object') return null;

          const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          let formattedValue = value;

          if (typeof value === 'number') {
            if (key.includes('p_value') && value < 0.001) {
              formattedValue = '< 0.001';
            } else if (key.includes('pct') || key.includes('impact')) {
              formattedValue = `${value.toFixed(2)}%`;
            } else {
              formattedValue = value.toFixed(2);
            }
          }

          return (
            <div key={key} className="metric">
              <span className="metric-label">{formattedKey}:</span>
              <span className="metric-value">{formattedValue}</span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="claim-card">
      <div className="claim-header">
        <h3>Claim {claim.id}: {claim.title}</h3>
        <span className={`verdict ${getVerdictClass(claim.verdict)}`}>
          {claim.verdict}
        </span>
      </div>
      <p className="claim-description">{claim.description}</p>
      {renderMetrics()}
    </div>
  );
};

export default ClaimCard;
