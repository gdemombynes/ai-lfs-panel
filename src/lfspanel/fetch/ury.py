"""Uruguay: Encuesta Continua de Hogares (ECH) monthly files from INE's NADA.

INE publishes one catalogue entry per year (``CATALOG``) with the twelve
monthly follow-up files (``ECH_MM_YYYY.csv``), the implantation file, the
variable dictionary and methodological notes. Downloads are open but sit
behind a terms-of-use form: a POST of ``accept=Aceptar`` on the entry's
``get-microdata`` page stores the acceptance in the session cookie, after
which ``catalog/<id>/download/<resource>`` serves the file. The resource ids
are recorded by hand in ``RESOURCES`` (INE's portal has no API listing).

The user accepted INE's terms (research use only, no redistribution, cite
INE, send INE a copy of publications) on 2026-09-07.
"""

from __future__ import annotations

import subprocess
import tempfile
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

BASE = "https://www4.ine.gub.uy/Anda5/index.php/catalog"
COUNTRY = get_country("ury")
CATALOG: Dict[int, int] = {2021: 716, 2022: 730, 2023: 735, 2024: 767, 2025: 779}
# year -> {resource id: file name}; monthly follow-up files first, then the
# implantation / annual base, then documentation
RESOURCES: Dict[int, Dict[int, str]] = {
    2021: {
        970: "ECH_2021_sem1_terceros.csv",
        972: "Bases_ECH_sem2_2021.rar",
        1236: "ECH_implantacion_sem2_2021.csv",
        1238: "Diccionario_ECH_2021_Sem2.pdf",
        1237: "Nota_cambio_base_semestre2_2021.pdf",
    },
    2022: {
        **{1130 + m: f"ECH_{m:02d}_22.csv" for m in range(1, 13)},
        1244: "ECH_2022.csv",
        1235: "Diccionario_variables_ECH_2022.pdf",
        1144: "Cuestionario_ECH_2022_implantacion.pdf",
        1145: "Cuestionario_ECH_2022_seguimiento.pdf",
        1148: "Nota_cambio_de_base_2022.pdf",
        1149: "Nota_microdatos_ECH_2022.pdf",
        1234: "Segunda_nota_cambio_base_anual_2022.pdf",
    },
    2023: {
        **{1279 + m: f"ECH_{m:02d}_23.csv" for m in range(1, 13)},
        1264: "ECH_implantacion_2023.csv",
        1271: "Diccionario_variables_ECH_2023.pdf",
        1227: "Formulario_implantacion_2023.pdf",
        1228: "Formulario_seguimiento_2023.pdf",
        1272: "Nota_ECH_2023.pdf",
    },
    2024: {
        **{1356 + m: f"ECH_{m:02d}_24.csv" for m in range(1, 13)},
        1501: "ECH_implantacion_2024.csv",
        1378: "Diccionario_ECH_2024.pdf",
        1380: "Cuestionario_implantacion_2024.pdf",
        1381: "Cuestionario_seguimiento_2024.pdf",
        1383: "Nota_ECH_2024.pdf",
    },
    2025: {
        1447: "ECH_01_2025.csv", 1448: "ECH_02_2025.csv", 1449: "ECH_03_2025.csv",
        1450: "ECH_04_2025.csv", 1451: "ECH_05_2025.csv", 1452: "ECH_06_2025.csv",
        1453: "ECH_07_2025.csv", 1460: "ECH_08_2025.csv", 1454: "ECH_09_2025.csv",
        1455: "ECH_10_2025.csv", 1456: "ECH_11_2025.csv", 1457: "ECH_12_2025.csv",
        1482: "ECH_implantacion_2025.csv",
        1466: "Diccionario_2025.pdf",
        1468: "Cuestionario_ECH_2025_implantacion.pdf",
        1469: "Cuestionario_ECH_2025_seguimiento.pdf",
        1483: "Nota_cambio_base_ECH2025.pdf",
        1487: "Nota_microdatos_ECH_anual_2025.pdf",
    },
}  # fmt: skip


# monthly files shipped inside an archive rather than as separate resources
ARCHIVED: Dict[int, str] = {2021: "Bases_ECH_sem2_2021.rar"}


def year_dir(year: int) -> Path:
    return COUNTRY.raw_dir / str(year)


