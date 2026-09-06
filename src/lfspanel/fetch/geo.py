"""Georgia: Geostat Labour Force Survey annual databases (SPSS, quarter identifiers).

One zip per calendar year holds a demographic file (all household members)
and the ECSTAT file (persons 15+ with labour status, occupation, industry).
The media id of each year's zip is recorded by hand from
geostat.ge/en/modules/categories/130/labour-force-survey-databases.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import requests

from lfspanel.config import get_country
from lfspanel.fetch.base import FetchResult, download, make_session
from lfspanel.periods import Period

COUNTRY = get_country("geo")
YEAR_ZIPS: Dict[int, str] = {
    2020: "https://geostat.ge/media/48123/Labour-Force-Survey-Database-2020-Year.zip",
    2021: "https://geostat.ge/media/48124/Labour-Force-Survey-Database-2021-Year.zip",
    2022: "https://geostat.ge/media/54646/Labour-Force-Survey-Database-2022-Year.zip",
    2023: "https://geostat.ge/media/63553/Labour-Force-Survey-2023-eng.zip",
    2024: "https://geostat.ge/media/71337/Labour-Force-Survey-2024.zip",
    2025: "https://geostat.ge/media/79807/Labour-Force-Survey-2025.zip",
}


def quarter_number(period: Period) -> int:
    """Geostat's running quarter number: 103 = 2022Q1, 115 = 2025Q1."""
    return 103 + 4 * (period.year - 2022) + (period.quarter - 1)


def year_url(year: int) -> str:
    try:
        return YEAR_ZIPS[year]
    except KeyError:
        raise FileNotFoundError(
            f"No Geostat LFS database recorded for {year}"
        ) from None


def year_dir(year: int) -> Path:
    return COUNTRY.raw_dir / str(year)


def find_zip(period: Period) -> Path:
    matches = sorted(year_dir(period.year).glob("*.zip"))
    if not matches:
        raise FileNotFoundError(
            f"No LFS zip in {year_dir(period.year)}; run scripts/01_fetch.py first"
        )
    return matches[-1]


def fetch_period(
    period: Period, force: bool = False, session: Optional[requests.Session] = None
) -> List[FetchResult]:
    s = session or make_session()
    try:
        url = year_url(period.year)
    except FileNotFoundError as exc:
        return [FetchResult(year_dir(period.year) / "?", "failed", error=str(exc))]
    return [
        download(url, year_dir(period.year) / Path(url).name, force=force, session=s)
    ]
