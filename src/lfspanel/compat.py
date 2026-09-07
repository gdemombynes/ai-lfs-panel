# ruff: noqa: E501
"""Compatibility audit of the harmonized panel across countries and quarters.

``quarter_profile`` summarises every country-quarter partition (sample,
population, headline rates, missingness, coding depth, code validity, id and
period integrity). ``flag_profile`` turns the profile into a list of issues:
absolute problems in a quarter and quarter-to-quarter jumps that mark a
design change, a coding change or a reading error. ``coverage_table`` and
``availability_table`` describe what each country can contribute to a
cross-country design (window, gaps, variables populated).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import duckdb
import pandas as pd

from lfspanel.crosswalks import isco08_codes_by_level
from lfspanel.periods import Period

# ISIC Rev.4 divisions (two digits) that exist in the classification
ISIC_DIVISIONS = frozenset(
    f"{d:02d}"
    for d in list(range(1, 4)) + list(range(5, 10)) + list(range(10, 34))
    + list(range(35, 40)) + list(range(41, 44)) + list(range(45, 48))
    + list(range(49, 54)) + [55, 56] + list(range(58, 64)) + list(range(64, 67))
    + [68] + list(range(69, 76)) + list(range(77, 83)) + list(range(84, 89))
    + list(range(90, 100))
)  # fmt: skip

# metric -> (absolute threshold on the level, threshold on the change against
# the previous quarter, kind). Shares are in per cent, rates in per cent.
LEVEL_RULES: Dict[str, Tuple[float, str]] = {
    "miss_lstatus_pct": (1.0, "labour status missing among persons of working age"),
    "miss_occup_pct": (5.0, "occupation missing among the employed"),
    "miss_isic_pct": (5.0, "industry missing among the employed"),
    "invalid_isco_pct": (0.5, "occupation codes outside the ISCO-08 structure"),
    "invalid_isic_pct": (0.5, "industry divisions outside ISIC Rev.4"),
    "occup_mismatch_pct": (0.1, "occup differs from the first ISCO digit"),
    "dup_pid_pct": (0.05, "duplicated person ids in the partition (% of rows)"),
    "bad_weight": (0, "non-positive or missing weights"),
    "bad_age": (0, "ages outside 0-120"),
    "status_below_min": (0, "labour status set below the minimum labour age"),
    "month_outside_pct": (5.0, "interview month outside the quarter"),
}
JUMP_RULES: Dict[str, Tuple[float, str, str]] = {
    "n_rows": (30.0, "rel", "sample size"),
    "pop": (10.0, "rel", "weighted population"),
    "pop15_share": (3.0, "abs", "share of population aged 15+"),
    "lfpr": (3.0, "abs", "participation rate 15+"),
    "ur": (3.0, "abs", "unemployment rate 15+"),
    "urban_pct": (5.0, "abs", "urban share"),
    "male_pct": (3.0, "abs", "male share"),
    "isco3_pct": (10.0, "abs", "employed with 3+ ISCO digits"),
    "isco4_pct": (10.0, "abs", "employed with 4 ISCO digits"),
    "isic3_pct": (10.0, "abs", "employed with 3+ ISIC digits"),
    "miss_educat7_pct": (5.0, "abs", "education missing"),
    "miss_empstat_pct": (5.0, "abs", "status in employment missing"),
    "miss_wage_pct": (10.0, "abs", "wage missing among employed"),
    "miss_whours_pct": (10.0, "abs", "hours missing among employed"),
    "miss_tenure_pct": (10.0, "abs", "tenure missing among employed"),
    "miss_socialsec_pct": (10.0, "abs", "social security missing among employed"),
    "miss_contract_pct": (10.0, "abs", "contract missing among employed"),
    "employee_pct": (5.0, "abs", "employee share of the employed"),
    "agri_pct": (5.0, "abs", "agriculture share of the employed"),
}
AVAILABILITY_VARS = [
    "int_month", "hhid", "pid", "rotation_group", "visit_no", "urban", "subnatid1",
    "educat7", "lstatus", "potential_lf", "underemployment", "nlfreason", "empstat",
    "ocusec", "industrycat_isic", "occup_isco", "wage_no_compen", "whours",
    "contract", "socialsec", "firmsize_l", "tenure_months", "tenure_lt12",
]  # fmt: skip


def _pct(num: str, den: str) -> str:
    return f"100.0 * {num} / nullif({den}, 0)"


def quarter_profile(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """One row per country-quarter with sample, rate, missingness and integrity stats."""
    emp = "lstatus = 1"
    adult = "age >= minlaborage"
    q = f"""
    SELECT countrycode, period,
           any_value(minlaborage) AS minlaborage,
           any_value(raw_release) AS raw_release,
           any_value(harmonize_version) AS harmonize_version,
           count(*) AS n_rows,
           count(CASE WHEN {emp} THEN 1 END) AS n_employed,
           sum(weight) AS pop,
           {_pct("sum(CASE WHEN age >= 15 THEN weight END)", "sum(weight)")} AS pop15_share,
           {_pct("sum(CASE WHEN age >= 15 AND lstatus IN (1, 2) THEN weight END)", "sum(CASE WHEN age >= 15 THEN weight END)")} AS lfpr,
           {_pct("sum(CASE WHEN age >= 15 AND lstatus = 2 THEN weight END)", "sum(CASE WHEN age >= 15 AND lstatus IN (1, 2) THEN weight END)")} AS ur,
           {_pct("sum(CASE WHEN urban = 1 THEN weight END)", "sum(CASE WHEN urban IS NOT NULL THEN weight END)")} AS urban_pct,
           {_pct("sum(CASE WHEN male = 1 THEN weight END)", "sum(CASE WHEN male IS NOT NULL THEN weight END)")} AS male_pct,
           {_pct(f"count(CASE WHEN {adult} AND lstatus IS NULL THEN 1 END)", f"count(CASE WHEN {adult} THEN 1 END)")} AS miss_lstatus_pct,
           {_pct("count(CASE WHEN age IS NULL THEN 1 END)", "count(*)")} AS miss_age_pct,
           {_pct("count(CASE WHEN educat7 IS NULL AND age >= 15 THEN 1 END)", "count(CASE WHEN age >= 15 THEN 1 END)")} AS miss_educat7_pct,
           {_pct(f"count(CASE WHEN {emp} AND occup_isco IS NULL THEN 1 END)", f"count(CASE WHEN {emp} THEN 1 END)")} AS miss_occup_pct,
           {_pct(f"count(CASE WHEN {emp} AND industrycat_isic IS NULL THEN 1 END)", f"count(CASE WHEN {emp} THEN 1 END)")} AS miss_isic_pct,
           {_pct(f"count(CASE WHEN {emp} AND empstat IS NULL THEN 1 END)", f"count(CASE WHEN {emp} THEN 1 END)")} AS miss_empstat_pct,
           {_pct(f"count(CASE WHEN {emp} AND wage_no_compen IS NULL THEN 1 END)", f"count(CASE WHEN {emp} THEN 1 END)")} AS miss_wage_pct,
           {_pct(f"count(CASE WHEN {emp} AND whours IS NULL THEN 1 END)", f"count(CASE WHEN {emp} THEN 1 END)")} AS miss_whours_pct,
           {_pct(f"count(CASE WHEN {emp} AND tenure_lt12 IS NULL THEN 1 END)", f"count(CASE WHEN {emp} THEN 1 END)")} AS miss_tenure_pct,
           {_pct(f"count(CASE WHEN {emp} AND socialsec IS NULL THEN 1 END)", f"count(CASE WHEN {emp} THEN 1 END)")} AS miss_socialsec_pct,
           {_pct(f"count(CASE WHEN {emp} AND contract IS NULL THEN 1 END)", f"count(CASE WHEN {emp} THEN 1 END)")} AS miss_contract_pct,
           {_pct(f"sum(CASE WHEN {emp} AND occup_isco_digits >= 3 THEN weight END)", f"sum(CASE WHEN {emp} THEN weight END)")} AS isco3_pct,
           {_pct(f"sum(CASE WHEN {emp} AND occup_isco_digits >= 4 THEN weight END)", f"sum(CASE WHEN {emp} THEN weight END)")} AS isco4_pct,
           {_pct(f"sum(CASE WHEN {emp} AND isic_digits >= 3 THEN weight END)", f"sum(CASE WHEN {emp} THEN weight END)")} AS isic3_pct,
           {_pct(f"sum(CASE WHEN {emp} AND empstat = 1 THEN weight END)", f"sum(CASE WHEN {emp} AND empstat IS NOT NULL THEN weight END)")} AS employee_pct,
           {_pct(f"sum(CASE WHEN {emp} AND industrycat10 = 1 THEN weight END)", f"sum(CASE WHEN {emp} AND industrycat10 IS NOT NULL THEN weight END)")} AS agri_pct,
           {_pct(f"count(CASE WHEN {emp} AND occup IS NOT NULL AND CAST(occup AS VARCHAR) <> substr(occup_isco, 1, 1) THEN 1 END)", f"count(CASE WHEN {emp} AND occup_isco IS NOT NULL THEN 1 END)")} AS occup_mismatch_pct,
           count(*) - count(DISTINCT pid) AS dup_pid,
           {_pct("(count(*) - count(DISTINCT pid))", "count(*)")} AS dup_pid_pct,
           count(CASE WHEN weight IS NULL OR weight <= 0 THEN 1 END) AS bad_weight,
           count(CASE WHEN age < 0 OR age > 120 THEN 1 END) AS bad_age,
           count(CASE WHEN age < minlaborage AND lstatus IS NOT NULL THEN 1 END) AS status_below_min,
           {_pct("count(CASE WHEN int_month IS NOT NULL AND int_month NOT BETWEEN 3 * CAST(substr(period, 6, 1) AS INTEGER) - 2 AND 3 * CAST(substr(period, 6, 1) AS INTEGER) THEN 1 END)", "count(CASE WHEN int_month IS NOT NULL THEN 1 END)")} AS month_outside_pct
    FROM harmonized
    GROUP BY 1, 2
    ORDER BY 1, 2
    """
    prof = con.execute(q).df()
    codes = con.execute(
        """
        SELECT countrycode, period, occup_isco, occup_isco_digits AS d,
               substr(industrycat_isic, 1, 2) AS div, sum(weight) AS w
        FROM harmonized WHERE lstatus = 1
        GROUP BY 1, 2, 3, 4, 5
        """
    ).df()
    prof = prof.merge(
        _invalid_code_shares(codes), on=["countrycode", "period"], how="left"
    )
    return prof


def _invalid_code_shares(codes: pd.DataFrame) -> pd.DataFrame:
    """Employment-weighted share of invalid ISCO and ISIC codes by country-quarter."""
    by_level = isco08_codes_by_level()
    c = codes.copy()
    c["isco_ok"] = [
        pd.isna(code)
        or (
            pd.notna(d)
            and int(d) >= 1
            and str(code)[: int(d)].ljust(4, "0") in by_level[int(d)]
        )
        for code, d in zip(c["occup_isco"], c["d"])
    ]
    section_only = c["div"].eq("00")  # 000<letter>: ISIC section without division
    c["isic_ok"] = c["div"].isna() | c["div"].isin(ISIC_DIVISIONS) | section_only
    g = c.groupby(["countrycode", "period"])
    out = pd.DataFrame(
        {
            "invalid_isco_pct": g.apply(
                lambda x: 100 * x.loc[~x["isco_ok"], "w"].sum() / x["w"].sum()
            ),
            "invalid_isic_pct": g.apply(
                lambda x: 100 * x.loc[~x["isic_ok"], "w"].sum() / x["w"].sum()
            ),
        }
    ).reset_index()
    return out


def flag_profile(
    prof: pd.DataFrame,
    level_rules: Optional[Dict[str, Tuple[float, str]]] = None,
    jump_rules: Optional[Dict[str, Tuple[float, str, str]]] = None,
) -> pd.DataFrame:
    """Issues found in the profile: level problems and quarter-to-quarter jumps."""
    level_rules = level_rules or LEVEL_RULES
    jump_rules = jump_rules or JUMP_RULES
    prof = prof.sort_values(["countrycode", "period"]).reset_index(drop=True)
    rows: List[dict] = []
    for metric, (limit, label) in level_rules.items():
        if metric not in prof:
            continue
        bad = prof[prof[metric].fillna(0) > limit]
        for _, r in bad.iterrows():
            rows.append(
                {
                    "countrycode": r["countrycode"],
                    "period": r["period"],
                    "kind": "level",
                    "metric": metric,
                    "value": round(float(r[metric]), 3),
                    "previous": None,
                    "change": None,
                    "threshold": limit,
                    "issue": label,
                }  # fmt: skip
            )
    for metric, (limit, how, label) in jump_rules.items():
        if metric not in prof:
            continue
        prev = prof.groupby("countrycode")[metric].shift(1)
        change = (
            100 * (prof[metric] - prev) / prev.abs()
            if how == "rel"
            else prof[metric] - prev
        )
        hit = change.abs() > limit
        for i in prof.index[hit.fillna(False)]:
            rows.append(
                {
                    "countrycode": prof.at[i, "countrycode"],
                    "period": prof.at[i, "period"],
                    "kind": "jump",
                    "metric": metric,
                    "value": round(float(prof.at[i, metric]), 3),
                    "previous": round(float(prev[i]), 3),
                    "change": round(float(change[i]), 3),
                    "threshold": limit,
                    "issue": f"{label} changed by {change[i]:+.1f}{'%' if how == 'rel' else ' pts'}",
                }  # fmt: skip
            )
    cols = [
        "countrycode",
        "period",
        "kind",
        "metric",
        "value",
        "previous",
        "change",
        "threshold",
        "issue",
    ]
    return pd.DataFrame(rows, columns=cols).sort_values(["countrycode", "period", "kind", "metric"]).reset_index(drop=True)  # fmt: skip


def missing_quarters(periods: List[str]) -> List[str]:
    """Quarters absent between the first and last of ``periods``."""
    if not periods:
        return []
    have = {str(Period(p)) for p in periods}
    first, last = min(Period(p) for p in periods), max(Period(p) for p in periods)
    out, p = [], first
    while p <= last:
        if str(p) not in have:
            out.append(str(p))
        p = p.next()
    return out


def coverage_table(prof: pd.DataFrame) -> pd.DataFrame:
    """Per country: window, gaps, sample, minimum labour age, coding depth, urban-only."""
    rows = []
    for cc, g in prof.groupby("countrycode"):
        periods = sorted(g["period"])
        rows.append(
            {
                "countrycode": cc,
                "first": periods[0],
                "last": periods[-1],
                "quarters": len(periods),
                "gaps": ",".join(missing_quarters(periods)),
                "minlaborage": int(g["minlaborage"].iloc[0]),
                "median_rows": int(g["n_rows"].median()),
                "min_rows": int(g["n_rows"].min()),
                "max_rows": int(g["n_rows"].max()),
                "urban_only": bool(g["urban_pct"].min() >= 99.5),
                "isco3_pct": round(float(g["isco3_pct"].median()), 1),
                "isco4_pct": round(float(g["isco4_pct"].median()), 1),
                "isic3_pct": round(float(g["isic3_pct"].median()), 1),
                "tenure_pct": round(100 - float(g["miss_tenure_pct"].median()), 1),
                "wage_pct": round(100 - float(g["miss_wage_pct"].median()), 1),
                "releases": ",".join(
                    sorted(set(g["raw_release"].dropna().astype(str)))
                ),
            }
        )
    return pd.DataFrame(rows)


def availability_table(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Share of rows (persons, or employed for job variables) with each variable filled, by country."""
    job = {
        "empstat", "ocusec", "industrycat_isic", "occup_isco", "wage_no_compen",
        "whours", "contract", "socialsec", "firmsize_l", "tenure_months", "tenure_lt12",
    }  # fmt: skip
    parts = []
    for v in AVAILABILITY_VARS:
        base = "lstatus = 1" if v in job else "age >= minlaborage"
        parts.append(
            f"round({_pct(f'count(CASE WHEN {base} AND {v} IS NOT NULL THEN 1 END)', f'count(CASE WHEN {base} THEN 1 END)')}, 1) AS {v}"
        )
    q = f"SELECT countrycode, {', '.join(parts)} FROM harmonized GROUP BY 1 ORDER BY 1"
    return con.execute(q).df()
