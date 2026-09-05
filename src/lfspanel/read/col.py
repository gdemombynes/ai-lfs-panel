"""Read GEIH monthly modules and stack the three months of a quarter.

DANE's monthly archives vary: comma- or semicolon-separated CSVs, a ``CSV``
(or ``CVS``) folder either at the top level, under a month folder, or zipped
inside the archive as ``CSV.zip``; non-breaking spaces in file names; and,
from December 2025, months that ship only Stata (``DTA``) and SPSS files. The
reader prefers CSV and falls back to the Stata files.
"""

from __future__ import annotations

import io
import tempfile
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import List, Optional

import pandas as pd

from lfspanel.fetch.col import find_zip
from lfspanel.periods import Period

KEYS = ["DIRECTORIO", "SECUENCIA_P", "ORDEN"]
# module -> file-name prefix (matched on the basename, case-insensitively)
MODULES = {
    "cg": "Caracter",
    "ft": "Fuerza de trabajo",
    "oc": "Ocupado",  # 'Ocupados'; never matches 'No ocupado(s)'
    "no": "No ocupado",  # 'No ocupados' or 'No ocupado' (2024M03)
}
FORMATS = (".CSV", ".DTA")


def _keep(module: str) -> List[str]:
    text = (
        files("lfspanel") / "resources" / "keep_lists" / f"col_{module}.txt"
    ).read_text()
    return [
        ln.split("#", 1)[0].strip()
        for ln in text.splitlines()
        if ln.split("#", 1)[0].strip()
    ]


def _basename(name: str) -> str:
    return name.replace("\\", "/").split("/")[-1].replace("\xa0", " ").strip()


def _find(z: zipfile.ZipFile, prefix: str, ext: str) -> Optional[str]:
    for name in z.namelist():
        base = _basename(name).upper()
        if base.startswith(prefix.upper()) and base.endswith(ext):
            return name
    return None


def _member(z: zipfile.ZipFile, prefix: str, ext: str = ".CSV") -> str:
    name = _find(z, prefix, ext)
    if name is None:
        raise FileNotFoundError(
            f"No {ext} member starting with {prefix!r} in {z.filename}"
        )
    return name


def _module_archive(outer: zipfile.ZipFile) -> tuple:
    """(archive, extension) holding the modules; CSV preferred, then Stata.

    Looks in the archive itself, then in nested ``CSV.zip`` / ``DTA.zip``.
    """
    for ext in FORMATS:
        if _find(outer, MODULES["cg"], ext):
            return outer, ext
    for ext in FORMATS:
        for name in outer.namelist():
            base = _basename(name).lower()
            if base.endswith(".zip") and ext.lower().strip(".") in base:
                inner = zipfile.ZipFile(io.BytesIO(outer.read(name)))
                if _find(inner, MODULES["cg"], ext):
                    return inner, ext
    raise FileNotFoundError(f"No CSV or DTA modules in {outer.filename}")


def _separator(z: zipfile.ZipFile, member: str) -> str:
    """DANE switched from comma- to semicolon-separated CSVs during 2022."""
    with z.open(member) as fh:
        header = fh.readline().decode("latin-1")
    return ";" if header.count(";") >= header.count(",") else ","


def _read_csv(
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
    return df


def _read_dta(
    z: zipfile.ZipFile, member: str, cols: List[str], nrows: Optional[int]
) -> pd.DataFrame:
    """Stata module as strings, integers rendered without a decimal part."""
    import pyreadstat

    with tempfile.NamedTemporaryFile(suffix=".dta", delete=True) as tmp:
        with z.open(member) as src:
            for block in iter(lambda: src.read(1 << 22), b""):
                tmp.write(block)
        tmp.flush()
        _, meta = pyreadstat.read_dta(tmp.name, metadataonly=True)
        actual = {c.upper(): c for c in meta.column_names}
        usecols = [actual[c] for c in cols if c in actual]
        df, _ = pyreadstat.read_dta(
            tmp.name,
            usecols=usecols,
            row_limit=nrows or 0,
            disable_datetime_conversion=True,
        )
    df.columns = [c.upper() for c in df.columns]
    for c in df.columns:
        s = df[c]
        if pd.api.types.is_numeric_dtype(s):
            whole = s.dropna().astype(float)
            if len(whole) and (whole == whole.round()).all():
                df[c] = s.map(lambda v: "" if pd.isna(v) else str(int(v)))
            else:
                df[c] = s.map(lambda v: "" if pd.isna(v) else repr(float(v)))
        else:
            df[c] = s.fillna("").astype(str).str.strip()
    return df


def _read(
    z: zipfile.ZipFile, member: str, cols: List[str], nrows: Optional[int], ext: str
) -> pd.DataFrame:
    df = (
        _read_csv(z, member, cols, nrows)
        if ext == ".CSV"
        else _read_dta(z, member, cols, nrows)
    )
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"{member}: missing columns {missing}")
    return df


def read_month(
    month: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    src = path or find_zip(month)
    with zipfile.ZipFile(src) as outer:
        z, ext = _module_archive(outer)
        cg = _read(z, _member(z, MODULES["cg"], ext), _keep("cg"), nrows, ext)
        ft = _read(z, _member(z, MODULES["ft"], ext), _keep("ft"), None, ext)
        oc = _read(z, _member(z, MODULES["oc"], ext), _keep("oc"), None, ext)
        no = _read(z, _member(z, MODULES["no"], ext), _keep("no"), None, ext)
    for name, t in (("ft", ft), ("oc", oc), ("no", no)):
        if t.duplicated(KEYS).any():
            raise ValueError(f"{name}: duplicate person keys in {src.name}")
    df = cg.merge(ft, on=KEYS, how="left", validate="1:1")
    df = df.merge(oc, on=KEYS, how="left", validate="1:1")
    df = df.merge(no, on=KEYS, how="left", validate="1:1", suffixes=("", "_no"))
    df["source_file"] = f"{src.name}:{ext.lower()}"
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
