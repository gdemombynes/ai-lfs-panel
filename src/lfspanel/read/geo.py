"""Read one quarter from Geostat's annual LFS database (ECSTAT SPSS file)."""

from __future__ import annotations

import tempfile
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import List, Optional

import pandas as pd

from lfspanel.fetch.geo import find_zip, quarter_number
from lfspanel.periods import Period

# spelling used in the 2022-2024 databases -> name used from 2025
ALIASES = {"brunch": "branch"}


def keep_list() -> List[str]:
    text = (files("lfspanel") / "resources" / "keep_lists" / "geo.txt").read_text()
    return [
        ln.split("#", 1)[0].strip()
        for ln in text.splitlines()
        if ln.split("#", 1)[0].strip()
    ]


def _member(z: zipfile.ZipFile) -> str:
    for name in z.namelist():
        base = name.replace("\\", "/").split("/")[-1].lower()
        if base.startswith("lfs_ecstat") and base.endswith(".sav"):
            return name
    raise FileNotFoundError(f"No LFS_ECSTAT .sav member in {z.filename}")


def read_raw(
    period: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    """Persons 15+ interviewed in the quarter; codes as strings, weight numeric."""
    import pyreadstat

    src = path or find_zip(period)
    with zipfile.ZipFile(src) as z:
        member = _member(z)
        with tempfile.NamedTemporaryFile(suffix=".sav", delete=True) as tmp:
            with z.open(member) as fh:
                for block in iter(lambda: fh.read(1 << 22), b""):
                    tmp.write(block)
            tmp.flush()
            _, meta = pyreadstat.read_sav(tmp.name, metadataonly=True)
            actual = {ALIASES.get(c.lower(), c.lower()): c for c in meta.column_names}
            missing = [c for c in keep_list() if c.lower() not in actual]
            if missing:
                raise KeyError(f"{member}: missing columns {missing}")
            df, _ = pyreadstat.read_sav(
                tmp.name,
                usecols=[actual[c.lower()] for c in keep_list()],
                disable_datetime_conversion=True,
            )
    df.columns = [ALIASES.get(c.lower(), c.lower()) for c in df.columns]
    df = df[df["quarterno"] == quarter_number(period)].copy()
    if nrows:
        df = df.head(nrows)
    for c in df.columns:
        s = df[c]
        if c == "p_weights":
            df[c] = pd.to_numeric(s, errors="coerce").astype("float64")
        elif pd.api.types.is_numeric_dtype(s):
            df[c] = s.round().astype("Int64").astype("string").fillna("")
        else:
            df[c] = s.astype("string").str.strip().fillna("")
    df["source_file"] = f"{src.name}:{Path(member).name}"
    return df.reset_index(drop=True)
