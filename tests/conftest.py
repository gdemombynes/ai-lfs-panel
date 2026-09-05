"""Shared fixtures: a tiny synthetic harmonized frame and a PNADC raw fixture."""

from __future__ import annotations

import pandas as pd
import pytest

from lfspanel.config import get_country
from lfspanel.periods import Period
from lfspanel.schema import cast_to_schema


@pytest.fixture
def harmonized_frame() -> pd.DataFrame:
    """Five valid rows: employed, unemployed, NLF, child, employed armed forces."""
    country = get_country("bra")
    rows = [
        dict(
            age=30,
            lstatus=1,
            occup_isco="2512",
            occup=2,
            industrycat_isic="6200",
            weight=100.0,
        ),
        dict(age=22, lstatus=2, weight=80.0),
        dict(age=65, lstatus=3, weight=120.0),
        dict(age=10, weight=50.0),
        dict(
            age=40,
            lstatus=1,
            occup_isco="0110",
            occup=0,
            industrycat_isic="8400",
            weight=60.0,
        ),
    ]
    df = pd.DataFrame(rows)
    df["countrycode"] = country.ccc
    df["source"] = "own"
    df["period"] = str(Period("2025Q1"))
    df["minlaborage"] = country.minlaborage
    df["occup_isco_digits"] = df["occup_isco"].notna().map({True: 4, False: pd.NA})
    df["isic_digits"] = df["industrycat_isic"].notna().map({True: 2, False: pd.NA})
    return cast_to_schema(df)
