import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Overview from './pages/Overview';
import Analysis from './pages/Analysis';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-container">
            <Link to="/" className="nav-logo">
              <span className="logo-icon">📊</span>
              <span className="logo-text">BlackSwans</span>
            </Link>
            <div className="nav-links">
              <Link to="/" className="nav-link">Overview</Link>
              <Link to="/analysis/sp500" className="nav-link">Analysis</Link>
            </div>
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/analysis/:ticker" element={<Analysis />} />
            <Route path="/analysis" element={<Analysis />} />
          </Routes>
        </main>

        <footer className="footer">
          <p>
            Based on <em>"Where the Black Swans Hide & The 10 Best Days Myth"</em> by Mebane Faber (2011)
          </p>
          <p className="footer-note">
            Statistical validation using S&P 500 data (1928-2010)
          </p>
        </footer>
      </div>
    </Router>
  );
}

export default App;
