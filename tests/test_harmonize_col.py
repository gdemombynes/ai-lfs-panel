# ruff: noqa: E501
from pathlib import Path

import pandas as pd
import pytest

from lfspanel.fetch.col import parse_resources
from lfspanel.harmonize.col import harmonize
from lfspanel.periods import Period
from lfspanel.read.col import KEYS, read_raw
from lfspanel.schema import COLUMNS, validate_frame

FIXTURE = Path(__file__).parent / "fixtures" / "col" / "geih_2025_01.zip"

PAGE = """
onclick="mostrarModal('GEIH_Enero_2022_Marco_2018.zip' , 'https://microdatos.dane.gov.co/index.php/catalog/771/download/22688 ');"
onclick="mostrarModal('Ene_2024.zip' , 'https://microdatos.dane.gov.co/index.php/catalog/819/download/23313 ');"
onclick="mostrarModal('Mayo_2024 1.zip' , 'https://microdatos.dane.gov.co/index.php/catalog/819/download/23598 ');"
onclick="mostrarModal('Septiembre 2025.zip' , 'https://microdatos.dane.gov.co/index.php/catalog/853/download/24270 ');"
"""


def test_parse_resources_handles_naming_variants():
    res = parse_resources(PAGE)
    assert res[1][1].endswith("/download/22688")  # first January entry wins
    assert res[5][0] == "Mayo_2024 1.zip"
    assert res[9][1].endswith("/download/24270")
    assert 2 not in res


@pytest.fixture(scope="module")
def raw():
    return read_raw(Period("2025M01"), path=FIXTURE)


@pytest.fixture(scope="module")
def out(raw):
    return harmonize(raw, Period("2025M01"))


def test_read_raw_joins_modules(raw):
    assert len(raw) == 500
    assert not raw.duplicated(KEYS).any()
    assert {"PET", "OCI", "DSI", "OFICIO_C8", "P6426"} <= set(raw.columns)


def test_output_schema_and_status(out, raw):
    assert list(out.columns) == COLUMNS
    assert validate_frame(out) == []
    assert (out["period"] == "2025Q1").all() and (out["wave"] == "M01").all()
    assert out["minlaborage"].eq(15).all()
    pet = raw["PET"] == "1"
    assert out.loc[pet.values, "lstatus"].notna().all()
    assert out.loc[~pet.values, "lstatus"].isna().all()
    assert (out.loc[(raw["OCI"] == "1").values, "lstatus"] == 1).all()
    assert (out.loc[(raw["DSI"] == "1").values, "lstatus"] == 2).all()


def test_weights_single_month_not_divided(out, raw):
    fex = pd.to_numeric(raw["FEX_C18"])
    assert (out["weight"].round(6) == fex.round(6)).all()


def test_occupation_industry_tenure(out):
    emp = out[out["lstatus"] == 1]
    assert emp["occup_isco"].notna().mean() > 0.99
    assert (emp["occup_isco_digits"].dropna() == 4).all()
    assert (emp["isic_digits"].dropna() == 2).all()
    assert emp["tenure_lt12"].isin([0, 1]).all()
    assert ((emp["tenure_months"] < 12) == (emp["tenure_lt12"] == 1)).all()
    assert emp["contract"].isin([0, 1]).all()
