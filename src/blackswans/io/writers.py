"""Output file writing utilities."""

from pathlib import Path

import pandas as pd


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    """Save DataFrame to a CSV file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path)
