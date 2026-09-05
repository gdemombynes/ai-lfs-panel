"""Download raw microdata for one country and a range of periods.

python scripts/01_fetch.py --country bra --periods 2022Q1:2026Q2 [--force] [--docs]
"""

from __future__ import annotations

import argparse
import importlib

from lfspanel.config import get_country
from lfspanel.fetch.base import make_session
from lfspanel.periods import parse_periods


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--country", required=True)
    ap.add_argument(
        "--periods", required=True, help="e.g. 2022Q1:2026Q2 or 2025Q1,2025Q2"
    )
    ap.add_argument("--force", action="store_true", help="re-download even if cached")
    ap.add_argument(
        "--docs", action="store_true", help="also fetch documentation files"
    )
    args = ap.parse_args()

    country = get_country(args.country)
    mod = importlib.import_module(f"lfspanel.fetch.{country.key}")
    session = make_session()
    if args.docs and hasattr(mod, "fetch_docs"):
        for r in mod.fetch_docs(force=args.force, session=session):
            print(f"docs  {r.status:7s} {r.path.name} {r.error or ''}")
    for period in parse_periods(args.periods):
        for r in mod.fetch_period(period, force=args.force, session=session):
            mb = r.bytes / 1e6 if r.bytes else 0
            print(f"{period} {r.status:7s} {r.path.name} {mb:8.1f} MB {r.error or ''}")


if __name__ == "__main__":
    main()
