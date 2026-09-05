"""Refresh resources/official/<ccc>_headline.csv from the statistical office's API.

python scripts/03_fetch_official.py --country bra --periods 2022Q1:2026Q2
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lfspanel.config import ROOT, get_country
from lfspanel.official import FETCHERS
from lfspanel.periods import parse_periods


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--country", required=True)
    ap.add_argument("--periods", required=True)
    args = ap.parse_args()
    country = get_country(args.country)
    df = FETCHERS[country.key](parse_periods(args.periods))
    dest = (
        Path(ROOT)
        / "src"
        / "lfspanel"
        / "resources"
        / "official"
        / f"{country.key}_headline.csv"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest, index=False)
    print(df.to_string(index=False))
    print(f"-> {dest}")


if __name__ == "__main__":
    main()
