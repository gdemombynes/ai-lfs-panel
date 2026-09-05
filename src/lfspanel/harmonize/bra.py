"""Brazil PNAD Contínua -> target schema.

Follows the World Bank GLD harmonization for BRA PNADC (MIT licence,
github.com/worldbank/gld) with two differences documented in
docs/harmonization/bra.md: quarterly weight V1028 instead of the annual
visit-1 weight, and tenure variables added from V4040.
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
    pad_code,
    to_int,
)
from lfspanel.periods import Period

COUNTRY = get_country("bra")

UF_NAMES = {
    "11": "Rondônia", "12": "Acre", "13": "Amazonas", "14": "Roraima", "15": "Pará",
    "16": "Amapá", "17": "Tocantins", "21": "Maranhão", "22": "Piauí", "23": "Ceará",
    "24": "Rio Grande do Norte", "25": "Paraíba", "26": "Pernambuco", "27": "Alagoas",
    "28": "Sergipe", "29": "Bahia", "31": "Minas Gerais", "32": "Espírito Santo",
    "33": "Rio de Janeiro", "35": "São Paulo", "41": "Paraná", "42": "Santa Catarina",
    "43": "Rio Grande do Sul", "50": "Mato Grosso do Sul", "51": "Mato Grosso",
    "52": "Goiás", "53": "Distrito Federal",
}  # fmt: skip

# COD codes that are not ISCO-08 unit groups (GLD BRA PNADC harmonization).
COD_FIXES = {"6225": "6220", "5168": "5160"}


def _tenure(raw: pd.DataFrame) -> tuple:
    """Months in main job from V4040 bands; midpoints where months are not asked."""
    band = to_int(raw["V4040"])
    months = pd.Series(pd.NA, index=raw.index, dtype="Float32")
    months = months.mask(band == 1, 0.5)
    m2 = pd.to_numeric(raw["V40401"], errors="coerce")
    months = months.mask(band == 2, m2.where(m2.notna(), 6.0))
    y3 = pd.to_numeric(raw["V40402"], errors="coerce")
    months = months.mask(band == 3, 12.0 * y3.where(y3.notna(), 1.0) + 6.0)
    y4 = pd.to_numeric(raw["V40403"], errors="coerce")
    months = months.mask(band == 4, 12.0 * y4.where(y4.notna(), 2.0))
    lt12 = pd.Series(pd.NA, index=raw.index, dtype="Int8")
    lt12 = lt12.mask(band.isin([1, 2]), 1).mask(band.isin([3, 4]), 0)
    return months.astype("float32"), lt12.astype("Int8")


def harmonize(
    raw: pd.DataFrame, period: Period, raw_release: Optional[str] = None
) -> pd.DataFrame:
    """Map one quarter of PNADC raw variables to the target schema."""
    df = pd.DataFrame(index=raw.index)
    df["year"] = to_int(raw["Ano"], "Int16")
    df["int_year"] = df["year"]
    df["int_month"] = pd.Series(pd.NA, index=raw.index, dtype="Int8")
    df["wave"] = "Q" + raw["Trimestre"].astype("string")
    df["hhid"] = (
        raw["UPA"].astype("string")
        + raw["V1008"].astype("string")
        + raw["V1014"].astype("string")
    )
    df["pid"] = df["hhid"] + raw["V2003"].astype("string")
    df["rotation_group"] = raw["V1014"].astype("string")
    df["visit_no"] = to_int(raw["V1016"])
    df["weight"] = pd.to_numeric(raw["V1028"], errors="coerce").astype("float64")
    df["urban"] = to_int(raw["V1022"]).map({1: 1, 2: 0}).astype("Int8")
    uf = raw["UF"].astype("string")
    df["subnatid1"] = (uf + " - " + uf.map(UF_NAMES)).astype("string")
    df["age"] = to_int(raw["V2009"], "Int16")
    df["male"] = to_int(raw["V2007"]).map({1: 1, 2: 0}).astype("Int8")
    vd3004 = to_int(raw["VD3004"])
    df["educat7"] = vd3004.mask(vd3004.isin([6, 7]), 7).astype("Int8")
    df["educat4"] = educat4_from_7(df["educat7"])

    minage = COUNTRY.minlaborage
    adult = df["age"] >= minage
    vd4001, vd4002 = to_int(raw["VD4001"]), to_int(raw["VD4002"])
    lstatus = pd.Series(pd.NA, index=raw.index, dtype="Int8")
    lstatus = lstatus.mask(adult & (vd4002 == 1), 1)
    lstatus = lstatus.mask(adult & (vd4002 == 2), 2)
    lstatus = lstatus.mask(adult & (vd4001 == 2), 3)
    df["lstatus"] = lstatus.astype("Int8")
    employed = df["lstatus"] == 1

    vd4003 = to_int(raw["VD4003"])
    df["potential_lf"] = (
        vd4003.map({1: 1, 2: 0}).astype("Int8").where(df["lstatus"] == 3)
    )
    df["underemployment"] = (
        to_int(raw["VD4004A"])
        .map({1: 1})
        .astype("Int8")
        .where(employed)
        .fillna(pd.Series(0, index=raw.index, dtype="Int8").where(employed))
    )
    vd4030 = to_int(raw["VD4030"])
    nlf = vd4030.map({2: 1, 1: 2, 4: 3, 3: 4, 5: 5, 6: 5}).astype("Int8")
    nlf = nlf.mask((nlf == 3) & (df["age"] <= 29), pd.NA)
    df["nlfreason"] = nlf.where(df["lstatus"] == 3).astype("Int8")

    vd4008 = to_int(raw["VD4008"])
    df["empstat"] = vd4008.map({1: 1, 2: 1, 3: 1, 6: 2, 4: 3, 5: 4}).astype("Int8")
    df["ocusec"] = (
        to_int(raw["V4012"])
        .map({2: 1, 1: 2, 3: 2, 5: 2, 6: 2, 7: 2, 4: 4})
        .astype("Int8")
    )

    cnae = pad_code(raw["V4013"], 5, side="left")
    df["industry_orig"] = cnae
    isic = cnae.str[:2] + "00"
    isic = isic.mask(cnae.isin(["48010", "48020", "48076", "48078"]), "4600")
    isic = isic.mask(isic == "4800", "4700")
    isic = isic.mask(isic == "0000", pd.NA)
    df["industrycat_isic"] = isic.astype("string")
    df["isic_digits"] = pd.Series(2, index=raw.index, dtype="Int8").where(isic.notna())
    df["industrycat10"] = industrycat10_from_isic(df["industrycat_isic"])
    df["industrycat4"] = industrycat4_from_10(df["industrycat10"])

    cod = pad_code(raw["V4010"], 4, side="left")
    df["occup_orig"] = cod
    isco = cod.replace(COD_FIXES)
    isco = isco.mask(isco.between("0200", "0512"), "0000")
    isco, digits = map_isco_codes(isco)
    df["occup_isco"] = isco
    df["occup_isco_digits"] = digits
    df["occup"] = isco_major(df["occup_isco"])
    df["occup_skill"] = occup_skill_from_major(df["occup"])

    df["wage_no_compen"] = pd.to_numeric(raw["V403412"], errors="coerce").astype(
        "float64"
    )
    df.loc[df["wage_no_compen"] > 999_000_000_000, "wage_no_compen"] = pd.NA
    df.loc[df["empstat"] == 2, "wage_no_compen"] = 0.0
    df["unitwage"] = pd.Series(5, index=raw.index, dtype="Int8").where(employed)
    df["whours"] = pd.to_numeric(raw["V4039"], errors="coerce").astype("float32")
    vd4009 = to_int(raw["VD4009"])
    df["contract"] = vd4009.isin([1, 3, 5, 7]).astype("Int8").where(employed)
    df["socialsec"] = to_int(raw["V4032"]).map({1: 1, 2: 0}).astype("Int8")
    band = to_int(raw["V4018"])
    lower = pd.Series(pd.NA, index=raw.index, dtype="Int16")
    upper = pd.Series(pd.NA, index=raw.index, dtype="Int16")
    for code, col in ((1, "V40181"), (2, "V40182"), (3, "V40183")):
        exact = to_int(raw[col], "Int16")
        lower = lower.mask(band == code, exact)
        upper = upper.mask(band == code, exact)
    lower = lower.mask(band == 4, 51)
    df["firmsize_l"], df["firmsize_u"] = lower.astype("Int16"), upper.astype("Int16")
    df["tenure_months"], df["tenure_lt12"] = _tenure(raw)
    df["source_file"] = (
        raw["source_file"].astype("string") if "source_file" in raw else pd.NA
    )

    return finalize(df, COUNTRY, period, source="own", raw_release=raw_release)
