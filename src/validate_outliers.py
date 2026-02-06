"""Backward-compatible wrapper for the blackswans package.

This script delegates to blackswans.cli.main().  All analysis logic
now lives in the ``src/blackswans/`` package.

Usage is unchanged::

    python src/validate_outliers.py --ticker ^GSPC --start 1928-09-01 --end 2010-12-31
"""

# Re-export public names so existing imports continue to work.
from blackswans.data.loaders import fetch_price_data  # noqa: F401
from blackswans.data.transforms import compute_daily_returns  # noqa: F401
from blackswans.analysis.outliers import OutlierStats, calculate_outlier_stats  # noqa: F401
from blackswans.analysis.scenarios import annualised_return, scenario_returns, CASH  # noqa: F401
from blackswans.analysis.regimes import (  # noqa: F401
    moving_average_regime,
    outlier_regime_counts,
    regime_performance,
)
from blackswans.visualization.plots import make_plots  # noqa: F401
from blackswans.io.writers import save_dataframe  # noqa: F401
from blackswans.cli import main  # noqa: F401

if __name__ == "__main__":
    main()
