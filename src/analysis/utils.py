"""Small helpers for loading and saving tabular data."""

from pathlib import Path
from typing import Union

import pandas as pd

PathLike = Union[str, Path]


def load_data(filepath: PathLike) -> pd.DataFrame:
    """Load a CSV file into a DataFrame.

    Raises FileNotFoundError with a clear message if the file is missing.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return pd.read_csv(path)


def save_data(df: pd.DataFrame, filepath: PathLike) -> None:
    """Write a DataFrame to CSV, creating parent folders as needed."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
