"""Shared test fixtures with synthetic data."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def price_series():
    """A synthetic price series: 500 trading days starting at 100, random walk."""
    rng = np.random.RandomState(42)
    dates = pd.bdate_range("2020-01-01", periods=500)
    daily_returns = rng.normal(0.0004, 0.01, size=500)
    prices = 100 * np.cumprod(1 + daily_returns)
    return pd.Series(prices, index=dates, name="Close")


@pytest.fixture
def price_dataframe(price_series):
    """Same synthetic prices as a DataFrame with 'Close' column."""
    return pd.DataFrame({"Close": price_series})


@pytest.fixture
def returns_series(price_series):
    """Daily returns derived from the synthetic price series."""
    r = price_series.pct_change().dropna()
    r.name = "Return"
    return r


@pytest.fixture
def known_returns():
    """Small hand-crafted returns for exact verification."""
    dates = pd.bdate_range("2020-01-01", periods=10)
    values = [-0.05, 0.03, -0.02, 0.01, 0.04, -0.03, 0.02, -0.01, 0.05, -0.04]
    return pd.Series(values, index=dates, name="Return")


@pytest.fixture
def regime_series(price_series):
    """Regime labels matching the price series length."""
    from blackswans.analysis.regimes import moving_average_regime
    return moving_average_regime(price_series, window=50)
