"""Sector cells for the IT and business-process services difference in differences.

Cells are country x quarter x industry group x sex. The treated group is IT
and business-process services (ISIC Rev. 4 divisions 62, 63 and 82; South
Africa 62 only because SIC 88 lumps business services; Mexico ENOE code 5611,
business support and employment services, because the ENOE classifier does
not separate computer services). Controls are the other white-collar service
industries: finance and insurance (64 to 66), professional, scientific and
technical services (69 to 75) and public administration (84). Outcomes per
cell are log employment, the shares of workers aged 15 to 29 and under 25,
and the share and log employment of clerical, service and sales occupations
(ISCO major groups 4 and 5). The frame has the same shape as the occupation
cells, so :func:`lfspanel.analysis.estimate_did` estimates it unchanged.
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

import duckdb
import numpy as np
import pandas as pd

from lfspanel.analysis import (
    MIN_CELL_N,
    REF_PERIOD,
    _min_period_clause,
    _visit_clauses,
    quarter_index,
)
from lfspanel.config import PROCESSED

SECTOR_CELLS_PATH = PROCESSED / "cells" / "sector_cells.parquet"
TREATED = "itbpo"
GROUPS: Dict[str, Tuple[str, ...]] = {
    "itbpo": ("62", "63", "82"),
    "finance": ("64", "65", "66"),
    "profserv": ("69", "70", "71", "72", "73", "74", "75"),
    "pubadmin": ("84",),
}
CONTROLS = ("finance", "profserv", "pubadmin")
LABELS = {
    "itbpo": "IT and business-process services (ISIC 62, 63, 82)",
    "finance": "finance and insurance (ISIC 64--66)",
    "profserv": "professional, scientific and technical services (ISIC 69--75)",
    "pubadmin": "public administration (ISIC 84)",
}
# Country-specific definitions of the treated group (docs/harmonization/*.md).
TREATED_SQL: Dict[str, str] = {
    "ZAF": "substr(e.industrycat_isic, 1, 2) = '62'",
    "MEX": "e.industry_orig = '5611'",
}
EXCLUDED = ("NGA",)  # no 2022 baseline


def _group_sql(cc: str) -> str:
    """CASE expression assigning each worker to a sector group or NULL."""
    d2 = "substr(e.industrycat_isic, 1, 2)"
    treated = TREATED_SQL.get(cc, f"{d2} IN ('62', '63', '82')")
    parts = [f"WHEN {treated} THEN 'itbpo'"]
    for g in CONTROLS:
        codes = ", ".join(f"'{c}'" for c in GROUPS[g])
        parts.append(f"WHEN {d2} IN ({codes}) THEN '{g}'")
    return "CASE " + " ".join(parts) + " END"


def build_sector_cells(
    con: duckdb.DuckDBPyConnection,
    countries: Optional[Sequence[str]] = None,
    min_age: int = 15,
) -> pd.DataFrame:
    """Country x quarter x sector group x sex cells from the ``employed`` view."""
    if countries is None:
        countries = [
            r[0]
            for r in con.execute(
                "SELECT DISTINCT countrycode FROM employed "
                "WHERE source = 'own' ORDER BY 1"
            ).fetchall()
        ]
    frames = []
    for cc in countries:
        if cc in EXCLUDED:
            continue
        cte, w, extra = _visit_clauses(cc)
        extra += _min_period_clause(cc)
        join = (
            "LEFT JOIN scale s ON s.period = e.period AND s.urban = e.urban"
            if cte
            else ""
        )
        isco1 = "substr(e.occup_isco, 1, 1)"
        cler = f"CAST(coalesce({isco1} IN ('4', '5'), FALSE) AS INTEGER)"
        prof = f"CAST(coalesce({isco1} IN ('1', '2', '3'), FALSE) AS INTEGER)"
        frames.append(
            con.execute(
                f"""
                {cte}
                SELECT countrycode, period, sector, male,
                       count(*) AS n,
                       sum(w) AS emp,
                       sum(w * young) / sum(w) AS young_share,
                       sum(w * u25) / sum(w) AS u25_share,
                       sum(w * cler) / sum(w) AS cler_share,
                       sum(w * cler) AS cler_emp,
                       sum(w * prof) AS prof_emp
                FROM (
                    SELECT e.countrycode, e.period, e.male, {w} AS w,
                           {_group_sql(cc)} AS sector,
                           CAST(e.age BETWEEN 15 AND 29 AS INTEGER) AS young,
                           CAST(e.age < 25 AS INTEGER) AS u25,
                           {cler} AS cler,
                           {prof} AS prof
                    FROM employed e {join}
                    WHERE e.source = 'own' AND e.countrycode = '{cc}'
                      AND e.age >= {min_age} AND e.male IS NOT NULL{extra}
                )
                WHERE sector IS NOT NULL
                GROUP BY 1, 2, 3, 4
                """
            ).df()
        )
    cells = pd.concat(frames, ignore_index=True)
    cells["male"] = cells["male"].astype("Int8")
    cells["treated"] = (cells["sector"] == TREATED).astype("Int8")
    cells["small"] = (cells["n"] < MIN_CELL_N).astype("Int8")
    return cells.sort_values(["countrycode", "period", "sector", "male"]).reset_index(
        drop=True
    )


def sector_frame(
    cells: pd.DataFrame,
    ref: str = REF_PERIOD,
    controls: Sequence[str] = CONTROLS,
    min_n: int = MIN_CELL_N,
) -> pd.DataFrame:
    """Balanced sector-cell panel in the shape ``estimate_did`` expects.

    Keeps the treated group and ``controls``; the sample is fixed at the
    baseline year of ``ref``: a cell enters when its mean unweighted count
    over that year reaches ``min_n`` and is then kept in every quarter with
    zero employment where absent. ``cluster`` is country x sector group and
    ``cat`` is country x sex x quarter.
    """
    df = cells[cells["sector"].isin([TREATED] + list(controls))].copy()
    df["cell"] = df["countrycode"] + "|" + df["sector"] + "|" + df["male"].astype(str)
    base_rows = df[df["period"].str.startswith(ref[:4])]
    base = base_rows.groupby("cell").agg(emp_base=("emp", "mean"), n_base=("n", "mean"))
    base = base[base["n_base"] >= min_n]
    keep = df[df["cell"].isin(base.index)]
    periods = sorted(df["period"].unique())
    attrs = keep.drop_duplicates("cell").set_index("cell")[
        ["countrycode", "sector", "male", "treated"]
    ]
    grid = pd.MultiIndex.from_product(
        [attrs.index, periods], names=["cell", "period"]
    ).to_frame(index=False)
    grid = grid.join(attrs, on="cell")
    vals = keep[
        [
            "cell",
            "period",
            "n",
            "emp",
            "young_share",
            "u25_share",
            "cler_share",
            "cler_emp",
            "prof_emp",
        ]
    ]
    out = grid.merge(vals, on=["cell", "period"], how="left")
    out["n"] = out["n"].fillna(0).astype(int)
    for c in ("emp", "cler_emp", "prof_emp"):
        out[c] = out[c].fillna(0.0)
    out = out.join(base[["emp_base"]], on="cell")
    out["k"] = out["period"].map(lambda p: quarter_index(p, ref)).astype(int)
    out["post"] = (out["k"] > 0).astype(int)
    out["log_emp"] = np.log(out["emp"].where(out["emp"] > 0))
    out["log_cler_emp"] = np.log(out["cler_emp"].where(out["cler_emp"] > 0))
    out["cluster"] = out["countrycode"] + "|" + out["sector"]
    out["cat"] = (
        out["countrycode"] + "|" + out["male"].astype(str) + "|" + out["period"]
    )
    return out.reset_index(drop=True)
