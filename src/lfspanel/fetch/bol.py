"""Bolivia: Encuesta Continua de Empleo (ECE) quarterly public-use files.

Two kinds of file, both downloaded by hand because INE's ANDA catalogue
(anda.ine.gob.bo) needs an account:

- one pooled file ``ECE_4T2015_3T2025.zip`` covering every quarter from
  2015Q4 to 2025Q3 on the revised expansion base (``fact_trim_act``), saved
  as ``data/raw/bol/ece/pooled/ECE_4T2015_3T2025.zip``; its CSV member is
  unpacked once and transcoded to UTF-8 (``extract_pooled``) because the
  original mixes UTF-8 and Windows-1252 bytes in free-text fields;
- one zip per quarter after that (ANDA entry per quarter in ``CATALOG``),
  saved as ``data/raw/bol/ece/<YYYYQn>/ECE_<n>T<YYYY>.zip``.

``source_for(period)`` says which file serves a quarter; ``fetch_period``
registers what is present in the manifest and prints where to get the rest.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Dict, List, Optional

import requests

from lfspanel.config import get_country
from lfspanel.fetch.base import FetchResult, download
from lfspanel.periods import Period

BASE = "https://anda.ine.gob.bo/index.php/catalog"
COUNTRY = get_country("bol")
CATALOG: Dict[str, int] = {
    "2021Q2": 91, "2021Q3": 94, "2021Q4": 95,
    "2022Q1": 96, "2022Q2": 97, "2022Q3": 100, "2022Q4": 101,
    "2023Q1": 103, "2023Q2": 104, "2023Q3": 105, "2023Q4": 107,
    "2024Q1": 109, "2024Q2": 110, "2024Q3": 231, "2024Q4": 232,
    "2025Q1": 131, "2025Q2": 170, "2025Q3": 254, "2025Q4": 257,
}  # fmt: skip
POOLED_NAME = "ECE_4T2015_3T2025"
POOLED_FIRST, POOLED_LAST = Period("2015Q4"), Period("2025Q3")
POOLED_URL = f"{BASE}#pooled-{POOLED_NAME}"  # hand-downloaded from INE, no page id


def period_dir(period: Period) -> Path:
    return COUNTRY.raw_dir / str(period)


def pooled_dir() -> Path:
    return COUNTRY.raw_dir / "pooled"


def pooled_zip() -> Path:
    return pooled_dir() / f"{POOLED_NAME}.zip"


def pooled_csv() -> Path:
    """UTF-8 copy of the pooled file's CSV member, made by ``extract_pooled``."""
    return pooled_dir() / f"{POOLED_NAME}.utf8.csv"


def catalog_url(period: Period) -> str:
    key = str(period)
    if key not in CATALOG:
        raise FileNotFoundError(f"No ANDA catalogue entry recorded for {period}")
    return f"{BASE}/{CATALOG[key]}"


def in_pooled(period: Period) -> bool:
    return POOLED_FIRST <= period <= POOLED_LAST


def extract_pooled(force: bool = False) -> Path:
    """Unpack the pooled CSV member and transcode it to UTF-8, once.

    Lines that are not valid UTF-8 (about 0.3 %, establishment names) are
    decoded as Windows-1252 with replacement; no coded field is affected.
    """
    out = pooled_csv()
    if out.exists() and not force:
        return out
    if not pooled_zip().exists():
        raise FileNotFoundError(f"Pooled ECE file missing: {pooled_zip()}")
    part = out.with_name(out.name + ".part")
    with zipfile.ZipFile(pooled_zip()) as z:
        member = f"{POOLED_NAME}.csv"
        with z.open(member) as fh, open(part, "w", encoding="utf-8", newline="") as w:
            for line in fh:
                try:
                    w.write(line.decode("utf-8"))
                except UnicodeDecodeError:
                    w.write(line.decode("cp1252", errors="replace"))
    part.replace(out)
    return out


def find_zip(period: Period) -> Path:
    matches = sorted(period_dir(period).glob("*.zip"))
    if not matches:
        raise FileNotFoundError(
            f"No ECE zip in {period_dir(period)}; download it from "
            f"{catalog_url(period)}/get-microdata (login) and save it there"
        )
    return matches[-1]


def source_for(period: Period) -> Path:
    """The file that serves ``period``: a per-quarter zip if present, else the
    pooled CSV (extracted on demand) for quarters it covers."""
    try:
        return find_zip(period)
    except FileNotFoundError:
        if in_pooled(period) and pooled_zip().exists():
            return extract_pooled()
        raise


def fetch_period(
    period: Period, force: bool = False, session: Optional[requests.Session] = None
) -> List[FetchResult]:
    """Register a hand-downloaded file in the manifest, or say where to get it."""
    try:
        path = source_for(period)
    except FileNotFoundError as exc:
        return [FetchResult(period_dir(period) / "?", "failed", error=str(exc))]
    if path == pooled_csv():
        # download() with an existing file only checksums and records it
        return [download(POOLED_URL, pooled_zip(), force=False)]
    return [download(catalog_url(period), path, force=False)]
