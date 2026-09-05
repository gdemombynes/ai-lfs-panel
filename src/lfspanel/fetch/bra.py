"""Brazil: PNAD Contínua quarterly microdata from IBGE's open FTP.

Current-year files are named ``PNADC_QQYYYY.zip``; earlier quarters carry a
release-date suffix, ``PNADC_QQYYYY_YYYYMMDD.zip``, and are re-issued when
IBGE revises weights (all quarters were re-released on 2025-08-15 with
Census-2022 projections; 2024 Q2 again on 2026-03-24). The fetcher therefore
lists the year directory and takes the newest matching file.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

import requests

from lfspanel.config import get_country
from lfspanel.fetch.base import FetchResult, download, make_session
from lfspanel.periods import Period

BASE = (
    "https://ftp.ibge.gov.br/Trabalho_e_Rendimento/"
    "Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados"
)
DOC_FILES = [
    "Dicionario_e_input_20221031.zip",
    "Variaveis_PNADC_Trimestral.xls",
    "Estrutura_Ocupacao_COD.xls",
    "Estrutura_Atividade_CNAE_Domiciliar_2_0.xls",
    "Deflatores.zip",
]

COUNTRY = get_country("bra")
_NAME = re.compile(r"PNADC_(\d{2})(\d{4})(?:_(\d{8}))?\.zip")


def period_dir(period: Period) -> Path:
    return COUNTRY.raw_dir / str(period)


def candidate_names(listing_html: str, period: Period) -> List[str]:
    """File names in a directory listing that belong to ``period``, newest last."""
    names = set()
    for m in _NAME.finditer(listing_html):
        if m.group(1) == f"{period.quarter:02d}" and m.group(2) == str(period.year):
            names.add(m.group(0))
    return sorted(names, key=lambda n: _NAME.match(n).group(3) or "99999999")


def release_date(filename: str) -> Optional[str]:
    """``2025-08-15`` from a suffixed name, None for unsuffixed current files."""
    m = _NAME.match(Path(filename).name)
    if m and m.group(3):
        d = m.group(3)
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return None


def resolve_filename(period: Period, session: Optional[requests.Session] = None) -> str:
    """Newest file name for ``period`` according to the FTP directory listing."""
    s = session or make_session()
    r = s.get(f"{BASE}/{period.year}/", timeout=60)
    r.raise_for_status()
    names = candidate_names(r.text, period)
    if not names:
        raise FileNotFoundError(f"No PNADC file for {period} in {BASE}/{period.year}/")
    return names[-1]


def find_zip(period: Period) -> Path:
    """Local zip for ``period`` (newest release if several are present)."""
    matches = sorted(period_dir(period).glob(f"PNADC_{period.ibge_code}*.zip"))
    if not matches:
        raise FileNotFoundError(
            f"No PNADC zip in {period_dir(period)}; run scripts/01_fetch.py first"
        )
    return matches[-1]


def fetch_period(
    period: Period, force: bool = False, session: Optional[requests.Session] = None
) -> List[FetchResult]:
    """Download one quarter's zip (about 200 MB) into data/raw/bra/pnadc/<period>/."""
    s = session or make_session()
    try:
        name = resolve_filename(period, s)
    except (requests.RequestException, FileNotFoundError) as exc:
        return [FetchResult(period_dir(period) / "?", "failed", error=str(exc))]
    url = f"{BASE}/{period.year}/{name}"
    return [download(url, period_dir(period) / name, force=force, session=s)]


def fetch_docs(
    force: bool = False, session: Optional[requests.Session] = None
) -> List[FetchResult]:
    """Download the dictionary, input layout and classification structures."""
    s = session or make_session()
    docs = COUNTRY.raw_dir / "docs"
    return [
        download(f"{BASE}/Documentacao/{name}", docs / name, force=force, session=s)
        for name in DOC_FILES
    ]
