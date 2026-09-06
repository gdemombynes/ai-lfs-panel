"""Occupational exposure to generative AI (ILO 2025 scores) on ISCO-08.

Source: Gmyrek, Berg, Kamiński et al. (2025), "Generative AI and jobs: a
refined global index of occupational exposure", ILO Working Paper 140. The
public workbook scores every ISCO-08 task (0-1); occupations are the mean of
their tasks and the ILO assigns each unit group to "Not Exposed", "Minimal
Exposure" or exposure gradients 1-4 (rising share of highly automatable
tasks). Scores are aggregated to 3, 2 and 1 digits both unweighted and
weighted by pooled 2022 employment from the panel countries that code
occupations at four digits. Exposure terciles, quintiles and deciles are
employment-weighted so each group holds an equal share of baseline
employment; ``high`` (top tercile), ``high_q5`` (top quintile) and
``high_d10`` (top decile) are the treatment dummies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import duckdb
import pandas as pd

from lfspanel.config import EXTERNAL, PROCESSED

ILO_TASKS = EXTERNAL / "exposure" / "Final_Scores_ISCO08_Gmyrek_et_al_2025.xlsx"
ILO_CATEGORIES = EXTERNAL / "exposure" / "4digits_with_tasks.xlsx"
EXPOSURE_TABLE = PROCESSED / "exposure" / "ilo_exposure.csv"
GRADIENT = {
    "Not Exposed": 0,
    "Minimal Exposure": 0,
    "Exposed: Gradient 1": 1,
    "Exposed: Gradient 2": 2,
    "Exposed: Gradient 3": 3,
    "Exposed: Gradient 4": 4,
}
BASELINE_COUNTRIES = ("BRA", "COL", "ECU", "PER")  # four-digit ISCO in own data
HIGH_TASK = 0.5  # task score at or above which the ILO treats a task as highly exposed


def load_ilo_tasks(
    tasks_path: Path = ILO_TASKS, categories_path: Path = ILO_CATEGORIES
) -> pd.DataFrame:
    """One row per ISCO-08 task: unit group, task id, 2023/2025 scores, ILO category."""
    t = pd.read_excel(tasks_path)
    c = pd.read_excel(categories_path)
    out = pd.DataFrame(
        {
            "isco4": t["ISCO_08"].astype(str).str.zfill(4),
            "title": t["Title"].astype(str),
            "task_id": pd.to_numeric(t["taskID"], errors="coerce").astype("Int16"),
            "score_2023": pd.to_numeric(t["score_2023"], errors="coerce"),
            "score_2025": pd.to_numeric(t["score_2025"], errors="coerce"),
        }
    )
    cat = (
        c.assign(isco4=c["isco08_4d"].astype(str).str[:4])
        .groupby("isco4")["potential25"]
        .first()
    )
    out["category"] = out["isco4"].map(cat)
    return out


def occupation_scores(tasks: pd.DataFrame) -> pd.DataFrame:
    """Unit-group exposure: mean task score, dispersion, ILO category and gradient."""
    g = tasks.groupby("isco4")
    occ = pd.DataFrame(
        {
            "title": g["title"].first(),
            "score": g["score_2025"].mean(),
            "score_2023": g["score_2023"].mean(),
            "sd": g["score_2025"].std().fillna(0.0),
            "n_tasks": g["task_id"].count(),
            "high_task_share": g["score_2025"].apply(lambda s: (s >= HIGH_TASK).mean()),
            "category": g["category"].first(),
        }
    )
    occ["gradient"] = occ["category"].map(GRADIENT).astype("Int8")
    return occ


def baseline_weights(
    con: duckdb.DuckDBPyConnection,
    year: int = 2022,
    countries=BASELINE_COUNTRIES,
) -> pd.Series:
    """Pooled employment by four-digit ISCO unit group in the baseline year."""
    ccs = ", ".join(f"'{c}'" for c in countries)
    df = con.execute(
        f"""
        SELECT occup_isco AS isco4, sum(weight) AS emp
        FROM employed
        WHERE occup_isco_digits = 4 AND period LIKE '{year}%' AND countrycode IN ({ccs})
        GROUP BY 1
        """
    ).df()
    return df.set_index("isco4")["emp"]


def _quantiles(score: pd.Series, weight: pd.Series, q: int) -> pd.Series:
    """Employment-weighted groups 1 (low) to q (high), each with 1/q of employment."""
    order = score.sort_values().index
    cum = weight.reindex(order).fillna(0).cumsum()
    share = cum / cum.iloc[-1] if cum.iloc[-1] > 0 else cum * 0
    group = pd.Series(1, index=order, dtype="Int8")
    for k in range(2, q + 1):
        group[share > (k - 1) / q] = k
    return group.reindex(score.index)


def _terciles(score: pd.Series, weight: pd.Series) -> pd.Series:
    return _quantiles(score, weight, 3)


def aggregate_isco(
    occ: pd.DataFrame, weights: Optional[pd.Series] = None
) -> pd.DataFrame:
    """Exposure at 4, 3, 2 and 1 digits, long format.

    ``score`` is the simple mean of unit-group scores; ``score_w`` the
    employment-weighted mean (unit groups without baseline employment carry
    the simple mean's weight of one); ``g4_share`` the employment share in ILO
    gradient 4; ``tercile`` the employment-weighted tercile of ``score_w``.
    """
    w = (
        weights.reindex(occ.index).fillna(weights.median())
        if weights is not None
        else pd.Series(1.0, index=occ.index)
    )
    base = occ.assign(w=w, g4=(occ["gradient"] == 4).astype(float))
    frames = []
    for d in (4, 3, 2, 1):
        key = base.index.str[:d]
        g = base.groupby(key)
        agg = pd.DataFrame(
            {
                "score": g["score"].mean(),
                "score_w": g.apply(
                    lambda x: (x["score"] * x["w"]).sum() / x["w"].sum()
                ),
                "score_2023_w": g.apply(
                    lambda x: (x["score_2023"] * x["w"]).sum() / x["w"].sum()
                ),
                "g4_share": g.apply(lambda x: (x["g4"] * x["w"]).sum() / x["w"].sum()),
                "emp_base": g["w"].sum(),
                "n_units": g["score"].count(),
            }
        )
        agg["tercile"] = _terciles(agg["score_w"], agg["emp_base"])
        agg["high"] = (agg["tercile"] == 3).astype("Int8")
        agg["quintile"] = _quantiles(agg["score_w"], agg["emp_base"], 5)
        agg["high_q5"] = (agg["quintile"] == 5).astype("Int8")
        agg["decile"] = _quantiles(agg["score_w"], agg["emp_base"], 10)
        agg["high_d10"] = (agg["decile"] == 10).astype("Int8")
        agg.index.name = "isco"
        frames.append(agg.reset_index().assign(digits=d))
    out = pd.concat(frames, ignore_index=True)
    return out[
        ["digits", "isco", "score", "score_w", "score_2023_w", "g4_share", "emp_base",
         "n_units", "tercile", "high", "quintile", "high_q5", "decile", "high_d10"]
    ]  # fmt: skip


def build_exposure_table(
    con: duckdb.DuckDBPyConnection, out_path: Path = EXPOSURE_TABLE
) -> pd.DataFrame:
    occ = occupation_scores(load_ilo_tasks())
    table = aggregate_isco(occ, baseline_weights(con))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_path, index=False)
    return table


def load_exposure_table(path: Path = EXPOSURE_TABLE) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"isco": str})


def attach_exposure(
    df: pd.DataFrame,
    table: pd.DataFrame,
    code_col: str = "isco",
    digits_col: str = "isco_digits",
    cols=(
        "score",
        "score_w",
        "g4_share",
        "tercile",
        "high",
        "quintile",
        "high_q5",
        "high_d10",
    ),
) -> pd.DataFrame:
    """Join exposure on the ISCO code at the digit level each row carries."""
    cols = [c for c in cols if c in table.columns]
    lookup: Dict[int, pd.DataFrame] = {
        d: t.set_index("isco")[cols] for d, t in table.groupby("digits")
    }
    parts = []
    for d, part in df.groupby(digits_col):
        parts.append(part.join(lookup[int(d)], on=code_col))
    return pd.concat(parts).sort_index()
