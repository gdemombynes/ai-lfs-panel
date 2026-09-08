"""Bolivia ECE (INE quarterly public-use file) -> target schema.

INE's own flags give labour status for persons 14+ (``pet``, ``peao``,
``pead``). Occupation is the Bolivian classification COB 2009, five digits
whose first four follow ISCO-08 (most codes resolve to the ISCO minor group,
some to the unit group); industry is CAEB, five digits whose first four are
the ISIC Rev.4 class. The quarterly expansion factor is ``fact_trim_act``,
INE's revised base, present for every quarter of the pooled 2015Q4-2025Q3
file and of the per-quarter files from 2025Q4; ``fact_trim`` (original base)
is used only when a per-quarter file lacks the revised factor. The pension
question (``s2_64a``) was not asked in 2021, so ``socialsec`` is missing
that year.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from lfspanel.config import get_country
from lfspanel.crosswalks import map_isco_codes
from lfspanel.harmonize.common import (
    educat4_from_7,
    finalize,
    industrycat4_from_10,
    industrycat10_from_isic,
    isco_major,
    occup_skill_from_major,
    to_int,
    true_only,
)
from lfspanel.periods import Period

COUNTRY = get_country("bol")
DEPTS = {
    1: "Chuquisaca", 2: "La Paz", 3: "Cochabamba", 4: "Oruro", 5: "Potosí",
    6: "Tarija", 7: "Santa Cruz", 8: "Beni", 9: "Pando",
}  # fmt: skip
# s2_18: 1 employee, 2 own account, 3 employer or unpaid partner, 4 producer
# cooperative member, 5 unpaid family worker, 6 unpaid apprentice, 7 domestic
EMPSTAT = {1: 1, 2: 4, 3: 3, 4: 5, 5: 2, 6: 2, 7: 1}
NLFREASON = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 5}
# niv_ed: 0 none, 1 primary incomplete, 2 primary complete, 3 secondary
# incomplete, 4 secondary complete, 5 higher (split by s1_07a), 7 other
EDUCAT7 = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5}
UNIVERSITY = {72, 73, 74, 75, 76}  # s1_07a: university degrees and postgraduate
FIRMSIZE = {
    1: (1, 1), 2: (2, 5), 3: (6, 10), 4: (11, 20), 5: (21, 30), 6: (31, 50),
    7: (51, 100), 8: (101, None),
}  # fmt: skip


def month_from_code(meses: pd.Series) -> pd.Series:
    """INE's month code counts months from January 1960 (0-based)."""
    code = pd.to_numeric(meses, errors="coerce")
    return (code % 12 + 1).astype("Int8")


def weight(raw: pd.DataFrame) -> pd.Series:
    """Revised-base quarterly factor, falling back to the original base."""
    w = pd.to_numeric(raw["fact_trim_act"], errors="coerce")
    return w.where(w.notna(), pd.to_numeric(raw["fact_trim"], errors="coerce"))


def _code(s: pd.Series, employed: pd.Series) -> pd.Series:
    c = s.astype("string").str.strip()
    return c.where(c.str.fullmatch(r"\d{2,5}") & employed, pd.NA)


