"""Colombia: GEIH monthly microdata zips from DANE's NADA catalogue.

One catalogue entry per year; each holds twelve monthly zips whose names vary
by year (``GEIH_Enero_2022_Marco_2018.zip``, ``Enero.zip``, ``Ene_2024.zip``,
``Enero 2025.zip``). The download URL is
``/index.php/catalog/<catalog>/download/<resource>`` and needs no login.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Dict, List, Optional

import requests

from lfspanel.config import get_country
from lfspanel.fetch.base import FetchResult, download, fetch_text, make_session
from lfspanel.periods import Period

BASE = "https://microdatos.dane.gov.co/index.php/catalog"
CATALOG_IDS = {2022: 771, 2023: 782, 2024: 819, 2025: 853, 2026: 900}
MONTHS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]  # fmt: skip
_MODAL = re.compile(
    r"mostrarModal\('([^']+\.zip)'\s*,\s*'(https://[^']+/download/(\d+))\s*'\)"
)
COUNTRY = get_country("col")


def month_dir(month: Period) -> Path:
    return COUNTRY.raw_dir / str(month)


def parse_resources(page_html: str) -> Dict[int, tuple]:
    """Map month number -> (file name, download url) from a get-microdata page."""
    out: Dict[int, tuple] = {}
    for name, url, _ in _MODAL.findall(html.unescape(page_html)):
        low = name.lower()
        for i, m in enumerate(MONTHS, start=1):
            if low.startswith(m[:3]) or low.startswith(f"geih_{m}"):
                out.setdefault(i, (name, url))
                break
    return out


def resources_for_year(
    year: int, session: Optional[requests.Session] = None
) -> Dict[int, tuple]:
    s = session or make_session()
    cat = CATALOG_IDS.get(year)
    if cat is None:
        raise KeyError(f"No GEIH catalogue id for {year}; add it to CATALOG_IDS")
    return parse_resources(fetch_text(f"{BASE}/{cat}/get-microdata", s))


def find_zip(month: Period) -> Path:
    matches = sorted(month_dir(month).glob("*.zip"))
    if not matches:
        raise FileNotFoundError(
            f"No GEIH zip in {month_dir(month)}; run scripts/01_fetch.py first"
        )
    return matches[-1]


def fetch_period(
    period: Period, force: bool = False, session: Optional[requests.Session] = None
) -> List[FetchResult]:
    """Download the month, or the three months of a quarter."""
    s = session or make_session()
    months = (
        [period]
        if period.is_month
        else [Period(f"{period.year}M{m:02d}") for m in period.months]
    )
    results: List[FetchResult] = []
    try:
        res = resources_for_year(period.year, s)
    except (requests.RequestException, KeyError) as exc:
        return [FetchResult(month_dir(period) / "?", "failed", error=str(exc))]
    for m in months:
        if m.month not in res:
            results.append(
                FetchResult(
                    month_dir(m) / "?", "failed", error="month not in catalogue"
                )
            )
            continue
        name, url = res[m.month]
        results.append(
            download(url, month_dir(m) / name.replace(" ", "_"), force=force, session=s)
        )
    return results
