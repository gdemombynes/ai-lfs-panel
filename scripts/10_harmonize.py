"""Harmonize raw microdata into Parquet partitions.

python scripts/10_harmonize.py --country bra --periods 2022Q1:2026Q2 [--source own]
"""

from __future__ import annotations

import argparse
import importlib
import time

from lfspanel.codebook import fingerprint
from lfspanel.config import get_country
from lfspanel.fetch.base import read_manifest
from lfspanel.periods import parse_periods
from lfspanel.store import write_partition


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--country", required=True)
    ap.add_argument("--periods", required=True)
    ap.add_argument("--source", default="own", choices=["own", "gld"])
    ap.add_argument(
        "--nrows", type=int, default=None, help="debug: read only this many rows"
    )
    args = ap.parse_args()

    country = get_country(args.country)
    mod_key = country.key if args.source == "own" else "gld"
    reader = importlib.import_module(f"lfspanel.read.{mod_key}")
    harmonizer = importlib.import_module(f"lfspanel.harmonize.{mod_key}")
    manifest = read_manifest()

    for period in parse_periods(args.periods):
        t0 = time.time()
        raw = reader.read_raw(period, nrows=args.nrows)
        if args.source == "own" and not args.nrows:
            fingerprint(raw, country.key, period)
        release = ""
        src = (
            str(raw["source_file"].iloc[0]).split(":")[0]
            if "source_file" in raw
            else ""
        )
        for rel, row in manifest.items():
            if rel.endswith(src) and src:
                release = row.get("http_last_modified") or row.get("retrieved_utc", "")
        if hasattr(reader, "release_date"):
            release = reader.release_date(src) or release
        df = harmonizer.harmonize(raw, period, raw_release=release or None)
        dest = write_partition(df)
        pop = df["weight"].sum()
        secs = time.time() - t0
        print(f"{period} rows={len(df):>9,} pop={pop:>14,.0f} -> {dest} ({secs:.0f}s)")


if __name__ == "__main__":
    main()
