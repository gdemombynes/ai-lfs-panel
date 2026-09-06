"""Recode helpers shared by all country harmonizers."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from lfspanel.config import HARMONIZE_VERSION, Country
from lfspanel.periods import Period
from lfspanel.schema import LABOR_VARS_EMPLOYED_ONLY, cast_to_schema, validate_frame


def pad_code(
    s: pd.Series, width: int, fill: str = "0", side: str = "right"
) -> pd.Series:
    """Zero-pad string codes to ``width`` (GLD pads ISCO/ISIC on the right)."""
    s = s.astype("string").str.strip()
    s = s.where(s.notna() & (s != ""), pd.NA)
    if side == "right":
        return s.str.ljust(width, fill)
    return s.str.rjust(width, fill)


def isco_major(occup_isco: pd.Series) -> pd.Series:
    """ISCO major group as Int8 (0 = armed forces)."""
    first = occup_isco.astype("string").str[0]
    return pd.to_numeric(first, errors="coerce").astype("Int8")


def occup_skill_from_major(major: pd.Series) -> pd.Series:
    """GLD skill level: 1-3 high, 4-8 medium, 9 low, armed forces NA."""
    out = pd.Series(pd.NA, index=major.index, dtype="Int8")
    out = out.mask(true_only(major.isin([1, 2, 3])), 3)
    out = out.mask(true_only(major.isin([4, 5, 6, 7, 8])), 2)
    out = out.mask(true_only(major == 9), 1)
    return out.astype("Int8")


_ISIC10 = [
    ((1, 3), 1),
    ((5, 9), 2),
    ((10, 33), 3),
    ((35, 39), 4),
    ((41, 43), 5),
    ((45, 47), 6),
    ((55, 56), 6),
    ((49, 53), 7),
    ((58, 63), 7),
    ((64, 82), 8),
    ((84, 84), 9),
    ((85, 99), 10),
]


def industrycat10_from_isic(isic: pd.Series) -> pd.Series:
    """GLD 10-category industry from the first two ISIC Rev.4 digits."""
    div = pd.to_numeric(isic.astype("string").str[:2], errors="coerce")
    out = pd.Series(pd.NA, index=isic.index, dtype="Int8")
    for (lo, hi), cat in _ISIC10:
        out = out.mask(true_only(div.between(lo, hi)), cat)
    return out.astype("Int8")


def industrycat4_from_10(cat10: pd.Series) -> pd.Series:
    out = pd.Series(pd.NA, index=cat10.index, dtype="Int8")
    out = out.mask(true_only(cat10 == 1), 1)
    out = out.mask(true_only(cat10.isin([2, 3, 4, 5])), 2)
    out = out.mask(true_only(cat10.isin([6, 7, 8, 9])), 3)
    out = out.mask(true_only(cat10 == 10), 4)
    return out.astype("Int8")


def educat4_from_7(educat7: pd.Series) -> pd.Series:
    out = pd.Series(pd.NA, index=educat7.index, dtype="Int8")
    out = out.mask(true_only(educat7 == 1), 1)
    out = out.mask(true_only(educat7.isin([2, 3])), 2)
    out = out.mask(true_only(educat7.isin([4, 5])), 3)
    out = out.mask(true_only(educat7.isin([6, 7])), 4)
    return out.astype("Int8")


def true_only(cond: pd.Series) -> pd.Series:
    """Boolean condition with missing values treated as False.

    ``Series.mask`` replaces where the condition is missing as well as where it
    is True, so a comparison against a nullable integer that is NA would
    otherwise assign a category to rows with no information.
    """
    return cond.fillna(False).astype(bool)


def to_int(s: pd.Series, dtype: str = "Int8") -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype(dtype)


def blank_non_employed(df: pd.DataFrame) -> pd.DataFrame:
    """Set job characteristics to NA where the person is not employed."""
    not_emp = df["lstatus"].isna() | (df["lstatus"] != 1)
    for col in LABOR_VARS_EMPLOYED_ONLY + [
        "wage_no_compen",
        "unitwage",
        "firmsize_l",
        "firmsize_u",
        "tenure_months",
    ]:
        if col in df.columns:
            df.loc[not_emp, col] = pd.NA
    return df


def finalize(
    df: pd.DataFrame,
    country: Country,
    period: Period,
    source: str = "own",
    raw_release: Optional[str] = None,
    strict: bool = True,
) -> pd.DataFrame:
    """Add provenance columns, cast to the schema and validate."""
    df = df.copy()
    df["countrycode"] = country.ccc
    df["source"] = source
    df["period"] = str(period.quarter_period)
    df["minlaborage"] = country.minlaborage
    df["raw_release"] = raw_release or pd.NA
    df["harmonize_version"] = HARMONIZE_VERSION
    df = blank_non_employed(df)
    out = cast_to_schema(df)
    validate_frame(out, strict=strict)
    return out.reset_index(drop=True)


def band_midpoint(lower: pd.Series, upper: pd.Series) -> pd.Series:
    return ((lower.astype("float") + upper.astype("float")) / 2).astype("float32")


def nan_to_na(s: pd.Series) -> pd.Series:
    return s.replace({np.nan: pd.NA})
