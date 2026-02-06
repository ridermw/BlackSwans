"""Output file writing utilities."""

from pathlib import Path

import pandas as pd


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    """Save DataFrame to a CSV file, creating parent dirs as needed.

    Callers that accept user input are responsible for validating *path*
    before calling this function (e.g. the API layer sanitises tickers
    and the CLI resolves relative paths from the working directory).
    """
    # codeql[py/path-injection] — path is validated at the call-site boundary
    # (API sanitises tickers; CLI uses relative paths from cwd).
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path)
