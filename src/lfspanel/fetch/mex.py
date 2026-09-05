"""Mexico: ENOE quarterly microdata (CSV zips) from INEGI.

File names changed with the "nueva edición": 2020 Q3 to 2022 Q4 are
``enoe_n_YYYY_trimN_csv.zip`` with members ``ENOEN_*``; from 2023 Q1 they are
``enoe_YYYY_trimN_csv.zip`` with members ``ENOE_*``. INEGI answers a missing
path with an HTML page and status 200, so the fetcher checks the zip magic
bytes before downloading.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import requests

from lfspanel.config import get_country
from lfspanel.fetch.base import FetchResult, download, make_session
from lfspanel.periods import Period

BASE = "https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/microdatos"
COUNTRY = get_country("mex")


def candidate_names(period: Period) -> List[str]:
    y, n = period.year, period.quarter
    names = [f"enoe_{y}_trim{n}_csv.zip", f"enoe_n_{y}_trim{n}_csv.zip"]
    return names if y >= 2023 else names[::-1]


def period_dir(period: Period) -> Path:
    return COUNTRY.raw_dir / str(period)


def is_zip_url(url: str, session: requests.Session) -> bool:
    r = session.get(url, headers={"Range": "bytes=0-3"}, timeout=60)
    return r.status_code in (200, 206) and r.content[:4] == b"PK\x03\x04"


def resolve_filename(period: Period, session: Optional[requests.Session] = None) -> str:
    s = session or make_session()
    for name in candidate_names(period):
        if is_zip_url(f"{BASE}/{name}", s):
            return name
    raise FileNotFoundError(f"No ENOE zip for {period} under {BASE}")


def find_zip(period: Period) -> Path:
    matches = sorted(period_dir(period).glob("enoe*_csv.zip"))
    if not matches:
        raise FileNotFoundError(
            f"No ENOE zip in {period_dir(period)}; run scripts/01_fetch.py first"
        )
    return matches[-1]


def fetch_period(
    period: Period, force: bool = False, session: Optional[requests.Session] = None
) -> List[FetchResult]:
    s = session or make_session()
    try:
        name = resolve_filename(period, s)
    except (requests.RequestException, FileNotFoundError) as exc:
        return [FetchResult(period_dir(period) / "?", "failed", error=str(exc))]
    return [
        download(f"{BASE}/{name}", period_dir(period) / name, force=force, session=s)
    ]
