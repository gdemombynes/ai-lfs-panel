"""South Africa: Stats SA QLFS via DataFirst (manual download).

DataFirst requires a login with a CAPTCHA and a per-dataset access form, so
nothing is downloaded here. ``fetch_period`` reports whether the quarter's
file is on disk and otherwise prints the catalogue page to download from.
Save the Stata (or CSV) archive DataFirst serves under
``data/raw/zaf/qlfs/<period>/`` with any name. GLD covers 2008-2024.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

from lfspanel.config import RAW, get_country
from lfspanel.fetch.base import FetchResult, append_manifest, read_manifest, sha256_file
from lfspanel.periods import Period

BASE = "https://www.datafirst.uct.ac.za/dataportal/index.php/catalog"
COUNTRY = get_country("zaf")
# DataFirst catalogue id per quarter (zaf-statssa-qlfs-<year>-q<n>-v1)
CATALOG_IDS: Dict[str, int] = {
    "2022Q1": 902, "2022Q2": 909, "2022Q3": 919, "2022Q4": 932,
    "2023Q1": 939, "2023Q2": 943, "2023Q3": 949, "2023Q4": 954,
    "2024Q1": 960, "2024Q2": 972, "2024Q3": 1001, "2024Q4": 1018,
    "2025Q1": 1026, "2025Q2": 1044, "2025Q3": 1118, "2025Q4": 1126,
    "2026Q1": 1138, "2026Q2": 1247,
}  # fmt: skip


def catalog_url(period: Period) -> str:
    try:
        return f"{BASE}/{CATALOG_IDS[str(period)]}/get-microdata"
    except KeyError:
        raise FileNotFoundError(
            f"No DataFirst catalogue id recorded for {period}"
        ) from None


def period_dir(period: Period) -> Path:
    return COUNTRY.raw_dir / str(period)


def find_zip(period: Period) -> Path:
    matches = sorted(
        p for p in period_dir(period).glob("*") if p.suffix.lower() in (".zip", ".dta")
    )
    if not matches:
        raise FileNotFoundError(
            f"No QLFS file in {period_dir(period)}; download from {catalog_url(period)}"
        )
    return matches[-1]


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
