"""Compare harmonized headline rates with published official figures.

python scripts/20_validate_official.py --country bra [--periods 2025Q1:2025Q4]
"""

from __future__ import annotations

import argparse

import pandas as pd

from lfspanel.config import OUTPUT, get_country
from lfspanel.periods import parse_periods
from lfspanel.store import partition_path, read_partition
from lfspanel.validate import age_band, compare_official, headline_rates, load_official


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
        else sorted(official["period"].unique())
    )
    results = []
    for period in periods:
        path = partition_path(args.source, country.ccc, period)
        if not path.exists():
            print(f"{period}: no partition at {path}")
            continue
        df = read_partition(path)
        pop = str(official.loc[official["period"] == period, "population"].iloc[0])
        min_age, max_age = age_band(pop)
        rates = headline_rates(df, min_age, max_age)
        results.append(compare_official(rates, official, period))
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
