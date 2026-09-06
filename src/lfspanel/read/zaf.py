"""Read the QLFS worker file (Stata) from a DataFirst archive.

The files declare a character set readstat rejects, so pandas' Stata reader is
used with value labels left as numeric codes. Column names change case
between releases (``Geo_type_code`` / ``Geo_Type_Code``) and are matched
case-insensitively; variables dropped in later questionnaires are optional.
"""

from __future__ import annotations

import io
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import List, Optional

import pandas as pd

from lfspanel.fetch.zaf import find_zip
from lfspanel.periods import Period

OPTIONAL = {"q415typebusns"}


def keep_list() -> List[str]:
    text = (files("lfspanel") / "resources" / "keep_lists" / "zaf.txt").read_text()
    return [
        ln.split("#", 1)[0].strip()
        for ln in text.splitlines()
        if ln.split("#", 1)[0].strip()
    ]


def _member(z: zipfile.ZipFile) -> str:
    dta = [n for n in z.namelist() if n.lower().endswith(".dta")]
    if not dta:
        raise FileNotFoundError(f"No .dta member in {z.filename}")
    return dta[0]


def read_raw(
    period: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    """Person records; codes as strings, weight and hours numeric."""
    src = path or find_zip(period)
    with zipfile.ZipFile(src) as z:
        member = _member(z)
        reader = pd.io.stata.StataReader(
            io.BytesIO(z.read(member)), convert_categoricals=False
        )
        try:
            df = reader.read(nrows=nrows) if nrows else reader.read()
        finally:
            reader.close()
    actual = {c.lower(): c for c in df.columns}
    wanted = [c for c in keep_list() if c.lower() in actual]
    missing = [c for c in keep_list() if c.lower() not in actual]
    if set(c.lower() for c in missing) - OPTIONAL:
        raise KeyError(f"{member}: missing columns {missing}")
    df = df[[actual[c.lower()] for c in wanted]].copy()
    df.columns = [c.lower() for c in wanted]
    for c in missing:
        df[c.lower()] = pd.NA
    for c in df.columns:
        s = df[c]
        if c in ("weight",):
            df[c] = pd.to_numeric(s, errors="coerce").astype("float64")
        elif pd.api.types.is_numeric_dtype(s):
            df[c] = s.round().astype("Int64").astype("string").fillna("")
        else:
            df[c] = s.astype("string").str.strip().fillna("")
    df["source_file"] = f"{src.name}:{Path(member).name}"
    return df
