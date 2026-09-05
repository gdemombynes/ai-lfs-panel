from pathlib import Path

import pytest

from lfspanel.periods import Period
from lfspanel.read.bra import keep_list, parse_sas_layout, read_raw

FIXTURE = Path(__file__).parent / "fixtures" / "bra" / "PNADC_sample.txt"


def test_layout_parses_all_fields_and_positions():
    fields = {f.name: f for f in parse_sas_layout()}
    assert len(fields) > 400
    assert (fields["Ano"].start, fields["Ano"].width, fields["Ano"].is_char) == (
        0,
        4,
        True,
    )
    assert fields["V1028"].is_char is False and fields["V1028"].width == 15
    assert fields["V4010"].width == 4 and fields["V4013"].width == 5
    # fields are contiguous in the layout: no overlaps
    ordered = sorted(fields.values(), key=lambda f: f.start)
    assert all(a.end <= b.start for a, b in zip(ordered, ordered[1:]))


def test_keep_list_names_exist_in_layout():
    names = {f.name for f in parse_sas_layout()}
    keep = keep_list()
    assert len(keep) >= 30
    assert set(keep) <= names


def test_read_raw_fixture_types_and_values():
    df = read_raw(Period("2025Q1"), path=FIXTURE)
    assert len(df) == 60
    assert set(keep_list()) <= set(df.columns)
    assert (df["Ano"] == "2025").all() and (df["Trimestre"] == "1").all()
    assert df["V1028"].dtype.kind == "f" and (df["V1028"] > 0).all()
    assert df["V2009"].between(0, 120).all()
    assert df["source_file"].iloc[0] == "PNADC_sample.txt"


def test_read_raw_unknown_keep_name_raises():
    with pytest.raises(KeyError):
        read_raw(Period("2025Q1"), keep=["Ano", "NOPE"], path=FIXTURE)
