"""Output file writing utilities."""

from pathlib import Path

import pandas as pd


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    """Save DataFrame to a CSV file, creating parent dirs as needed."""
    # Validate no path traversal in relative paths
    if not path.is_absolute():
        parts = path.parts
        if ".." in parts:
            raise ValueError(f"Path traversal detected: {path}")

    resolved_path = path.resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(resolved_path)
