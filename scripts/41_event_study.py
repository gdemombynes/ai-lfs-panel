"""Event-study and difference-in-differences estimates by exposure tercile.

    python scripts/41_event_study.py [--outcome log_emp|emp_ratio|new_hire_share]
                                     [--treat high|high_q5|high_d10|score_w]
                                     [--keep-small]

Reference quarter 2022Q4; cell and country x age x sex x quarter fixed
effects; baseline-employment weights; clusters country x occupation.
Writes output/tables/event_study_<outcome>.csv, did_<outcome>.csv and
employment_index.csv.
"""

from __future__ import annotations

import argparse

import pandas as pd

from lfspanel.analysis import (
    CELLS_PATH,
    employment_index,
    estimate_did,
    estimate_event_study,
    event_study_frame,
    iter_subsets,
    occupation_totals,
    pooled_index,
)
from lfspanel.config import OUTPUT
from lfspanel.exposure import load_exposure_table


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outcome", default="log_emp")
    ap.add_argument("--treat", default="high")
    ap.add_argument(
        "--keep-small", action="store_true", help="keep cells under 30 observations"
    )
    args = ap.parse_args()
    cells = pd.read_parquet(CELLS_PATH)
    exposure = load_exposure_table()
    frame = event_study_frame(cells, exposure, drop_small=not args.keep_small)
    tables = OUTPUT / "tables"
    tables.mkdir(parents=True, exist_ok=True)

    es, did = [], []
    for name, sub in iter_subsets(frame):
        if sub[args.outcome].notna().sum() < 100:
            continue
        e = estimate_event_study(sub, outcome=args.outcome, treat=args.treat)
        es.append(e.assign(subset=name))
        d = estimate_did(
            sub, outcome=args.outcome, treat=args.treat, triple=name == "all"
        )
        did.append(d.assign(subset=name))
        post = e[e["k"] > 0]
        n_cells, n_cl = int(e["n_cells"].iloc[0]), int(e["n_clusters"].iloc[0])
        mean_post = post["coef"].mean()
        print(
            f"{name:12s} cells={n_cells:>7,} clusters={n_cl:>5}  post={mean_post:+.4f}"
        )
    suffix = f"{args.outcome}" + ("" if args.treat == "high" else f"_{args.treat}")
    pd.concat(es).to_csv(tables / f"event_study_{suffix}.csv", index=False)
    pd.concat(did).to_csv(tables / f"did_{suffix}.csv", index=False)
    if args.outcome == "log_emp" and args.treat == "high":
        totals = occupation_totals(cells)
        idx = employment_index(totals, exposure)
        idx.to_csv(tables / "employment_index.csv", index=False)
        q5 = employment_index(totals, exposure, group="quintile")
        pd.concat([q5, pooled_index(q5)]).to_csv(
            tables / "employment_index_q5.csv", index=False
        )
    print(pd.concat(did).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
