import React, { useState } from 'react';
import { HashRouter as Router, Routes, Route, NavLink, Link } from 'react-router-dom';
import Landing from './pages/Landing';
import PeriodComparison from './pages/PeriodComparison';
import MultiIndex from './pages/MultiIndex';
import CagrResearch from './pages/CagrResearch';
import Analysis from './pages/Analysis';
import './App.css';

function App() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-container">
            <Link to="/" className="nav-logo">
              <span className="logo-icon">🦢</span>
              <span className="logo-text">BlackSwans</span>
            </Link>

            <button
              className={`hamburger ${menuOpen ? 'open' : ''}`}
              onClick={() => setMenuOpen(!menuOpen)}
              aria-label="Toggle navigation"
            >
              <span />
              <span />
              <span />
            </button>

            <div className={`nav-links ${menuOpen ? 'nav-open' : ''}`}>
              <NavLink to="/" end className="nav-link" onClick={() => setMenuOpen(false)}>
                Home
              </NavLink>
              <NavLink to="/period-comparison" className="nav-link" onClick={() => setMenuOpen(false)}>
                Period Comparison
              </NavLink>
              <NavLink to="/multi-index" className="nav-link" onClick={() => setMenuOpen(false)}>
                Multi-Index
              </NavLink>
              <NavLink to="/cagr" className="nav-link" onClick={() => setMenuOpen(false)}>
                CAGR Research
              </NavLink>
              <NavLink to="/analysis/sp500" className="nav-link" onClick={() => setMenuOpen(false)}>
                Legacy Analysis
              </NavLink>
            </div>
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/period-comparison" element={<PeriodComparison />} />
            <Route path="/multi-index" element={<MultiIndex />} />
            <Route path="/cagr" element={<CagrResearch />} />
            <Route path="/analysis/:ticker" element={<Analysis />} />
          </Routes>
        </main>

        <footer className="footer">
          <div className="footer-content">
            <p className="footer-citation">
              Based on <em>"Where the Black Swans Hide &amp; The 10 Best Days Myth"</em> by Mebane Faber (2011)
            </p>
            <p className="footer-stats">
              Statistical validation using S&amp;P 500 data (1928–2025) • 12 Global Indices
            </p>
            <p className="footer-disclaimer">
              This is a research tool, not financial advice.
            </p>
            <a
              href="https://github.com/ridermw/BlackSwans"
              target="_blank"
              rel="noopener noreferrer"
              className="footer-github"
            >
              GitHub
            </a>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
