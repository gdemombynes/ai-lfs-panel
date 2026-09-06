"""Read the PSA LFS public-use CSV from a PUF archive (one survey month)."""

from __future__ import annotations

import zipfile
from importlib.resources import files
from pathlib import Path
from typing import List, Optional

import pandas as pd

from lfspanel.fetch.phl import find_zip
from lfspanel.periods import Period

ALIASES = {"pufurb2015": "pufurb2020"}  # urban flag renamed with the 2020 census frame
BOM = "\ufeff"


def _norm(name: str) -> str:
    """Lower-case name without a UTF-8 byte-order mark (present in some rounds)."""
    n = (
        name.strip()
        .lower()
        .replace(BOM, "")
        .replace("\xef\xbb\xbf", "")
        .replace("ï»¿", "")
    )
    return ALIASES.get(n, n)


OPTIONAL = {"pufurb2020"}


def keep_list() -> List[str]:
    text = (files("lfspanel") / "resources" / "keep_lists" / "phl.txt").read_text()
    return [
        ln.split("#", 1)[0].strip()
        for ln in text.splitlines()
        if ln.split("#", 1)[0].strip()
    ]


def _member(z: zipfile.ZipFile) -> str:
    csv = [n for n in z.namelist() if n.lower().endswith(".csv")]
    if not csv:
        raise FileNotFoundError(f"No CSV member in {z.filename}")
    return csv[0]


def read_raw(
    period: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    src = path or find_zip(period)
    keep = [c.lower() for c in keep_list()]
    with zipfile.ZipFile(src) as z:
        member = _member(z)
        with z.open(member) as fh:
            df = pd.read_csv(
                fh,
                dtype=str,
                keep_default_na=False,
                encoding="latin-1",
                nrows=nrows,
                usecols=lambda c: _norm(c) in keep,
            )
    df.columns = [_norm(c) for c in df.columns]
    missing = [c for c in keep if c not in df.columns]
    if set(missing) - OPTIONAL:
        raise KeyError(f"{member}: missing columns {sorted(set(missing) - OPTIONAL)}")
    for c in missing:
        df[c] = ""
    for c in df.columns:
        df[c] = df[c].str.strip()
    df["pufpwgtprv"] = pd.to_numeric(df["pufpwgtprv"], errors="coerce").astype(
        "float64"
    )
    df["source_file"] = f"{src.name}:{Path(member).name}"
    return df
