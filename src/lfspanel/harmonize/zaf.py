"""South Africa QLFS (quarterly, DataFirst release) -> target schema.

Stats SA's ``Status`` gives labour status for persons 15-64 (the public file
covers all ages; 15+ used here): 1 employed, 2 unemployed (official, searching
definition), 3 discouraged work-seeker (not in the labour force,
``potential_lf = 1``), 4 other not economically active. Occupation is SASCO
2003 (ISCO-88 structure with national extensions), mapped SASCO -> ISCO-88 ->
ISCO-08 through the ILO correspondence; industry is SIC 5 (ISIC Rev.3
structure) mapped to ISIC Rev.4 divisions where the correspondence is one to
one and to sections otherwise. Tenure comes from the job start date.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, Optional, Tuple

import pandas as pd

from lfspanel.config import get_country
from lfspanel.crosswalks import load_crosswalk, map_isco_codes
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

COUNTRY = get_country("zaf")

PROVINCES = {
    1: "Western Cape", 2: "Eastern Cape", 3: "Northern Cape", 4: "Free State",
    5: "KwaZulu-Natal", 6: "North West", 7: "Gauteng", 8: "Mpumalanga", 9: "Limpopo",
}  # fmt: skip
EDUCAT7 = {**{0: 1, 98: 1}, **{k: 2 for k in range(1, 7)}, 7: 3}
EDUCAT7.update({k: 4 for k in (8, 9, 10, 11, 14, 15)})
EDUCAT7.update({k: 5 for k in (12, 13, 16)})
EDUCAT7.update({k: 6 for k in (17, 18, 19, 20, 21, 22, 23, 24)})
EDUCAT7.update({k: 7 for k in (25, 26, 27, 28, 29)})
FIRMSIZE = {
    1: (1, 1),
    2: (2, 2),
    3: (3, 5),
    4: (6, 10),
    5: (11, 20),
    6: (21, 50),
    7: (51, None),
}
NLFREASON = {1: 1, 2: 2, 3: 4, 4: 3, 5: 5, 6: 5}

# SIC 5 division (first two digits of the 3-digit code) -> ISIC Rev.4 code and
# the number of digits that are reliable (2 = division, 1 = section only).
# Derived from the GLD SIC 5 -> ISIC Rev.3 table and the UN Rev.3 -> Rev.4
# correspondence; divisions split across Rev.4 sections take the section of
# their dominant employment.
SIC_DIV_TO_ISIC4: Dict[int, Tuple[str, int]] = {
    1: ("9700", 2), 2: ("9900", 2), 3: ("9900", 2),
    11: ("0100", 2), 12: ("0200", 2), 13: ("0300", 2),
    21: ("0500", 2), 22: ("0600", 2), 23: ("0700", 2), 24: ("0700", 2), 25: ("0800", 2),
    30: ("1000", 1), 31: ("1300", 1), 32: ("1600", 1), 33: ("1800", 1), 34: ("2000", 1),
    35: ("2400", 1), 36: ("2600", 1), 37: ("2900", 1), 38: ("3100", 1), 39: ("3100", 1),
    41: ("3500", 2), 42: ("3600", 2),
    50: ("4100", 1),
    61: ("4600", 2), 62: ("4700", 2), 63: ("4500", 2), 64: ("5500", 1),
    71: ("4900", 2), 72: ("5000", 2), 73: ("5100", 2), 74: ("5200", 2), 75: ("6100", 1),
    81: ("6400", 2), 82: ("6500", 2), 83: ("6600", 2),
    84: ("6800", 2), 85: ("7700", 2), 86: ("6200", 1), 87: ("7200", 2), 88: ("8200", 1),
    91: ("8400", 2), 92: ("8500", 2), 93: ("8600", 1), 94: ("3700", 1), 95: ("9400", 2),
    96: ("9000", 1), 99: ("9600", 2),
}  # fmt: skip
# three-digit SIC codes with a one-to-one Rev.4 division
SIC3_TO_ISIC4: Dict[int, Tuple[str, int]] = {
    301: ("1000", 2), 302: ("1000", 2), 303: ("1000", 2), 304: ("1000", 2),
    305: ("1100", 2), 306: ("1200", 2), 311: ("1300", 2), 312: ("1300", 2),
    313: ("1300", 2), 314: ("1400", 2), 315: ("1400", 2), 316: ("1500", 2),
    317: ("1500", 2), 321: ("1600", 2), 322: ("1600", 2), 323: ("1700", 2),
    324: ("1800", 2), 325: ("1800", 2), 331: ("1900", 2), 332: ("1900", 2),
    334: ("2000", 2), 335: ("2000", 2), 336: ("2000", 2), 337: ("2200", 2),
    338: ("2200", 2), 341: ("2300", 2), 342: ("2300", 2), 351: ("2400", 2),
    352: ("2400", 2), 353: ("2400", 2), 354: ("2500", 2), 355: ("2500", 2),
    356: ("2800", 2), 357: ("2800", 2), 358: ("2800", 2), 359: ("2800", 2),
    361: ("2700", 2), 362: ("2700", 2), 363: ("2700", 2), 364: ("2700", 2),
    365: ("2700", 2), 371: ("2600", 2), 372: ("2600", 2), 373: ("2600", 2),
    374: ("2600", 2), 375: ("2600", 2), 376: ("2600", 2), 381: ("2900", 2),
    382: ("2900", 2), 383: ("2900", 2), 384: ("3000", 2), 385: ("3000", 2),
    386: ("3000", 2), 387: ("3000", 2), 391: ("3100", 2), 392: ("3200", 2),
    393: ("3200", 2), 394: ("3200", 2), 395: ("3800", 2), 881: ("6800", 2),
    882: ("7700", 2), 883: ("6200", 2), 884: ("7200", 2), 641: ("5500", 2),
    642: ("5600", 2), 643: ("5600", 2), 751: ("5300", 2), 752: ("6100", 2),
    931: ("8600", 2), 932: ("8600", 2), 933: ("8700", 2), 934: ("8800", 2),
    961: ("9000", 2), 962: ("9100", 2), 963: ("9100", 2), 964: ("9300", 2),
}  # fmt: skip


@lru_cache(maxsize=None)
def _isco_tables():
    i88 = load_crosswalk("isco88_to_isco08")
    i88["isco08"] = i88["isco08"].astype("string").fillna("")
    unit = i88.set_index("isco88")
    by_prefix: Dict[str, Tuple[str, int]] = {}
    for d in (3, 2, 1):
        for prefix, g in i88.groupby(i88["isco88"].str[:d]):
            targets = sorted({t for ts in g["targets"] for t in ts.split(",")})
            p = os.path.commonprefix(targets)
            by_prefix[prefix] = (p.ljust(4, "0") if p else "", len(p))
    sasco = (
        load_crosswalk("sasco2003_to_isco88").set_index("sasco3")["isco88"].astype(str)
    )
    return unit, by_prefix, sasco


def sasco_to_isco08(code: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """SASCO 2003 (4 digits) -> ISCO-08 prefix padded to 4 chars, and digits.

    Unit groups that exist in ISCO-88 follow the ILO correspondence; national
    groups fall back to the SASCO minor group's ISCO-88 counterpart (GLD
    mapping) and the common ISCO-08 prefix of that group's targets.
    """
    unit, by_prefix, sasco = _isco_tables()
    s = code.astype("string").str.strip().str.zfill(4)

    def widen(prefix: str):
        """Common ISCO-08 prefix of an ISCO-88 group, widening the group as needed."""
        for d in range(len(prefix), 0, -1):
            hit = by_prefix.get(prefix[:d])
            if hit and hit[1] > 0:
                return hit
        return ("", 0)

    def one(c):
        if pd.isna(c) or c in ("", "0000", "9999", "9888"):
            return ("", 0)
        if c in unit.index and int(unit.loc[c, "digits"]) > 0:
            return (unit.loc[c, "isco08"], int(unit.loc[c, "digits"]))
        i88 = sasco.get(c[:3]) if c not in unit.index else c[:3]
        if i88 is None or i88 == "0":
            return ("", 0)
        return widen(i88)

    mapped = s.map(one)
    isco = mapped.map(lambda t: t[0] or pd.NA).astype("string")
    digits = mapped.map(lambda t: t[1]).astype("Int8")
    return isco.where(digits > 0), digits.where(digits > 0)


def sic_to_isic4(code: pd.Series) -> Tuple[pd.Series, pd.Series]:
    sic = pd.to_numeric(code, errors="coerce")

    def one(v):
        if pd.isna(v) or v in (988, 999):
            return ("", 0)
        v = int(v)
        if v in SIC3_TO_ISIC4:
            return SIC3_TO_ISIC4[v]
        return SIC_DIV_TO_ISIC4.get(v // 10, ("", 0))

    mapped = sic.map(one)
    isic = mapped.map(lambda t: t[0] or pd.NA).astype("string")
    digits = mapped.map(lambda t: t[1]).astype("Int8")
    return isic.where(digits > 0), digits.where(digits > 0)


ICSE18_FROM = Period(
    "2025Q3"
)  # Stats SA recoded Q45WRK4WHOM to ICSE-18 style categories


def status_in_employment(raw: pd.DataFrame, period: Period) -> pd.Series:
    """GLD empstat from Q45WRK4WHOM, whose codes changed meaning in 2025Q3.

    Up to 2025Q2: 1 employee, 2 employer, 3 own account, 4 unpaid household
    business. From 2025Q3: 1 employee, 2 in own business (employers and own
    account together), 3 helping in a family business, 4 paid apprentice,
    5 helping a relative employed elsewhere. Own-business workers are split
    by the number of employees reported in Q416NRWORKERS (0 employees ->
    own account, otherwise employer; unknown -> own account).
    """
    code = to_int(raw["q45wrk4whom"])
    if period < ICSE18_FROM:
        return code.map({1: 1, 2: 3, 3: 4, 4: 2}).astype("Int8")
    out = code.map({1: 1, 2: 4, 3: 2, 4: 1, 5: 2}).astype("Int8")
    employees = to_int(raw["q416nrworkers"])
    employer = ((code == 2) & employees.between(2, 7)).fillna(False)
    return out.mask(true_only(employer), 3).astype("Int8")


def harmonize(
    raw: pd.DataFrame, period: Period, raw_release: Optional[str] = None
) -> pd.DataFrame:
    raw = raw[raw["weight"].notna() & (raw["weight"] > 0)].copy()
    df = pd.DataFrame(index=raw.index)
    df["year"] = period.year
    df["int_year"] = period.year
    df["int_month"] = pd.NA
    df["wave"] = f"Q{period.quarter}"
    df["hhid"] = raw["uqno"].astype("string")
    df["pid"] = (raw["uqno"] + "-" + raw["personno"]).astype("string")
    df["rotation_group"] = pd.NA
    df["visit_no"] = pd.NA
    df["weight"] = raw["weight"].astype("float64")
    df["urban"] = to_int(raw["geo_type_code"]).map({1: 1, 2: 0, 3: 0}).astype("Int8")
    prov = to_int(raw["province"])
    df["subnatid1"] = (prov.astype("string") + " - " + prov.map(PROVINCES)).astype(
        "string"
    )
    df["age"] = to_int(raw["q14age"], "Int16")
    df["male"] = to_int(raw["q13gender"]).map({1: 1, 2: 0}).astype("Int8")
    df["educat7"] = to_int(raw["q17education"]).map(EDUCAT7).astype("Int8")
    df["educat4"] = educat4_from_7(df["educat7"])

    status = to_int(raw["status"])
    adult = df["age"] >= COUNTRY.minlaborage
    df["lstatus"] = status.map({1: 1, 2: 2, 3: 3, 4: 3}).astype("Int8").where(adult)
    employed, nlf = df["lstatus"] == 1, df["lstatus"] == 3
    df["potential_lf"] = (status == 3).astype("Int8").where(nlf)
    df["underemployment"] = (
        (to_int(raw["underempl"]) == 1).astype("Int8").where(employed)
    )
    df["nlfreason"] = (
        to_int(raw["inactreason"]).map(NLFREASON).astype("Int8").where(nlf)
    )
    df["empstat"] = status_in_employment(raw, period)
    df["ocusec"] = (
        to_int(raw["q415typebusns"]).map({1: 1, 2: 1, 3: 2, 4: 2, 5: 2}).astype("Int8")
    )

    df["industry_orig"] = (
        raw["q43industry"].where(raw["q43industry"] != "").astype("string")
    )
    df["industrycat_isic"], df["isic_digits"] = sic_to_isic4(raw["q43industry"])
    df["industrycat10"] = industrycat10_from_isic(df["industrycat_isic"])
    df["industrycat4"] = industrycat4_from_10(df["industrycat10"])

    df["occup_orig"] = (
        raw["q42occupation"].where(raw["q42occupation"] != "").astype("string")
    )
    isco, digits = sasco_to_isco08(raw["q42occupation"])
    isco, digits2 = map_isco_codes(isco)
    df["occup_isco"] = isco
    df["occup_isco_digits"] = (
        pd.concat([digits, digits2], axis=1).min(axis=1).astype("Int8")
    )
    df["occup"] = isco_major(df["occup_isco"])
    df["occup_skill"] = occup_skill_from_major(df["occup"])

    df["wage_no_compen"] = pd.NA  # earnings are not in the public-use file
    df["unitwage"] = pd.NA
    hrs = pd.to_numeric(raw["q419totalhrs"], errors="coerce")
    df["whours"] = hrs.where(hrs > 0).astype("float32")
    df["contract"] = to_int(raw["q411contracttype"]).map({1: 1, 2: 0}).astype("Int8")
    df["socialsec"] = to_int(raw["q46pension"]).map({1: 1, 2: 0}).astype("Int8")
    band = to_int(raw["q416nrworkers"])
    df["firmsize_l"] = band.map({k: v[0] for k, v in FIRMSIZE.items()}).astype("Int16")
    df["firmsize_u"] = band.map({k: v[1] for k, v in FIRMSIZE.items()}).astype("Int16")
    start_y = pd.to_numeric(raw["q44yearstart"], errors="coerce")
    start_m = pd.to_numeric(raw["q44monthstart"], errors="coerce")
    mid_month = (
        period.quarter * 3 - 1
    )  # interview month taken as the quarter's middle month
    months = (period.year - start_y) * 12 + (mid_month - start_m.fillna(6))
    months = months.where((start_y > 1900) & (months >= 0))
    df["tenure_months"] = months.astype("float32")
    df["tenure_lt12"] = (
        pd.Series(pd.NA, index=raw.index, dtype="Int8")
        .mask(true_only(months < 12), 1)
        .mask(true_only(months >= 12), 0)
    )
    df["source_file"] = raw["source_file"].astype("string")
    return finalize(df, COUNTRY, period, source="own", raw_release=raw_release)
