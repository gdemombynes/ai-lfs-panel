# ruff: noqa: E501
from pathlib import Path

import pandas as pd
import pytest

from lfspanel.fetch.phl import round_month
from lfspanel.harmonize.phl import educat7_from_grade, harmonize
from lfspanel.periods import Period
from lfspanel.read.phl import _norm, read_raw
from lfspanel.schema import COLUMNS, validate_frame

FIXTURE = Path(__file__).parent / "fixtures" / "phl" / "PHL-PSA-LFS-2025-01-PUF.zip"


def test_round_month_and_column_normalisation():
    assert (
        round_month(Period("2025Q1")) == "2025M01"
        and round_month(Period("2025Q4")) == "2025M10"
    )
    assert _norm("﻿PUFREG") == "pufreg" and _norm("ï»¿PUFREG") == "pufreg"
    assert _norm("PUFURB2015") == "pufurb2020"


def test_educat7_from_grade():
    g = pd.Series(
        [
            "00000",
            "10011",
            "10018",
            "24012",
            "24015",
            "34011",
            "34013",
            "40011",
            "60002",
            "60111",
            "",
            "x",
        ]
    )
    assert educat7_from_grade(g).tolist()[:10] == [1, 2, 3, 4, 5, 4, 5, 6, 7, 7]
    assert educat7_from_grade(g).iloc[10:].isna().all()


@pytest.fixture(scope="module")
def raw():
    return read_raw(Period("2025Q1"), path=FIXTURE)


@pytest.fixture(scope="module")
def out(raw):
    return harmonize(raw, Period("2025Q1"))


def test_read_raw(raw):
    assert len(raw) == 400
    assert {
        "pufnewempstat",
        "pufc14_procc",
        "pufc16_pkb",
        "pufpwgtprv",
        "pufurb2020",
    } <= set(raw.columns)
    assert raw["pufpwgtprv"].dtype == "float64"


def test_output_schema_and_scope(out, raw):
    assert list(out.columns) == COLUMNS
    assert validate_frame(out) == []
    age = pd.to_numeric(raw["pufc05_age"])
    in_scope = (age < 15) | raw["pufnewempstat"].isin(["1", "2", "3"])
    assert len(out) == int((in_scope & (raw["pufpwgtprv"] > 0)).sum())
    assert out["minlaborage"].eq(15).all()
    assert out.loc[out["age"] >= 15, "lstatus"].notna().all()
    assert out.loc[out["age"] < 15, "lstatus"].isna().all()
    assert out["subnatid1"].str.contains(" - ").all()


def test_job_characteristics(out):
    emp = out[out["lstatus"] == 1]
    assert emp["occup_isco"].notna().all() and (emp["occup_isco_digits"] == 2).all()
    assert emp["occup_isco"].str.endswith("00").all()
    assert (emp["isic_digits"].dropna() == 2).all()
    assert emp["empstat"].notna().all()
    paid = emp[emp["empstat"] == 1]
    assert (paid["unitwage"].dropna() == 1).all()  # basic pay per day
    assert emp["tenure_lt12"].isna().all() and emp["socialsec"].isna().all()
