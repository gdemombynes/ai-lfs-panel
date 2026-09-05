"""Mexico ENOE -> target schema.

Follows the World Bank GLD MEX ENOE harmonization with these documented
differences (docs/harmonization/mex.md): INEGI's derived labour-status
variables (clase1/clase2) instead of re-deriving from COE questions, so
headline rates reproduce the quarterly bulletin; minimum labour age 15 to match
the "15 y más" release; social security from imssissste; tenure from p3r.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
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

COUNTRY = get_country("mex")

ENT_NAMES = {
    "01": "Aguascalientes", "02": "Baja California", "03": "Baja California Sur",
    "04": "Campeche", "05": "Coahuila", "06": "Colima", "07": "Chiapas", "08": "Chihuahua",  # noqa: E501
    "09": "Ciudad de México", "10": "Durango", "11": "Guanajuato", "12": "Guerrero",
    "13": "Hidalgo", "14": "Jalisco", "15": "México", "16": "Michoacán", "17": "Morelos",  # noqa: E501
    "18": "Nayarit", "19": "Nuevo León", "20": "Oaxaca", "21": "Puebla", "22": "Querétaro",  # noqa: E501
    "23": "Quintana Roo", "24": "San Luis Potosí", "25": "Sinaloa", "26": "Sonora",
    "27": "Tabasco", "28": "Tamaulipas", "29": "Tlaxcala", "30": "Veracruz", "31": "Yucatán",  # noqa: E501
    "32": "Zacatecas",
}  # fmt: skip


def _educat7(raw: pd.DataFrame) -> pd.Series:
    """GLD MEX rule from schooling level (cs_p13_1) and years (anios_esc)."""
    lvl = to_int(raw["cs_p13_1"])
    yrs = pd.to_numeric(raw["anios_esc"], errors="coerce")
    out = pd.Series(pd.NA, index=raw.index, dtype="Int8")
    out = out.mask(lvl.isin([0, 1]), 1)
    out = out.mask(lvl == 2, 2)
    out = out.mask((lvl == 2) & (yrs >= 6), 3)
    out = out.mask(lvl.isin([3, 4]), 4)
    out = out.mask((lvl == 4) & (yrs >= 12), 5)
    out = out.mask(lvl.isin([5, 6]), 6)
    out = out.mask(lvl.isin([7, 8, 9]), 7)
    return out.astype("Int8")


def _ocusec(raw: pd.DataFrame, empstat: pd.Series) -> pd.Series:
    """GLD MEX rule from the type of economic unit (p4b, p4c, p4d1, p4d2)."""
    p4b, p4c, p4d1, p4d2 = (to_int(raw[c]) for c in ("p4b", "p4c", "p4d1", "p4d2"))
    out = pd.Series(pd.NA, index=raw.index, dtype="Int8")
    out = out.mask((p4b == 4) | ((p4b == 5) & p4c.isin([1, 2])), 2)
    inst = p4b.isin([2, 3])
    out = out.mask(inst & (p4d1 == 1) & p4d2.between(1, 7), 1)
    out = out.mask(inst & (p4d1 == 2) & p4d2.isin([2, 3, 6]), 1)
    out = out.mask(inst & (p4d1 == 2) & p4d2.isin([1, 4, 5, 7]), 2)
    out = out.mask((p4b == 1) & empstat.isin([2, 3, 4]), 2)
    out = out.mask(out.isna() & (raw["p4a"] == "8140"), 2)
    return out.astype("Int8")


def _tenure(raw: pd.DataFrame, period: Period, int_month: pd.Series) -> tuple:
    """Months since the job started (p3r: 1 this year, 2 last year, 3 earlier)."""
    p3r = to_int(raw["p3r"])
    mes = pd.to_numeric(raw["p3r_mes"], errors="coerce")
    mes = mes.where(mes.between(1, 12))
    anio = pd.to_numeric(raw["p3r_anio"], errors="coerce")
    start_year = pd.Series(np.nan, index=raw.index, dtype="float")
    start_year = start_year.mask(p3r == 1, float(period.year))
    start_year = start_year.mask(p3r == 2, float(period.year - 1))
    start_year = start_year.mask(p3r == 3, anio)
    start_month = mes.where(p3r.isin([1, 2]), 6.0)  # unknown month: mid-year
    ref_month = int_month.astype("float").fillna(float(period.months[1]))
    months = (period.year - start_year) * 12 + (ref_month - start_month)
    months = months.clip(lower=0.5).astype("float32")
    lt12 = pd.Series(pd.NA, index=raw.index, dtype="Int8")
    lt12 = lt12.mask(months.notna() & (months < 12), 1).mask(
        months.notna() & (months >= 12), 0
    )
    # started before last year: at least a year ago. The comparison is NA
    # outside first quarters (question not asked); NA must stay NA, not 0.
    lt12 = lt12.mask((p3r == 3).fillna(False), 0)
    return months, lt12.astype("Int8")


def harmonize(
    raw: pd.DataFrame, period: Period, raw_release: Optional[str] = None
) -> pd.DataFrame:
    # Complete interviews of usual residents only (INEGI convention for headline rates).
    raw = raw[(raw["r_def"] == "0") & (raw["c_res"] != "2")].reset_index(drop=True)
    df = pd.DataFrame(index=raw.index)
    df["year"] = period.year
    df["int_year"] = period.year
    mes_cal = to_int(raw["mes_cal"])
    df["int_month"] = (
        ((period.quarter - 1) * 3 + mes_cal).where(mes_cal.between(1, 3)).astype("Int8")
    )
    df["wave"] = f"Q{period.quarter}"
    key_cols = ["cd_a", "ent", "con", "v_sel", "tipo", "mes_cal", "n_hog", "h_mud"]
    df["hhid"] = raw[key_cols].astype(str).agg("-".join, axis=1)
    df["pid"] = df["hhid"] + "-" + raw["n_ren"].astype(str)
    df["rotation_group"] = pd.NA
    df["visit_no"] = to_int(raw["n_ent"])
    df["weight"] = pd.to_numeric(raw["fac_tri"], errors="coerce").astype("float64")
    tloc = to_int(raw["t_loc_tri"])
    df["urban"] = (
        pd.Series(pd.NA, index=raw.index, dtype="Int8")
        .mask(tloc.between(1, 3), 1)
        .mask(tloc == 4, 0)
    )
    ent = raw["ent"].str.zfill(2)
    df["subnatid1"] = (ent + " - " + ent.map(ENT_NAMES)).astype("string")
    age = pd.to_numeric(raw["eda"], errors="coerce")
    df["age"] = age.where(age < 99).astype("Int16")
    df["male"] = to_int(raw["sex"]).map({1: 1, 2: 0}).astype("Int8")
    df["educat7"] = _educat7(raw)
    df["educat4"] = educat4_from_7(df["educat7"])

    adult = df["age"] >= COUNTRY.minlaborage
    clase2 = to_int(raw["clase2"])
    lstatus = pd.Series(pd.NA, index=raw.index, dtype="Int8")
    lstatus = lstatus.mask(adult & (clase2 == 1), 1).mask(adult & (clase2 == 2), 2)
    lstatus = lstatus.mask(adult & clase2.isin([3, 4]), 3)
    df["lstatus"] = lstatus.astype("Int8")
    employed, nlf = df["lstatus"] == 1, df["lstatus"] == 3
    df["potential_lf"] = clase2.map({3: 1, 4: 0}).astype("Int8").where(nlf)
    df["underemployment"] = (to_int(raw["sub_o"]) == 1).astype("Int8").where(employed)
    df["nlfreason"] = (
        to_int(raw["c_inac5c"])
        .where(lambda s: s.between(1, 5))
        .astype("Int8")
        .where(nlf)
    )
    df["empstat"] = (
        to_int(raw["pos_ocu"]).map({1: 1, 2: 3, 3: 4, 4: 2, 5: 5}).astype("Int8")
    )
    df["ocusec"] = _ocusec(raw, df["empstat"])

    scian = raw["p4a"].str.zfill(4).where(raw["p4a"] != "")
    df["industry_orig"] = scian.astype("string")
    xw = load_crosswalk("scian2018_to_isic4").set_index("scian")["isic"]
    isic = scian.map(xw)
    df["industrycat_isic"] = isic.astype("string")
    df["isic_digits"] = isic.str.rstrip("0").str.len().clip(1, 4).astype("Int8")
    df["industrycat10"] = industrycat10_from_isic(df["industrycat_isic"])
    df["industrycat4"] = industrycat4_from_10(df["industrycat10"])

    sinco = raw["p3"].str.zfill(4).where(raw["p3"] != "")
    df["occup_orig"] = sinco.astype("string")
    xo = load_crosswalk("sinco2019_to_isco08").set_index("sinco")["isco"]
    isco, digits = map_isco_codes(sinco.map(xo))
    df["occup_isco"], df["occup_isco_digits"] = isco, digits
    df["occup"] = isco_major(df["occup_isco"])
    df["occup_skill"] = occup_skill_from_major(df["occup"])

    ing = pd.to_numeric(raw["ingocup"], errors="coerce")
    df["wage_no_compen"] = ing.where(ing > 0).astype("float64")
    df.loc[df["empstat"] == 2, "wage_no_compen"] = 0.0
    df["unitwage"] = pd.Series(5, index=raw.index, dtype="Int8").where(
        df["wage_no_compen"].notna()
    )
    hrs = pd.to_numeric(raw["hrsocup"], errors="coerce")
    df["whours"] = hrs.where(hrs > 0).astype("float32")
    contract_src = raw["p3j"] if period.quarter == 1 else raw["p3i"]
    df["contract"] = to_int(contract_src).map({1: 1, 2: 0}).astype("Int8")
    df["socialsec"] = (
        to_int(raw["imssissste"]).map({1: 1, 2: 1, 3: 1, 4: 0}).astype("Int8")
    )
    df["firmsize_l"] = pd.NA
    df["firmsize_u"] = pd.NA
    df["tenure_months"], df["tenure_lt12"] = _tenure(raw, period, df["int_month"])
    df["source_file"] = (
        raw["source_file"].astype("string") if "source_file" in raw else pd.NA
    )
    return finalize(df, COUNTRY, period, source="own", raw_release=raw_release)
