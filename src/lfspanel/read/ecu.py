"""Read the ENEMDU person file (SPSS .sav) from the quarterly zip."""

from __future__ import annotations

import tempfile
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import List, Optional

import pandas as pd

from lfspanel.fetch.ecu import find_zip
from lfspanel.periods import Period


def keep_list() -> List[str]:
    text = (files("lfspanel") / "resources" / "keep_lists" / "ecu.txt").read_text()
    return [
        ln.split("#", 1)[0].strip()
        for ln in text.splitlines()
        if ln.split("#", 1)[0].strip()
    ]


def _person_member(z: zipfile.ZipFile) -> str:
    for name in z.namelist():
        base = name.replace("\\", "/").split("/")[-1].lower()
        if "persona" in base and base.endswith(".sav"):
            return name
    raise FileNotFoundError(f"No persona .sav member in {z.filename}")


def read_raw(
    period: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    """Person records as strings (numeric codes without decimal parts)."""
    import pyreadstat

    src = path or find_zip(period)
    with zipfile.ZipFile(src) as z:
        member = _person_member(z)
        with tempfile.NamedTemporaryFile(suffix=".sav", delete=True) as tmp:
            with z.open(member) as fh:
                for block in iter(lambda: fh.read(1 << 22), b""):
                    tmp.write(block)
            tmp.flush()
            _, meta = pyreadstat.read_sav(tmp.name, metadataonly=True)
            actual = {c.lower(): c for c in meta.column_names}
            wanted = [actual[c] for c in keep_list() if c in actual]
            missing = [c for c in keep_list() if c not in actual]
            if missing:
                raise KeyError(f"{member}: missing columns {missing}")
            df, _ = pyreadstat.read_sav(
                tmp.name,
                usecols=wanted,
                row_limit=nrows or 0,
                disable_datetime_conversion=True,
            )
    df.columns = [c.lower() for c in df.columns]
    for c in df.columns:
        s = df[c]
        if pd.api.types.is_numeric_dtype(s):
            vals = s.dropna().astype(float)
            if len(vals) and (vals == vals.round()).all():
                df[c] = s.map(lambda v: "" if pd.isna(v) else str(int(v)))
            else:
                df[c] = s.map(lambda v: "" if pd.isna(v) else repr(float(v)))
        else:
            df[c] = s.fillna("").astype(str).str.strip()
    df["source_file"] = f"{src.name}:{Path(member).name}"
    return df
