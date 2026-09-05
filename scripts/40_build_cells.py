"""Aggregate the employed view into analysis cells.

    python scripts/40_build_cells.py

Cells: country x quarter x ISCO (3 digits where at least 90 % of employment
carries three digits, else 2) x age group x sex. Writes
data/processed/cells/cells.parquet and output/tables/cells_summary.csv.
"""

from __future__ import annotations

from lfspanel.analysis import CELLS_PATH, build_cells, cell_depth
from lfspanel.config import OUTPUT
from lfspanel.store import duckdb_connect


def main() -> None:
    con = duckdb_connect(read_only=True)
    try:
        depth = cell_depth(con)
        cells = build_cells(con, depth)
    finally:
        con.close()
    CELLS_PATH.parent.mkdir(parents=True, exist_ok=True)
    cells.to_parquet(CELLS_PATH, index=False)
    summary = (
        cells.groupby("countrycode")
        .agg(
            digits=("isco_digits", "first"),
            quarters=("period", "nunique"),
            occupations=("isco", "nunique"),
            cells=("n", "count"),
            small_share=("small", "mean"),
            tenure_coverage=("tenure_coverage", "mean"),
        )
        .reset_index()
    )
    out = OUTPUT / "tables" / "cells_summary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    summary.round(3).to_csv(out, index=False)
    print(f"{len(cells):,} cells -> {CELLS_PATH}")
    print(summary.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
