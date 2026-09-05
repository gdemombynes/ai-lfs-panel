"""(Re)build DuckDB views over all harmonized partitions and print a summary."""

from __future__ import annotations

from lfspanel.store import build_views, panel_summary


def main() -> None:
    build_views()
    summary = panel_summary()
    with __import__("pandas").option_context(
        "display.width", 200, "display.max_rows", 500
    ):
        print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
