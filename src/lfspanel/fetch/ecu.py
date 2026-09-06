"""Ecuador: ENEMDU quarterly SPSS zips from INEC's document store.

Files sit under ``documentos/web-inec/EMPLEO/{YYYY}/Trimestre_{I..IV}/`` with
names that vary slightly by year; ``CANDIDATES`` lists the patterns seen.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import requests

from lfspanel.config import get_country
from lfspanel.fetch.base import FetchResult, download, make_session, url_exists
from lfspanel.periods import Period

BASE = "https://www.ecuadorencifras.gob.ec/documentos/web-inec/EMPLEO"
# 2023 onwards: Trimestre_{r}; 2022 used one folder name per quarter, including a
# stray control character (%1F) in the fourth quarter's folder name
FOLDERS = [
    "{y}/Trimestre_{r}",
    "{y}/Trimestre-{months}-{y}",
    "{y}/Trimestre_{r}_{y}",
    "{y}/Trimestre%1F_{r}_{y}",
    "{y}/Trimestre%1F_{months_}_{y}",
]
FILES = [
    "1_BDD_ENEMDU_{y}_{r}_TRIMESTRE_SPSS.zip",
    "BDD_ENEMDU_{y}_{r}_TRIMESTRE_SPSS.zip",
    "1_BDD_ENEMDU_{y}_{r}_Trimestre_SPSS.zip",
    "BDD_ENEMDU_{y}_{r}_Trimestre_SPSS.zip",
]
CANDIDATES = [f"{d}/{f}" for d in FOLDERS for f in FILES]
# quarters whose published file name does not follow any pattern (typos included)
OVERRIDES = {
    "2021Q3": "2021/Trimestre-julio-septiembre-2021/"
    "1_BDD_ENEMDU_2021_IlI_TRIMESTRE_SPSS.zip",  # 'IlI' as published
    "2021Q4": "2021/Trimestre-octubre-diciembre-2021/"
    "1_BDD_ENEMDU_2021_IV_TRIMESTRE_SPSS.zip",
}
MONTHS = {
    1: "enero-marzo",
    2: "abril-junio",
    3: "julio-septiembre",
    4: "octubre-diciembre",
}
COUNTRY = get_country("ecu")


def period_dir(period: Period) -> Path:
    return COUNTRY.raw_dir / str(period)


def candidate_urls(period: Period) -> List[str]:
    months = MONTHS[period.quarter]
    months_ = months.replace("-", "_")
    if str(period) in OVERRIDES:
        return [f"{BASE}/{OVERRIDES[str(period)]}"]
    return [
        BASE
        + "/"
        + c.format(y=period.year, r=period.roman, months=months, months_=months_)
        for c in CANDIDATES
    ]


def resolve_url(period: Period, session: Optional[requests.Session] = None) -> str:
    s = session or make_session()
    for url in candidate_urls(period):
        if url_exists(url, s):
            return url
    raise FileNotFoundError(f"No ENEMDU zip found for {period}")


def find_zip(period: Period) -> Path:
    matches = sorted(period_dir(period).glob("*.zip"))
    if not matches:
        raise FileNotFoundError(
            f"No ENEMDU zip in {period_dir(period)}; run scripts/01_fetch.py first"
        )
    return matches[-1]


def fetch_period(
    period: Period, force: bool = False, session: Optional[requests.Session] = None
) -> List[FetchResult]:
    s = session or make_session()
    try:
        url = resolve_url(period, s)
    except (requests.RequestException, FileNotFoundError) as exc:
        return [FetchResult(period_dir(period) / "?", "failed", error=str(exc))]
    return [download(url, period_dir(period) / Path(url).name, force=force, session=s)]
