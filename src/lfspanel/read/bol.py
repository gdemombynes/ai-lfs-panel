"""Read one quarter of the ECE.

Quarters up to 2025Q3 come from the pooled file (one CSV for 2015Q4-2025Q3,
filtered on ``gestion`` and ``trimestre`` with DuckDB); later quarters from
the Stata member of INE's per-quarter zip. Both return the same columns:
codes as strings, weights and amounts numeric (the CSV writes decimals with a
comma).
"""

from __future__ import annotations

import tempfile
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import List, Optional

import duckdb
import pandas as pd

from lfspanel.fetch.bol import source_for
from lfspanel.periods import Period

OPTIONAL = {"fact_trim", "fact_trim_act", "s2_22"}
NUMERIC = ("fact_trim", "fact_trim_act", "yprilab", "phrs")


def keep_list() -> List[str]:
    text = (files("lfspanel") / "resources" / "keep_lists" / "bol.txt").read_text()
    return [
        ln.split("#", 1)[0].strip()
        for ln in text.splitlines()
        if ln.split("#", 1)[0].strip()
    ]


def _member(z: zipfile.ZipFile) -> str:
    dta = [n for n in z.namelist() if n.lower().endswith(".dta")]
    if not dta:
        raise FileNotFoundError(f"No Stata member in {z.filename}")
    return dta[0]


def _check_missing(available: set, keep: List[str], label: str) -> List[str]:
    missing = [c for c in keep if c not in available]
    if set(missing) - OPTIONAL:
        raise KeyError(f"{label}: missing columns {sorted(set(missing) - OPTIONAL)}")
    return missing


def _from_csv(src: Path, period: Period, keep: List[str], nrows: Optional[int]):
    """Rows of one quarter from the pooled CSV; every column read as text."""
    con = duckdb.connect()
    header = con.execute(
        f"select * from read_csv('{src}', delim=';', header=true, "
        f"all_varchar=true, quote='\"') limit 0"
    ).df()
    missing = _check_missing(set(header.columns), keep, src.name)
    cols = ", ".join(f'"{c}"' for c in keep if c not in missing)
    limit = f" limit {int(nrows)}" if nrows else ""
    df = con.execute(
        f"select {cols} from read_csv('{src}', delim=';', header=true, "
        f"all_varchar=true, quote='\"') where gestion = '{period.year}' "
        f"and trimestre = '{period.quarter}'{limit}"
    ).df()
    con.close()
    if df.empty:
        raise FileNotFoundError(f"{src.name}: no rows for {period}")
    for c in NUMERIC:
        if c in df:
            df[c] = pd.to_numeric(
                df[c].str.strip().str.replace(",", ".", regex=False), errors="coerce"
            ).astype("float64")
    return df, missing, f"{src.name}"


def _from_zip(src: Path, keep: List[str], nrows: Optional[int]):
    with zipfile.ZipFile(src) as z, tempfile.TemporaryDirectory() as tmp:
        member = _member(z)
        out = Path(tmp) / "ece.dta"
        with z.open(member) as fh, open(out, "wb") as dst:
            for block in iter(lambda: fh.read(1 << 22), b""):
                dst.write(block)
        with pd.read_stata(out, iterator=True) as reader:
            available = set(reader.variable_labels())
        missing = _check_missing(available, keep, member)
        cols = [c for c in keep if c not in missing]
        df = pd.read_stata(out, columns=cols, convert_categoricals=False)
        if nrows:
            df = df.head(nrows)
    for c in NUMERIC:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    return df, missing, f"{src.name}:{Path(member).name}"


def read_raw(
    period: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    src = Path(path) if path else source_for(period)
    keep = keep_list()
    if src.suffix.lower() == ".csv":
        df, missing, label = _from_csv(src, period, keep, nrows)
    else:
        df, missing, label = _from_zip(src, keep, nrows)
    for c in missing:
        df[c] = ""
    for c in df.columns:
        s = df[c]
        if c in NUMERIC:
            continue
        if pd.api.types.is_numeric_dtype(s):
            df[c] = s.round().astype("Int64").astype("string").fillna("")
        else:
            df[c] = s.astype("string").str.strip().fillna("")
    df["source_file"] = label
    df.attrs["value_labels"] = {}
    return df[keep + ["source_file"]].reset_index(drop=True)
