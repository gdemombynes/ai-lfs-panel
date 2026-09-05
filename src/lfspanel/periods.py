"""Reference periods: calendar quarters (``2023Q1``) and months (``2023M03``)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import Iterator, Optional

_PATTERN = re.compile(r"^(\d{4})([QM])(\d{1,2})$")
ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV"}


@total_ordering
@dataclass(frozen=True)
class Period:
    """A calendar quarter or month.

    ``Period("2023Q1")`` is the quarter, ``Period("2023M03")`` the month.
    Months know their quarter; quarters have ``month is None``.
    """

    year: int
    quarter: int
    month: Optional[int] = None

    def __init__(self, text: str):
        m = _PATTERN.match(text.strip().upper())
        if not m:
            raise ValueError(f"Bad period {text!r}; expected e.g. 2023Q1 or 2023M03")
        year, kind, n = int(m.group(1)), m.group(2), int(m.group(3))
        if kind == "Q":
            if not 1 <= n <= 4:
                raise ValueError(f"Quarter out of range in {text!r}")
            object.__setattr__(self, "year", year)
            object.__setattr__(self, "quarter", n)
            object.__setattr__(self, "month", None)
        else:
            if not 1 <= n <= 12:
                raise ValueError(f"Month out of range in {text!r}")
            object.__setattr__(self, "year", year)
            object.__setattr__(self, "quarter", (n - 1) // 3 + 1)
            object.__setattr__(self, "month", n)

    @property
    def is_month(self) -> bool:
        return self.month is not None

    @property
    def quarter_period(self) -> "Period":
        return Period(f"{self.year}Q{self.quarter}")

    @property
    def roman(self) -> str:
        return ROMAN[self.quarter]

    @property
    def ibge_code(self) -> str:
        """IBGE file suffix, e.g. ``012025`` for 2025Q1."""
        return f"{self.quarter:02d}{self.year}"

    @property
    def months(self) -> list:
        """Calendar months covered (three for a quarter, one for a month)."""
        if self.month is not None:
            return [self.month]
        start = (self.quarter - 1) * 3 + 1
        return [start, start + 1, start + 2]

    def __str__(self) -> str:
        if self.month is not None:
            return f"{self.year}M{self.month:02d}"
        return f"{self.year}Q{self.quarter}"

    def _key(self) -> tuple:
        return (self.year, self.quarter, self.month or 0)

    def __lt__(self, other: "Period") -> bool:
        return self._key() < other._key()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Period) and self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())

    def next(self) -> "Period":
        if self.month is not None:
            if self.month == 12:
                return Period(f"{self.year + 1}M01")
            return Period(f"{self.year}M{self.month + 1:02d}")
        if self.quarter == 4:
            return Period(f"{self.year + 1}Q1")
        return Period(f"{self.year}Q{self.quarter + 1}")


def period_range(start: str, end: str) -> Iterator[Period]:
    """Yield periods from ``start`` to ``end`` inclusive, same kind."""
    a, b = Period(start), Period(end)
    if a.is_month != b.is_month:
        raise ValueError("start and end must both be quarters or both be months")
    if a > b:
        raise ValueError(f"start {a} is after end {b}")
    cur = a
    while cur <= b:
        yield cur
        cur = cur.next()


def parse_periods(spec: str) -> list:
    """Parse ``2022Q1:2026Q2`` or a comma list ``2023Q1,2023Q3`` into Periods."""
    spec = spec.strip()
    if ":" in spec:
        a, b = spec.split(":", 1)
        return list(period_range(a, b))
    return [Period(p) for p in spec.split(",") if p.strip()]
