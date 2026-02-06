"""Data transformation utilities."""

import pandas as pd


def compute_daily_returns(prices: pd.Series) -> pd.Series:
    """Calculate daily percentage returns from price series.

    Accepts either a Series or single-column DataFrame.
    """
    if isinstance(prices, pd.DataFrame):
        prices = prices['Close'] if 'Close' in prices else prices.iloc[:, 0]

    prices = pd.to_numeric(prices, errors='coerce').dropna()
    returns = prices.pct_change(fill_method=None).dropna()
    returns.name = "Return"
    return returns
