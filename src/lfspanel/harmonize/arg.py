"""Argentina EPH continua (31 urban agglomerations) -> target schema.

INDEC's derived ``ESTADO`` gives labour status for persons aged 10 and over,
and INDEC's published rates use the whole population (all ages) as the base,
so validation runs with ``population = "all"``. Occupation is CNO 2017,
mapped to ISCO-08 at two digits (occupationcross crosswalk); industry is
CAES Mercosur 1.0 whose two-digit divisions equal ISIC Rev.4 divisions.
"""

from __future__ import annotations

from typing import Optional

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
)
from lfspanel.periods import Period

COUNTRY = get_country("arg")

REGIONS = {
    "1": "Gran Buenos Aires", "40": "Noroeste", "41": "Noreste", "42": "Cuyo",
    "43": "Pampeana", "44": "Patagonia",
}  # fmt: skip
# time-in-job bands (PP07A employees, PP05H self-employed): midpoint months
TENURE_MID = {1: 0.5, 2: 2.0, 3: 4.5, 4: 9.0, 5: 36.0, 6: 72.0}
FIRMSIZE = {
    1: (1, 1), 2: (2, 2), 3: (3, 3), 4: (4, 4), 5: (5, 5), 6: (6, 10), 7: (11, 25),
    8: (26, 40), 9: (41, 100), 10: (101, 200), 11: (201, 500), 12: (501, None),
}  # fmt: skip
# CAES divisions used by INDEC for commerce not elsewhere classified
COMMERCE_DIVISIONS = {"40", "48"}


def harmonize(
    raw: pd.DataFrame, period: Period, raw_release: Optional[str] = None
) -> pd.DataFrame:
    df = pd.DataFrame(index=raw.index)
    df["year"] = to_int(raw["ANO4"], "Int16")
    df["int_year"] = df["year"]
    df["int_month"] = pd.NA
    df["wave"] = "Q" + raw["TRIMESTRE"].astype("string")
    df["hhid"] = raw["CODUSU"] + "-" + raw["NRO_HOGAR"]
    df["pid"] = df["hhid"] + "-" + raw["COMPONENTE"]
    df["rotation_group"] = pd.NA
    df["visit_no"] = pd.NA
    df["weight"] = pd.to_numeric(raw["PONDERA"], errors="coerce").astype("float64")
    df["urban"] = 1  # the EPH covers urban agglomerations only
    reg = raw["REGION"].str.lstrip("0")
    df["subnatid1"] = (reg + " - " + reg.map(REGIONS)).astype("string")
    age = pd.to_numeric(raw["CH06"], errors="coerce")
    df["age"] = age.clip(lower=0).astype("Int16")
    df["male"] = to_int(raw["CH04"]).map({1: 1, 2: 0}).astype("Int8")
    lvl = to_int(raw["NIVEL_ED"])
    df["educat7"] = lvl.map({7: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 7, 6: 7}).astype("Int8")
    df["educat4"] = educat4_from_7(df["educat7"])

    estado = to_int(raw["ESTADO"])
    adult = df["age"] >= COUNTRY.minlaborage
    df["lstatus"] = estado.where(estado.isin([1, 2, 3]) & adult).astype("Int8")
    employed, nlf = df["lstatus"] == 1, df["lstatus"] == 3
    df["potential_lf"] = pd.NA
    intensi = to_int(raw["INTENSI"])
    df["underemployment"] = intensi.isin([3, 4]).astype("Int8").where(employed)
    df["nlfreason"] = (
        to_int(raw["CAT_INAC"])
        .map({1: 3, 2: 5, 3: 1, 4: 2, 5: 5, 6: 4, 7: 5})
        .astype("Int8")
        .where(nlf)
    )
    cat = to_int(raw["CAT_OCUP"])
    df["empstat"] = cat.map({1: 3, 2: 4, 3: 1, 4: 2, 9: 5}).astype("Int8")
    df["ocusec"] = to_int(raw["PP04A"]).map({1: 1, 2: 2, 3: 2}).astype("Int8")

    caes = raw["PP04B_COD"].str.strip()
    caes = caes.where(caes != "").str.zfill(4)
    df["industry_orig"] = caes.astype("string")
    div = caes.str[:2]
    isic = (div + "00").mask(div.isin(COMMERCE_DIVISIONS), "4700")
    df["industrycat_isic"] = isic.astype("string")
    df["isic_digits"] = (
        pd.Series(2, index=raw.index, dtype="Int8")
        .mask(div.isin(COMMERCE_DIVISIONS), 1)
        .where(isic.notna())
    )
    df["industrycat10"] = industrycat10_from_isic(df["industrycat_isic"])
    df["industrycat4"] = industrycat4_from_10(df["industrycat10"])

    cno = raw["PP04D_COD"].str.strip()
    cno = cno.where(cno != "").str.zfill(5)
    df["occup_orig"] = cno.astype("string")
    xw = load_crosswalk("cno2017_to_isco08_2d").set_index("cno2017")["isco08"]
    mapped = cno.map(xw).where(lambda s: ~s.isin(["0000", "9900"]))
    isco, digits = map_isco_codes(mapped)
    df["occup_isco"], df["occup_isco_digits"] = isco, digits
    df["occup"] = isco_major(df["occup_isco"])
    df["occup_skill"] = occup_skill_from_major(df["occup"])

    p21 = pd.to_numeric(raw["P21"], errors="coerce")
    df["wage_no_compen"] = p21.where(p21 > 0).astype("float64")
    df.loc[df["empstat"] == 2, "wage_no_compen"] = 0.0
    df["unitwage"] = pd.Series(5, index=raw.index, dtype="Int8").where(
        df["wage_no_compen"].notna()
    )
    hrs = pd.to_numeric(raw["PP3E_TOT"], errors="coerce")
    df["whours"] = hrs.where((hrs > 0) & (hrs < 999)).astype("float32")
    df["contract"] = pd.NA  # not asked in the EPH
    df["socialsec"] = to_int(raw["PP07H"]).map({1: 1, 2: 0}).astype("Int8")
    band = to_int(raw["PP04C"])
    df["firmsize_l"] = band.map({k: v[0] for k, v in FIRMSIZE.items()}).astype("Int16")
    df["firmsize_u"] = band.map({k: v[1] for k, v in FIRMSIZE.items()}).astype("Int16")
    tenure_band = to_int(raw["PP07A"]).where(cat == 3, to_int(raw["PP05H"]))
    df["tenure_months"] = tenure_band.map(TENURE_MID).astype("float32")
    df["tenure_lt12"] = (
        pd.Series(pd.NA, index=raw.index, dtype="Int8")
        .mask(tenure_band.between(1, 4), 1)
        .mask(tenure_band.isin([5, 6]), 0)
    )
    df["source_file"] = raw["source_file"].astype("string")
    return finalize(df, COUNTRY, period, source="own", raw_release=raw_release)
