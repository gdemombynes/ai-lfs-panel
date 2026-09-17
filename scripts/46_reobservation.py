# ruff: noqa: E501
"""Diagnostic: who is re-observed in the next quarter, by country.

For every country whose person ids link across quarters, take each person
aged 15+ in quarter t who is scheduled by the rotation design to be
interviewed again in t+1, and model whether the same id is found in t+1
with the same sex and an age within one year. One logit per country pooling
all quarter pairs, with interview-number, quarter-of-year and year dummies
plus baseline characteristics. Unweighted; a diagnostic for the attrition
adjustment, not the adjustment itself.

Interview number: the survey's own (Brazil V1016, Mexico n_ent, Uruguay
ronda) where it exists, else the position of the quarter in the person's
run of consecutive observed quarters (Argentina, Peru, Bolivia, South
Africa). Scheduled to return: Brazil and Mexico interview < 5; Uruguay
record in the last month of the quarter with ronda 1-5 (2021-2022, without
ronda, excluded); Argentina and
Peru (two in, two out, two in) first quarter of a run; Bolivia rotation
groups other than 0 whose last quarter is after t; South Africa run
position < 4.

Writes output/tables/reobservation_<ccc>.csv (coefficients) and
output/tables/reobservation_summary.csv.
"""

from __future__ import annotations

import sys

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm

from lfspanel.config import OUTPUT, PROCESSED

COUNTRIES = ["BRA", "MEX", "ZAF", "ARG", "URY", "BOL", "PER"]
MAX_ROWS = 1_200_000
AGE_BINS = [15, 22, 26, 30, 40, 50, 65, 200]
AGE_LABELS = ["15-21", "22-25", "26-29", "30-39", "40-49", "50-64", "65+"]


def qidx(p: pd.Series) -> pd.Series:
    return p.str[:4].astype(int) * 4 + p.str[-1].astype(int) - 1


def load(cc: str) -> pd.DataFrame:
    con = duckdb.connect(str(PROCESSED / "panel.duckdb"), read_only=True)
    df = con.execute(f"""
        select pid, period, male, age, educat4, urban, lstatus, occup, visit_no,
               rotation_group, int_month, weight
        from harmonized where source = 'own' and countrycode = '{cc}' and age >= 15""").df()
    con.close()
    if cc == "URY":  # person-months: keep the last month of the quarter
        df = df.sort_values(["pid", "period", "int_month"]).drop_duplicates(
            ["pid", "period"], keep="last"
        )
    else:
        df = df.drop_duplicates(["pid", "period"])
    df["q"] = qidx(df["period"])
    return df


def run_position(df: pd.DataFrame) -> pd.Series:
    """1 + number of immediately preceding consecutive quarters the pid was observed."""
    d = df.sort_values(["pid", "q"])
    new_run = (d["pid"] != d["pid"].shift()) | (d["q"] != d["q"].shift() + 1)
    run_id = new_run.cumsum()
    pos = d.groupby(run_id).cumcount() + 1
    return pos.reindex(df.index)


def scheduled(cc: str, df: pd.DataFrame) -> pd.Series:
    if cc in ("BRA", "MEX"):
        return df["interview"] < 5
    if cc == "URY":
        # rondas are consecutive months. Base = the person's record in the
        # last month of the quarter (a last record in an earlier month means
        # the person already left the panel within the quarter) with an
        # interview left; quarters without ronda (2021-2022) are excluded.
        month_pos = (df["int_month"] - 1) % 3 + 1  # 1..3 within the quarter
        return (month_pos == 3) & (df["interview"] <= 5) & df["visit_no"].notna()
    if cc in ("ARG", "PER"):
        return df["interview"] == 1
    if cc == "BOL":
        last = df.groupby("rotation_group")["q"].transform("max")
        return (df["rotation_group"] != "0") & (df["q"] < last)
    if cc == "ZAF":
        return df["interview"] < 4
    raise ValueError(cc)


def build(cc: str) -> pd.DataFrame:
    df = load(cc)
    have_visit = df["visit_no"].notna().mean() > 0.5
    df["interview"] = (
        df["visit_no"].astype("float") if have_visit else run_position(df).astype(float)
    )
    periods = sorted(df["q"].unique())
    has_next = {q for q in periods if q + 1 in periods}
    nxt = df[["pid", "q", "male", "age"]].copy()
    nxt["q"] -= 1
    m = df.merge(nxt, on=["pid", "q"], how="left", suffixes=("", "_n"))
    m["found"] = (
        (m["male_n"] == m["male"]) & ((m["age_n"] - m["age"]).abs() <= 1)
    ).astype(int)
    m = m[m["q"].isin(has_next)]
    m = m[scheduled(cc, m)]
    m["agegrp"] = pd.cut(m["age"], AGE_BINS, right=False, labels=AGE_LABELS)
    m["year"] = m["period"].str[:4]
    m["quarter"] = "Q" + m["period"].str[-1]
    # one categorical for labour status and, for the employed, the ISCO major group
    status = m["lstatus"].map({2: "unemployed", 3: "inactive"})
    occ = "employed occ " + m["occup"].astype("string").fillna("na")
    m["labour"] = status.astype("string").fillna(
        occ.where(m["lstatus"] == 1, "status missing")
    )
    m["educ"] = m["educat4"].astype("string").fillna("missing")
    m["urb"] = m["urban"].astype("string").fillna("missing")
    m["interview"] = m["interview"].clip(upper=6).astype(int).astype(str)
    return m


