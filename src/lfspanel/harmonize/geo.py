"""Georgia LFS (Geostat annual database, quarterly) -> target schema.

Geostat's derived flags give ILO status for persons 15+: ``Employed``,
``Unemployed``, and outside the labour force with a potential-labour-force
flag. Occupation is ISCO-08 at four digits and industry NACE Rev.2 at up to
four digits (divisions equal ISIC Rev.4 divisions, so two digits are kept).
The public file covers persons 15+ only; tenure and earnings (bands) are not
available.
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
)
from lfspanel.periods import Period

COUNTRY = get_country("geo")
REGIONS = {
    11: "Tbilisi", 15: "Adjara A.R.", 23: "Guria", 26: "Imereti", 29: "Kakheti",
    32: "Mtskheta-Mtianeti", 35: "Racha-Lechkhumi and Kvemo Svaneti",
    38: "Samegrelo-Zemo Svaneti", 41: "Samtskhe-Javakheti", 44: "Kvemo Kartli",
    47: "Shida Kartli",
}  # fmt: skip
EDUCAT7 = {1: 1, 2: 1, 3: 1, 4: 3, 5: 4, 6: 5, 7: 4, 8: 5, 9: 6, 10: 6, 11: 7, 12: 7}
EMPSTAT = {1: 1, 2: 4, 3: 2, 4: 1, 5: 2, 97: 5}
FIRMSIZE = {1: (1, 1), 2: (2, 4), 3: (5, 10), 4: (11, 19), 5: (20, 49), 6: (50, None)}


def _pad(code: pd.Series) -> pd.Series:
    s = code.astype("string").str.strip()
    s = s.where(s.notna() & (s != "") & (s != "0"), pd.NA)
    return s.str.zfill(4)


def harmonize(
    raw: pd.DataFrame, period: Period, raw_release: Optional[str] = None
) -> pd.DataFrame:
    raw = raw[raw["p_weights"].notna() & (raw["p_weights"] > 0)].copy()
    df = pd.DataFrame(index=raw.index)
    df["year"] = to_int(raw["year"], "Int16")
    df["int_year"] = df["year"]
    df["int_month"] = to_int(raw["month"]).astype("Int8")
    df["wave"] = f"Q{period.quarter}"
    df["hhid"] = raw["uid"].astype("string")
    df["pid"] = (raw["uid"] + "-" + raw["memberno"]).astype("string")
    df["rotation_group"] = raw["diaryid"].astype("string")
    df["visit_no"] = pd.NA
    df["weight"] = raw["p_weights"].astype("float64")
    df["urban"] = to_int(raw["urban_rural"]).map({1: 1, 2: 0}).astype("Int8")
    reg = to_int(raw["region"])
    df["subnatid1"] = (reg.astype("string") + " - " + reg.map(REGIONS)).astype("string")
    df["age"] = to_int(raw["age"], "Int16")
    df["male"] = to_int(raw["sex"]).map({2: 1, 1: 0}).astype("Int8")
    df["educat7"] = to_int(raw["education"]).map(EDUCAT7).astype("Int8")
    df["educat4"] = educat4_from_7(df["educat7"])

    emp_flag = to_int(raw["employed"]) == 1
    unemp_flag = to_int(raw["unemployed"]) == 1
    adult = df["age"] >= COUNTRY.minlaborage
    lstatus = pd.Series(3, index=raw.index, dtype="Int8")
    lstatus = lstatus.mask(unemp_flag, 2).mask(emp_flag, 1)
    df["lstatus"] = lstatus.where(adult)
    employed, nlf = df["lstatus"] == 1, df["lstatus"] == 3
    df["potential_lf"] = (
        (to_int(raw["potential_labour_force_plf"]) == 1).astype("Int8").where(nlf)
    )
    df["underemployment"] = (
        (to_int(raw["time_related_underemployment_tru"]) == 1)
        .astype("Int8")
        .where(employed)
    )
    reason = pd.Series(5, index=raw.index, dtype="Int8")
    reason = reason.mask(to_int(raw["outsidethelabourforce_disabled"]) == 1, 4)
    reason = reason.mask(to_int(raw["outsidethelabourforce_pensioner"]) == 1, 3)
    reason = reason.mask(to_int(raw["outsidethelabourforce_homemaker"]) == 1, 2)
    reason = reason.mask(to_int(raw["outsidethelabourforce_student"]) == 1, 1)
    df["nlfreason"] = reason.where(nlf)
    df["empstat"] = to_int(raw["status"]).map(EMPSTAT).astype("Int8")
    df["ocusec"] = (
        to_int(raw["sector_ownership"])
        .map({1: 1, 2: 2, 3: 2, 4: 2, 97: 2})
        .astype("Int8")
    )

    nace = _pad(raw["branch"])
    df["industry_orig"] = nace.astype("string")
    df["industrycat_isic"] = (nace.str[:2] + "00").astype("string")
    df["isic_digits"] = pd.Series(2, index=raw.index, dtype="Int8").where(nace.notna())
    df["industrycat10"] = industrycat10_from_isic(df["industrycat_isic"])
    df["industrycat4"] = industrycat4_from_10(df["industrycat10"])

    isco_raw = _pad(raw["occupation"])
    df["occup_orig"] = isco_raw.astype("string")
    isco, digits = map_isco_codes(isco_raw)
    df["occup_isco"], df["occup_isco_digits"] = isco, digits
    df["occup"] = isco_major(df["occup_isco"])
    df["occup_skill"] = occup_skill_from_major(df["occup"])

    df["wage_no_compen"] = pd.NA  # earnings are published in bands only
    df["unitwage"] = pd.NA
    hrs = pd.to_numeric(raw["m_actually_worked"], errors="coerce")
    df["whours"] = hrs.where(hrs > 0).astype("float32")
    df["contract"] = to_int(raw["b12_agreement_type"]).map({1: 1, 2: 0}).astype("Int8")
    informal = to_int(raw["informal_employment"])
    df["socialsec"] = informal.map({1: 0, 0: 1}).astype("Int8")
    band = to_int(raw["b26_employed_at_local_unit"])
    df["firmsize_l"] = band.map({k: v[0] for k, v in FIRMSIZE.items()}).astype("Int16")
    df["firmsize_u"] = band.map({k: v[1] for k, v in FIRMSIZE.items()}).astype("Int16")
    df["tenure_months"] = pd.NA
    df["tenure_lt12"] = pd.NA
    df["source_file"] = raw["source_file"].astype("string")
    return finalize(df, COUNTRY, period, source="own", raw_release=raw_release)
