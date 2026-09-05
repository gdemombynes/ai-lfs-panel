"""Argentina: EPH continua quarterly user files (text) from INDEC's FTP folder."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import requests

from lfspanel.config import get_country
from lfspanel.fetch.base import FetchResult, download, make_session, url_exists
from lfspanel.periods import Period

BASE = "https://www.indec.gob.ar/ftp/cuadros/menusuperior/eph"
COUNTRY = get_country("arg")


def microdata_url(period: Period) -> str:
    return f"{BASE}/EPH_usu_{period.quarter}_Trim_{period.year}_txt.zip"


def period_dir(period: Period) -> Path:
    return COUNTRY.raw_dir / str(period)


def find_zip(period: Period) -> Path:
    matches = sorted(period_dir(period).glob("EPH_usu_*.zip"))
    if not matches:
        raise FileNotFoundError(
            f"No EPH zip in {period_dir(period)}; run scripts/01_fetch.py first"
        )
    return matches[-1]


def fetch_period(
    period: Period, force: bool = False, session: Optional[requests.Session] = None
) -> List[FetchResult]:
    s = session or make_session()
    url = microdata_url(period)
    target = period_dir(period) / Path(url).name
    # INDEC answers 200 with an HTML page for quarters not yet released
    if not target.exists() and not url_exists(url, s, require_zip=True):
        return [FetchResult(target, "failed", error=f"not published: {url}")]
    return [download(url, target, force=force, session=s)]
