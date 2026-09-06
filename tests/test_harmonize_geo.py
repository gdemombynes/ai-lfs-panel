# ruff: noqa: E501
from pathlib import Path

import pandas as pd
import pytest

from lfspanel.fetch.geo import quarter_number, year_url
from lfspanel.harmonize.geo import harmonize
from lfspanel.periods import Period
from lfspanel.read.geo import read_raw
from lfspanel.schema import COLUMNS, validate_frame

FIXTURE = Path(__file__).parent / "fixtures" / "geo" / "Labour-Force-Survey-2025.zip"


def test_quarter_number_and_urls():
    assert quarter_number(Period("2022Q1")) == 103
    assert quarter_number(Period("2025Q1")) == 115
    assert quarter_number(Period("2025Q4")) == 118
    assert year_url(2025).endswith("/79807/Labour-Force-Survey-2025.zip")
    with pytest.raises(FileNotFoundError):
        year_url(2030)


@pytest.fixture(scope="module")
def raw():
    return read_raw(Period("2025Q1"), path=FIXTURE)


@pytest.fixture(scope="module")
def out(raw):
    return harmonize(raw, Period("2025Q1"))


def test_read_raw_selects_quarter(raw):
    assert len(raw) == 400
    assert (raw["quarterno"] == "115").all()
    assert {"employed", "occupation", "branch", "p_weights", "region"} <= set(
        raw.columns
    )
    assert read_raw(Period("2025Q2"), path=FIXTURE).empty


def test_output_schema_and_status(out, raw):
    assert list(out.columns) == COLUMNS
    assert validate_frame(out) == []
    assert out["minlaborage"].eq(15).all() and (out["age"] >= 15).all()
    emp = pd.to_numeric(raw["employed"]) == 1
    unemp = pd.to_numeric(raw["unemployed"]) == 1
    assert (out.loc[emp.values, "lstatus"] == 1).all()
    assert (out.loc[unemp.values, "lstatus"] == 2).all()
    assert (out.loc[~(emp | unemp).values, "lstatus"] == 3).all()
    assert out["male"].isin([0, 1]).all() and out["subnatid1"].str.contains(" - ").all()
    assert out["rotation_group"].notna().all()


def test_job_characteristics(out):
    emp = out[out["lstatus"] == 1]
    assert emp["occup_isco"].notna().mean() > 0.98
    assert (emp["occup_isco_digits"].dropna() == 4).mean() > 0.9
    assert (emp["isic_digits"].dropna() == 2).all()
    assert emp["industrycat_isic"].str.endswith("00").all()
    assert emp["socialsec"].dropna().isin([0, 1]).all()
    assert emp["wage_no_compen"].isna().all() and emp["tenure_lt12"].isna().all()
