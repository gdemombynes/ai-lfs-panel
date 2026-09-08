# ruff: noqa: E501
from pathlib import Path

import pandas as pd

from lfspanel.fetch.bol import (
    CATALOG,
    POOLED_FIRST,
    POOLED_LAST,
    catalog_url,
    in_pooled,
)
from lfspanel.harmonize.bol import harmonize, month_from_code, weight
from lfspanel.periods import Period
from lfspanel.read.bol import keep_list, read_raw
from lfspanel.schema import COLUMNS, validate_frame

FIXTURES = Path(__file__).parent / "fixtures" / "bol"
POOLED = FIXTURES / "ECE_4T2015_3T2025.csv"
QUARTER = FIXTURES / "ECE_4T2025.zip"


def test_catalogue_tables():
    assert CATALOG["2025Q4"] == 257
    assert catalog_url(Period("2025Q4")).endswith("/catalog/257")
    assert (
        in_pooled(Period("2021Q1"))
        and in_pooled(POOLED_FIRST)
        and in_pooled(POOLED_LAST)
    )
    assert not in_pooled(Period("2025Q4"))


def test_month_from_code():
    codes = pd.Series(["756", "758", "789", ""])
    assert month_from_code(codes).tolist()[:3] == [1, 3, 10]
    assert pd.isna(month_from_code(codes).iloc[3])


def test_read_raw_pooled_csv():
    raw = read_raw(Period("2023Q1"), path=POOLED)
    assert list(raw.columns) == keep_list() + ["source_file"]
    assert len(raw) == 400
    assert (raw["gestion"] == "2023").all() and (raw["trimestre"] == "1").all()
    assert raw["fact_trim_act"].gt(0).all()  # decimal commas parsed
    assert (raw["fact_trim"] == "").all()  # absent from the pooled file
    assert raw["s2_15acod"].str.fullmatch(r"\d{1,5}|").all()


def test_read_raw_pooled_csv_wrong_quarter():
    import pytest

    with pytest.raises(FileNotFoundError):
        read_raw(Period("2022Q3"), path=POOLED)


def test_read_raw_quarter_zip():
    raw = read_raw(Period("2025Q4"), path=QUARTER)
    assert list(raw.columns) == keep_list() + ["source_file"]
    assert len(raw) == 400
    assert raw["fact_trim_act"].gt(0).all()
    assert raw["source_file"].iloc[0] == "ECE_4T2025.zip:ECE_4T2025.dta"


def _check(raw: pd.DataFrame, period: Period) -> pd.DataFrame:
    out = harmonize(raw, period)
    assert list(out.columns) == COLUMNS
    assert validate_frame(out) == []
    assert out["minlaborage"].eq(14).all()
    assert (out["weight"].values == weight(raw).values).all()
    assert not out["pid"].duplicated().any()
    assert out["urban"].isin([0, 1]).all()
    assert out["subnatid1"].str.match(r"\d - ").all()
    emp_flag = pd.to_numeric(raw["peao"]) == 1
    adult = pd.to_numeric(raw["s1_03a"]) >= 14
    assert (out.loc[(emp_flag & adult).values, "lstatus"] == 1).all()
    assert out.loc[(~adult).values, "lstatus"].isna().all()
    emp = out[out["lstatus"] == 1]
    assert (emp["occup_isco_digits"].dropna() >= 3).mean() > 0.6
    assert emp["industrycat_isic"].dropna().str.len().eq(4).all()
    assert emp["industrycat10"].notna().mean() > 0.9
    assert emp["empstat"].dropna().isin([1, 2, 3, 4, 5]).all()
    assert emp["whours"].dropna().between(1, 140).all()
    assert emp["wage_no_compen"].dropna().gt(0).all()
    assert emp["contract"].dropna().isin([0, 1]).all()
    assert emp["tenure_lt12"].isna().all()
    return out


def test_harmonize_pooled_quarter():
    out = _check(read_raw(Period("2023Q1"), path=POOLED), Period("2023Q1"))
    assert out["int_month"].isin([1, 2, 3]).all()
    assert out["socialsec"].dropna().isin([0, 1]).any()


def test_harmonize_quarter_zip():
    out = _check(read_raw(Period("2025Q4"), path=QUARTER), Period("2025Q4"))
    assert out["int_month"].isin([10, 11, 12]).all()
    assert out["wave"].eq("Q4").all()
