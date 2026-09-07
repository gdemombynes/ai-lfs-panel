"""Compare harmonized headline rates with published official figures.

python scripts/20_validate_official.py --country bra [--periods 2025Q1:2025Q4]
"""

from __future__ import annotations

import argparse
import re
from typing import Optional

import pandas as pd

from lfspanel.config import OUTPUT, get_country
from lfspanel.periods import parse_periods
from lfspanel.store import partition_path, read_partition
from lfspanel.validate import (
    compare_official,
    headline_rates,
    load_official,
    population_filter,
)


def _load(source: str, ccc: str, period: str) -> Optional[pd.DataFrame]:
    """One quarter's partition, or the four quarters of a calendar year pooled.

    A year label (``"2024"``) pools the quarterly partitions with their
    quarter-level weights, i.e. the annual average that statistical offices
    publish for calendar years (India's PLFS calendar-year notes).
    """
    if re.fullmatch(r"\d{4}", period):
        paths = [partition_path(source, ccc, f"{period}Q{q}") for q in range(1, 5)]
        paths = [p for p in paths if p.exists()]
        if not paths:
            print(f"{period}: no quarterly partitions")
            return None
        return pd.concat([read_partition(p) for p in paths], ignore_index=True)
    path = partition_path(source, ccc, period)
    if not path.exists():
        print(f"{period}: no partition at {path}")
        return None
    return read_partition(path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--country", required=True)
    ap.add_argument(
        "--periods", default=None, help="default: every period in the official table"
    )
    ap.add_argument("--source", default="own")
    args = ap.parse_args()

    country = get_country(args.country)
    official = load_official(country.key)
    periods = (
        [str(p) for p in parse_periods(args.periods)]
        if args.periods
        else sorted(official["period"].astype(str).unique())
    )
    results = []
    for period in periods:
        frame = _load(args.source, country.ccc, period)
        if frame is None:
            continue
        sub = official[official["period"] == period]
        for pop in sub["population"].astype(str).unique():
            min_age, max_age, urban = population_filter(pop)
            rates = headline_rates(frame, min_age, max_age, urban)
            rows = compare_official(
                rates, sub[sub["population"].astype(str) == pop], period
            )
            rows.insert(1, "population", pop)
            results.append(rows)
    if not results:
        return
    out = pd.concat(results, ignore_index=True)
    dest = OUTPUT / "tables" / f"validation_official_{country.key}.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(dest, index=False)
    with pd.option_context("display.width", 200):
        print(out.to_string(index=False))
    n_pass, n_fail = (out["status"] == "PASS").sum(), (out["status"] == "FAIL").sum()
    print(f"\n{n_pass} PASS, {n_fail} FAIL -> {dest}")


if __name__ == "__main__":
    main()
