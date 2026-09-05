"""Read the EPH 'usu_individual' text file (semicolon-separated, quoted header)."""

from __future__ import annotations

import zipfile
from importlib.resources import files
from pathlib import Path
from typing import List, Optional

import pandas as pd

from lfspanel.fetch.arg import find_zip
from lfspanel.periods import Period

# variables INDEC has dropped from recent user files; filled with "" when absent
OPTIONAL = {"CAT_INAC"}


def keep_list() -> List[str]:
    text = (files("lfspanel") / "resources" / "keep_lists" / "arg.txt").read_text()
    return [
        ln.split("#", 1)[0].strip()
        for ln in text.splitlines()
        if ln.split("#", 1)[0].strip()
    ]


def _member(z: zipfile.ZipFile) -> str:
    for name in z.namelist():
        base = name.replace("\\", "/").split("/")[-1].lower()
        if "individual" in base and base.endswith(".txt"):
            return name
    raise FileNotFoundError(f"No usu_individual member in {z.filename}")


def read_raw(
    period: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    src = path or find_zip(period)
    keep = keep_list()
    with zipfile.ZipFile(src) as z:
        member = _member(z)
        with z.open(member) as fh:
            df = pd.read_csv(
                fh,
                sep=";",
                dtype=str,
                usecols=lambda c: c.strip().strip('"').upper() in set(keep),
                keep_default_na=False,
                encoding="latin-1",
                nrows=nrows,
            )
    df.columns = [c.strip().strip('"').upper() for c in df.columns]
    missing = [c for c in keep if c not in df.columns]
    if set(missing) - OPTIONAL:
        raise KeyError(f"{member}: missing columns {sorted(set(missing) - OPTIONAL)}")
    for c in missing:
        df[c] = ""
    for c in df.columns:
        df[c] = df[c].str.strip()
    df["source_file"] = f"{src.name}:{Path(member).name}"
    return df