CATS = ["interview", "agegrp", "educ", "urb", "labour", "quarter", "year"]
REF = {
    "interview": "1",
    "agegrp": "30-39",
    "educ": "2",
    "urb": "1",
    "labour": "employed occ 5",
    "quarter": "Q1",
}


def fold_rare(m: pd.DataFrame) -> pd.DataFrame:
    """Categories with under 100 persons, or with no variation in the outcome
    (which would send a logit coefficient to infinity), join the reference."""
    m = m.copy()
    for c in CATS:
        ref = REF.get(c, m[c].min())
        g = m.groupby(c)["found"].agg(["size", "mean"])
        bad = g.index[(g["size"] < 100) | (g["mean"] <= 0) | (g["mean"] >= 1)]
        if len(bad):
            m[c] = m[c].where(~m[c].isin(bad), ref)
            m.attrs.setdefault("folded", []).extend(f"{c}={b}" for b in bad)
    return m


def fit(cc: str, m: pd.DataFrame) -> pd.DataFrame:
    if len(m) > MAX_ROWS:
        m = m.sample(MAX_ROWS, random_state=11)
    m = fold_rare(m)
    X = pd.get_dummies(
        m[["interview", "agegrp", "educ", "urb", "labour", "quarter", "year"]].astype(
            str
        ),
        drop_first=False,
    ).astype(float)
    # reference categories
    ref = {
        "interview": "interview_1",
        "agegrp": "agegrp_30-39",
        "educ": "educ_2",
        "urb": "urb_1",
        "labour": "labour_employed occ 5",
        "quarter": "quarter_Q1",
        "year": f"year_{m['year'].min()}",
    }
    X = X.drop(columns=[c for c in ref.values() if c in X.columns])
    X = X.loc[:, X.std() > 0]
    X["male"] = m["male"].fillna(0).astype(float).values
    X = sm.add_constant(X)
    res = sm.GLM(m["found"].values, X, family=sm.families.Binomial()).fit(maxiter=200)
    out = pd.DataFrame(
        {
            "term": X.columns,
            "coef": res.params.values,
            "se": res.bse.values,
            "z": res.tvalues.values,
            "p": res.pvalues.values,
        }
    )
    out["odds_ratio"] = np.exp(out["coef"])
    out["countrycode"] = cc
    null = sm.GLM(
        m["found"].values, np.ones((len(m), 1)), family=sm.families.Binomial()
    ).fit()
    out.attrs["n"] = int(res.nobs)
    out.attrs["llf"] = float(res.llf)
    out.attrs["prsq"] = float(1 - res.llf / null.llf)
    out.attrs["mean_found"] = float(m["found"].mean())
    out.attrs["folded"] = m.attrs.get("folded", [])
    return out


def main() -> None:
    tables = OUTPUT / "tables"
    summ = []
    codes = sys.argv[1:] or COUNTRIES
    for cc in codes:
        m = build(cc)
        by_int = m.groupby("interview")["found"].agg(["mean", "size"]).round(3)
        out = fit(cc, m)
        out.to_csv(tables / f"reobservation_{cc.lower()}.csv", index=False)
        summ.append(
            {
                "countrycode": cc,
                "persons_scheduled": len(m),
                "rows_fitted": out.attrs["n"],
                "share_found": round(out.attrs["mean_found"], 3),
                "pseudo_r2": round(out.attrs["prsq"], 4),
                "quarter_pairs": m["q"].nunique(),
                "folded": "; ".join(out.attrs["folded"]),
                "found_by_interview": " ".join(
                    f"{k}:{v['mean']:.2f}" for k, v in by_int.iterrows()
                ),
            }
        )
        print(
            f"== {cc}: scheduled persons {len(m):,}, found {out.attrs['mean_found']:.3f}, pseudo-R2 {out.attrs['prsq']:.3f}, folded {out.attrs['folded']}"
        )
        print(out.drop(columns="countrycode").round(4).to_string(index=False))
    new = pd.DataFrame(summ)
    path = tables / "reobservation_summary.csv"
    if path.exists():  # keep rows of countries not run this time
        old = pd.read_csv(path)
        new = pd.concat(
            [old[~old["countrycode"].isin(new["countrycode"])], new], ignore_index=True
        )
    new.to_csv(path, index=False)


if __name__ == "__main__":
    main()
