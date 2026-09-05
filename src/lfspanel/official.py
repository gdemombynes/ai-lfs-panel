"""Fetch published headline rates used to validate the harmonization.

Each fetcher returns rows ``period, indicator, value, tolerance, population,
source_url`` for the indicators produced by ``lfspanel.validate.headline_rates``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import openpyxl
import pandas as pd
import requests

from lfspanel.config import RAW
from lfspanel.fetch.base import download, make_session, url_exists
from lfspanel.periods import Period


# ---------------------------------------------------------------- shared
def _rows(
    period: Period,
    url: str,
    total: float,
    lf: float,
    emp: float,
    unemp: float,
    tol: float,
    pop: str,
) -> List[dict]:
    base = {
        "period": str(period),
        "population": pop,
        "source_url": url,
        "tolerance": tol,
    }
    return [
        dict(base, indicator="participation_rate", value=round(100 * lf / total, 3)),
        dict(base, indicator="unemployment_rate", value=round(100 * unemp / lf, 3)),
        dict(base, indicator="employment_rate", value=round(100 * emp / total, 3)),
        dict(base, indicator="population", value=total, tolerance=0.005 * total),
        dict(base, indicator="employed", value=emp, tolerance=0.005 * emp),
    ]


# ---------------------------------------------------------------- Brazil
SIDRA = (
    "https://apisidra.ibge.gov.br/values/t/4092/n1/all/v/all/p/{period}/c629/all"
    "?formato=json"
)
SIDRA_TOL = 0.06  # published rates are rounded to one decimal


def sidra_bra(
    periods: Iterable[Period], session: Optional[requests.Session] = None
) -> pd.DataFrame:
    """PNADC table 4092 (IBGE SIDRA): population 14+, labour force, employed, unemployed."""  # noqa: E501
    s = session or make_session()
    rows: List[dict] = []
    for p in periods:
        url = SIDRA.format(period=f"{p.year}{p.quarter:02d}")
        data = s.get(url, timeout=120).json()[1:]
        counts = {}
        for r in data:
            if r["D2N"].startswith("Pessoas de 14 anos") and r["MN"] == "Mil pessoas":
                counts[r["D4N"]] = float(r["V"].replace(",", ".")) * 1000
        rows += _rows(
            p,
            url,
            counts["Total"],
            counts["Força de trabalho"],
            counts["Força de trabalho - ocupada"],
            counts["Força de trabalho - desocupada"],
            SIDRA_TOL,
            "14+",
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- Colombia
DANE_ANNEX = "https://www.dane.gov.co/files/operaciones/GEIH/anex-GEIH-{mmm}{yyyy}.xlsx"
DANE_MONTHS = [
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
]
DANE_QUARTERS = {"Ene - Mar": 1, "Abr - Jun": 2, "Jul - Sep": 3, "Oct - Dic": 4}
DANE_TOL = 0.05


def _dane_block(ws) -> Dict[str, list]:
    """First (national) block of a DANE annex sheet: year/period headers and label rows."""  # noqa: E501
    rows = list(ws.iter_rows(values_only=True))
    i = next(j for j, r in enumerate(rows) if r and r[0] == "Concepto")
    years, cur = [], None
    for y in rows[i][1:]:
        if y is not None:
            cur = str(y)[:4]
        years.append(cur)
    labels = {}
    for r in rows[i + 2 :]:
        if r and r[0] is not None and str(r[0]).startswith("Total "):
            break
        if r and r[0] is not None:
            labels[str(r[0]).strip().lower()] = r
    return {"years": years, "periods": list(rows[i + 1][1:]), "labels": labels}


def _dane_value(block: dict, prefix: str, col: int) -> float:
    key = next(k for k in block["labels"] if k.startswith(prefix))
    return float(block["labels"][key][col + 1])


def latest_dane_annex(session: requests.Session, newest: Period) -> Path:
    """Download the most recent 'anex-GEIH-<mmm><yyyy>.xlsx' that exists."""
    candidates = [Period(f"{newest.year + 1}M{m:02d}") for m in range(12, 0, -1)]
    candidates += [Period(f"{newest.year}M{m:02d}") for m in range(12, 0, -1)]
    for cand in candidates:
        url = DANE_ANNEX.format(mmm=DANE_MONTHS[cand.month - 1], yyyy=cand.year)
        if url_exists(url, session):
            res = download(
                url, RAW / "col" / "geih" / "docs" / Path(url).name, session=session
            )
            if res.status != "failed":
                return res.path
    raise FileNotFoundError("No DANE annex workbook found")


def annex_col(
    periods: Iterable[Period],
    annex_path: Optional[Path] = None,
    session: Optional[requests.Session] = None,
) -> pd.DataFrame:
    """DANE 'anexo GEIH' workbook, national calendar quarters (sheet 'Total nacional Trim')."""  # noqa: E501
    periods = list(periods)
    if annex_path is None:
        annex_path = latest_dane_annex(session or make_session(), max(periods))
    wb = openpyxl.load_workbook(annex_path, read_only=True, data_only=True)
    block = _dane_block(wb["Total nacional Trim"])
    src = f"DANE anexo GEIH {annex_path.name}, sheet 'Total nacional Trim'"
    wanted = {str(p): p for p in periods}
    rows: List[dict] = []
    for col, (year, label) in enumerate(zip(block["years"], block["periods"])):
        if year is None or label not in DANE_QUARTERS:
            continue
        key = f"{year}Q{DANE_QUARTERS[label]}"
        if key not in wanted:
            continue
        pet = _dane_value(block, "población en edad de trabajar", col) * 1000
        lf = _dane_value(block, "fuerza de trabajo", col) * 1000
        emp = _dane_value(block, "población ocupada", col) * 1000
        unemp = _dane_value(block, "población desocupada", col) * 1000
        rows += _rows(wanted[key], src, pet, lf, emp, unemp, DANE_TOL, "15+")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- Mexico
INEGI_BULLETINS = "https://www.inegi.org.mx/contenidos/saladeprensa/boletines/{path}"
# Quarterly ENOE press bulletins under the boletines folder (published two
# months after the quarter). Earlier bulletins use other folders and layouts;
# add paths here as they are located.
BULLETIN_PATHS = {
    "2023Q4": "2024/enoe/enoe2024_02.pdf",
    "2024Q1": "2024/enoe/enoe2024_05.pdf",
    "2024Q4": "2025/enoe/enoe2025_02.pdf",
    "2025Q1": "2025/enoe/enoe2025_05.pdf",
    "2025Q2": "2025/enoe/enoe2025_08.pdf",
    "2025Q3": "2025/enoe/enoe2025_11.pdf",
    "2025Q4": "2026/enoe/enoe2026_02.pdf",
    "2026Q1": "2026/enoe/enoe2026_05.pdf",
    "2026Q2": "2026/enoe/enoe2026_08.pdf",
}
INEGI_TOL = 0.06  # bulletin rates are rounded to one decimal


def parse_bulletin_text(text: str) -> Dict[str, float]:
    """Headline figures from an ENOE quarterly bulletin's text (population 15+)."""
    t = re.sub(r"\s+", " ", text)
    out: Dict[str, float] = {}
    m = re.search(r"tasa de desocupaci[oó]n[^.%]{0,60}?(\d{1,2}\.\d) ?%", t, re.I)
    if m:
        out["unemployment_rate"] = float(m.group(1))
    m = re.search(r"tasa de participaci[oó]n[^.%]{0,160}?(\d{2}\.\d) ?%", t, re.I)
    if m:
        out["participation_rate"] = float(m.group(1))
    m = re.search(
        r"(\d{2}\.\d) millones de personas estuvieron ocupadas"
        r"|poblaci[oó]n ocupada[^.]{0,40}?(\d{2}\.\d) millones",
        t,
        re.I,
    )
    if m:
        out["employed_millions"] = float(next(g for g in m.groups() if g))
    return out


