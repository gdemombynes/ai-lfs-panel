# ruff: noqa: E501
from pathlib import Path

import pandas as pd
import pytest

from lfspanel.harmonize.zaf import harmonize, sasco_to_isco08, sic_to_isic4
from lfspanel.periods import Period
from lfspanel.read.zaf import read_raw
from lfspanel.schema import COLUMNS, validate_frame
from lfspanel.validate import age_band

FIXTURE = Path(__file__).parent / "fixtures" / "zaf" / "qlfs-2025-q1-v1.zip"


def test_age_band():
    assert age_band("all") == (0, None)
    assert age_band("15+") == (15, None)
    assert age_band("15-64") == (15, 64)
    assert age_band("14+") == (14, None)
    assert age_band("") == (None, None)


def test_sasco_to_isco08_rules():
    codes = ["1110", "5122", "1223", "4122", "9211", "5169", "4190", "9999", ""]
    isco, digits = sasco_to_isco08(pd.Series(codes))
    assert isco.tolist()[:7] == ["1111", "5120", "1323", "4312", "9210", "5419", "4110"]
    assert digits.tolist()[:7] == [4, 4, 4, 4, 3, 4, 4]
    assert pd.isna(isco.iloc[7]) and pd.isna(isco.iloc[8])


def test_sic_to_isic4():
    isic, digits = sic_to_isic4(pd.Series(["111", "889", "305", "620", "999", ""]))
    assert isic.tolist()[:4] == ["0100", "8200", "1100", "4700"]
    assert digits.tolist()[:4] == [2, 1, 2, 2]
    assert pd.isna(isic.iloc[4]) and pd.isna(isic.iloc[5])


@pytest.fixture(scope="module")
def raw():
    return read_raw(Period("2025Q1"), path=FIXTURE)


@pytest.fixture(scope="module")
def out(raw):
    return harmonize(raw, Period("2025Q1"))


def test_read_raw_columns(raw):
    assert len(raw) == 400
    assert {
        "status",
        "q42occupation",
        "q43industry",
        "weight",
        "geo_type_code",
        "q44yearstart",
    } <= set(raw.columns)
    assert raw["weight"].dtype == "float64"
    assert (raw["q13gender"].isin(["1", "2"])).all()


def test_output_schema_and_status(out, raw):
    assert list(out.columns) == COLUMNS
    assert validate_frame(out) == []
    assert out["minlaborage"].eq(15).all()
    status = pd.to_numeric(raw["status"], errors="coerce")
    age = pd.to_numeric(raw["q14age"])
    adult = (age >= 15).values
    assert (out.loc[adult & (status == 1).values, "lstatus"] == 1).all()
    assert (out.loc[adult & (status == 2).values, "lstatus"] == 2).all()
    discouraged = adult & (status == 3).values
    assert (out.loc[discouraged, "lstatus"] == 3).all()
    assert (out.loc[discouraged, "potential_lf"] == 1).all()
    assert out.loc[~adult, "lstatus"].isna().all()
    assert out["subnatid1"].str.contains(" - ").all()
    assert out["urban"].isin([0, 1]).all()


def test_job_characteristics(out):
    emp = out[out["lstatus"] == 1]
    assert emp["occup_isco"].notna().mean() > 0.95
    assert (emp["occup_isco_digits"].dropna() >= 3).mean() > 0.85
    assert emp["industrycat_isic"].notna().mean() > 0.95
    assert emp["isic_digits"].dropna().isin([1, 2]).all()
    assert emp["wage_no_compen"].isna().all()
    assert emp["contract"].dropna().isin([0, 1]).all()
    assert emp["tenure_lt12"].notna().mean() > 0.9
    assert ((emp["tenure_months"] < 12) == (emp["tenure_lt12"] == 1)).all()


def test_status_in_employment_break_2025q3():
    from lfspanel.harmonize.zaf import status_in_employment

    raw = pd.DataFrame(
        {
            "q45wrk4whom": ["1", "2", "3", "4", "5", ""],
            "q416nrworkers": ["3", "1", "1", "7", "", ""],
        }
    )
    before = status_in_employment(raw, Period("2025Q2")).tolist()
    assert before[:4] == [1, 3, 4, 2]
    after = status_in_employment(raw, Period("2025Q3")).tolist()
    assert after[:5] == [1, 4, 2, 1, 2]  # own business with 0 employees -> own account
    raw2 = pd.DataFrame({"q45wrk4whom": ["2", "2"], "q416nrworkers": ["4", ""]})
    assert status_in_employment(raw2, Period("2026Q1")).tolist() == [3, 4]
