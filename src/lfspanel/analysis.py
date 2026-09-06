# ruff: noqa: E501
"""Cells, event-study frame and fixed-effects estimation.

Cells are country x quarter x occupation (ISCO-08 at the country's cell
depth) x age group x sex, with weighted employment, unweighted counts and the
weighted new-hire share (in the job under 12 months). The estimator is OLS
after alternating-projection demeaning of the cell and country x age x sex x
quarter fixed effects, weighted by baseline cell employment, with standard
errors clustered by country x occupation.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import duckdb
import numpy as np
import pandas as pd

from lfspanel.config import PROCESSED
from lfspanel.periods import Period

CELLS_PATH = PROCESSED / "cells" / "cells.parquet"
AGE_GROUPS = ["15-21", "22-25", "26-29", "30-49", "50+"]
YOUNG = {"15-21", "22-25", "26-29"}
MIN_CELL_N = 30
EXPOSURE_COLS = (
    "score", "score_w", "g4_share", "tercile", "high", "quintile", "high_q5", "high_d10"
)  # fmt: skip
REF_PERIOD = "2022Q4"
DEPTH_SHARE = 0.9  # employment share that must carry 3 digits for 3-digit cells


def cell_depth(con: duckdb.DuckDBPyConnection) -> Dict[str, int]:
    """3-digit cells where at least ``DEPTH_SHARE`` of employment has 3+ digits, else 2."""
    df = con.execute(
        """
        SELECT countrycode,
               sum(CASE WHEN occup_isco_digits >= 3 THEN weight END) / sum(weight) AS s3,
               sum(CASE WHEN occup_isco_digits >= 2 THEN weight END) / sum(weight) AS s2
        FROM employed GROUP BY 1
        """
    ).df()
    out = {}
    for _, r in df.iterrows():
        out[r["countrycode"]] = 3 if (r["s3"] or 0) >= DEPTH_SHARE else 2
    return out


def build_cells(
    con: duckdb.DuckDBPyConnection, depth: Dict[str, int], min_age: int = 15
) -> pd.DataFrame:
    frames = []
    for cc, d in sorted(depth.items()):
        frames.append(
            con.execute(
                f"""
                SELECT countrycode, period, substr(occup_isco, 1, {d}) AS isco,
                       age_group, male,
                       count(*) AS n,
                       sum(weight) AS emp,
                       sum(weight * tenure_lt12) / sum(CASE WHEN tenure_lt12 IS NOT NULL THEN weight END)
                           AS new_hire_share,
                       sum(CASE WHEN tenure_lt12 IS NOT NULL THEN weight END) / sum(weight)
                           AS tenure_coverage,
                       sum(weight * socialsec) / sum(CASE WHEN socialsec IS NOT NULL THEN weight END)
                           AS formal_share,
                       sum(CASE WHEN empstat = 1 THEN weight ELSE 0 END) / sum(weight) AS employee_share
                FROM employed
                WHERE countrycode = '{cc}' AND occup_isco_digits >= {d}
                  AND age >= {min_age} AND age_group IS NOT NULL AND male IS NOT NULL
                GROUP BY 1, 2, 3, 4, 5
                """
            )
            .df()
            .assign(isco_digits=d)
        )
    cells = pd.concat(frames, ignore_index=True)
    cells["male"] = cells["male"].astype("Int8")
    cells["young"] = cells["age_group"].isin(YOUNG).astype("Int8")
    cells["small"] = (cells["n"] < MIN_CELL_N).astype("Int8")
    return cells.sort_values(
        ["countrycode", "period", "isco", "age_group", "male"]
    ).reset_index(drop=True)


def quarter_index(period: str, ref: str = REF_PERIOD) -> int:
    p, r = Period(period), Period(ref)
    return (p.year - r.year) * 4 + (p.quarter - r.quarter)


def event_study_frame(
    cells: pd.DataFrame,
    exposure: pd.DataFrame,
    ref: str = REF_PERIOD,
    drop_small: bool = True,
) -> pd.DataFrame:
    """Balanced cell panel with exposure, relative quarter and baseline weight.

    The sample is fixed at the baseline year (the year of ``ref``): cells whose
    mean unweighted count over that year reaches ``MIN_CELL_N`` (when
    ``drop_small``) are kept in every quarter, with zero employment where the
    cell is absent, so cell selection never depends on later outcomes.
    Outcomes: ``log_emp`` (NA when zero) and ``emp_ratio`` = employment over
    its baseline-year mean.
    """
    from lfspanel.exposure import attach_exposure

    df = attach_exposure(cells, exposure)
    df = df[df["high"].notna()].copy()
    df["cell"] = (
        df["countrycode"]
        + "|"
        + df["isco"]
        + "|"
        + df["age_group"]
        + "|"
        + df["male"].astype(str)
    )
    base_rows = df[df["period"].str.startswith(ref[:4])]
    base = base_rows.groupby("cell").agg(emp_base=("emp", "mean"), n_base=("n", "mean"))
    if drop_small:
        base = base[base["n_base"] >= MIN_CELL_N]
    keep = df[df["cell"].isin(base.index)]
    periods = sorted(df["period"].unique())
    fixed = [
        "cell",
        "countrycode",
        "isco",
        "isco_digits",
        "age_group",
        "male",
        "young",
    ] + [c for c in EXPOSURE_COLS if c in df]
    attrs = keep.drop_duplicates("cell").set_index("cell")[
        [c for c in fixed if c != "cell"]
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
            "new_hire_share",
            "tenure_coverage",
            "formal_share",
            "employee_share",
            "small",
        ]
    ]
    df = grid.merge(vals, on=["cell", "period"], how="left")
    df["n"] = df["n"].fillna(0).astype(int)
    df["emp"] = df["emp"].fillna(0.0)
    df = df.join(base[["emp_base"]], on="cell")
    df["k"] = df["period"].map(lambda p: quarter_index(p, ref)).astype(int)
    df["post"] = (df["k"] > 0).astype(int)
    df["log_emp"] = np.log(df["emp"].where(df["emp"] > 0))
    df["emp_ratio"] = df["emp"] / df["emp_base"]
    df["cluster"] = df["countrycode"] + "|" + df["isco"]
    df["cat"] = (
        df["countrycode"]
        + "|"
        + df["age_group"]
        + "|"
        + df["male"].astype(str)
        + "|"
        + df["period"]
    )
    return df.reset_index(drop=True)


def demean(
    df: pd.DataFrame,
    cols: Sequence[str],
    fe: Sequence[str],
    weight: Optional[str] = None,
    tol: float = 1e-8,
    max_iter: int = 500,
) -> pd.DataFrame:
    """Weighted alternating projections: remove the fixed effects in ``fe`` from ``cols``."""
    x = df[list(cols)].astype(float).to_numpy()
    w = df[weight].astype(float).to_numpy() if weight else np.ones(len(df))
    codes = [pd.factorize(df[f])[0] for f in fe]
    sizes = [c.max() + 1 for c in codes]
    wsum = [np.bincount(c, weights=w, minlength=s) for c, s in zip(codes, sizes)]
    for _ in range(max_iter):
        delta = 0.0
        for c, s, ws in zip(codes, sizes, wsum):
            for j in range(x.shape[1]):
                means = np.bincount(c, weights=w * x[:, j], minlength=s) / np.where(
                    ws > 0, ws, 1
                )
                adj = means[c]
                delta = max(delta, float(np.abs(adj).max()) if len(adj) else 0.0)
                x[:, j] -= adj
        if delta < tol:
            break
    return pd.DataFrame(x, columns=list(cols), index=df.index)


def wls_cluster(
    y: np.ndarray, X: np.ndarray, w: np.ndarray, cluster: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Weighted least squares with cluster-robust standard errors."""
    Xw = X * w[:, None]
    XtWX = X.T @ Xw
    XtWX_inv = np.linalg.pinv(XtWX)
    beta = XtWX_inv @ (Xw.T @ y)
    e = y - X @ beta
    codes, uniques = pd.factorize(cluster)
    G = len(uniques)
    meat = np.zeros_like(XtWX)
    scores = Xw * e[:, None]
    for g in range(G):
        s = scores[codes == g].sum(axis=0)
        meat += np.outer(s, s)
    k, n = X.shape[1], len(y)
    adj = (G / (G - 1)) * ((n - 1) / (n - k)) if G > 1 and n > k else 1.0
    V = adj * XtWX_inv @ meat @ XtWX_inv
    return beta, np.sqrt(np.diag(V))


