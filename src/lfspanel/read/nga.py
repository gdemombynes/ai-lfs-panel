"""Read one NLFS individual file: SPSS (2024Q1), Stata, or a zip holding Stata.

readstat rejects the Stata files' character set, so those go through pandas'
Stata reader; the SPSS file needs an explicit UTF-8 flag.
"""

from __future__ import annotations

import io
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from lfspanel.fetch.nga import find_zip
from lfspanel.periods import Period


def keep_list() -> List[str]:
    text = (files("lfspanel") / "resources" / "keep_lists" / "nga.txt").read_text()
    return [
        ln.split("#", 1)[0].strip()
        for ln in text.splitlines()
        if ln.split("#", 1)[0].strip()
    ]


def _read_dta(data: bytes, nrows: Optional[int]) -> Tuple[pd.DataFrame, dict]:
    reader = pd.io.stata.StataReader(io.BytesIO(data), convert_categoricals=False)
    try:
        df = reader.read(nrows=nrows) if nrows else reader.read()
        labels = {k.lower(): v for k, v in reader.value_labels().items()}
    finally:
        reader.close()
    return df, labels


def _read_sav(
    path: Path, wanted: List[str], nrows: Optional[int]
) -> Tuple[pd.DataFrame, dict]:
    import pyreadstat

    _, meta = pyreadstat.read_sav(str(path), metadataonly=True, encoding="utf-8")
    actual = {c.lower(): c for c in meta.column_names}
    df, meta = pyreadstat.read_sav(
        str(path),
        encoding="utf-8",
        usecols=[actual[c] for c in wanted if c in actual],
        row_limit=nrows or 0,
        disable_datetime_conversion=True,
    )
    return df, {k.lower(): v for k, v in meta.variable_value_labels.items()}


def read_raw(
    period: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    src = path or find_zip(period)
    keep = [c.lower() for c in keep_list()]
    member = src.name
    if src.suffix.lower() == ".sav":
        df, labels = _read_sav(src, keep, nrows)
    elif src.suffix.lower() == ".dta":
        df, labels = _read_dta(src.read_bytes(), nrows)
    else:
        with zipfile.ZipFile(src) as z:
            member = next(n for n in z.namelist() if n.lower().endswith("indiv.dta"))
            df, labels = _read_dta(z.read(member), nrows)
    df.columns = [c.lower() for c in df.columns]
    missing = [c for c in keep if c not in df.columns]
    if missing:
        raise KeyError(f"{member}: missing columns {missing}")
    df = df[keep].copy()
    for c in df.columns:
        s = df[c]
        if c == "popw":
            df[c] = pd.to_numeric(s, errors="coerce").astype("float64")
        elif c == "interviewdate":
            df[c] = (
                pd.to_datetime(s, errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
            )
        elif pd.api.types.is_numeric_dtype(s):
            df[c] = s.round().astype("Int64").astype("string").fillna("")
        else:
            df[c] = s.astype("string").str.strip().fillna("")
    df["source_file"] = f"{src.name}:{Path(member).name}"
    df.attrs["value_labels"] = {c: labels[c] for c in df.columns if c in labels}
    return df.reset_index(drop=True)
