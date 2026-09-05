import pandas as pd
import pytest

from lfspanel.schema import COLUMNS, TARGET_SCHEMA, cast_to_schema, validate_frame


def test_cast_adds_missing_columns_in_order():
    df = cast_to_schema(pd.DataFrame({"age": [1], "weight": [2.0]}))
    assert list(df.columns) == COLUMNS
    assert str(df["age"].dtype) == TARGET_SCHEMA["age"][0]
    assert df["lstatus"].isna().all()


def test_valid_frame_passes(harmonized_frame):
    assert validate_frame(harmonized_frame) == []


def test_domain_violation_detected(harmonized_frame):
    bad = harmonized_frame.copy()
    bad.loc[0, "lstatus"] = 7
    problems = validate_frame(bad, strict=False)
    assert any(p.startswith("lstatus") for p in problems)
    with pytest.raises(ValueError):
        validate_frame(bad)


def test_lstatus_below_minlaborage_detected(harmonized_frame):
    bad = harmonized_frame.copy()
    bad.loc[3, "lstatus"] = 3
    assert any("minlaborage" in p for p in validate_frame(bad, strict=False))


def test_occup_must_match_isco_first_digit(harmonized_frame):
    bad = harmonized_frame.copy()
    bad.loc[0, "occup"] = 3
    assert any("disagrees" in p for p in validate_frame(bad, strict=False))


def test_job_vars_only_for_employed(harmonized_frame):
    bad = harmonized_frame.copy()
    bad.loc[1, "occup_isco"] = "4110"
    assert any("non-employed" in p for p in validate_frame(bad, strict=False))
