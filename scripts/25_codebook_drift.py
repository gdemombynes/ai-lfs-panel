"""Codebook and distribution drift report.

    python scripts/25_codebook_drift.py [--country bra] [--fingerprint 2021Q1:2026Q2]

Without --fingerprint, uses the fingerprints written by 10_harmonize.py.
With it, re-reads the raw files for those periods to (re)build them first.
Writes output/tables/codebook_changes[_<ccc>].csv and
output/tables/distribution_drift[_<ccc>].csv and prints the flagged rows.
"""

from __future__ import annotations

import argparse
import importlib

import pandas as pd

from lfspanel.codebook import (
    diff_codebooks,
    distribution_drift,
    fingerprint,
    load_fingerprints,
)
from lfspanel.config import COUNTRIES, OUTPUT, get_country
from lfspanel.periods import parse_periods
from lfspanel.store import duckdb_connect


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--country")
    ap.add_argument(
        "--fingerprint", help="periods A:B to (re)build fingerprints from raw"
    )
    ap.add_argument(
        "--min-share", type=float, default=0.001, help="ignore code changes below"
    )
    args = ap.parse_args()
    keys = [get_country(args.country).key] if args.country else [
        k for k in COUNTRIES if load_fingerprints(k)
    ]  # fmt: skip
    tables = OUTPUT / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    suffix = f"_{keys[0]}" if args.country else ""

    if args.fingerprint:
        reader = importlib.import_module(f"lfspanel.read.{keys[0]}")
        for period in parse_periods(args.fingerprint):
            try:
                fingerprint(reader.read_raw(period), keys[0], period)
                print(f"fingerprint {keys[0]} {period}")
            except FileNotFoundError as exc:
                print(f"skip {period}: {exc}")

    changes = pd.concat(
        [diff_codebooks(k, args.min_share).assign(country=k) for k in keys],
        ignore_index=True,
    )
    changes.to_csv(tables / f"codebook_changes{suffix}.csv", index=False)
    print(f"{len(changes)} codebook changes -> codebook_changes{suffix}.csv")
    if len(changes):
        print(changes.to_string(index=False, max_rows=60))

    con = duckdb_connect(read_only=True)
    try:
        drift = pd.concat([distribution_drift(con, k) for k in keys], ignore_index=True)
    finally:
        con.close()
    drift.to_csv(tables / f"distribution_drift{suffix}.csv", index=False)
    flagged = drift[drift["flag"] != ""]
    print(
        f"{len(flagged)} flagged distribution moves -> distribution_drift{suffix}.csv"
    )
    if len(flagged):
        cols = [
            "countrycode",
            "variable",
            "category",
            "period",
            "share",
            "d_prev",
            "d_next",
            "flag",
        ]
        print(flagged[cols].round(2).to_string(index=False, max_rows=60))


if __name__ == "__main__":
    main()