def estimate_event_study(
    frame: pd.DataFrame,
    outcome: str = "log_emp",
    treat: str = "high",
    ref: str = REF_PERIOD,
    fe: Sequence[str] = ("cell", "cat"),
    weight: Optional[str] = "emp_base",
    cluster: str = "cluster",
) -> pd.DataFrame:
    """Coefficients on 1[quarter = k] x treatment for every k except the reference."""
    df = frame[frame[outcome].notna() & frame[treat].notna()].copy()
    ks = sorted(k for k in df["k"].unique() if k != 0)
    names = [f"k{k}" for k in ks]
    for k, name in zip(ks, names):
        df[name] = ((df["k"] == k) * df[treat]).astype(float)
    dm = demean(df, [outcome] + names, fe, weight)
    w = df[weight].to_numpy(float) if weight else np.ones(len(df))
    beta, se = wls_cluster(
        dm[outcome].to_numpy(), dm[names].to_numpy(), w, df[cluster].to_numpy()
    )
    out = pd.DataFrame({"k": ks, "coef": beta, "se": se})
    out["period"] = [_shift(ref, k) for k in ks]
    out["n_cells"] = len(df)
    out["n_clusters"] = df[cluster].nunique()
    return (
        pd.concat(
            [
                out,
                pd.DataFrame({"k": [0], "coef": [0.0], "se": [0.0], "period": [ref]}),
            ],
            ignore_index=True,
        )
        .sort_values("k")
        .reset_index(drop=True)
    )