def month_file(period: Period, month: int) -> Path:
    """Path of one monthly follow-up file (name pattern differs by year)."""
    names = RESOURCES[period.year]
    target = f"ECH_{month:02d}_"
    for name in names.values():
        if name.startswith(target) and name.endswith(".csv"):
            return year_dir(period.year) / name
    if period.year in ARCHIVED:
        return year_dir(period.year) / f"ECH_{month:02d}_{period.year}.csv"
    raise FileNotFoundError(f"No monthly file recorded for {period.year}-{month:02d}")


def extract_archive(year: int) -> List[Path]:
    """Unpack the year's RAR of monthly bases next to it (bsdtar reads RAR)."""
    archive = year_dir(year) / ARCHIVED[year]
    if not archive.exists():
        return []
    subprocess.run(
        ["bsdtar", "-xf", str(archive), "-C", str(year_dir(year))],
        check=True,
        capture_output=True,
    )
    return sorted(year_dir(year).glob(f"ECH_??_{year}.csv"))


def _curl(args: List[str], timeout: int) -> subprocess.CompletedProcess:
    # INE's certificate chain is rejected by LibreSSL; -k as for microdata.gov.in
    cmd = ["curl", "-sS", "-k", "-L", "-A", USER_AGENT, "-m", str(timeout)] + args
    return subprocess.run(cmd, capture_output=True, timeout=timeout + 30)


def accept_terms(catalog_id: int, cookies: Path) -> None:
    """POST the terms form so the session may download the entry's files."""
    url = f"{BASE}/{catalog_id}/get-microdata"
    _curl(["-c", str(cookies), "-b", str(cookies), "-o", "/dev/null", url], 60)
    args = ["-c", str(cookies), "-b", str(cookies), "-d", "accept=Aceptar"]
    proc = _curl(args + ["-o", "/dev/null", url], 60)
    if proc.returncode != 0:
        raise requests.RequestException(proc.stderr.decode("utf-8", "ignore"))


def _download(url: str, dest: Path, cookies: Path, force: bool) -> FetchResult:
    rel = str(dest.resolve().relative_to(RAW.resolve()))
    known = read_manifest().get(rel)
    if dest.exists() and not force:
        digest = sha256_file(dest)
        if not (known and known["sha256"] == digest):
            _register(rel, url, dest, digest)
        return FetchResult(dest, "cached", digest, dest.stat().st_size)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    proc = _curl(["-b", str(cookies), "-o", str(part), url], 3600)
    if proc.returncode != 0 or not part.exists() or part.stat().st_size < 1000:
        if part.exists():
            part.unlink()
        return FetchResult(dest, "failed", error=proc.stderr.decode("utf-8", "ignore"))
    head = part.read_bytes()[:200].lstrip().lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html"):
        part.unlink()
        return FetchResult(
            dest, "failed", error="portal answered HTML (terms not accepted?)"
        )
    part.replace(dest)
    digest = sha256_file(dest)
    _register(rel, url, dest, digest)
    return FetchResult(dest, "ok", digest, dest.stat().st_size)


def _register(rel: str, url: str, dest: Path, digest: str) -> None:
    append_manifest(
        {
            "path": rel,
            "url": url,
            "sha256": digest,
            "bytes": dest.stat().st_size,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "http_last_modified": "",
        }
    )


def fetch_year(year: int, force: bool = False, docs: bool = True) -> List[FetchResult]:
    if year not in CATALOG:
        return [
            FetchResult(
                year_dir(year) / "?", "failed", error=f"no catalogue entry for {year}"
            )
        ]
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        cookies = Path(tmp) / "cookies.txt"
        try:
            accept_terms(CATALOG[year], cookies)
        except requests.RequestException as exc:
            return [FetchResult(year_dir(year) / "?", "failed", error=str(exc))]
        for rid, name in RESOURCES[year].items():
            if not docs and name.lower().endswith(".pdf"):
                continue
            url = f"{BASE}/{CATALOG[year]}/download/{rid}"
            out.append(_download(url, year_dir(year) / name, cookies, force))
    if year in ARCHIVED and all(r.status != "failed" for r in out):
        extract_archive(year)
    return out


def fetch_period(
    period: Period, force: bool = False, session: Optional[requests.Session] = None
) -> List[FetchResult]:
    """The three monthly files of a quarter (the whole year is fetched once)."""
    results = fetch_year(period.year, force=force, docs=True)
    wanted = {
        month_file(period, m).name for m in period.months if _has_month(period, m)
    }
    return [r for r in results if r.path.name in wanted or r.status == "failed"]


def _has_month(period: Period, month: int) -> bool:
    try:
        month_file(period, month)
        return True
    except FileNotFoundError:
        return False
