from pathlib import Path

import pytest

from lfspanel.fetch.mex import candidate_names
from lfspanel.harmonize.mex import harmonize
from lfspanel.periods import Period
from lfspanel.read.mex import KEYS, read_raw
from lfspanel.schema import COLUMNS, validate_frame

FIXTURE = Path(__file__).parent / "fixtures" / "mex" / "enoe_2025_trim1_csv.zip"


@pytest.fixture(scope="module")
def raw():
    return read_raw(Period("2025Q1"), path=FIXTURE)


@pytest.fixture(scope="module")
def out(raw):
    return harmonize(raw, Period("2025Q1"))


def test_candidate_names_by_era():
    assert candidate_names(Period("2022Q4"))[0] == "enoe_n_2022_trim4_csv.zip"
    assert candidate_names(Period("2023Q1"))[0] == "enoe_2023_trim1_csv.zip"


def test_read_raw_merges_tables(raw):
    assert len(raw) == 400
    assert not raw.duplicated(KEYS).any()
    assert {"clase2", "p3", "p4a", "p6b2"} <= set(raw.columns)
    employed = raw["clase2"] == "1"
    assert (raw.loc[employed, "p3"].str.len() == 4).all()


def test_output_schema_and_rates(out):
    assert list(out.columns) == COLUMNS
    assert validate_frame(out) == []
    assert (out["countrycode"] == "MEX").all()
    assert out["minlaborage"].eq(15).all()
    assert out.loc[out["age"] < 15, "lstatus"].isna().all()
    assert set(out["lstatus"].dropna().unique()) <= {1, 2, 3}


def test_occupation_and_industry_mapping(out):
    emp = out[out["lstatus"] == 1]
    assert emp["occup_isco"].notna().mean() > 0.99
    assert emp["occup_isco"].dropna().str.len().eq(4).all()
    assert emp["occup_isco_digits"].dropna().between(1, 4).all()
    assert emp["industrycat_isic"].notna().all()
    assert emp["industrycat10"].between(1, 10).all()


def test_tenure_and_contract(raw, out):
    emp = out[out["lstatus"] == 1]
    assert emp["tenure_months"].dropna().ge(0.5).all()
    kept = raw[(raw["r_def"] == "0") & (raw["c_res"] != "2")].reset_index(drop=True)
    earlier = kept.loc[emp.index, "p3r"] == "3"
    assert (emp.loc[earlier, "tenure_lt12"] == 0).all()
    assert (emp.loc[earlier, "tenure_months"].dropna() >= 12).all()
    # Q1 uses the extended-questionnaire contract item p3j
    subordinate = emp[emp["empstat"] == 1]
    assert subordinate["contract"].notna().mean() > 0.9


def test_weight_and_geography(out):
    assert (out["weight"] > 0).all()
    assert out["urban"].isin([0, 1]).all()
    assert out["subnatid1"].str.match(r"^\d{2} - ").all()
    assert out["male"].isin([0, 1]).all()


def test_normalize_columns_handles_bom_and_renames():
    from lfspanel.read.mex import normalize_columns

    assert normalize_columns(["﻿r_def", "CVE_ENT ", "p3"]) == ["r_def", "ent", "p3"]
    assert normalize_columns(["ï»¿cd_a"]) == ["cd_a"]


def test_tenure_missing_outside_first_quarter(raw):
    """Q2-Q4 files lack p3r; tenure must be NA, never 0."""
    q2 = raw.copy()
    for col in ("p3r", "p3r_anio", "p3r_mes", "p3j"):
        q2[col] = ""
    out = harmonize(q2, Period("2025Q2"))
    emp = out[out["lstatus"] == 1]
    assert emp["tenure_lt12"].isna().all()
    assert emp["tenure_months"].isna().all()
    assert emp.loc[emp["empstat"] == 1, "contract"].notna().mean() > 0.9
