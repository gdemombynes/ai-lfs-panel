# ruff: noqa: E501
import re
from pathlib import Path

import pandas as pd

from lfspanel.fetch.ury import CATALOG, RESOURCES, month_file
from lfspanel.harmonize.ury import educat7, harmonize
from lfspanel.periods import Period
from lfspanel.read.ury import keep_list, read_raw
from lfspanel.schema import COLUMNS, validate_frame

FIXTURE = Path(__file__).parent / "fixtures" / "ury" / "ECH_01_2025.csv"


def test_catalogue_tables():
    assert CATALOG[2025] == 779
    assert month_file(Period("2025Q1"), 1).name == "ECH_01_2025.csv"
    assert month_file(Period("2024Q4"), 12).name == "ECH_12_24.csv"
    for year, res in RESOURCES.items():
        months = [n for n in res.values() if re.match(r"ECH_\d{2}_\d{2,4}\.csv$", n)]
        assert len(months) == (12 if year >= 2022 else 0), year


def test_read_raw_single_file():
    raw = read_raw(Period("2025Q1"), path=FIXTURE)
    assert list(raw.columns) == keep_list() + ["source_file"]
    assert len(raw) == 400
    assert raw["W"].gt(0).all()
    assert (raw["mes"] == "1").all()
    assert raw["f71_2"].str.fullmatch(r"\d{4}|").all()


def test_harmonize_schema_and_rules():
    raw = read_raw(Period("2025Q1"), path=FIXTURE)
    out = harmonize(raw, Period("2025Q1"))
    assert list(out.columns) == COLUMNS
    assert validate_frame(out) == []
    assert (out["age"] >= 14).all() and out["minlaborage"].eq(14).all()
    act = pd.to_numeric(raw["POBPCOAC"])
    assert (out.loc[(act == 2).values, "lstatus"] == 1).all()
    assert (out.loc[act.isin([3, 4, 5]).values, "lstatus"] == 2).all()
    assert (out.loc[act.between(6, 11).values, "lstatus"] == 3).all()
    # single month: weights equal W (division by number of months present)
    assert (out["weight"].values == raw["W"].values).all()
    assert not out["pid"].duplicated().any()
    assert out["pid"].str.endswith("-01").all()
    emp = out[out["lstatus"] == 1]
    assert (emp["occup_isco_digits"].dropna() >= 3).mean() > 0.95
    assert emp["industrycat_isic"].str.len().eq(4).all()
    assert emp["socialsec"].dropna().isin([0, 1]).all()
    assert emp["empstat"].isin([1, 2, 3, 4, 5]).all()
    assert emp["whours"].dropna().between(1, 120).all()
    assert emp["tenure_lt12"].isna().all()  # no implantation file in the fixture


def test_educat7_ladder():
    raw = pd.DataFrame(
        {
            "e51_2": ["0", "3", "6", "6", "6", "6", "6"],
            "e197_1": ["2", "2", "1", "1", "1", "1", "1"],
            "e51_4_a": ["0", "0", "0", "3", "3", "3", "3"],
            "e51_4_b": ["0"] * 7,
            "e51_5": ["0", "0", "0", "0", "3", "3", "3"],
            "e51_6": ["0"] * 7,
            "e201_1c": ["2", "2", "2", "2", "1", "1", "1"],
            "e201_1d": ["2"] * 7,
            "e51_8": ["0", "0", "0", "0", "0", "2", "0"],
            "e51_9": ["0"] * 7,
            "e51_10": ["0", "0", "0", "0", "0", "0", "4"],
            "e51_11": ["0"] * 7,
        }
    )
    assert educat7(raw).tolist() == [1, 2, 3, 4, 5, 6, 7]
