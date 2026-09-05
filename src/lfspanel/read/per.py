"""Read the EPEN national quarterly person file (Stata .dta) from the zip."""

from __future__ import annotations

import tempfile
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import List, Optional

import pandas as pd

from lfspanel.fetch.per import find_zip
from lfspanel.periods import Period

# city identifiers appear only from 2024Q2 (NOMCIUDAD) / 2025Q1 (CODciudad)
OPTIONAL = {"codciudad", "nomciudad"}


def keep_list() -> List[str]:
    text = (files("lfspanel") / "resources" / "keep_lists" / "per.txt").read_text()
    return [
        ln.split("#", 1)[0].strip()
        for ln in text.splitlines()
        if ln.split("#", 1)[0].strip()
    ]


def _member(z: zipfile.ZipFile) -> str:
    dta = [n for n in z.namelist() if n.lower().endswith(".dta")]
    national = [n for n in dta if "nacional" in n.lower()]
    if national:
        return national[0]
    if len(dta) == 1:
        return dta[0]
    raise FileNotFoundError(f"No national .dta member in {z.filename}: {dta}")


def read_raw(
    period: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    """Person records as strings (numeric codes without decimal parts)."""
    import pyreadstat

    src = path or find_zip(period)
    with zipfile.ZipFile(src) as z:
        member = _member(z)
        with tempfile.NamedTemporaryFile(suffix=".dta", delete=True) as tmp:
            with z.open(member) as fh:
                for block in iter(lambda: fh.read(1 << 22), b""):
                    tmp.write(block)
            tmp.flush()
            _, meta = pyreadstat.read_dta(tmp.name, metadataonly=True)
            actual = {c.lower(): c for c in meta.column_names}
            wanted = [actual[c.lower()] for c in keep_list() if c.lower() in actual]
            missing = [c for c in keep_list() if c.lower() not in actual]
            if set(c.lower() for c in missing) - OPTIONAL:
                raise KeyError(f"{member}: missing columns {missing}")
            df, _ = pyreadstat.read_dta(
                tmp.name,
                usecols=wanted,
                row_limit=nrows or 0,
                disable_datetime_conversion=True,
            )
    df.columns = [c.lower() for c in df.columns]
    for c in OPTIONAL - set(df.columns):
        df[c] = ""
    for c in df.columns:
        s = df[c]
        if pd.api.types.is_numeric_dtype(s):
            if c in ("fac_t300", "ingtotp"):
                df[c] = s.astype("float64")
            else:
                df[c] = s.round().astype("Int64").astype("string").fillna("")
        else:
            df[c] = s.astype("string").str.strip().fillna("")
    df["source_file"] = f"{src.name}:{Path(member).name}"
    return df
