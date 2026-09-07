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


@lru_cache(maxsize=None)
def _isco88_group_map() -> dict:
    """ISCO-88 minor group (3 digits) -> (ISCO-08 prefix padded to 4, digits).

    The unit groups of each minor group are mapped with the ILO correspondence
    (primary target); the modal ISCO-08 minor group is kept when it covers at
    least half of the unit groups, otherwise the modal sub-major or major group.
    """
    i88 = load_crosswalk("isco88_to_isco08")
    i88 = i88[i88["isco08"].str.len() == 4]
    out = {}
    for k in (3, 2, 1):  # keys of 1-2 digits serve codes with no minor group
        for prefix, g in i88.groupby(i88["isco88"].astype(str).str[:k]):
            for d in (k, 2, 1):
                if d > k:
                    continue
                counts = g["isco08"].str[:d].value_counts()
                if counts.iloc[0] / counts.sum() >= 0.5:
                    out[prefix] = (counts.index[0].ljust(4, "0"), d)
                    break
    return out


def isco88_group_to_isco08(codes: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """ISCO-88 minor groups (3 digits) -> ISCO-08 code (4 chars) and digits.

    Codes with no ISCO-88 counterpart become NA; see ``_isco88_group_map``.
    """
    table = _isco88_group_map()
    s = codes.astype("string").str.strip().str[:3]

    def lookup(c):
        if c is pd.NA or not c:
            return None
        for d in (3, 2, 1):
            if c[:d] in table:
                return table[c[:d]]
        return None

    hit = s.map(lookup)
    out = hit.map(lambda h: h[0] if h else pd.NA).astype("string")
    digits = hit.map(lambda h: h[1] if h else pd.NA).astype("Int8")
    return out, digits
