"""Colombia GEIH (2022 redesign, marco 2018) -> target schema.

Follows the World Bank GLD COL GEIH harmonization with these documented
differences (docs/harmonization/col.md): quarterly weight FEX_C18 / 3 after
stacking three monthly files; working-age threshold 15 (DANE's PET) instead of
GLD's 10; industry carried at the 2-digit division level (identical between
CIIU Rev.4 A.C. and ISIC Rev.4) until a class-level correspondence is added.
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

COUNTRY = get_country("col")

DPTO_NAMES = {
    "05": "Antioquia", "08": "Atlántico", "11": "Bogotá D.C.", "13": "Bolívar", "15": "Boyacá",  # noqa: E501
    "17": "Caldas", "18": "Caquetá", "19": "Cauca", "20": "Cesar", "23": "Córdoba",
    "25": "Cundinamarca", "27": "Chocó", "41": "Huila", "44": "La Guajira", "47": "Magdalena",  # noqa: E501
    "50": "Meta", "52": "Nariño", "54": "Norte de Santander", "63": "Quindío", "66": "Risaralda",  # noqa: E501
    "68": "Santander", "70": "Sucre", "73": "Tolima", "76": "Valle del Cauca", "81": "Arauca",  # noqa: E501
    "85": "Casanare", "86": "Putumayo", "88": "San Andrés", "91": "Amazonas", "94": "Guainía",  # noqa: E501
    "95": "Guaviare", "97": "Vaupés", "99": "Vichada",
}  # fmt: skip

# Colombian CIUO-08 A.C. unit groups that are not ISCO-08 unit groups (GLD COL GEIH).
CIUO_AC_FIXES = {
    "7361": "7313", "7362": "7313", "7363": "7313",
    "7341": "7317", "7342": "7317", "7351": "7317", "7352": "7317",
    "7331": "7318", "7332": "7318", "7333": "7318", "7370": "7318",
    "7391": "7319", "7392": "7319", "7393": "7319", "7399": "7319",
    "8323": "8322", "8324": "8322", "9625": "9623", "9626": "9623",
}  # fmt: skip


def _educy(raw: pd.DataFrame) -> pd.Series:
    """Years of schooling from level (P3042) and grade (P3042S1), GLD rule."""
    lvl = to_int(raw["P3042"], "Int16")
    grd = pd.to_numeric(raw["P3042S1"], errors="coerce")
    y = pd.Series(pd.NA, index=raw.index, dtype="Float64")
    y = y.mask(lvl.isin([1, 2]) | ((lvl == 3) & (grd == 0)), 0)
    y = y.mask((lvl == 3) & grd.between(1, 5), grd)
    y = y.mask(lvl == 4, 5 + grd)
    y = y.mask(lvl.isin([5, 6]), 9 + grd)
    for level in (7, 8, 9, 10):
        y = y.mask((lvl == level) & grd.between(0, 1), 11)
        y = y.mask((lvl == level) & grd.between(2, 3), 12)
        y = y.mask((lvl == level) & grd.between(4, 5), 13)
    y = y.mask((lvl == 8) & grd.between(4, 12), 13)
    y = y.mask((lvl == 9) & grd.between(6, 12), 14)
    y = y.mask((lvl == 10) & grd.between(6, 7), 14)
    y = y.mask((lvl == 10) & grd.between(8, 9), 15)
    y = y.mask((lvl == 10) & grd.between(10, 28), 16)
    y = y.mask(lvl == 11, 17).mask(lvl == 12, 18).mask(lvl == 13, 21)
    return y


def _educat7(raw: pd.DataFrame) -> pd.Series:
    lvl = to_int(raw["P3042"], "Int16")
    educy = _educy(raw)
    out = pd.Series(pd.NA, index=raw.index, dtype="Int8")
    out = out.mask(educy == 0, 1)
    out = out.mask(educy.between(1, 4), 2)
    out = out.mask((educy == 5) & (lvl == 3), 3)
    out = out.mask(lvl == 4, 4)
    out = out.mask(lvl.isin([5, 6]), 5)
    out = out.mask(lvl.isin([7, 8, 9]), 6)
    out = out.mask(lvl.isin([10, 11, 12, 13]), 7)
    return out.astype("Int8")


def harmonize(
    raw: pd.DataFrame, period: Period, raw_release: Optional[str] = None
) -> pd.DataFrame:
    df = pd.DataFrame(index=raw.index)
    mes = to_int(raw["MES"])
    n_months = int(mes.nunique()) or 1
    df["year"] = period.year
    df["int_year"] = period.year
    df["int_month"] = mes.astype("Int8")
    df["wave"] = "M" + raw["MES"].str.zfill(2)
    df["hhid"] = raw["DIRECTORIO"] + "-" + raw["SECUENCIA_P"] + "-" + raw["HOGAR"]
    df["pid"] = df["hhid"] + "-" + raw["ORDEN"]
    df["rotation_group"] = pd.NA
    df["visit_no"] = pd.NA
    df["weight"] = (pd.to_numeric(raw["FEX_C18"], errors="coerce") / n_months).astype(
        "float64"
    )
    df["urban"] = to_int(raw["CLASE"]).map({1: 1, 2: 0}).astype("Int8")
    dpto = raw["DPTO"].str.zfill(2)
    df["subnatid1"] = (dpto + " - " + dpto.map(DPTO_NAMES)).astype("string")
    df["age"] = to_int(raw["P6040"], "Int16")
    df["male"] = to_int(raw["P3271"]).map({1: 1, 2: 0}).astype("Int8")
    df["educat7"] = _educat7(raw)
    df["educat4"] = educat4_from_7(df["educat7"])

    pet = raw["PET"] == "1"
    oci, dsi = raw["OCI"] == "1", raw["DSI"] == "1"
    lstatus = pd.Series(pd.NA, index=raw.index, dtype="Int8")
    lstatus = lstatus.mask(pet, 3).mask(pet & dsi, 2).mask(pet & oci, 1)
    lstatus = lstatus.where(df["age"] >= COUNTRY.minlaborage)
    df["lstatus"] = lstatus.astype("Int8")
    employed, nlf = df["lstatus"] == 1, df["lstatus"] == 3
    df["potential_lf"] = pd.NA
    df["underemployment"] = (to_int(raw["P6810"]) == 1).astype("Int8").where(employed)
    df["nlfreason"] = (
        to_int(raw["P6240"])
        .map({3: 1, 4: 2, 5: 4, 6: 5, 1: 5, 2: 5})
        .astype("Int8")
        .where(nlf)
    )
    pos = to_int(raw["P6430"])
    df["empstat"] = pos.map(
        {1: 1, 2: 1, 3: 1, 8: 1, 4: 4, 5: 3, 6: 2, 7: 2, 9: 5}
    ).astype("Int8")
    df["ocusec"] = (
        pd.Series(pd.NA, index=raw.index, dtype="Int8")
        .mask(pos == 2, 1)
        .mask(pos.notna() & (pos != 2), 2)
    )

    rama4 = raw["RAMA4D_R4"].str.zfill(4).where(raw["RAMA4D_R4"].str.strip() != "")
    rama2 = raw["RAMA2D_R4"].str.zfill(2).where(raw["RAMA2D_R4"].str.strip() != "")
    df["industry_orig"] = rama4.astype("string")
    isic = (rama2 + "00").where(rama2.notna() & (rama2 != "00"))
    df["industrycat_isic"] = isic.astype("string")
    df["isic_digits"] = pd.Series(2, index=raw.index, dtype="Int8").where(isic.notna())
    df["industrycat10"] = industrycat10_from_isic(df["industrycat_isic"])
    df["industrycat4"] = industrycat4_from_10(df["industrycat10"])

    ciuo = raw["OFICIO_C8"].str.zfill(4).where(raw["OFICIO_C8"].str.strip() != "")
    df["occup_orig"] = ciuo.astype("string")
    isco, digits = map_isco_codes(
        ciuo.replace(CIUO_AC_FIXES).where(~ciuo.isin(["0000", "0612", "5629"]))
    )
    df["occup_isco"], df["occup_isco_digits"] = isco, digits
    df["occup"] = isco_major(df["occup_isco"])
    df["occup_skill"] = occup_skill_from_major(df["occup"])

    wage = pd.to_numeric(raw["P6500"], errors="coerce")
    df["wage_no_compen"] = wage.where(wage > 0).astype("float64")
    df.loc[df["empstat"] == 2, "wage_no_compen"] = 0.0
    df["unitwage"] = pd.Series(5, index=raw.index, dtype="Int8").where(
        df["wage_no_compen"].notna()
    )
    last = pd.to_numeric(raw["P6850"], errors="coerce")
    usual = pd.to_numeric(raw["P6800"], errors="coerce")
    df["whours"] = last.where(last > 0, usual).where(lambda s: s > 0).astype("float32")
    p6440, p6450 = to_int(raw["P6440"]), to_int(raw["P6450"])
    contract = pd.Series(pd.NA, index=raw.index, dtype="Int8")
    contract = contract.mask(p6440 == 2, 0).mask(p6450 == 1, 0).mask(p6450 == 2, 1)
    df["contract"] = contract.astype("Int8")
    df["socialsec"] = to_int(raw["P6920"]).map({1: 1, 2: 0}).astype("Int8")
    df["firmsize_l"] = pd.NA
    df["firmsize_u"] = pd.NA
    months = pd.to_numeric(raw["P6426"], errors="coerce").astype("float32")
    df["tenure_months"] = months
    df["tenure_lt12"] = (
        pd.Series(pd.NA, index=raw.index, dtype="Int8")
        .mask(months < 12, 1)
        .mask(months >= 12, 0)
    )
    df["source_file"] = (
        raw["source_file"].astype("string") if "source_file" in raw else pd.NA
    )
    return finalize(df, COUNTRY, period, source="own", raw_release=raw_release)
