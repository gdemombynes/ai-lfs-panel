# ruff: noqa: E501
from pathlib import Path

import pandas as pd
import pytest

from lfspanel.fetch.ind import release_for, select_resources
from lfspanel.harmonize.ind import harmonize, weight
from lfspanel.periods import Period
from lfspanel.read.ind import ALIASES, keep_list, quarter_label, read_raw
from lfspanel.schema import COLUMNS, validate_frame

FIX = Path(__file__).parent / "fixtures" / "ind"
Q2025 = FIX / "q2025" / "Data_in_STATA.zip"
CY2024 = FIX / "cy2024" / "Data_in_STATA.zip"
CY2022 = FIX / "cy2022" / "PLFS_Data_2022-22_STATA.zip"
CY2021 = FIX / "cy2021" / "STATA_PLFS_Calendar_Year_2021.zip"


def test_release_and_quarter_labels():
    assert release_for(Period("2021Q1")).label == "cy2021"
    assert release_for(Period("2025Q1")).label == "cy2025"
    assert release_for(Period("2025Q2")).label == "q2025"
    assert quarter_label(release_for(Period("2022Q1")), Period("2022Q1")) == "Q3"
    assert quarter_label(release_for(Period("2023Q1")), Period("2023Q1")) == "Q7"
    assert quarter_label(release_for(Period("2024Q4")), Period("2024Q4")) == "Q6"
    with pytest.raises(FileNotFoundError):
        release_for(Period("2027Q1"))


def test_aliases_cover_keep_list():
    keep = set(keep_list())
    for label, alias in ALIASES.items():
        assert set(alias) <= keep, label


def test_select_resources_prefers_stata():
    res = [
        {"filename": "Data_in_CSV.zip", "is_microdata": True, "dctype": "Microdata"},
        {"filename": "Data_in_STATA.zip", "is_microdata": True, "dctype": "Microdata"},
        {
            "filename": "2_Data_LayoutPLFS_Q2025.xlsx",
            "is_microdata": False,
            "dctype": "Document",
        },
        {
            "filename": "1_README_PLFS_Q2025.docx",
            "is_microdata": False,
            "dctype": "Document",
        },
    ]
    chosen = select_resources(res)
    assert chosen["data"]["filename"] == "Data_in_STATA.zip"
    assert chosen["layout"]["filename"].startswith("2_Data_Layout")
    assert chosen["readme"]["filename"].startswith("1_README")


@pytest.fixture(scope="module", params=["q2025", "cy2024", "cy2022", "cy2021"])
def case(request):
    period, path = {
        "q2025": (Period("2025Q2"), Q2025),
        "cy2024": (Period("2024Q1"), CY2024),
        "cy2022": (Period("2022Q3"), CY2022),
        "cy2021": (Period("2021Q1"), CY2021),
    }[request.param]
    raw = read_raw(period, path=path)
    return request.param, period, raw, harmonize(raw, period, raw_release=request.param)


def test_read_raw_canonical_columns(case):
    label, period, raw, _ = case
    assert list(raw.columns) == keep_list() + ["plfs_release", "source_file"]
    assert (raw["plfs_release"] == label).all()
    assert raw["qtr"].nunique() == 1
    assert raw["mult"].gt(0).all()
    assert raw["month"].str.fullmatch(r"\d{1,2}").all()
    assert raw["ocu_cws"].str.fullmatch(r"\d{3}|").all()


def test_weight_rule(case):
    label, _, raw, out = case
    w = weight(raw)
    if label == "q2025":
        assert (w == raw["mult"] / 100).all()
    else:
        scale = 2 if label == "cy2021" else 1
        nss, nsc = pd.to_numeric(raw["nss"]), pd.to_numeric(raw["nsc"])
        assert (w[nss == nsc] == raw.loc[nss == nsc, "mult"] / 100 * scale).all()
        assert (w[nss != nsc] == raw.loc[nss != nsc, "mult"] / 200 * scale).all()
    assert (out["weight"] > 0).all()


def test_schema_and_status(case):
    _, period, raw, out = case
    assert list(out.columns) == COLUMNS
    assert validate_frame(out) == []
    cws = pd.to_numeric(raw["acws"], errors="coerce")
    adult = pd.to_numeric(raw["age"]) >= 15
    emp = cws.between(11, 72) & adult
    un = cws.isin([81, 82]) & adult
    assert (out.loc[emp.values, "lstatus"] == 1).all()
    assert (out.loc[un.values, "lstatus"] == 2).all()
    assert (out.loc[(adult & ~emp & ~un).values, "lstatus"] == 3).all()
    assert out.loc[(~adult).values, "lstatus"].isna().all()
    assert out["urban"].isin([0, 1]).all() and out["male"].isin([0, 1]).all()
    assert out["subnatid1"].str.contains(" - ").all()
    assert (out["int_month"].dropna().between(1, 12)).all()
    assert out["hhid"].str.len().eq(12).all()
    assert not out["pid"].duplicated().any()


def test_job_characteristics(case):
    label, _, _, out = case
    emp = out[out["lstatus"] == 1]
    assert emp["occup_isco"].notna().mean() > 0.98
    allowed = [1, 2, 3] if label == "cy2021" else [2, 3]
    assert emp["occup_isco_digits"].dropna().isin(allowed).all()
    # NCO-2004 (2021H1) resolves about 80 % of codes to an ISCO-08 minor group
    assert (emp["occup_isco_digits"].dropna() == 3).mean() > (
        0.75 if label == "cy2021" else 0.9
    )
    assert emp["industrycat_isic"].str.endswith("00").all()
    assert (emp["isic_digits"].dropna() == 2).all()
    assert emp["whours"].dropna().between(1, 140).all()
    if label == "cy2021":
        assert emp["whours"].isna().all() and emp["wage_no_compen"].isna().all()
    assert emp["wage_no_compen"].dropna().gt(0).all()
    assert emp["unitwage"].dropna().isin([2, 5]).all()
    assert emp["contract"].isna().all() and emp["tenure_lt12"].isna().all()
    assert emp["empstat"].isin([1, 2, 3, 4]).all()
