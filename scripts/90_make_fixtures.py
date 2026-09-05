"""Write small raw extracts under tests/fixtures/ for unit tests.

    python scripts/90_make_fixtures.py --country bra --period 2025Q1 --n 60

The Brazil fixture is a random sample of raw fixed-width lines (public data),
so the reader and harmonizer tests exercise the real layout.
"""

from __future__ import annotations

import argparse
import random
import zipfile
from pathlib import Path

from lfspanel.config import ROOT, get_country
from lfspanel.fetch.bra import zip_path
from lfspanel.periods import Period


def make_bra(period: Period, n: int, seed: int = 7) -> Path:
    rng = random.Random(seed)
    src = zip_path(period)
    out = ROOT / "tests" / "fixtures" / "bra" / "PNADC_sample.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    keep = []
    with zipfile.ZipFile(src) as z:
        member = next(m for m in z.namelist() if m.lower().endswith(".txt"))
        with z.open(member) as f:
            for i, line in enumerate(f):
                if i < 200_000 and rng.random() < 0.0004:
                    keep.append(line)
                if len(keep) >= n:
                    break
    out.write_bytes(b"".join(keep))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--country", required=True)
    ap.add_argument("--period", required=True)
    ap.add_argument("--n", type=int, default=60)
    args = ap.parse_args()
    country = get_country(args.country)
    if country.key == "bra":
        print(make_bra(Period(args.period), args.n))
    else:
        raise SystemExit(f"No fixture builder for {country.key} yet")


if __name__ == "__main__":
    main()
