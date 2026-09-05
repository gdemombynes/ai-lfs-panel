"""Read GEIH monthly CSV modules and stack the three months of a quarter."""

from __future__ import annotations

import io
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import List, Optional

import pandas as pd

from lfspanel.fetch.col import find_zip
from lfspanel.periods import Period

KEYS = ["DIRECTORIO", "SECUENCIA_P", "ORDEN"]
# module -> CSV file-name prefix inside the zip. Archives nest the CSV folder at
# different depths by year and mangle accents, so members are matched by
# basename prefix inside any ".../CSV/" folder, case-insensitively.
MODULES = {
    "cg": "Caracter",
    "ft": "Fuerza de trabajo",
    "oc": "Ocupado",  # 'Ocupados.CSV'; never matches 'No ocupado(s)'
    "no": "No ocupado",  # 'No ocupados.CSV' or 'No ocupado.CSV' (2024M03)
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
    """CSV member whose basename starts with ``prefix`` (any folder, any case).

    Folder names vary (``CSV``, ``CVS``, nested month folders), so only the
    basename and the ``.csv`` extension are matched.
    """
    for name in z.namelist():
        base = name.replace("\\", "/").split("/")[-1]
        if base.upper().startswith(prefix.upper()) and base.upper().endswith(".CSV"):
            return name
    raise FileNotFoundError(f"No CSV member starting with {prefix!r} in {z.filename}")


def _separator(z: zipfile.ZipFile, member: str) -> str:
    """DANE switched from comma- to semicolon-separated CSVs during 2022."""
    with z.open(member) as fh:
        header = fh.readline().decode("latin-1")
    return ";" if header.count(";") >= header.count(",") else ","


def _read(
    z: zipfile.ZipFile, member: str, cols: List[str], nrows: Optional[int]
) -> pd.DataFrame:
    sep = _separator(z, member)
    with z.open(member) as fh:
        df = pd.read_csv(
            fh,
            sep=sep,
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


def _csv_archive(outer: zipfile.ZipFile) -> zipfile.ZipFile:
    """The archive holding the CSV modules: ``outer`` itself or a nested CSV.zip.

    Several 2022 monthly archives wrap the CSV folder in an inner ``CSV.zip``.
    """
    try:
        _member(outer, MODULES["cg"])
        return outer
    except FileNotFoundError:
        pass
    for name in outer.namelist():
        base = Path(name).name.lower()
        if base.endswith(".zip") and "csv" in base:
            return zipfile.ZipFile(io.BytesIO(outer.read(name)))
    raise FileNotFoundError(f"No CSV modules (direct or nested) in {outer.filename}")


def read_month(
    month: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    src = path or find_zip(month)
    with zipfile.ZipFile(src) as outer:
        z = _csv_archive(outer)
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
