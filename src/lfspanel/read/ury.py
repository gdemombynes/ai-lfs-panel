"""Read one quarter of the ECH: the three monthly follow-up files stacked.

INE's monthly bases hold every interview of the month (rotating panel, six
interviews per household, ``ronda`` = interview number) for persons aged 14
and over, with a monthly weight ``W``. The implantation file of the year adds
the job start date (``f307``, ``f308``), asked at the first interview only;
it is merged on household id, person number and month.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import List, Optional

import pandas as pd

from lfspanel.fetch.ury import RESOURCES, month_file, year_dir
from lfspanel.periods import Period

# variable names are matched case-insensitively: the 2022 files use
# ``region_4``, ``niv_edu`` and ``w`` where later years use upper case
OPTIONAL = {"REGION_4", "SUBEMPLEO", "ronda", "nom_dpto", "f307", "f308"}
KEYS = ["ID", "nper", "mes"]


def keep_list() -> List[str]:
    text = (files("lfspanel") / "resources" / "keep_lists" / "ury.txt").read_text()
    return [
        ln.split("#", 1)[0].strip()
        for ln in text.splitlines()
        if ln.split("#", 1)[0].strip()
    ]


def _encoding(path: Path) -> str:
    """Most monthly bases are latin-1; some 2025 months are UTF-8."""
    try:
        path.read_bytes().decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


def _read_csv(
    path: Path, wanted: List[str], nrows: Optional[int] = None
) -> pd.DataFrame:
    encoding = _encoding(path)
    header = pd.read_csv(
        path, nrows=0, sep=None, engine="python", encoding=encoding
    ).columns
    lower = {c.lower(): c for c in header}
    have = {lower[c.lower()]: c for c in wanted if c.lower() in lower}
    df = pd.read_csv(
        path,
        usecols=list(have),
        dtype=str,
        keep_default_na=False,
        nrows=nrows,
        sep=None,
        engine="python",
        encoding=encoding,
    )
    df = df.rename(columns=have)
    for c in df.columns:
        df[c] = df[c].str.strip()
    return df


def implantation_file(year: int) -> Optional[Path]:
    """The year's implantation (first-interview) base (``ECH_2022.csv`` in 2022)."""
    for name in RESOURCES.get(year, {}).values():
        if name.endswith(".csv") and (
            "implantacion" in name.lower() or name == f"ECH_{year}.csv"
        ):
            path = year_dir(year) / name
            return path if path.exists() else None
    return None


def read_raw(
    period: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    keep = keep_list()
    base = [c for c in keep if c not in ("f307", "f308")]
    parts = []
    paths = [path] if path else [month_file(period, m) for m in period.months]
    for p in paths:
        if not Path(p).exists():
            raise FileNotFoundError(f"{p} missing; run scripts/01_fetch.py first")
        df = _read_csv(Path(p), base, nrows)
        df["source_file"] = Path(p).name
        parts.append(df)
    raw = pd.concat(parts, ignore_index=True)
    missing = [c for c in base if c not in raw.columns]
    if set(missing) - OPTIONAL:
        raise KeyError(f"{period}: missing columns {sorted(set(missing) - OPTIONAL)}")
    for c in missing:
        raw[c] = ""
    imp = implantation_file(period.year) if path is None else None
    if imp is not None:
        start = _read_csv(imp, KEYS + ["f307", "f308"])
        start = start.drop_duplicates(KEYS)
        raw = raw.merge(start, on=KEYS, how="left")
    for c in ("f307", "f308"):
        if c not in raw.columns:
            raw[c] = ""
        raw[c] = raw[c].fillna("")
    raw["W"] = pd.to_numeric(raw["W"], errors="coerce").astype("float64")
    return raw[keep + ["source_file"]].reset_index(drop=True)
