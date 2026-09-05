"""Fetch published headline rates used to validate the harmonization."""

from __future__ import annotations

from typing import Iterable, List

import pandas as pd
import requests

from lfspanel.fetch.base import make_session
from lfspanel.periods import Period

SIDRA = "https://apisidra.ibge.gov.br/values/t/4092/n1/all/v/all/p/{period}/c629/all?formato=json"
SIDRA_TOL = 0.06  # published rates are rounded to one decimal


def sidra_bra(
    periods: Iterable[Period], session: requests.Session = None
) -> pd.DataFrame:
    """PNADC table 4092 (IBGE SIDRA): population 14+, labour force, employed,
    unemployed.

    Returns one row per period and indicator with the tolerance used in validation.
    """
    s = session or make_session()
    rows: List[dict] = []
    for p in periods:
        code = f"{p.year}{p.quarter:02d}"
        url = SIDRA.format(period=code)
        data = s.get(url, timeout=120).json()[1:]
        counts = {}
        for r in data:
            if r["D2N"].startswith("Pessoas de 14 anos") and r["MN"] == "Mil pessoas":
                counts[r["D4N"]] = float(r["V"].replace(",", ".")) * 1000
        total = counts["Total"]
        lf = counts["Força de trabalho"]
        emp = counts["Força de trabalho - ocupada"]
        unemp = counts["Força de trabalho - desocupada"]
        base = {
            "period": str(p),
            "population": "14+",
            "source_url": url,
            "tolerance": SIDRA_TOL,
        }
        rows += [
            dict(
                base, indicator="participation_rate", value=round(100 * lf / total, 2)
            ),
            dict(base, indicator="unemployment_rate", value=round(100 * unemp / lf, 2)),
            dict(base, indicator="employment_rate", value=round(100 * emp / total, 2)),
            dict(base, indicator="population", value=total, tolerance=0.005 * total),
            dict(base, indicator="employed", value=emp, tolerance=0.005 * emp),
        ]
    return pd.DataFrame(rows)


FETCHERS = {"bra": sidra_bra}