def bulletins_mex(
    periods: Iterable[Period], session: Optional[requests.Session] = None
) -> pd.DataFrame:
    """INEGI quarterly ENOE bulletins: participation, unemployment, employed (15+)."""
    import pypdf

    s = session or make_session()
    rows: List[dict] = []
    for p in periods:
        path = BULLETIN_PATHS.get(str(p))
        if not path:
            continue
        url = INEGI_BULLETINS.format(path=path)
        dest = RAW / "mex" / "enoe" / "docs" / "bulletins" / Path(path).name
        res = download(url, dest, session=s)
        if res.status == "failed":
            continue
        reader = pypdf.PdfReader(res.path)
        text = " ".join((pg.extract_text() or "") for pg in reader.pages[:4])
        figs = parse_bulletin_text(text)
        base = {
            "period": str(p),
            "population": "15+",
            "source_url": url,
            "tolerance": INEGI_TOL,
        }
        for ind in ("participation_rate", "unemployment_rate"):
            if ind in figs:
                rows.append(dict(base, indicator=ind, value=figs[ind]))
        if "employed_millions" in figs:
            emp = figs["employed_millions"] * 1e6
            rows.append(dict(base, indicator="employed", value=emp, tolerance=0.05e6))
    return pd.DataFrame(rows)


FETCHERS = {"bra": sidra_bra, "col": annex_col, "mex": bulletins_mex}