def estimate_did(
    frame: pd.DataFrame,
    outcome: str = "log_emp",
    treat: str = "high",
    fe: Sequence[str] = ("cell", "cat"),
    weight: Optional[str] = "emp_base",
    cluster: str = "cluster",
    triple: bool = False,
) -> pd.DataFrame:
    """Post x treatment (and post x treatment x young) difference in differences."""
    df = frame[frame[outcome].notna() & frame[treat].notna()].copy()
    df["post_x_treat"] = (df["post"] * df[treat]).astype(float)
    names = ["post_x_treat"]
    if (
        triple
    ):  # post x young itself is absorbed by the country x age x sex x quarter effects
        df["post_x_treat_x_young"] = df["post_x_treat"] * df["young"].astype(float)
        names += ["post_x_treat_x_young"]
    dm = demean(df, [outcome] + names, fe, weight)
    w = df[weight].to_numpy(float) if weight else np.ones(len(df))
    beta, se = wls_cluster(
        dm[outcome].to_numpy(), dm[names].to_numpy(), w, df[cluster].to_numpy()
    )
    return pd.DataFrame(
        {
            "term": names,
            "coef": beta,
            "se": se,
            "n_cells": len(df),
            "n_clusters": df[cluster].nunique(),
        }
    )


def _shift(ref: str, k: int) -> str:
    p = Period(ref)
    q = p.year * 4 + (p.quarter - 1) + k
    return f"{q // 4}Q{q % 4 + 1}"


def occupation_totals(cells: pd.DataFrame) -> pd.DataFrame:
    """Country x period x occupation totals with the young share of employment."""
    g = cells.groupby(["countrycode", "period", "isco", "isco_digits"])
    out = g.agg(n=("n", "sum"), emp=("emp", "sum"))
    young = (
        cells[cells["young"] == 1]
        .groupby(["countrycode", "period", "isco", "isco_digits"])["emp"]
        .sum()
    )
    out["young_share"] = (young / out["emp"]).fillna(0.0)
    return out.reset_index()


def employment_index(
    totals: pd.DataFrame, exposure: pd.DataFrame, ref_year: str = "2022"
) -> pd.DataFrame:
    """Employment by country x period x exposure tercile, indexed to the reference year."""
    from lfspanel.exposure import attach_exposure

    t = attach_exposure(totals, exposure)
    t = t[t["tercile"].notna()]
    agg = t.groupby(["countrycode", "period", "tercile"])["emp"].sum().reset_index()
    base = (
        agg[agg["period"].str.startswith(ref_year)]
        .groupby(["countrycode", "tercile"])["emp"]
        .mean()
        .rename("emp_ref")
    )
    agg = agg.join(base, on=["countrycode", "tercile"])
    agg["index"] = 100 * agg["emp"] / agg["emp_ref"]
    return agg


def list_countries(frame: pd.DataFrame) -> List[str]:
    return sorted(frame["countrycode"].unique())


def iter_subsets(frame: pd.DataFrame) -> Iterable[Tuple[str, pd.DataFrame]]:
    """Named subsets for the standard set of estimates."""
    yield "all", frame
    yield "young", frame[frame["young"] == 1]
    yield "older", frame[frame["young"] == 0]
    for cc in list_countries(frame):
        yield f"country_{cc}", frame[frame["countrycode"] == cc]
