"""Philippines LFS public-use file (full-sample rounds) -> target schema.

PSA's ``PUFNEWEMPSTAT`` gives labour status for persons 15+ (2005 ILO
definition). Occupation is PSOC 2012 released at two digits (sub-major
groups, ISCO-08 numbering; 01-03 armed forces) and industry PSIC 2009 at two
digits (ISIC Rev.4 divisions). Earnings are basic pay per day; tenure and
social-security coverage are not asked. Each quarter is represented by the
full-sample round in its first month (January, April, July, October).
Persons 15+ with no labour status (overseas Filipino workers and other
non-household-population members) are dropped, as PSA excludes them from the
population 15 and over.
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

COUNTRY = get_country("phl")
REGIONS = {
    1: "Region I (Ilocos)", 2: "Region II (Cagayan Valley)",
    3: "Region III (Central Luzon)", 4: "Region IV-A (CALABARZON)",
    5: "Region V (Bicol)", 6: "Region VI (Western Visayas)",
    7: "Region VII (Central Visayas)", 8: "Region VIII (Eastern Visayas)",
    9: "Region IX (Zamboanga Peninsula)", 10: "Region X (Northern Mindanao)",
    11: "Region XI (Davao)", 12: "Region XII (SOCCSKSARGEN)", 13: "NCR", 14: "CAR",
    15: "ARMM", 16: "Region XIII (Caraga)", 17: "MIMAROPA", 18: "Negros Island Region",
    19: "BARMM",
}  # fmt: skip
EMPSTAT = {0: 1, 1: 1, 2: 1, 3: 4, 4: 3, 5: 1, 6: 2}
NLFREASON = {"08": 1, "07": 2, "62": 3, "61": 3, "63": 4, "03": 4}


def educat7_from_grade(grade: pd.Series) -> pd.Series:
    """PSCED 2017 five-digit codes -> GLD educat7 (GLD PHL notes, 2019+ rule)."""
    g = grade.astype("string").str.strip()
    g = g.where(g != "").str.zfill(5)
    g = g.where(g.str.match(r"^\d{5}$"))
    first = g.str[0]
    out = pd.Series(pd.NA, index=grade.index, dtype="Int8")
    out = out.mask(true_only(first == "0"), 1)  # no grade, preschool, kindergarten
    out = out.mask(true_only(first == "1"), 2).mask(
        true_only(g == "10018"), 3
    )  # elementary; graduate
    out = out.mask(true_only(first == "2"), 4).mask(
        true_only(g == "24015"), 5
    )  # junior high; completed
    out = out.mask(true_only(first == "3"), 4).mask(
        true_only(g.isin(["34013", "35013"])), 5
    )  # senior high
    out = out.mask(
        true_only(first.isin(["4", "5"])), 6
    )  # post-secondary, short-cycle tertiary
    out = out.mask(true_only(first.isin(["6", "7", "8"])), 7)  # bachelor and above
    return out


def harmonize(
    raw: pd.DataFrame, period: Period, raw_release: Optional[str] = None
) -> pd.DataFrame:
    # persons 15+ without a labour status are overseas workers and others whom
    # PSA excludes from its working-age population; keep children for hhid work
    age = pd.to_numeric(raw["pufc05_age"], errors="coerce")
    in_scope = (age < 15) | raw["pufnewempstat"].isin(["1", "2", "3"])
    raw = raw[raw["pufpwgtprv"].notna() & (raw["pufpwgtprv"] > 0) & in_scope].copy()
    df = pd.DataFrame(index=raw.index)
    df["year"] = to_int(raw["pufsvyyr"], "Int16")
    df["int_year"] = df["year"]
    df["int_month"] = to_int(raw["pufsvymo"]).astype("Int8")
    df["wave"] = f"Q{period.quarter}"
    df["hhid"] = (
        raw["pufsvyyr"] + raw["pufsvymo"].str.zfill(2) + "-" + raw["pufhhnum"]
    ).astype("string")
    df["pid"] = (df["hhid"] + "-" + raw["pufc01_lno"]).astype("string")
    df["rotation_group"] = pd.NA
    df["visit_no"] = pd.NA
    df["weight"] = raw["pufpwgtprv"].astype("float64")
    df["urban"] = to_int(raw["pufurb2020"]).map({1: 1, 2: 0}).astype("Int8")
    reg = to_int(raw["pufreg"])
    df["subnatid1"] = (reg.astype("string") + " - " + reg.map(REGIONS)).astype("string")
    df["age"] = to_int(raw["pufc05_age"], "Int16")
    df["male"] = to_int(raw["pufc04_sex"]).map({1: 1, 2: 0}).astype("Int8")
    df["educat7"] = educat7_from_grade(raw["pufc07_grade"])
    df["educat4"] = educat4_from_7(df["educat7"])

    status = to_int(raw["pufnewempstat"])
    adult = df["age"] >= COUNTRY.minlaborage
    df["lstatus"] = status.map({1: 1, 2: 2, 3: 3}).astype("Int8").where(adult)
    employed, nlf = df["lstatus"] == 1, df["lstatus"] == 3
    df["potential_lf"] = pd.NA
    df["underemployment"] = (
        (to_int(raw["pufc20_pwmore"]) == 1).astype("Int8").where(employed)
    )
    reason = raw["pufc34_wynot"].str.zfill(2).map(NLFREASON)
    df["nlfreason"] = (
        reason.fillna(5).astype("Int8").where(nlf & (raw["pufc34_wynot"] != ""))
    )
    pclass = to_int(raw["pufc23_pclass"])
    df["empstat"] = pclass.map(EMPSTAT).astype("Int8")
    df["ocusec"] = pclass.map({2: 1, 0: 2, 1: 2, 3: 2, 4: 2, 5: 2, 6: 2}).astype("Int8")

    pkb = raw["pufc16_pkb"].str.zfill(2)
    pkb = pkb.where(raw["pufc16_pkb"] != "")
    df["industry_orig"] = pkb.astype("string")
    df["industrycat_isic"] = (pkb + "00").astype("string")
    df["isic_digits"] = pd.Series(2, index=raw.index, dtype="Int8").where(pkb.notna())
    df["industrycat10"] = industrycat10_from_isic(df["industrycat_isic"])
    df["industrycat4"] = industrycat4_from_10(df["industrycat10"])

    procc = raw["pufc14_procc"].str.zfill(2)
    procc = procc.where(raw["pufc14_procc"] != "")
    df["occup_orig"] = procc.astype("string")
    isco, digits = map_isco_codes((procc + "00").astype("string"))
    df["occup_isco"], df["occup_isco_digits"] = isco, digits
    df["occup"] = isco_major(df["occup_isco"])
    df["occup_skill"] = occup_skill_from_major(df["occup"])

    pay = pd.to_numeric(raw["pufc25_pbasic"], errors="coerce")
    df["wage_no_compen"] = pay.where((pay > 0) & (df["empstat"] == 1)).astype("float64")
    df.loc[df["empstat"] == 2, "wage_no_compen"] = 0.0
    df["unitwage"] = pd.Series(1, index=raw.index, dtype="Int8").where(
        df["wage_no_compen"] > 0
    )
    df.loc[df["empstat"] == 2, "unitwage"] = 5
    hrs = pd.to_numeric(raw["pufc19_phours"], errors="coerce")
    df["whours"] = hrs.where(hrs > 0).astype("float32")
    df["contract"] = (
        pd.NA
    )  # nature of employment (permanent / short-term) is not a contract question
    df["socialsec"] = pd.NA
    df["firmsize_l"] = pd.NA
    df["firmsize_u"] = pd.NA
    df["tenure_months"] = pd.NA
    df["tenure_lt12"] = pd.NA
    df["source_file"] = raw["source_file"].astype("string")
    return finalize(df, COUNTRY, period, source="own", raw_release=raw_release)
