"""Download external resources: ILO GenAI occupational exposure scores.

    python scripts/04_fetch_external.py [--force]

Files land in data/external/<family>/ with a row in data/raw/manifest.csv.
"""

from __future__ import annotations

import argparse

from lfspanel.config import EXTERNAL
from lfspanel.fetch.base import download, make_session

ILO_REPO = "https://raw.githubusercontent.com/pgmyrek/2025_GenAI_scores_ISCO08/main"
FILES = {
    "exposure": [
        f"{ILO_REPO}/Final_Scores_ISCO08_Gmyrek_et_al_2025.xlsx",
        f"{ILO_REPO}/4digits_with_tasks.xlsx",
    ],
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    s = make_session()
    for family, urls in FILES.items():
        for url in urls:
            res = download(
                url,
                EXTERNAL / family / url.rsplit("/", 1)[1],
                force=args.force,
                session=s,
            )
            size = f"{res.bytes / 1e6:.1f} MB"
            err = res.error or ""
            print(f"{family:10s} {res.status:8s} {res.path.name}  {size} {err}")


if __name__ == "__main__":
    main()
