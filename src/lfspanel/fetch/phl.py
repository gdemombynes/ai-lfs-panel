"""Philippines: PSA Labor Force Survey public-use files (manual download).

PSADA (psada.psa.gov.ph) sits behind a Cloudflare challenge and a login, so
files are downloaded by hand and stored by survey month under
``data/raw/phl/lfs/<YYYYMnn>/``. The full-sample rounds are January, April,
July and October; ``fetch_period`` for a quarter looks for the round in the
quarter's first month.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import requests

from lfspanel.config import RAW, get_country
from lfspanel.fetch.base import FetchResult, append_manifest, read_manifest, sha256_file
from lfspanel.periods import Period

COUNTRY = get_country("phl")
CATALOG = "https://psada.psa.gov.ph/catalog/LFS"


def round_month(period: Period) -> str:
    """Survey month of the full-sample round for a quarter (e.g. 2025Q2 -> 2025M04)."""
    return f"{period.year}M{period.quarter * 3 - 2:02d}"


def month_dir(period: Period) -> Path:
    return COUNTRY.raw_dir / round_month(period)


def find_zip(period: Period) -> Path:
    files = month_dir(period).glob("*")
    matches = sorted(
        p for p in files if p.suffix.lower() in (".zip", ".csv", ".dta", ".sav")
    )
    if not matches:
        raise FileNotFoundError(
            f"No LFS file in {month_dir(period)}; download the {round_month(period)} "
            f"public-use file from {CATALOG}"
        )
    return matches[-1]


def fetch_period(
    period: Period, force: bool = False, session: Optional[requests.Session] = None
) -> List[FetchResult]:
    try:
        path = find_zip(period)
    except FileNotFoundError as exc:
        return [FetchResult(month_dir(period) / "?", "failed", error=f"MANUAL: {exc}")]
    rel = str(path.relative_to(RAW))
    known = read_manifest().get(rel)
    if known and not force:
        return [FetchResult(path, "cached", known["sha256"], int(known["bytes"]))]
    digest = sha256_file(path)
    append_manifest(
        {
            "path": rel,
            "url": CATALOG,
            "sha256": digest,
            "bytes": path.stat().st_size,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "http_last_modified": "",
        }
    )
    return [FetchResult(path, "ok", digest, path.stat().st_size)]
