"""Classification crosswalks and ISCO-08 / ISIC Rev.4 code utilities."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from typing import Tuple

import pandas as pd

RESOURCES = files("lfspanel") / "resources" / "crosswalks"


@lru_cache(maxsize=None)
def load_crosswalk(name: str) -> pd.DataFrame:
    """Load ``resources/crosswalks/<name>.csv`` with all columns as strings."""
    path = RESOURCES / f"{name}.csv"
    with path.open("r", encoding="utf-8") as f:
        return pd.read_csv(f, dtype=str, comment="#").fillna("")


@lru_cache(maxsize=None)
def isco08_unit_groups() -> frozenset:
    """The ISCO-08 unit-group codes (4 digits) shipped in resources."""
    df = load_crosswalk("isco08_structure")
    return frozenset(df.loc[df["level"] == "4", "code"])


@lru_cache(maxsize=None)
def isco08_codes_by_level() -> dict:
    df = load_crosswalk("isco08_structure")
    return {int(lvl): frozenset(sub["code"]) for lvl, sub in df.groupby("level")}


def map_isco_codes(codes: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """Validate ISCO-08-style codes; fall back to the deepest valid parent.

    Returns ``(occup_isco, occup_isco_digits)``. A 4-digit code that is an
    ISCO-08 unit group keeps 4 digits; otherwise the code is truncated to the
    longest prefix that is a valid minor / sub-major / major group and padded
    with trailing zeros, with the digit count recorded. Unknown first digits
    become NA.
    """
    codes = codes.astype("string").str.strip()
    by_level = isco08_codes_by_level()
    out = pd.Series(pd.NA, index=codes.index, dtype="string")
    digits = pd.Series(pd.NA, index=codes.index, dtype="Int8")
    valid = codes.notna() & (codes != "")
    for level in (4, 3, 2, 1):
        prefix = codes.str[:level].str.ljust(4, "0")
        ok = (
            valid
            & out.isna()
            & codes.str.len().ge(level)
            & prefix.isin(by_level[level])
        )
        out = out.mask(ok, prefix)
        digits = digits.mask(ok, level)
    return out.astype("string"), digits.astype("Int8")


def isco_parent(code: pd.Series, digits: int) -> pd.Series:
    """Truncate 4-char ISCO codes to ``digits`` and pad with trailing zeros."""
    return code.astype("string").str[:digits].str.ljust(4, "0")
