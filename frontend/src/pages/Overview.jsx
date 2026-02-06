import React, { useState, useEffect } from 'react';
import { fetchClaims } from '../services/api';
import ClaimCard from '../components/ClaimCard';
import './Overview.css';

const Overview = () => {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadClaims = async () => {
      try {
        setLoading(true);
        const data = await fetchClaims('sp500');
        setClaims(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadClaims();
  }, []);

  if (loading) {
    return <div className="loading">Loading validation results...</div>;
  }

  if (error) {
    return <div className="error">Error loading data. Is the API server running? ({error})</div>;
  }

  return (
    <div className="overview-page">
      <header className="page-header">
        <h1>Black Swans: Validation Summary</h1>
        <p className="subtitle">
          Statistical validation of Mebane Faber's 2011 paper:
          <em>"Where the Black Swans Hide & The 10 Best Days Myth"</em>
        </p>
      </header>

      <section className="claims-section">
        <h2>Faber's Four Claims</h2>
        <div className="claims-grid">
          {claims.map((claim) => (
            <ClaimCard key={claim.id} claim={claim} />
          ))}
        </div>
      </section>

      <section className="methodology">
        <h2>Methodology</h2>
        <p>
          This dashboard presents statistical validation of Faber's claims using:
        </p>
        <ul>
          <li><strong>Chi-squared tests</strong> for regime clustering analysis</li>
          <li><strong>Jarque-Bera tests</strong> for fat-tail detection</li>
          <li><strong>Bootstrap confidence intervals</strong> for robust estimation</li>
          <li><strong>Scenario analysis</strong> for outlier impact quantification</li>
        </ul>
        <p>
          All analyses use S&P 500 daily returns from 1928-2010 (~20,000 trading days).
        </p>
      </section>
    </div>
  );
};

export default Overview;
