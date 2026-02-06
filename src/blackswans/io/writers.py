"""Output file writing utilities."""

from pathlib import Path

import pandas as pd


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    """Save DataFrame to a CSV file, creating parent dirs as needed."""
    resolved = path.resolve()
    cwd = Path.cwd().resolve()
    try:
        resolved.relative_to(cwd)
    except ValueError:
        raise ValueError(
            f"Output path must be within the working directory: {path}"
        )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(resolved)
