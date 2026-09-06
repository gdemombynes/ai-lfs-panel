"""Peru EPEN national quarterly file -> target schema.

INEI's ``OCUP300`` gives labour status for persons aged 14 and over who
answered the employment module: 1 employed, 2 open unemployment, 3 hidden
unemployment (wanted work, did not search: not in the labour force with
``potential_lf = 1``, as INEI's own unemployment rate counts only open
unemployment), 4 inactive. The quarterly weight ``FAC_T300`` exists only for
those persons, so rows without it (children, non-residents) are dropped, as
are the few weighted rows without a status code.
Occupation is CNO 2015, built on ISCO-08 (identity, invalid unit groups
truncated to their parent); industry is CIIU Rev.4 at four digits.
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

COUNTRY = get_country("per")

EDUCAT7 = {1: 1, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 2, 8: 6, 9: 6, 10: 7, 11: 7, 12: 7}
EMPSTAT = {1: 3, 2: 4, 3: 1, 4: 2, 5: 2, 6: 1, 7: 1, 8: 2, 9: 2, 10: 2}
NLFREASON = {1: 5, 2: 5, 3: 5, 4: 1, 5: 2, 6: 3, 7: 4, 8: 5}
FIRMSIZE = {1: (1, 20), 2: (21, 50), 3: (51, 100), 4: (101, 500), 5: (501, None)}


def _pad(code: pd.Series) -> pd.Series:
    """Codes stored as numbers lose leading zeros (113 -> 0113)."""
    s = code.astype("string").str.strip()
    s = s.where(s.notna() & (s != "") & (s != "0"), pd.NA)
    return s.str.zfill(4)


def harmonize(
    raw: pd.DataFrame, period: Period, raw_release: Optional[str] = None
) -> pd.DataFrame:
    # persons with a weight but no labour-status code (932 rows in 2023Q2) are
    # outside INEI's working-age population totals
    keep = raw["fac_t300"].notna() & (raw["fac_t300"] > 0) & (raw["ocup300"] != "")
    raw = raw[keep].copy()
    months = set(pd.to_numeric(raw["mes"], errors="coerce").dropna().astype(int))
    if not months <= set(period.months):
        raise ValueError(
            f"{period}: file covers months {sorted(months)}; check SURVEY_CODES"
        )
    df = pd.DataFrame(index=raw.index)
    df["year"] = to_int(raw["anio"], "Int16")
    df["int_year"] = df["year"]
    df["int_month"] = to_int(raw["mes"]).astype("Int8")
    df["wave"] = f"Q{period.quarter}"
    df["hhid"] = (
        raw["conglomerado"] + "-" + raw["selviv"] + "-" + raw["hogar"]
    ).astype("string")
    df["pid"] = (df["hhid"] + "-" + raw["c201"]).astype("string")
    df["rotation_group"] = pd.NA
    df["visit_no"] = pd.NA
    df["weight"] = raw["fac_t300"].astype("float64")
    df["urban"] = to_int(raw["area"]).map({1: 1, 2: 0}).astype("Int8")
    df["subnatid1"] = pd.NA  # the national file carries no department code
    df["age"] = to_int(raw["c208"], "Int16")
    df["male"] = to_int(raw["c207"]).map({1: 1, 2: 0}).astype("Int8")
    df["educat7"] = to_int(raw["c366"]).map(EDUCAT7).astype("Int8")
    df["educat4"] = educat4_from_7(df["educat7"])

    ocup = to_int(raw["ocup300"])
    adult = df["age"] >= COUNTRY.minlaborage
    df["lstatus"] = ocup.map({1: 1, 2: 2, 3: 3, 4: 3}).astype("Int8").where(adult)
    employed, nlf = df["lstatus"] == 1, df["lstatus"] == 3
    df["potential_lf"] = (ocup == 3).astype("Int8").where(nlf)
    df["underemployment"] = (to_int(raw["p209h"]) == 1).astype("Int8").where(employed)
    df["nlfreason"] = to_int(raw["c353"]).map(NLFREASON).astype("Int8").where(nlf)
    c310 = to_int(raw["c310"])
    df["empstat"] = c310.map(EMPSTAT).astype("Int8")
    df["ocusec"] = (
        to_int(raw["c311"]).map({1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2}).astype("Int8")
    )

    ciiu = _pad(raw["c309_cod"])
    df["industry_orig"] = ciiu.astype("string")
    df["industrycat_isic"] = ciiu.astype("string")
    df["isic_digits"] = pd.Series(4, index=raw.index, dtype="Int8").where(ciiu.notna())
    df["industrycat10"] = industrycat10_from_isic(df["industrycat_isic"])
    df["industrycat4"] = industrycat4_from_10(df["industrycat10"])

    cno = _pad(raw["c308_cod"])
    df["occup_orig"] = cno.astype("string")
    isco, digits = map_isco_codes(cno)
    df["occup_isco"], df["occup_isco_digits"] = isco, digits
    df["occup"] = isco_major(df["occup_isco"])
    df["occup_skill"] = occup_skill_from_major(df["occup"])

    wage = raw["ingtotp"]
    df["wage_no_compen"] = wage.where(wage > 0).astype("float64")
    df.loc[df["empstat"] == 2, "wage_no_compen"] = 0.0
    df["unitwage"] = pd.Series(5, index=raw.index, dtype="Int8").where(
        df["wage_no_compen"].notna()
    )
    hrs = pd.to_numeric(raw["c318_t"], errors="coerce")
    df["whours"] = hrs.where(hrs > 0).astype("float32")
    df["contract"] = pd.NA  # not in the national module
    pens = pd.concat([to_int(raw[c]) for c in ("c364_1", "c364_2", "c364_3")], axis=1)
    df["socialsec"] = (
        pd.Series(pd.NA, index=raw.index, dtype="Int8")
        .mask(true_only(pens.notna().any(axis=1)), 0)
        .mask(true_only((pens == 1).any(axis=1)), 1)
    )
    band = to_int(raw["c317"])
    exact = pd.to_numeric(raw["c317a"], errors="coerce").where(band == 1)
    df["firmsize_l"] = band.map({k: v[0] for k, v in FIRMSIZE.items()}).astype("Int16")
    df["firmsize_u"] = band.map({k: v[1] for k, v in FIRMSIZE.items()}).astype("Int16")
    df["firmsize_l"] = (
        df["firmsize_l"].mask(true_only(exact.notna()), exact).astype("Int16")
    )
    df["firmsize_u"] = (
        df["firmsize_u"].mask(true_only(exact.notna()), exact).astype("Int16")
    )
    df["tenure_months"] = pd.NA  # no tenure question in the EPEN
    df["tenure_lt12"] = pd.NA
    df["source_file"] = (
        raw["source_file"].astype("string") if "source_file" in raw else pd.NA
    )
    return finalize(df, COUNTRY, period, source="own", raw_release=raw_release)
