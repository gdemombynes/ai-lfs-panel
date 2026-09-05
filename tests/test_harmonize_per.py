from pathlib import Path

import pandas as pd
import pytest

from lfspanel.fetch.per import microdata_url, survey_code
from lfspanel.harmonize.per import harmonize
from lfspanel.official import parse_inei_report
from lfspanel.periods import Period
from lfspanel.read.per import read_raw
from lfspanel.schema import COLUMNS, validate_frame

FIXTURE = Path(__file__).parent / "fixtures" / "per" / "969-Modulo76.zip"

REPORT = """
CUADRO N° 1.1
PERÚ: POBLACIÓN EN EDAD DE TRABAJAR, SEGÚN CONDICIÓN DE ACTIVIDAD Y ÁREA DE RESIDENCIA
Primer trimestre: 2024 y 2025
(Miles de personas y porcentaje)
Total
Población en Edad de Trabajar 26 159,2 26 473,6  314,4  1,2
Población Económicamente Activa 18 328,9 18 377,2  48,3  0,3
Población Económicamente No Activa 7 830,3 8 096,4  266,1  3,4
Urbana
Población en Edad de Trabajar 21 954,3 22 345,0  390,7  1,8
CUADRO N° 1.7
PERÚ: POBLACIÓN OCUPADA, SEGÚN ÁREA DE RESIDENCIA
Primer trimestre: 2024 y 2025
(Miles de personas y porcentaje)
Total 17 159,1 17 374,0 214,9 1,3
Urbana 13 839,8 14 068,7 228,9 1,7
"""


def test_survey_codes_and_url():
    assert survey_code(Period("2025Q1")) == 969
    assert microdata_url(Period("2022Q1")).endswith("/STATA/855-Modulo76.zip")
    with pytest.raises(FileNotFoundError):
        survey_code(Period("2030Q1"))


def test_parse_inei_report():
    got = parse_inei_report(REPORT)
    assert got["2025Q1"] == {"pet": 26473.6, "pea": 18377.2, "emp": 17374.0}
    assert got["2024Q1"]["pea"] == 18328.9


@pytest.fixture(scope="module")
def raw():
    return read_raw(Period("2025Q1"), path=FIXTURE)


@pytest.fixture(scope="module")
def out(raw):
    return harmonize(raw, Period("2025Q1"))


def test_read_raw_columns(raw):
    assert len(raw) == 400
    assert {"ocup300", "c308_cod", "c309_cod", "fac_t300", "codciudad"} <= set(
        raw.columns
    )
    assert raw["fac_t300"].dtype == "float64"


def test_output_drops_unweighted_and_maps_status(out, raw):
    assert list(out.columns) == COLUMNS
    assert validate_frame(out) == []
    weighted = raw["fac_t300"].notna() & (raw["fac_t300"] > 0)
    assert len(out) == int(weighted.sum())
    assert (out["age"] >= 14).all()
    assert out["minlaborage"].eq(14).all()
    ocup = pd.to_numeric(raw.loc[weighted, "ocup300"], errors="coerce")
    assert (out.loc[(ocup == 1).values, "lstatus"] == 1).all()
    assert (out.loc[(ocup == 2).values, "lstatus"] == 2).all()
    hidden = (ocup == 3).values
    assert (out.loc[hidden, "lstatus"] == 3).all()
    assert (out.loc[hidden, "potential_lf"] == 1).all()
    assert out["subnatid1"].isna().all()
    assert out["tenure_lt12"].isna().all()


def test_occupation_industry_padding(out):
    emp = out[out["lstatus"] == 1]
    assert emp["occup_isco"].notna().all() and emp["industrycat_isic"].notna().all()
    assert emp["industrycat_isic"].str.len().eq(4).all()
    assert (emp["occup_isco_digits"].dropna() >= 2).all()
    assert emp["empstat"].notna().all()
    assert emp["socialsec"].isin([0, 1]).all()


def test_month_check_rejects_wrong_quarter(raw):
    with pytest.raises(ValueError):
        harmonize(raw, Period("2025Q3"))
