"""Read GEIH monthly CSV modules and stack the three months of a quarter."""

from __future__ import annotations

import zipfile
from importlib.resources import files
from pathlib import Path
from typing import List, Optional

import pandas as pd

from lfspanel.fetch.col import find_zip
from lfspanel.periods import Period

KEYS = ["DIRECTORIO", "SECUENCIA_P", "ORDEN"]
# module -> member-name prefix inside the zip (accents are mangled in the archive)
MODULES = {
    "cg": "CSV/Caracter",
    "ft": "CSV/Fuerza de trabajo",
    "oc": "CSV/Ocupados",
    "no": "CSV/No ocupados",
}


def _keep(module: str) -> List[str]:
    text = (
        files("lfspanel") / "resources" / "keep_lists" / f"col_{module}.txt"
    ).read_text()
    return [
        ln.split("#", 1)[0].strip()
        for ln in text.splitlines()
        if ln.split("#", 1)[0].strip()
    ]


def _member(z: zipfile.ZipFile, prefix: str) -> str:
    for name in z.namelist():
        if name.startswith(prefix) and name.upper().endswith(".CSV"):
            return name
    raise FileNotFoundError(f"No member starting with {prefix!r} in {z.filename}")


def _read(
    z: zipfile.ZipFile, member: str, cols: List[str], nrows: Optional[int]
) -> pd.DataFrame:
    with z.open(member) as fh:
        df = pd.read_csv(
            fh,
            sep=";",
            dtype=str,
            usecols=lambda c: c.strip().upper() in set(cols),
            keep_default_na=False,
            encoding="latin-1",
            nrows=nrows,
        )
    df.columns = [c.strip().upper() for c in df.columns]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"{member}: missing columns {missing}")
    return df


def read_month(
    month: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    src = path or find_zip(month)
    with zipfile.ZipFile(src) as z:
        cg = _read(z, _member(z, MODULES["cg"]), _keep("cg"), nrows)
        ft = _read(z, _member(z, MODULES["ft"]), _keep("ft"), None)
        oc = _read(z, _member(z, MODULES["oc"]), _keep("oc"), None)
        no = _read(z, _member(z, MODULES["no"]), _keep("no"), None)
    for name, t in (("ft", ft), ("oc", oc), ("no", no)):
        if t.duplicated(KEYS).any():
            raise ValueError(f"{name}: duplicate person keys in {src.name}")
    df = cg.merge(ft, on=KEYS, how="left", validate="1:1")
    df = df.merge(oc, on=KEYS, how="left", validate="1:1")
    df = df.merge(no, on=KEYS, how="left", validate="1:1", suffixes=("", "_no"))
    df["source_file"] = src.name
    return df


def read_raw(
    period: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    """All persons in the quarter's three monthly files (or one month)."""
    if period.is_month or path is not None:
        return read_month(period, nrows=nrows, path=path)
    parts = [
        read_month(Period(f"{period.year}M{m:02d}"), nrows=nrows) for m in period.months
    ]
    return pd.concat(parts, ignore_index=True)
