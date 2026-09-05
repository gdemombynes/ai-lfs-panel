from pathlib import Path

import pandas as pd
import pytest

from lfspanel.fetch.ecu import candidate_urls
from lfspanel.harmonize.ecu import _isco, harmonize
from lfspanel.periods import Period
from lfspanel.read.ecu import read_raw
from lfspanel.schema import COLUMNS, validate_frame

FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "ecu"
    / "1_BDD_ENEMDU_2025_I_TRIMESTRE_SPSS.zip"
)


def test_candidate_urls_cover_2022_folder_names():
    urls = candidate_urls(Period("2022Q2"))
    assert any(
        "Trimestre%1F_abril_junio_2022/1_BDD_ENEMDU_2022_II_TRIMESTRE_SPSS.zip" in u
        for u in urls
    )
    assert any("2022/Trimestre-abril-junio-2022/" in u for u in urls)
    assert candidate_urls(Period("2025Q3"))[0].endswith(
        "2025/Trimestre_III/1_BDD_ENEMDU_2025_III_TRIMESTRE_SPSS.zip"
    )


def test_isco_padding():
    s = pd.Series(["5223", "110", "343", "", None, "9629"])
    got = _isco(s).tolist()
    assert got[0] == "5223" and got[1] == "0110" and got[2] == "3430"
    assert pd.isna(got[3]) and pd.isna(got[4]) and got[5] == "9629"


@pytest.fixture(scope="module")
def raw():
    return read_raw(Period("2025Q1"), path=FIXTURE)


@pytest.fixture(scope="module")
def out(raw):
    return harmonize(raw, Period("2025Q1"))


def test_read_raw_columns(raw):
    assert len(raw) == 400
    assert {"condact", "p41", "p40", "fexp", "id_persona"} <= set(raw.columns)
    assert (raw["p03"].str.match(r"^\d+$")).all()


def test_output_schema_and_status(out, raw):
    assert list(out.columns) == COLUMNS
    assert validate_frame(out) == []
    assert (out["period"] == "2025Q1").all()
    assert out["minlaborage"].eq(15).all()
    cond = pd.to_numeric(raw["condact"], errors="coerce")
    age = pd.to_numeric(raw["p03"])
    adult = (age >= 15).values
    assert (out.loc[adult & cond.between(1, 6).values, "lstatus"] == 1).all()
    assert (out.loc[adult & cond.isin([7, 8]).values, "lstatus"] == 2).all()
    assert out.loc[~adult, "lstatus"].isna().all()
    assert out["subnatid1"].str.contains(" - ").all()


def test_occupation_industry_four_digits(out):
    emp = out[out["lstatus"] == 1]
    assert emp["occup_isco"].notna().mean() > 0.98
    assert (emp["occup_isco_digits"].dropna() >= 3).mean() > 0.9
    assert (emp["isic_digits"].dropna() == 4).all()
    assert emp["contract"].dropna().isin([0, 1]).all()
    assert ((emp["tenure_months"] < 12) == (emp["tenure_lt12"] == 1)).all()
