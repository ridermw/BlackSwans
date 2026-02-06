"""Command-line interface for running the Black Swans outlier analysis."""

import argparse
import logging
from pathlib import Path

import pandas as pd

from .data.loaders import fetch_price_data
from .data.transforms import compute_daily_returns
from .analysis.outliers import calculate_outlier_stats
from .analysis.scenarios import annualised_return, scenario_returns
from .analysis.regimes import moving_average_regime, regime_performance, outlier_regime_counts
from .visualization.plots import make_plots
from .io.writers import save_dataframe

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)


def main():
    """Command-line interface for running outlier analysis."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticker', type=str, default='^GSPC')
    parser.add_argument('--start', type=str, default='1928-09-04')
    parser.add_argument('--end', type=str, default='2025-01-31')
    parser.add_argument('--csv', type=str)
    parser.add_argument('--quantiles', type=float, nargs='+', default=[0.99, 0.999])
    parser.add_argument('--ma-window', type=int, default=200)
    parser.add_argument('--best-count', type=int, default=10)
    parser.add_argument('--worst-count', type=int, default=10)
    parser.add_argument('--output-dir', type=str, default='output')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    prices_df = fetch_price_data(args.ticker, args.start, args.end, args.csv, overwrite=args.overwrite)
    returns = compute_daily_returns(prices_df['Close'])

    # outlier stats
    stats = [calculate_outlier_stats(returns, q) for q in args.quantiles]
    df_stats = pd.DataFrame([vars(s) for s in stats]).set_index('quantile')
    save_dataframe(df_stats, output_dir / 'outlier_stats.csv')

    # scenario returns — fixed N days
    scenarios = scenario_returns(returns, args.best_count, args.worst_count)
    summary = [annualised_return(s) for s in scenarios]
    rows = []
    rows.extend([
        {'scenario': 'all', 'n_days': 0, 'annualised_return': summary[0]},
        {'scenario': f'miss_best_{args.best_count}', 'n_days': args.best_count, 'annualised_return': summary[1]},
        {'scenario': f'miss_worst_{args.worst_count}', 'n_days': args.worst_count, 'annualised_return': summary[2]},
        {'scenario': f'miss_both_{args.best_count}_{args.worst_count}', 'n_days': args.best_count + args.worst_count, 'annualised_return': summary[3]},
    ])

    # scenario returns — quantile-based
    for q in args.quantiles:
        n = int(round(len(returns) * (1 - q)))
        if n < 1:
            continue
        sc = scenario_returns(returns, n, n)
        rows.extend([
            {'scenario': f'miss_best_{q}', 'n_days': n, 'annualised_return': annualised_return(sc[1])},
            {'scenario': f'miss_worst_{q}', 'n_days': n, 'annualised_return': annualised_return(sc[2])},
            {'scenario': f'miss_both_{q}', 'n_days': 2 * n, 'annualised_return': annualised_return(sc[3])},
        ])

    df_scenarios = pd.DataFrame(rows).set_index('scenario')
    save_dataframe(df_scenarios, output_dir / 'return_scenarios.csv')

    # regimes
    regimes = moving_average_regime(prices_df['Close'], args.ma_window)
    df_regime = regime_performance(returns, regimes).set_index('regime')
    save_dataframe(df_regime, output_dir / 'regime_performance.csv')

    # outlier regime counts
    counts = [
        {'quantile': q, 'down': outlier_regime_counts(returns, regimes, q)[0],
         'up': outlier_regime_counts(returns, regimes, q)[1]}
        for q in args.quantiles
    ]
    df_counts = pd.DataFrame(counts).set_index('quantile')
    save_dataframe(df_counts, output_dir / 'outlier_regime_counts.csv')

    make_plots(returns, stats, regimes, output_dir)
    logging.info(f"Analysis complete. Results in {output_dir}")


if __name__ == '__main__':
    main()
