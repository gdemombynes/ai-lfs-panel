# ruff: noqa: E501
from pathlib import Path

import pytest

from lfspanel.fetch.nga import catalog_url
from lfspanel.harmonize.nga import employed_flag, harmonize
from lfspanel.periods import Period
from lfspanel.read.nga import read_raw
from lfspanel.schema import COLUMNS, validate_frame

FIXTURE = Path(__file__).parent / "fixtures" / "nga" / "nlfs_2024q3_indiv.dta"


def test_catalog_url():
    assert catalog_url(Period("2024Q1")).endswith("/catalog/151/get-microdata")
    assert catalog_url(Period("2025Q2")).endswith("/catalog/152/get-microdata")
    with pytest.raises(FileNotFoundError):
        catalog_url(Period("2021Q1"))


@pytest.fixture(scope="module")
def raw():
    return read_raw(Period("2024Q3"), path=FIXTURE)


@pytest.fixture(scope="module")
def out(raw):
    return harmonize(raw, Period("2024Q3"))


def test_read_raw(raw):
    assert len(raw) == 400
    assert {
        "atw1",
        "mjj2cclean",
        "mjj3cclean",
        "popw",
        "um10b",
        "interviewdate",
    } <= set(raw.columns)
    assert raw["popw"].dtype == "float64"
    assert raw["interviewdate"].str.match(r"^\d{4}-\d{2}-\d{2}$").all()


def test_employment_rule_and_status(out, raw):
    assert list(out.columns) == COLUMNS
    assert validate_frame(out) == []
    assert out["minlaborage"].eq(15).all()
    emp = employed_flag(raw).values
    adult = (out["age"] >= 15).values
    assert (out.loc[adult & emp, "lstatus"] == 1).all()
    routed = (raw["mjj1"] != "").values  # the main-job module is asked of the employed
    assert (out.loc[adult & routed, "lstatus"] == 1).mean() > 0.98
    assert out.loc[~adult, "lstatus"].isna().all()
    nlf = out["lstatus"] == 3
    assert out.loc[nlf, "potential_lf"].isin([0, 1]).all()


def test_job_characteristics(out):
    emp = out[out["lstatus"] == 1]
    assert emp["occup_isco"].notna().mean() > 0.95
    assert (emp["occup_isco_digits"].dropna() == 4).mean() > 0.95
    assert emp["industrycat_isic"].str.len().eq(4).all()
    assert emp["empstat"].notna().all() and emp["empstat"].isin([1, 2, 3, 4, 5]).all()
    assert emp["contract"].dropna().isin([0, 1]).all()
    assert emp["tenure_lt12"].notna().mean() > 0.8
    assert emp["subnatid1"].str.contains(" - ").all()
