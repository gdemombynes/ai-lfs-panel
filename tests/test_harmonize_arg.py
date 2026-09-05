from pathlib import Path

import pandas as pd
import pytest

from lfspanel.harmonize.arg import harmonize
from lfspanel.periods import Period
from lfspanel.read.arg import read_raw
from lfspanel.schema import COLUMNS, validate_frame

FIXTURE = Path(__file__).parent / "fixtures" / "arg" / "EPH_usu_1_Trim_2025_txt.zip"


@pytest.fixture(scope="module")
def raw():
    return read_raw(Period("2025Q1"), path=FIXTURE)


@pytest.fixture(scope="module")
def out(raw):
    return harmonize(raw, Period("2025Q1"))


def test_read_raw_columns(raw):
    assert 300 < len(raw) <= 400  # whole households sampled
    assert {"CODUSU", "ESTADO", "PP04D_COD", "PP04B_COD", "PONDERA"} <= set(raw.columns)
    assert raw["source_file"].str.contains("usu_individual").all()


def test_output_schema_and_status(out, raw):
    assert list(out.columns) == COLUMNS
    assert validate_frame(out) == []
    assert (out["period"] == "2025Q1").all() and (out["wave"] == "Q1").all()
    assert out["minlaborage"].eq(10).all()
    assert out["urban"].eq(1).all()
    estado = pd.to_numeric(raw["ESTADO"])
    assert (out.loc[(estado == 1).values, "lstatus"] == 1).all()
    assert (out.loc[(estado == 4).values, "lstatus"].isna()).all()
    assert (out["weight"] == pd.to_numeric(raw["PONDERA"])).all()


def test_occupation_two_digits_and_industry(out):
    emp = out[out["lstatus"] == 1]
    assert emp["occup_isco"].notna().mean() > 0.9
    assert (emp["occup_isco_digits"].dropna() <= 2).all()
    assert emp["occup_isco"].dropna().str.endswith("00").all()
    assert emp["isic_digits"].dropna().isin([1, 2]).all()
    commerce = emp["industry_orig"].str[:2].isin(["40", "48"])
    assert (emp.loc[commerce, "industrycat_isic"] == "4700").all()
    assert emp["tenure_lt12"].dropna().isin([0, 1]).all()


def test_cat_inac_optional(tmp_path):
    """INDEC dropped CAT_INAC in 2026Q1; the reader fills it with blanks."""
    import zipfile

    with zipfile.ZipFile(FIXTURE) as z:
        member = z.namelist()[0]
        text = z.read(member).decode("latin-1").splitlines()
    header = text[0].split(";")
    idx = header.index("CAT_INAC")
    rows = [";".join(v for i, v in enumerate(ln.split(";")) if i != idx) for ln in text]
    path = tmp_path / "EPH_usu_1_Trim_2026_txt.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("usu_individual_T126.txt", "\n".join(rows).encode("latin-1"))
    raw = read_raw(Period("2026Q1"), path=path)
    assert (raw["CAT_INAC"] == "").all()
    out = harmonize(raw, Period("2026Q1"))
    assert out["nlfreason"].isna().all()