def harmonize(
    raw: pd.DataFrame, period: Period, raw_release: Optional[str] = None
) -> pd.DataFrame:
    w = weight(raw)
    raw = raw[w.notna() & (w > 0)].copy()
    w = w[raw.index]
    df = pd.DataFrame(index=raw.index)
    df["year"] = period.year
    df["int_year"] = period.year
    df["int_month"] = month_from_code(raw["meses"])
    df["wave"] = f"Q{period.quarter}"
    df["hhid"] = (str(period) + "-" + raw["id_hogar"]).astype("string")
    df["pid"] = (df["hhid"] + "-" + raw["nro"]).astype("string")
    df["rotation_group"] = raw["panel"].astype("string")
    df["visit_no"] = pd.NA
    df["weight"] = w.astype("float64")
    df["urban"] = to_int(raw["area"]).map({1: 1, 2: 0}).astype("Int8")
    dep = to_int(raw["depto"])
    df["subnatid1"] = (dep.astype("string") + " - " + dep.map(DEPTS)).astype("string")
    df["age"] = to_int(raw["s1_03a"], "Int16")
    df["male"] = to_int(raw["s1_02"]).map({1: 1, 2: 0}).astype("Int8")
    niv = to_int(raw["niv_ed"])
    level = to_int(raw["s1_07a"], "Int16")
    educ = niv.map(EDUCAT7).astype("Int8")
    higher = niv == 5
    educ = educ.mask(true_only(higher), 6).mask(
        true_only(higher & level.isin(UNIVERSITY)), 7
    )
    df["educat7"] = educ
    df["educat4"] = educat4_from_7(df["educat7"])

    pet = to_int(raw["pet"]) == 1
    emp_flag = to_int(raw["peao"]) == 1
    unemp_flag = to_int(raw["pead"]) == 1
    adult = df["age"] >= COUNTRY.minlaborage
    lstatus = pd.Series(3, index=raw.index, dtype="Int8")
    lstatus = lstatus.mask(true_only(unemp_flag), 2).mask(true_only(emp_flag), 1)
    df["lstatus"] = lstatus.where(adult & pet)
    employed, nlf = df["lstatus"] == 1, df["lstatus"] == 3
    df["potential_lf"] = pd.NA
    df["underemployment"] = (
        (to_int(raw["psubocup"]) == 1).astype("Int8").where(employed)
    )
    df["nlfreason"] = to_int(raw["s2_07"]).map(NLFREASON).astype("Int8").where(nlf)
    cat = to_int(raw["s2_18"])
    df["empstat"] = cat.map(EMPSTAT).astype("Int8").where(employed)
    employer = to_int(raw["s2_22"])
    df["ocusec"] = (
        employer.map({1: 1, 2: 1})
        .fillna(2)
        .astype("Int8")
        .where(employed & employer.notna())
    )

    caeb = _code(raw["s2_16acod"], employed)
    isic = caeb.str[:4].str.ljust(4, "0")
    df["industry_orig"] = caeb.astype("string")
    df["industrycat_isic"] = isic.astype("string")
    digits = caeb.str.len().clip(upper=4).astype("Int8")
    df["isic_digits"] = digits.where(isic.notna())
    df["industrycat10"] = industrycat10_from_isic(df["industrycat_isic"])
    df["industrycat4"] = industrycat4_from_10(df["industrycat10"])

    cob = _code(raw["s2_15acod"], employed)
    df["occup_orig"] = cob.astype("string")
    isco, odigits = map_isco_codes(cob.str[:4])
    df["occup_isco"], df["occup_isco_digits"] = isco, odigits
    df["occup"] = isco_major(df["occup_isco"])
    df["occup_skill"] = occup_skill_from_major(df["occup"])

    income = pd.to_numeric(raw["yprilab"], errors="coerce")
    df["wage_no_compen"] = income.where(income > 0).astype("float64").where(employed)
    df["unitwage"] = pd.Series(5, index=raw.index, dtype="Int8").where(
        df["wage_no_compen"].notna()
    )
    hrs = pd.to_numeric(raw["phrs"], errors="coerce")
    df["whours"] = hrs.where(hrs > 0).astype("float32").where(employed)
    contract = to_int(raw["s2_21"])
    df["contract"] = (
        contract.map({1: 1, 2: 1, 4: 1, 3: 0, 5: 0}).astype("Int8").where(employed)
    )
    pension = to_int(raw["s2_64a"])
    df["socialsec"] = (
        pension.map({1: 1, 2: 1, 3: 0, 4: 0}).astype("Int8").where(employed)
    )
    band = to_int(raw["s2_26a"])
    df["firmsize_l"] = band.map({k: v[0] for k, v in FIRMSIZE.items()}).astype("Int16")
    df["firmsize_u"] = band.map({k: v[1] for k, v in FIRMSIZE.items()}).astype("Int16")
    df["tenure_months"] = pd.NA
    df["tenure_lt12"] = pd.NA
    df["source_file"] = raw["source_file"].astype("string")
    return finalize(df, COUNTRY, period, source="own", raw_release=raw_release)
