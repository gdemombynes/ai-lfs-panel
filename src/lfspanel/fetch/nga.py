"""Nigeria: NBS Labour Force Survey (NLFS) public-use files (manual download).

The NBS microdata catalogue needs a login, so files are downloaded by hand into
``data/raw/nga/nlfs/<YYYYQn>/``. Releases mix formats: SPSS (2024Q1), Stata
(2024Q3, 2024Q4) and zips holding Stata files (2025Q1 onward). ``find_zip``
returns whichever individual-level file the quarter folder holds.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

from lfspanel.config import RAW, get_country
from lfspanel.fetch.base import FetchResult, append_manifest, read_manifest, sha256_file
from lfspanel.periods import Period

COUNTRY = get_country("nga")
BASE = "https://microdata.nigerianstat.gov.ng/index.php/catalog"
CATALOG_IDS: Dict[str, int] = {
    "2022Q4": 74, "2023Q1": 73, "2023Q2": 75, "2023Q3": 76, "2024Q1": 151,
    "2024Q2": 152, "2024Q3": 152, "2024Q4": 152, "2025Q1": 152, "2025Q2": 152,
}  # fmt: skip


def catalog_url(period: Period) -> str:
    try:
        return f"{BASE}/{CATALOG_IDS[str(period)]}/get-microdata"
    except KeyError:
        raise FileNotFoundError(f"No NBS catalogue id recorded for {period}") from None


def period_dir(period: Period) -> Path:
    return COUNTRY.raw_dir / str(period)


def find_zip(period: Period) -> Path:
    """The individual-level file of the quarter (zip, .dta or .sav)."""
    files = sorted(period_dir(period).glob("*"))
    indiv = [
        p for p in files
        if p.suffix.lower() in (".zip", ".dta", ".sav")
        and ("indiv" in p.name.lower() or p.suffix.lower() == ".zip")
    ]  # fmt: skip
    if not indiv:
        raise FileNotFoundError(
            f"No NLFS individual file in {period_dir(period)}; "
            f"download from {catalog_url(period)}"
        )
    return indiv[-1]


def fetch_period(
    period: Period, force: bool = False, session: Optional[requests.Session] = None
) -> List[FetchResult]:
    try:
        path = find_zip(period)
    except FileNotFoundError as exc:
        return [FetchResult(period_dir(period) / "?", "failed", error=f"MANUAL: {exc}")]
    rel = str(path.relative_to(RAW))
    known = read_manifest().get(rel)
    if known and not force:
        return [FetchResult(path, "cached", known["sha256"], int(known["bytes"]))]
    digest = sha256_file(path)
    append_manifest(
        {
            "path": rel,
            "url": catalog_url(period),
            "sha256": digest,
            "bytes": path.stat().st_size,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "http_last_modified": "",
        }
    )
    return [FetchResult(path, "ok", digest, path.stat().st_size)]
