"""Headline labor market rates and comparisons with official tables."""

from __future__ import annotations

import re
from importlib.resources import files
from typing import Dict, Optional, Tuple

import pandas as pd

INDICATORS = ["participation_rate", "unemployment_rate", "employment_rate"]


def headline_rates(
    df: pd.DataFrame, min_age: Optional[int] = None, max_age: Optional[int] = None
) -> Dict[str, float]:
    """Weighted participation, unemployment and employment-to-population rates (%)."""
    age_cut = min_age if min_age is not None else int(df["minlaborage"].iloc[0])
    pop = df[df["age"] >= age_cut]
    if max_age is not None:
        pop = pop[pop["age"] <= max_age]
    w = pop["weight"].astype(float)
    lf = pop["lstatus"].isin([1, 2])
    emp = pop["lstatus"] == 1
    unemp = pop["lstatus"] == 2
    total_w = w.sum()
    lf_w = w[lf].sum()
    return {
        "participation_rate": 100.0 * lf_w / total_w,
        "unemployment_rate": 100.0 * w[unemp].sum() / lf_w,
        "employment_rate": 100.0 * w[emp].sum() / total_w,
        "population": float(total_w),
        "employed": float(w[emp].sum()),
    }


def age_band(label: str) -> Tuple[Optional[int], Optional[int]]:
    """Population label of an official table -> (min_age, max_age).

    ``"all"`` -> (0, None); ``"15+"`` -> (15, None); ``"15-64"`` -> (15, 64);
    anything else -> (None, None), i.e. the country's minimum labour age.
    """
    text = label.strip().lower()
    if text == "all":
        return 0, None
    m = re.match(r"^(\d+)\s*-\s*(\d+)$", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"^(\d+)\s*\+$", text)
    if m:
        return int(m.group(1)), None
    return None, None


def employment_by_major_group(df: pd.DataFrame) -> pd.Series:
    """Weighted employment shares (%) by ISCO major group."""
    emp = df[df["lstatus"] == 1]
    shares = emp.groupby("occup", dropna=True)["weight"].sum()
    return (100.0 * shares / shares.sum()).round(2)


def load_official(ccc: str) -> pd.DataFrame:
    """Published headline rates shipped in resources/official/<ccc>_headline.csv."""
    path = files("lfspanel") / "resources" / "official" / f"{ccc.lower()}_headline.csv"
    with path.open("r", encoding="utf-8") as f:
        return pd.read_csv(f, dtype={"period": str, "indicator": str}, comment="#")


def compare_official(
    rates: Dict[str, float],
    official: pd.DataFrame,
    period: str,
    tolerance: float = 0.15,
) -> pd.DataFrame:
    """Compare computed rates with the official rows for ``period``."""
    rows = []
    sub = official[official["period"] == period]
    for _, r in sub.iterrows():
        ind = r["indicator"]
        if ind not in rates:
            continue
        tol = (
            float(r["tolerance"])
            if "tolerance" in r and pd.notna(r.get("tolerance"))
            else tolerance
        )
        diff = rates[ind] - float(r["value"])
        rows.append(
            {
                "period": period,
                "indicator": ind,
                "computed": round(rates[ind], 3),
                "official": float(r["value"]),
                "diff": round(diff, 3),
                "tolerance": tol,
                "status": "PASS" if abs(diff) <= tol else "FAIL",
                "source": r.get("source_url", ""),
            }
        )
    return pd.DataFrame(rows)
