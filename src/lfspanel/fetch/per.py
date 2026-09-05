"""Peru: EPEN (Encuesta Permanente de Empleo Nacional) quarterly national files.

INEI's microdata site (``srienaho``) is rendered client-side, so the survey
code of each quarterly release is recorded by hand in ``SURVEY_CODES``.
Module 76 holds the national quarterly person file (``Nacional EPEN Trim.
<months> <year>.dta``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import requests

from lfspanel.config import get_country
from lfspanel.fetch.base import FetchResult, download, make_session
from lfspanel.periods import Period

BASE = "https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA"
MODULE = "76"
COUNTRY = get_country("per")
# survey code per calendar quarter (from the srienaho listing, "EPEN Nacional-Trim")
SURVEY_CODES: Dict[str, int] = {
    "2022Q1": 855, "2022Q2": 857, "2022Q3": 859, "2022Q4": 861,
    "2023Q1": 847, "2023Q2": 849, "2023Q3": 863, "2023Q4": 871,
    "2024Q1": 907, "2024Q2": 917, "2024Q3": 923, "2024Q4": 931,
    "2025Q1": 969, "2025Q2": 980, "2025Q3": 990, "2025Q4": 997,
    "2026Q1": 1034, "2026Q2": 1043,
}  # fmt: skip


def survey_code(period: Period) -> int:
    try:
        return SURVEY_CODES[str(period)]
    except KeyError:
        raise FileNotFoundError(
            f"No EPEN survey code recorded for {period}; add it to fetch/per.py"
        ) from None


def microdata_url(period: Period) -> str:
    return f"{BASE}/{survey_code(period)}-Modulo{MODULE}.zip"


def period_dir(period: Period) -> Path:
    return COUNTRY.raw_dir / str(period)


def find_zip(period: Period) -> Path:
    matches = sorted(period_dir(period).glob(f"*-Modulo{MODULE}.zip"))
    if not matches:
        raise FileNotFoundError(
            f"No EPEN zip in {period_dir(period)}; run scripts/01_fetch.py first"
        )
    return matches[-1]


def fetch_period(
    period: Period, force: bool = False, session: Optional[requests.Session] = None
) -> List[FetchResult]:
    s = session or make_session()
    try:
        url = microdata_url(period)
    except FileNotFoundError as exc:
        return [FetchResult(period_dir(period) / "?", "failed", error=str(exc))]
    return [download(url, period_dir(period) / Path(url).name, force=force, session=s)]
