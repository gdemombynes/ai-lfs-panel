"""Ecuador ENEMDU (quarterly) -> target schema.

INEC's ``condact`` classification drives labour status (working-age 15+):
1-6 employed (adequate, time- or income-underemployed, other non-full,
unpaid, unclassified), 7-8 unemployed (open, hidden), 9 not in the labour
force. Occupation is CIUO-08 and industry CIIU Rev.4, both 4-digit.
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

COUNTRY = get_country("ecu")

PROVINCES = {
    "01": "Azuay", "02": "Bolívar", "03": "Cañar", "04": "Carchi", "05": "Cotopaxi",
    "06": "Chimborazo", "07": "El Oro", "08": "Esmeraldas", "09": "Guayas",
    "10": "Imbabura", "11": "Loja", "12": "Los Ríos", "13": "Manabí",
    "14": "Morona Santiago", "15": "Napo", "16": "Pastaza", "17": "Pichincha",
    "18": "Tungurahua", "19": "Zamora Chinchipe", "20": "Galápagos", "21": "Sucumbíos",
    "22": "Orellana", "23": "Santo Domingo de los Tsáchilas", "24": "Santa Elena",
    "90": "Zonas no delimitadas",
}  # fmt: skip
MILITARY_3DIGIT = {"110", "210", "310"}


def _educat7(raw: pd.DataFrame) -> pd.Series:
    lvl = to_int(raw["p10a"])
    grd = pd.to_numeric(raw["p10b"], errors="coerce")
    out = pd.Series(pd.NA, index=raw.index, dtype="Int8")
    out = out.mask(lvl.isin([1, 2, 3]), 1)
    out = out.mask((lvl == 4) & (grd < 6), 2).mask((lvl == 4) & (grd >= 6), 3)
    out = out.mask((lvl == 5) & (grd < 6), 2).mask((lvl == 5) & (grd == 6), 3)
    out = out.mask((lvl == 5) & (grd >= 7), 4)
    out = out.mask((lvl == 6) & (grd < 6), 4).mask((lvl == 6) & (grd >= 6), 5)
    out = out.mask((lvl == 7) & (grd < 3), 4).mask((lvl == 7) & (grd >= 3), 5)
    out = out.mask(lvl == 8, 6).mask(lvl.isin([9, 10]), 7)
    return out.astype("Int8")


def _isco(raw_code: pd.Series) -> pd.Series:
    """CIUO-08 stored as a number: 3-digit values are minor groups, except
    the armed-forces unit groups 0110/0210/0310 whose leading zero was lost."""
    s = raw_code.astype("string").str.strip()
    s = s.where(s.notna() & (s != ""), pd.NA)
    three = s.str.len() == 3
    fixed = s.where(~three, s.str.ljust(4, "0"))
    fixed = fixed.mask(three & s.isin(MILITARY_3DIGIT), s.str.zfill(4))
    return fixed


def harmonize(
    raw: pd.DataFrame, period: Period, raw_release: Optional[str] = None
) -> pd.DataFrame:
    df = pd.DataFrame(index=raw.index)
    df["year"] = period.year
    df["int_year"] = period.year
    df["int_month"] = to_int(raw["mes"]).astype("Int8")
    df["wave"] = f"Q{period.quarter}"
    df["hhid"] = raw["id_hogar"].astype("string")
    df["pid"] = raw["id_persona"].astype("string")
    df["rotation_group"] = raw["panelm"].astype("string")
    df["visit_no"] = pd.NA
    df["weight"] = pd.to_numeric(raw["fexp"], errors="coerce").astype("float64")
    df["urban"] = to_int(raw["area"]).map({1: 1, 2: 0}).astype("Int8")
    prov = raw["ciudad"].str.zfill(6).str[:2]
    df["subnatid1"] = (prov + " - " + prov.map(PROVINCES)).astype("string")
    df["age"] = to_int(raw["p03"], "Int16")
    df["male"] = to_int(raw["p02"]).map({1: 1, 2: 0}).astype("Int8")
    df["educat7"] = _educat7(raw)
    df["educat4"] = educat4_from_7(df["educat7"])

    cond = to_int(raw["condact"])
    adult = df["age"] >= COUNTRY.minlaborage
    lstatus = pd.Series(pd.NA, index=raw.index, dtype="Int8")
    lstatus = lstatus.mask(adult & cond.between(1, 6), 1)
    lstatus = lstatus.mask(adult & cond.isin([7, 8]), 2)
    lstatus = lstatus.mask(adult & (cond == 9), 3)
    df["lstatus"] = lstatus.astype("Int8")
    employed = df["lstatus"] == 1
    df["potential_lf"] = pd.NA
    df["underemployment"] = (cond == 2).astype("Int8").where(employed)
    df["nlfreason"] = pd.NA
    p42 = to_int(raw["p42"])
    df["empstat"] = p42.map(
        {1: 1, 2: 1, 3: 1, 4: 1, 10: 1, 5: 3, 6: 4, 7: 2, 8: 2, 9: 2}
    ).astype("Int8")
    df["ocusec"] = (
        pd.Series(pd.NA, index=raw.index, dtype="Int8")
        .mask(p42 == 1, 1)
        .mask(p42.notna() & (p42 != 1), 2)
    )

    ciiu = raw["p40"].str.strip().where(raw["p40"].str.strip() != "").str.zfill(4)
    df["industry_orig"] = ciiu.astype("string")
    df["industrycat_isic"] = ciiu.astype("string")
    df["isic_digits"] = pd.Series(4, index=raw.index, dtype="Int8").where(ciiu.notna())
    df["industrycat10"] = industrycat10_from_isic(df["industrycat_isic"])
    df["industrycat4"] = industrycat4_from_10(df["industrycat10"])

    ciuo = _isco(raw["p41"])
    df["occup_orig"] = ciuo.astype("string")
    isco, digits = map_isco_codes(ciuo)
    df["occup_isco"], df["occup_isco_digits"] = isco, digits
    df["occup"] = isco_major(df["occup_isco"])
    df["occup_skill"] = occup_skill_from_major(df["occup"])

    wage = pd.to_numeric(raw["p66"], errors="coerce")
    df["wage_no_compen"] = wage.where(wage > 0).astype("float64")
    df.loc[df["empstat"] == 2, "wage_no_compen"] = 0.0
    df["unitwage"] = pd.Series(5, index=raw.index, dtype="Int8").where(
        df["wage_no_compen"].notna()
    )
    hrs = pd.to_numeric(raw["p24"], errors="coerce")
    df["whours"] = hrs.where(hrs > 0).astype("float32")
    p43 = to_int(raw["p43"])
    df["contract"] = (
        pd.Series(pd.NA, index=raw.index, dtype="Int8")
        .mask(p43.isin([1, 2, 3]), 1)
        .mask(p43.isin([4, 5, 6]), 0)
    )
    p05a = to_int(raw["p05a"])
    df["socialsec"] = (
        pd.Series(pd.NA, index=raw.index, dtype="Int8")
        .mask(p05a.between(1, 4), 1)
        .mask(p05a.between(5, 10), 0)
    )
    size = pd.to_numeric(raw["p47b"], errors="coerce")
    band = to_int(raw["p47a"])
    df["firmsize_l"] = size.where(band == 1).mask(band == 2, 100).astype("Int16")
    df["firmsize_u"] = size.where(band == 1).astype("Int16")
    years = pd.to_numeric(raw["p45"], errors="coerce")
    df["tenure_months"] = (years * 12 + 6).astype("float32")
    df["tenure_lt12"] = (
        pd.Series(pd.NA, index=raw.index, dtype="Int8")
        .mask(years == 0, 1)
        .mask(years >= 1, 0)
    )
    df["source_file"] = raw["source_file"].astype("string")
    return finalize(df, COUNTRY, period, source="own", raw_release=raw_release)
