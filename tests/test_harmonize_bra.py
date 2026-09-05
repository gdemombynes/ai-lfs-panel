from pathlib import Path

import pandas as pd
import pytest

from lfspanel.harmonize.bra import harmonize
from lfspanel.periods import Period
from lfspanel.read.bra import read_raw
from lfspanel.schema import COLUMNS, validate_frame

FIXTURE = Path(__file__).parent / "fixtures" / "bra" / "PNADC_sample.txt"


@pytest.fixture(scope="module")
def raw():
    return read_raw(Period("2025Q1"), path=FIXTURE)


@pytest.fixture(scope="module")
def out(raw):
    return harmonize(raw, Period("2025Q1"), raw_release="2025-08-15")


def test_output_schema_and_validation(out):
    assert list(out.columns) == COLUMNS
    assert validate_frame(out) == []
    assert (out["countrycode"] == "BRA").all() and (out["period"] == "2025Q1").all()
    assert (out["raw_release"] == "2025-08-15").all()


def test_lstatus_reproduces_vd4002(raw, out):
    adult = pd.to_numeric(raw["V2009"]) >= 14
    emp_raw = adult & (raw["VD4002"] == "1")
    assert (out.loc[emp_raw.values, "lstatus"] == 1).all()
    assert out.loc[~adult.values, "lstatus"].isna().all()


def test_occupation_and_industry_codes(out):
    emp = out[out["lstatus"] == 1]
    assert emp["occup_isco"].notna().all()
    assert emp["occup_isco"].str.len().eq(4).all()
    assert emp["occup_isco_digits"].isin([1, 3, 4]).all()
    assert emp["industrycat_isic"].str.len().eq(4).all()
    assert (emp["isic_digits"] == 2).all()
    assert emp["industrycat10"].between(1, 10).all()
    assert (emp["occup"] == emp["occup_isco"].str[0].astype(int)).all()


def test_tenure_bands(raw, out):
    band = pd.to_numeric(raw["V4040"], errors="coerce")
    emp = out["lstatus"] == 1
    lt = out.loc[emp.values & band.isin([1, 2]).values, "tenure_lt12"]
    ge = out.loc[emp.values & band.isin([3, 4]).values, "tenure_lt12"]
    assert (lt == 1).all() and (ge == 0).all()
    assert out.loc[emp.values & (band == 1).values, "tenure_months"].eq(0.5).all()


def test_synthetic_rows_cover_recodes():
    """Hand-built rows: unpaid worker, military, discouraged NLF, child."""
    base = {k: pd.NA for k in read_raw.__globals__["keep_list"]()}
    rows = [
        dict(base, Ano="2025", Trimestre="1", UF="35", UPA="350000001", V1008="01", V1014="1", V1016="1",  # noqa: E501
             V1022="1", V1028=1000.0, V2003="01", V2007="2", V2009=30, VD3004="5", V4010="9111", V4013="97000",  # noqa: E501
             V4012="1", VD4001="1", VD4002="1", VD4008="6", VD4009="09", V4032="2", V4039=20, V4040="2",  # noqa: E501
             V40401=3, V403412=0),
        dict(base, Ano="2025", Trimestre="1", UF="35", UPA="350000001", V1008="01", V1014="1", V1016="1",  # noqa: E501
             V1022="1", V1028=1000.0, V2003="02", V2007="1", V2009=25, VD3004="4", V4010="0412", V4013="84010",  # noqa: E501
             V4012="2", VD4001="1", VD4002="1", VD4008="1", VD4009="07", V4032="1", V4039=44, V4040="4",  # noqa: E501
             V40403=3, V403412=5000),
        dict(base, Ano="2025", Trimestre="1", UF="35", UPA="350000001", V1008="01", V1014="1", V1016="1",  # noqa: E501
             V1022="2", V1028=1000.0, V2003="03", V2007="2", V2009=45, VD3004="1", VD4001="2", VD4003="1",  # noqa: E501
             VD4030="1"),
        dict(base, Ano="2025", Trimestre="1", UF="35", UPA="350000001", V1008="01", V1014="1", V1016="1",  # noqa: E501
             V1022="1", V1028=1000.0, V2003="04", V2007="1", V2009=8, VD3004="2"),
    ]  # fmt: skip  # noqa: E501
    raw = pd.DataFrame(rows).astype({"V1028": float})
    raw["source_file"] = "synthetic"
    out = harmonize(raw, Period("2025Q1"))
    assert validate_frame(out) == []
    assert out["lstatus"].tolist() == [1, 1, 3, pd.NA] or out["lstatus"].isna().iloc[3]
    unpaid, military, nlf, child = (out.iloc[i] for i in range(4))
    assert (
        unpaid["empstat"] == 2
        and unpaid["wage_no_compen"] == 0
        and unpaid["tenure_lt12"] == 1
    )
    assert (
        unpaid["tenure_months"] == 3
        and unpaid["contract"] == 0
        and unpaid["socialsec"] == 0
    )
    assert (
        military["occup_isco"] == "0000"
        and military["occup"] == 0
        and military["ocusec"] == 1
    )
    assert (
        military["contract"] == 1
        and military["tenure_months"] == 36
        and military["tenure_lt12"] == 0
    )
    assert nlf["potential_lf"] == 1 and nlf["nlfreason"] == 2 and nlf["urban"] == 0
    assert pd.isna(child["lstatus"]) and child["educat4"] == 2
