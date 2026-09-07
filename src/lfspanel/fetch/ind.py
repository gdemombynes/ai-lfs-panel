"""India: PLFS unit-level data from MoSPI's microdata portal (NADA REST API).

MoSPI publishes two kinds of PLFS unit-level release that cover our window:

* calendar-year files (``cy2021`` .. ``cy2025``): first-visit records only,
  one file per year with a quarter identifier, multipliers built for annual
  estimates (the 2021-2024 files come from the old design, urban rotational
  panel plus rural first visits; the 2025 file is the new design);
* the quarterly file (``q2025``): all visits of the redesigned survey from
  2025Q2 with the quarterly multipliers used in the quarterly bulletins.

``release_for`` picks the release a quarter is read from: calendar-year files
for 2021Q1-2025Q1, the quarterly file from 2025Q2. Each release is downloaded
once into ``data/raw/ind/plfs/<label>/`` (Stata zip plus layout and README).

The portal's certificate chain (an eMudhra intermediate) is rejected by the
LibreSSL that Python and curl link on this Mac, so every request goes through
``curl -k``. The API key is read from ``IND_API`` or ``MOSPI_API_KEY`` in
``.env`` and sent as ``X-API-KEY``; it is never written to disk or logs.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

from lfspanel.config import RAW, get_country
from lfspanel.fetch.base import (
    USER_AGENT,
    FetchResult,
    append_manifest,
    read_manifest,
    sha256_file,
)
from lfspanel.periods import Period

API = "https://microdata.gov.in/NADA/index.php/api"
COUNTRY = get_country("ind")


@dataclass(frozen=True)
class Release:
    label: str
    idno: str  # NADA study id
    first: str  # first quarter served from this release
    last: str
    person_member: str  # regex on the person-level .dta member name
    hh_member: str  # regex on the household-level .dta member name


_CY = (r"cperv1\.dta$", r"chhv1\.dta$")
RELEASES: List[Release] = [
    Release(
        "cy2021", "DDI-IND-CSO-PLFS-2021-21", "2021Q1", "2021Q4", _CY[0], r"hhv1\.dta$"
    ),
    Release("cy2022", "DDI-IND-CSO-PLFS-2022-22", "2022Q1", "2022Q4", *_CY),
    Release("cy2023", "DDI-IND-CSO-PLFS-2023-23", "2023Q1", "2023Q4", *_CY),
    Release("cy2024", "DDI-IND-NSO-PLFS-2024-24", "2024Q1", "2024Q4", *_CY),
    Release(
        "cy2025",
        "DDI-IND-NSO-PLFS-Jan2025-Dec2025",
        "2025Q1",
        "2025Q1",
        r"cperv12025\.dta$",
        r"chhv12025\.dta$",
    ),
    Release(
        "q2025",
        "DDI-IND-NSO-PLFS-Apr-Jun2025-to-Oct-Dec2025",
        "2025Q2",
        "2025Q4",
        r"mper.*\.dta$",
        r"mhh.*\.dta$",
    ),
]


def release_for(period: Period) -> Release:
    for rel in RELEASES:
        if Period(rel.first) <= period <= Period(rel.last):
            return rel
    raise FileNotFoundError(
        f"No PLFS unit-level release recorded for {period}; add it to fetch/ind.py"
    )


def release_dir(rel: Release) -> Path:
    return COUNTRY.raw_dir / rel.label


def find_zip(period: Period) -> Path:
    rel = release_for(period)
    matches = sorted(
        p for p in release_dir(rel).glob("*.zip") if "stata" in p.name.lower()
    )
    if not matches:
        raise FileNotFoundError(
            f"No PLFS Stata zip in {release_dir(rel)}; run scripts/01_fetch.py first"
        )
    return matches[-1]


def api_key() -> str:
    for name in ("IND_API", "MOSPI_API_KEY"):
        value = os.environ.get(name, "").strip().strip('"')
        if value:
            return value
    raise RuntimeError("IND_API (or MOSPI_API_KEY) is not set; add it to .env")


def _curl(url: str, dest: Optional[Path] = None, timeout: int = 120) -> bytes:
    cmd = [
        "curl", "-sS", "-k", "-L", "-A", USER_AGENT, "-m", str(timeout),
        "-H", f"X-API-KEY: {api_key()}", url,
    ]  # fmt: skip
    if dest is not None:
        cmd += ["-o", str(dest)]
    proc = subprocess.run(cmd, capture_output=True, timeout=timeout + 30)
    if proc.returncode != 0:
        raise requests.RequestException(
            f"curl exit {proc.returncode}: {proc.stderr.decode('utf-8', 'ignore')}"
        )
    return proc.stdout


def api_json(path: str) -> dict:
    return json.loads(_curl(f"{API}/{path}").decode("utf-8"))


def list_resources(idno: str) -> List[dict]:
    """Every resource (microdata files and documents) attached to a study."""
    return api_json(f"resources/{idno}").get("resources", [])


def select_resources(resources: List[dict]) -> Dict[str, dict]:
    """The Stata microdata zip plus the layout and README documents."""
    out: Dict[str, dict] = {}
    for r in resources:
        name = (r.get("filename") or "").lower()
        if r.get("is_microdata") and "stata" in name:
            out["data"] = r
        elif re.search(r"layout", name) and "layout" not in out:
            out["layout"] = r
        elif re.search(r"readme", name) and "readme" not in out:
            out["readme"] = r
    if "data" not in out:
        raise FileNotFoundError("No Stata microdata resource in the study")
    return out


def _download(url: str, dest: Path, force: bool = False) -> FetchResult:
    """curl -k download with the same manifest bookkeeping as fetch.base."""
    rel = str(dest.resolve().relative_to(RAW.resolve()))
    known = read_manifest().get(rel)
    if dest.exists() and not force:
        digest = sha256_file(dest)
        if known and known["sha256"] == digest:
            return FetchResult(dest, "cached", digest, dest.stat().st_size)
        _register(rel, url, dest, digest)
        return FetchResult(dest, "cached", digest, dest.stat().st_size)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    try:
        _curl(url, part, timeout=3600)
    except (requests.RequestException, subprocess.TimeoutExpired) as exc:
        if part.exists():
            part.unlink()
        return FetchResult(dest, "failed", error=str(exc))
    if part.stat().st_size < 1000 or part.read_bytes()[:1] == b"{":
        # the API answers a small JSON document instead of the file on error
        msg = part.read_bytes()[:200].decode("utf-8", "ignore")
        part.unlink()
        return FetchResult(dest, "failed", error=f"unexpected reply: {msg}")
    part.replace(dest)
    digest = sha256_file(dest)
    _register(rel, url, dest, digest)
    return FetchResult(dest, "ok", digest, dest.stat().st_size)


def _register(rel: str, url: str, dest: Path, digest: str) -> None:
    append_manifest(
        {
            "path": rel,
            "url": url.split("?")[0],
            "sha256": digest,
            "bytes": dest.stat().st_size,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "http_last_modified": "",
        }
    )


def fetch_release(rel: Release, force: bool = False) -> List[FetchResult]:
    try:
        chosen = select_resources(list_resources(rel.idno))
    except (requests.RequestException, FileNotFoundError, ValueError) as exc:
        return [FetchResult(release_dir(rel) / "?", "failed", error=str(exc))]
    out = []
    for kind in ("data", "layout", "readme"):
        r = chosen.get(kind)
        if r is None:
            continue
        url = r["_links"]["download"]
        name = re.sub(r"\s+\(\d+\)", "", r["filename"]).replace(" ", "_")
        out.append(_download(url, release_dir(rel) / name, force=force))
    return out


def fetch_period(
    period: Period, force: bool = False, session: Optional[requests.Session] = None
) -> List[FetchResult]:
    try:
        rel = release_for(period)
    except FileNotFoundError as exc:
        return [FetchResult(COUNTRY.raw_dir / "?", "failed", error=str(exc))]
    return fetch_release(rel, force=force)
