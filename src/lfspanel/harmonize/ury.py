"""Uruguay ECH (INE monthly follow-up files, three months stacked) -> schema.

The monthly base covers persons 14+ with a monthly weight ``W``; stacking
three months and dividing ``W`` by three gives quarter-level totals, as for
Colombia. ``POBPCOAC`` is INE's activity classification (2 employed; 3, 4, 5
unemployed, including first-time job seekers and workers on unemployment
insurance, which INE counts as unemployed; 6-11 inactive). Occupation is
CIUO-08 and industry CIIU Rev.4, both at four digits. The job start date is
asked at the first interview only, so tenure exists for about one sixth of
the records (the ``ronda = 1`` rows merged from the implantation file).
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

COUNTRY = get_country("ury")
DEPTS = {
    1: "Montevideo", 2: "Artigas", 3: "Canelones", 4: "Cerro Largo", 5: "Colonia",
    6: "Durazno", 7: "Flores", 8: "Florida", 9: "Lavalleja", 10: "Maldonado",
    11: "Paysandú", 12: "Río Negro", 13: "Rivera", 14: "Rocha", 15: "Salto",
    16: "San José", 17: "Soriano", 18: "Tacuarembó", 19: "Treinta y Tres",
}  # fmt: skip
EMPLOYED, UNEMPLOYED = [2], [3, 4, 5]
NLFREASON = {6: 2, 7: 1, 8: 5, 9: 3, 10: 3, 11: 5}
# f73: 1 private employee, 2 public employee, 3 cooperative member, 4 employer,
# 5/6 own account (to 2024: without/with premises), 9 own account (2025),
# 7 unpaid family worker, 8 social employment programme
EMPSTAT = {1: 1, 2: 1, 3: 5, 4: 3, 5: 4, 6: 4, 9: 4, 7: 2, 8: 1}


def _years(raw: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(raw[col], errors="coerce").fillna(0)


def educat7(raw: pd.DataFrame) -> pd.Series:
    """Highest level from years passed by level and completion flags."""
    out = pd.Series(1, index=raw.index, dtype="Int8")
    out = out.mask(true_only(_years(raw, "e51_2") > 0), 2)
    out = out.mask(true_only(to_int(raw["e197_1"]) == 1), 3)
    lower = (_years(raw, "e51_4_a") > 0) | (_years(raw, "e51_4_b") > 0)
    upper = (_years(raw, "e51_5") > 0) | (_years(raw, "e51_6") > 0)
    out = out.mask(true_only(lower | upper), 4)
    done = (to_int(raw["e201_1c"]) == 1) | (to_int(raw["e201_1d"]) == 1)
    out = out.mask(true_only(done), 5)
    tertiary = (_years(raw, "e51_8") > 0) | (_years(raw, "e51_9") > 0)
    out = out.mask(true_only(tertiary), 6)
    univ = (_years(raw, "e51_10") > 0) | (_years(raw, "e51_11") > 0)
    return out.mask(true_only(univ), 7)


def harmonize(
    raw: pd.DataFrame, period: Period, raw_release: Optional[str] = None
) -> pd.DataFrame:
    raw = raw[raw["W"].notna() & (raw["W"] > 0)].copy()
    n_months = max(raw["mes"].nunique(), 1)
    df = pd.DataFrame(index=raw.index)
    df["year"] = to_int(raw["anio"], "Int16")
    df["int_year"] = df["year"]
    df["int_month"] = to_int(raw["mes"]).astype("Int8")
    df["wave"] = f"Q{period.quarter}"
    df["hhid"] = (raw["anio"] + "-" + raw["ID"]).astype("string")
    # a person is interviewed in up to three months of a quarter, so the
    # record is a person-month and the month is part of the id
    df["pid"] = (df["hhid"] + "-" + raw["nper"] + "-" + raw["mes"].str.zfill(2)).astype(
        "string"
    )
    df["rotation_group"] = raw["GR"].astype("string")
    df["visit_no"] = to_int(raw["ronda"]).astype("Int8")
    df["weight"] = (raw["W"] / n_months).astype("float64")
    region4 = to_int(raw["REGION_4"])
    region = to_int(raw["region"])
    urban = region4.map({1: 1, 2: 1, 3: 1, 4: 0}).astype("Int8")
    df["urban"] = urban.where(urban.notna(), region.map({1: 1, 2: 1, 3: 0})).astype(
        "Int8"
    )
    dpto = to_int(raw["dpto"])
    df["subnatid1"] = (dpto.astype("string") + " - " + dpto.map(DEPTS)).astype("string")
    df["age"] = to_int(raw["e27"], "Int16")
    df["male"] = to_int(raw["e26"]).map({1: 1, 2: 0}).astype("Int8")
    df["educat7"] = educat7(raw)
    df["educat4"] = educat4_from_7(df["educat7"])

    act = to_int(raw["POBPCOAC"])
    adult = df["age"] >= COUNTRY.minlaborage
    lstatus = pd.Series(3, index=raw.index, dtype="Int8")
    lstatus = lstatus.mask(true_only(act.isin(UNEMPLOYED)), 2)
    lstatus = lstatus.mask(true_only(act.isin(EMPLOYED)), 1)
    df["lstatus"] = lstatus.where(adult & act.notna())
    employed, nlf = df["lstatus"] == 1, df["lstatus"] == 3
    df["potential_lf"] = pd.NA
    sub = to_int(raw["SUBEMPLEO"])
    df["underemployment"] = (sub == 1).astype("Int8").where(employed)
    df["nlfreason"] = act.map(NLFREASON).astype("Int8").where(nlf)
    status = to_int(raw["f73"])
    df["empstat"] = status.map(EMPSTAT).astype("Int8").where(employed)
    df["ocusec"] = (
        status.map({2: 1}).fillna(2).astype("Int8").where(employed & status.notna())
    )

    isic = raw["f72_2"].str.strip()
    isic = isic.where(isic.str.fullmatch(r"\d{3,4}") & employed, pd.NA).str.zfill(4)
    df["industry_orig"] = isic.astype("string")
    df["industrycat_isic"] = isic.astype("string")
    df["isic_digits"] = pd.Series(4, index=raw.index, dtype="Int8").where(isic.notna())
    df["industrycat10"] = industrycat10_from_isic(df["industrycat_isic"])
    df["industrycat4"] = industrycat4_from_10(df["industrycat10"])

    ciuo = raw["f71_2"].str.strip()
    ciuo = ciuo.where(ciuo.str.fullmatch(r"\d{3,4}") & employed, pd.NA).str.zfill(4)
    df["occup_orig"] = ciuo.astype("string")
    isco, digits = map_isco_codes(ciuo)
    df["occup_isco"], df["occup_isco_digits"] = isco, digits
    df["occup"] = isco_major(df["occup_isco"])
    df["occup_skill"] = occup_skill_from_major(df["occup"])

    df["wage_no_compen"] = pd.NA  # earnings are in the implantation file only
    df["unitwage"] = pd.NA
    hrs = pd.to_numeric(raw["f85"], errors="coerce")
    df["whours"] = hrs.where(hrs > 0).astype("float32").where(employed)
    df["contract"] = pd.NA
    df["socialsec"] = (
        to_int(raw["f82"]).map({1: 1, 2: 0}).astype("Int8").where(employed)
    )
    df["firmsize_l"] = pd.NA
    df["firmsize_u"] = pd.NA
    # job start: year always, month often 0 (not recalled). With the month
    # unknown, jobs begun two or more years ago are at least 12 months old and
    # jobs begun this year under 12; a start last year is left undetermined.
    y0, m0 = _years(raw, "f307"), _years(raw, "f308")
    year, month = df["year"].astype("float"), df["int_month"].astype("float")
    known_month = m0.between(1, 12)
    exact = (year * 12 + month) - (y0 * 12 + m0)
    approx = (year - y0) * 12 + (month - 6.5)
    months = exact.where(known_month, approx)
    valid = (y0 > 1900) & (y0 <= year) & (months >= 0)
    ambiguous = ~known_month & (y0 == year - 1)
    tenure = months.where(valid & ~ambiguous)
    df["tenure_months"] = tenure.astype("float32").where(employed)
    df["tenure_lt12"] = (tenure < 12).astype("Int8").where(employed & tenure.notna())
    df["source_file"] = raw["source_file"].astype("string")
    return finalize(df, COUNTRY, period, source="own", raw_release=raw_release)
