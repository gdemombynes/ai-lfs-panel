"""Nigeria NLFS (quarterly, ICLS-19) -> target schema.

Follows the World Bank GLD harmonization of the same files. Employment is
work for pay or profit in the last seven days: paid work for someone else,
a non-farm business or family business, or farming whose products are
mainly sold; subsistence farmers are outside employment, as in NBS's own
(ICLS-19) headline rates. Unemployment is searching in the last four weeks
(or having a job arranged) and being available now or within two weeks,
which reproduces NBS's published rates; the GLD rule without future
starters and two-week availability gives 5.1 % against NBS's 5.3 % in
2024Q1. Occupation is ISCO-08 and industry ISIC Rev.4 at four
digits (leading zeros lost in the files). Tenure comes from the job start
date; earnings are kept as NA pending a unit crosswalk.
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

COUNTRY = get_country("nga")
ZONES = {
    1: "North Central", 2: "North East", 3: "North West",
    4: "South East", 5: "South South", 6: "South West",
}  # fmt: skip
# ed7 (highest qualification) -> educat7, as in GLD
EDUCAT7 = {
    1: 1,
    2: 3,
    3: 4,
    5: 4,
    6: 5,
    7: 6,
    8: 6,
    10: 6,
    41: 6,
    42: 6,
    9: 7,
    11: 7,
    12: 7,
}
NLFREASON = {1: 5, 2: 5, 3: 5, 4: 3, 5: 5, 6: 5, 7: 5, 8: 4, 9: 5, 10: 5}


def _pad(code: pd.Series) -> pd.Series:
    s = code.astype("string").str.strip()
    s = s.where(s.notna() & (s != "") & (s != "0"), pd.NA)
    return s.str.zfill(4)


def employed_flag(raw: pd.DataFrame) -> pd.Series:
    """ICLS-19 employment (GLD rule): any route into the main-job module."""
    yes = lambda c: to_int(raw[c]) == 1  # noqa: E731
    farm_sold = to_int(raw["agf2b"]).isin([4, 5]) | to_int(raw["agf2c"]).isin([1, 3])
    cond = yes("atw1") | yes("agf1b_4") | yes("agf2a") | farm_sold | yes("agf2d")
    return true_only(cond)


def harmonize(
    raw: pd.DataFrame, period: Period, raw_release: Optional[str] = None
) -> pd.DataFrame:
    raw = raw[raw["popw"].notna() & (raw["popw"] > 0)].copy()
    df = pd.DataFrame(index=raw.index)
    date = pd.to_datetime(raw["interviewdate"], errors="coerce")
    df["year"] = period.year
    df["int_year"] = date.dt.year.astype("Int16")
    df["int_month"] = date.dt.month.astype("Int8")
    df["wave"] = f"Q{period.quarter}"
    df["hhid"] = raw["interview_key"].astype("string")
    df["pid"] = (raw["interview_key"] + "-" + raw["hhroster_id"].str.zfill(2)).astype(
        "string"
    )
    df["rotation_group"] = pd.NA
    df["visit_no"] = pd.NA
    df["weight"] = raw["popw"].astype("float64")
    df["urban"] = to_int(raw["id5_sector"]).map({1: 1, 2: 0}).astype("Int8")
    zone = to_int(raw["id1_zone"])
    df["subnatid1"] = (zone.astype("string") + " - " + zone.map(ZONES)).astype("string")
    df["age"] = to_int(raw["dc5"], "Int16")
    df["male"] = to_int(raw["dc3"]).map({1: 1, 2: 0}).astype("Int8")
    df["educat7"] = to_int(raw["ed7"]).map(EDUCAT7).astype("Int8")
    df["educat4"] = educat4_from_7(df["educat7"])

    adult = true_only(df["age"] >= COUNTRY.minlaborage)
    emp = employed_flag(raw)
    searching = true_only((to_int(raw["um1_1"]) == 1) | (to_int(raw["um1_2"]) == 1))
    # future starters count as searching (NBS); available now or within two weeks
    future = true_only((to_int(raw["um4"]) == 1) | (to_int(raw["um9"]) == 17))
    searching = searching | future
    available = true_only((to_int(raw["um10a"]) == 1) | (to_int(raw["um10b"]) == 1))
    lstatus = pd.Series(3, index=raw.index, dtype="Int8")
    lstatus = lstatus.mask(searching & available, 2).mask(emp, 1)
    df["lstatus"] = lstatus.where(adult)
    employed, nlf = df["lstatus"] == 1, df["lstatus"] == 3
    not_available = true_only(to_int(raw["um10a"]).isin([2, 3]))
    plf = (searching & not_available) | (available & ~searching)
    df["potential_lf"] = plf.astype("Int8").where(nlf)
    df["underemployment"] = (to_int(raw["sjj7"]) == 1).astype("Int8").where(employed)
    df["nlfreason"] = to_int(raw["um7"]).map(NLFREASON).astype("Int8").where(nlf)
    mjj4 = to_int(raw["mjj4"])
    empstat = mjj4.map({1: 1, 2: 4, 3: 2, 4: 5, 5: 5}).astype("Int8")
    empstat = empstat.mask(true_only((mjj4 == 2) & (to_int(raw["mjj6"]) == 1)), 3)
    empstat = empstat.mask(true_only((mjj4 == 4) & (to_int(raw["mjj8b_9"]) == 0)), 1)
    df["empstat"] = empstat
    sector = to_int(raw["mjj8a"])
    df["ocusec"] = (
        pd.Series(pd.NA, index=raw.index, dtype="Int8")
        .mask(true_only(sector.between(1, 4)), 1)
        .mask(true_only(sector.between(5, 12)), 2)
        .mask(true_only(sector.isna() & empstat.isin([2, 3, 4])), 2)
    )

    isic = _pad(raw["mjj3cclean"])
    df["industry_orig"] = isic.astype("string")
    df["industrycat_isic"] = isic.astype("string")
    df["isic_digits"] = pd.Series(4, index=raw.index, dtype="Int8").where(isic.notna())
    df["industrycat10"] = industrycat10_from_isic(df["industrycat_isic"])
    df["industrycat4"] = industrycat4_from_10(df["industrycat10"])

    isco_raw = _pad(raw["mjj2cclean"])
    df["occup_orig"] = isco_raw.astype("string")
    isco, digits = map_isco_codes(isco_raw)
    df["occup_isco"], df["occup_isco_digits"] = isco, digits
    df["occup"] = isco_major(df["occup_isco"])
    df["occup_skill"] = occup_skill_from_major(df["occup"])

    df["wage_no_compen"] = pd.NA
    df["unitwage"] = pd.NA
    hrs = pd.to_numeric(raw["mjj12"], errors="coerce")
    df["whours"] = hrs.where(hrs > 0).astype("float32")
    mjj8c = to_int(raw["mjj8c"])
    df["contract"] = (
        pd.Series(pd.NA, index=raw.index, dtype="Int8")
        .mask(true_only(mjj8c.isin([1, 2])), 1)
        .mask(true_only(mjj8c == 3), 0)
    )
    df["socialsec"] = to_int(raw["mjj8l_1"]).map({1: 1, 0: 0}).astype("Int8")
    df["firmsize_l"] = pd.NA
    df["firmsize_u"] = pd.NA
    start_y = pd.to_numeric(raw["mjj10"], errors="coerce").where(
        lambda s: s.between(1900, 2100)
    )
    start_m = pd.to_numeric(raw["mjj11"], errors="coerce").where(
        lambda s: s.between(1, 12)
    )
    months = (date.dt.year - start_y) * 12 + (date.dt.month - start_m.fillna(6))
    months = months.where(months >= 0)
    df["tenure_months"] = months.astype("float32")
    df["tenure_lt12"] = (
        pd.Series(pd.NA, index=raw.index, dtype="Int8")
        .mask(true_only(months < 12), 1)
        .mask(true_only(months >= 12), 0)
    )
    df["source_file"] = raw["source_file"].astype("string")
    return finalize(df, COUNTRY, period, source="own", raw_release=raw_release)
