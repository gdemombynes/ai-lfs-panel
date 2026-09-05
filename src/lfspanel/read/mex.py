"""Read ENOE quarterly CSV tables (SDEM, COE1, COE2) and merge them per person.

Header quirks handled here: a UTF-8 byte-order mark on the first column in
some 2022 files, the 2025 Q3 rename of geography codes (``ent`` -> ``cve_ent``),
and questionnaire items that exist only in the first-quarter extended
questionnaire (``p3j``, ``p3r``, ``p3r_anio``, ``p3r_mes``), which are added
as blank columns in other quarters.
"""

from __future__ import annotations

import fnmatch
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import List, Optional

import pandas as pd

from lfspanel.fetch.mex import find_zip
from lfspanel.periods import Period

# Person-level merge keys shared by SDEM, COE1 and COE2 (GLD MEX ENOE).
KEYS = ["cd_a", "ent", "con", "v_sel", "tipo", "mes_cal", "n_hog", "h_mud", "n_ren"]
TABLES = {"sdem": "*SDEM*.csv", "coe1": "*COE1*.csv", "coe2": "*COE2*.csv"}
RENAMES = {"cve_ent": "ent", "cve_mun": "mun", "cve_loc": "loc", "cve_ageb": "ageb"}
OPTIONAL = {"p3j", "p3r", "p3r_anio", "p3r_mes"}  # extended questionnaire (Q1) only


def normalize_columns(cols: List[str]) -> List[str]:
    """Lower-case, strip BOM and whitespace, apply known renames."""
    out = []
    for c in cols:
        c = c.replace("﻿", "").replace("ï»¿", "").strip().lower()
        out.append(RENAMES.get(c, c))
    return out


def _keep(table: str) -> List[str]:
    text = (
        files("lfspanel") / "resources" / "keep_lists" / f"mex_{table}.txt"
    ).read_text()
    return [
        ln.split("#", 1)[0].strip()
        for ln in text.splitlines()
        if ln.split("#", 1)[0].strip()
    ]


def _member(z: zipfile.ZipFile, pattern: str) -> str:
    for name in z.namelist():
        if fnmatch.fnmatch(Path(name).name.upper(), pattern.upper()):
            return name
    raise FileNotFoundError(f"No member matching {pattern} in {z.filename}")


def _read(
    z: zipfile.ZipFile, member: str, cols: List[str], nrows: Optional[int]
) -> pd.DataFrame:
    with z.open(member) as fh:
        raw_header = list(pd.read_csv(fh, nrows=0, encoding="latin-1").columns)
    header = normalize_columns(raw_header)
    wanted = {raw for raw, norm in zip(raw_header, header) if norm in set(cols)}
    missing = [c for c in cols if c not in header and c not in OPTIONAL]
    if missing:
        raise KeyError(f"{member}: missing columns {missing}")
    with z.open(member) as fh:
        df = pd.read_csv(
            fh,
            dtype=str,
            usecols=lambda c: c in wanted,
            keep_default_na=False,
            encoding="latin-1",
            nrows=nrows,
        )
    df.columns = normalize_columns(list(df.columns))
    for c in df.columns:
        df[c] = df[c].str.strip()
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df


def read_raw(
    period: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    """SDEM rows (all residents) left-joined with COE1 and COE2 job questions."""
    src = path or find_zip(period)
    with zipfile.ZipFile(src) as z:
        sdem = _read(z, _member(z, TABLES["sdem"]), _keep("sdem"), nrows)
        coe1 = _read(z, _member(z, TABLES["coe1"]), _keep("coe1"), None)
        coe2 = _read(z, _member(z, TABLES["coe2"]), _keep("coe2"), None)
        member = _member(z, TABLES["sdem"])
    for name, t in (("coe1", coe1), ("coe2", coe2)):
        if t.duplicated(KEYS).any():
            raise ValueError(f"{name}: duplicate merge keys")
    df = sdem.merge(coe1, on=KEYS, how="left", validate="1:1")
    df = df.merge(coe2, on=KEYS, how="left", validate="1:1")
    df["source_file"] = f"{src.name}:{Path(member).name}"
    return df
