"""Build the ISCO-08 exposure table from the ILO 2025 task scores.

    python scripts/30_attach_exposure.py

Writes data/processed/exposure/ilo_exposure.csv (4, 3, 2 and 1 digits:
simple and employment-weighted scores, gradient-4 share, employment-weighted
terciles) and output/tables/exposure_summary.csv.
"""

from __future__ import annotations

from lfspanel.config import OUTPUT
from lfspanel.exposure import EXPOSURE_TABLE, build_exposure_table
from lfspanel.store import duckdb_connect


def main() -> None:
    con = duckdb_connect(read_only=True)
    try:
        table = build_exposure_table(con)
    finally:
        con.close()
    summary = (
        table.groupby("digits")
        .agg(
            codes=("isco", "count"),
            score_mean=("score_w", "mean"),
            high_codes=("high", "sum"),
        )
        .reset_index()
    )
    out = OUTPUT / "tables" / "exposure_summary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out, index=False)
    print(f"{len(table)} rows -> {EXPOSURE_TABLE}")
    print(summary.to_string(index=False))
    top = table[(table["digits"] == 2)].sort_values("score_w", ascending=False).head(8)
    print("most exposed 2-digit groups:")
    print(
        top[["isco", "score_w", "g4_share", "tercile"]].round(3).to_string(index=False)
    )


if __name__ == "__main__":
    main()
