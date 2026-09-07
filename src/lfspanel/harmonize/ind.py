"""India PLFS (MoSPI unit-level releases) -> target schema.

Labour status follows the current weekly status (CWS) codes, as in the
quarterly bulletins: 11-72 employed, 81 and 82 unemployed, 91-99 outside the
labour force. This departs from GLD's IND harmonization in two places, both
needed to reproduce MoSPI's published rates: code 82 (available but not
seeking) is unemployed, not inactive, and code 98 (casual worker sick all
week) is inactive, not employed. Occupation is the NCO-2015 code of the CWS
activity at 3 digits, which is the ISCO-08 minor group; industry is the
NIC-2008 division, which is the ISIC Rev.4 division.

Weights depend on the release (``plfs_release`` from the reader):

* ``q2025``: quarterly multiplier / 100 (bulletin definition);
* ``cy2021``-``cy2024``: first-visit multiplier / 100, halved when the
  stratum has two sub-samples (``nss != nsc``), i.e. the quarter-level weight
  before MoSPI's division by the number of quarters that builds the annual
  estimate;
* ``cy2021``: as above times 2, because the 2021 file's multipliers sum to
  the population over each two-quarter panel rather than per quarter;
* ``cy2025``: annual first-visit multiplier / 100 times 4 (the 2025 file
  spreads the year's population over twelve monthly panels; only 2025Q1 is
  read from it).

Job characteristics beyond status, occupation, industry, hours and earnings
refer to the usual principal activity, not the CWS job, and are absent from
the quarterly file, so contract, social security, firm size, sector of
employment and tenure are left missing for every quarter.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from lfspanel.config import get_country
from lfspanel.crosswalks import isco88_group_to_isco08, map_isco_codes
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

COUNTRY = get_country("ind")
STATES = {
    1: "Jammu & Kashmir", 2: "Himachal Pradesh", 3: "Punjab", 4: "Chandigarh",
    5: "Uttarakhand", 6: "Haryana", 7: "Delhi", 8: "Rajasthan", 9: "Uttar Pradesh",
    10: "Bihar", 11: "Sikkim", 12: "Arunachal Pradesh", 13: "Nagaland", 14: "Manipur",
    15: "Mizoram", 16: "Tripura", 17: "Meghalaya", 18: "Assam", 19: "West Bengal",
    20: "Jharkhand", 21: "Odisha", 22: "Chhattisgarh", 23: "Madhya Pradesh",
    24: "Gujarat", 25: "Dadra & Nagar Haveli and Daman & Diu", 26: "Daman & Diu",
    27: "Maharashtra", 28: "Andhra Pradesh", 29: "Karnataka", 30: "Goa",
    31: "Lakshadweep", 32: "Kerala", 33: "Tamil Nadu", 34: "Puducherry",
    35: "Andaman & Nicobar Islands", 36: "Telangana", 37: "Ladakh",
}  # fmt: skip
EMPLOYED = [11, 12, 21, 31, 41, 42, 51, 61, 62, 71, 72]
UNEMPLOYED = [81, 82]
EMPSTAT = {
    11: 4, 12: 3, 21: 2, 31: 1, 41: 1, 42: 1, 51: 1, 61: 4, 62: 4, 71: 1, 72: 1,
}  # fmt: skip
NLFREASON = {91: 1, 92: 2, 93: 2, 94: 3, 95: 4, 97: 5, 98: 5, 99: 5}
EDUCAT7 = {
    1: 1, 2: 1, 3: 1, 4: 1, 5: 2, 6: 3, 7: 4, 8: 5, 9: 5, 10: 5, 11: 6, 12: 7, 13: 7,
}  # fmt: skip
REGULAR, SELF, CASUAL = [31, 71, 72], [11, 12, 21, 61, 62], [41, 42, 51]
NCO2004_PANELS = {"P2"}  # rotation panel 2 (to June 2021) still coded NCO-2004
# No PLFS person weight exceeds 0.9 million; the 2022 calendar file carries
# one Assam FSU (July 2022, sub-strata 2-3) with multipliers of 1.2-23.7
# million per person, which alone would add 240 million rural residents.
MAX_WEIGHT = 1_000_000.0


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def weight(raw: pd.DataFrame) -> pd.Series:
    """Quarter-level person weight, by release (see module docstring)."""
    mult = _num(raw["mult"])
    release = str(raw["plfs_release"].iloc[0]) if len(raw) else "q2025"
    if release == "q2025":
        return mult / 100.0
    if release == "cy2025":
        return mult / 100.0 * 4.0
    nss, nsc = _num(raw["nss"]), _num(raw["nsc"])
    quarterly = (mult / 100.0).mask(true_only(nss != nsc), mult / 200.0)
    if release == "cy2021":
        return quarterly * 2.0  # 2021 multipliers are built per half-year panel
    return quarterly


def _day_sum(raw: pd.DataFrame, prefix: str) -> pd.Series:
    cols = [f"{prefix}{d}" for d in range(1, 8) if f"{prefix}{d}" in raw.columns]
    if not cols:
        return pd.Series(np.nan, index=raw.index, dtype="float64")
    vals = pd.concat([_num(raw[c]) for c in cols], axis=1)
    return vals.sum(axis=1, min_count=1)


def harmonize(
    raw: pd.DataFrame, period: Period, raw_release: Optional[str] = None
) -> pd.DataFrame:
    w = weight(raw)
    raw = raw[w.notna() & (w > 0) & (w <= MAX_WEIGHT)].copy()
    w = w[raw.index]
    df = pd.DataFrame(index=raw.index)
    df["year"] = period.year
    df["int_year"] = period.year
    df["int_month"] = to_int(raw["month"]).astype("Int8")
    df["wave"] = raw["qtr"].astype("string")
    hh = (
        raw["sec"].str.zfill(1)
        + raw["st"].str.zfill(2)
        + raw["mfsu"].str.zfill(5)
        + raw["hg"].str.zfill(1)
        + raw["sss"].str.zfill(1)
        + raw["ssu"].str.zfill(2)
    )
    df["hhid"] = hh.astype("string")
    df["pid"] = (hh + "-" + raw["srl"].str.zfill(2)).astype("string")
    df["rotation_group"] = raw["panel"].astype("string")
    df["visit_no"] = to_int(raw["visit"].str.extract(r"(\d+)$")[0]).astype("Int8")
    df["weight"] = w.astype("float64")
    df["urban"] = to_int(raw["sec"]).map({1: 0, 2: 1}).astype("Int8")
    st = to_int(raw["st"])
    df["subnatid1"] = (st.astype("string") + " - " + st.map(STATES)).astype("string")
    df["age"] = to_int(raw["age"], "Int16")
    df["male"] = to_int(raw["sex"]).map({1: 1, 2: 0}).astype("Int8")
    df["educat7"] = to_int(raw["gedu_lvl"]).map(EDUCAT7).astype("Int8")
    df["educat4"] = educat4_from_7(df["educat7"])

    cws = to_int(raw["acws"])
    adult = df["age"] >= COUNTRY.minlaborage
    lstatus = pd.Series(3, index=raw.index, dtype="Int8")
    lstatus = lstatus.mask(true_only(cws.isin(UNEMPLOYED)), 2)
    lstatus = lstatus.mask(true_only(cws.isin(EMPLOYED)), 1)
    df["lstatus"] = lstatus.where(adult)
    employed, nlf = df["lstatus"] == 1, df["lstatus"] == 3
    df["potential_lf"] = pd.NA
    addl = _day_sum(raw, "ahr")
    df["underemployment"] = (addl > 0).astype("Int8").where(employed & addl.notna())
    df["nlfreason"] = cws.map(NLFREASON).astype("Int8").where(nlf)
    df["empstat"] = cws.map(EMPSTAT).astype("Int8").where(employed)
    df["ocusec"] = pd.NA

    nic = raw["aind_cws"].str.strip()
    nic = nic.where(nic.str.fullmatch(r"\d{1,2}") & employed, pd.NA).str.zfill(2)
    df["industry_orig"] = nic.astype("string")
    df["industrycat_isic"] = (nic + "00").astype("string")
    df["isic_digits"] = pd.Series(2, index=raw.index, dtype="Int8").where(nic.notna())
    df["industrycat10"] = industrycat10_from_isic(df["industrycat_isic"])
    df["industrycat4"] = industrycat4_from_10(df["industrycat10"])

    nco = raw["ocu_cws"].str.strip()
    nco = nco.where(nco.str.fullmatch(r"\d{3}") & ~nco.isin(["998", "999"]), pd.NA)
    nco = nco.where(employed, pd.NA)
    df["occup_orig"] = nco.astype("string")
    isco, digits = map_isco_codes(nco)
    old = true_only(raw["panel"].str.strip().isin(NCO2004_PANELS))
    if old.any():  # NCO-2004 (ISCO-88 minor groups) before July 2021
        isco88, digits88 = isco88_group_to_isco08(nco[old])
        isco, digits = isco.mask(old, isco88), digits.mask(old, digits88)
    df["occup_isco"], df["occup_isco_digits"] = isco, digits
    df["occup"] = isco_major(df["occup_isco"])
    df["occup_skill"] = occup_skill_from_major(df["occup"])

    reg, self_, casual = cws.isin(REGULAR), cws.isin(SELF), cws.isin(CASUAL)
    wage = pd.Series(np.nan, index=raw.index, dtype="float64")
    wage = wage.mask(true_only(reg), _num(raw["ern_reg"]))
    wage = wage.mask(true_only(self_), _num(raw["ern_self"]))
    daily = _day_sum(raw, "ern1") + _day_sum(raw, "ern2").fillna(0)
    wage = wage.mask(true_only(casual), daily)
    df["wage_no_compen"] = wage.where(wage > 0).astype("float64")
    unit = pd.Series(pd.NA, index=raw.index, dtype="Int8")
    unit = unit.mask(true_only(reg | self_), 5).mask(true_only(casual), 2)
    df["unitwage"] = unit.where(df["wage_no_compen"].notna())
    hrs = _day_sum(raw, "hr")
    df["whours"] = hrs.where(hrs > 0).astype("float32").where(employed)
    df["contract"] = pd.NA
    df["socialsec"] = pd.NA
    df["firmsize_l"] = pd.NA
    df["firmsize_u"] = pd.NA
    df["tenure_months"] = pd.NA
    df["tenure_lt12"] = pd.NA
    df["source_file"] = raw["source_file"].astype("string")
    return finalize(df, COUNTRY, period, source="own", raw_release=raw_release)
