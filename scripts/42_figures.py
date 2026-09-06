"""Event-study and employment-index figures.

    python scripts/42_figures.py

Reads output/tables/event_study_*.csv, employment_index.csv and
employment_index_q5.csv; writes output/figures/es_<outcome>_<subset>.png,
emp_index_<country>.png (terciles), emp_index_q5_<country>.png and the
multi-panel emp_index_q5_panel.png (quintiles, with the pooled series).
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from lfspanel.config import OUTPUT  # noqa: E402

FIG = OUTPUT / "figures"
NAMES = {
    "ARG": "Argentina", "BRA": "Brazil", "COL": "Colombia", "ECU": "Ecuador",
    "GEO": "Georgia", "MEX": "Mexico", "NGA": "Nigeria", "PER": "Peru",
    "PHL": "Philippines", "ZAF": "South Africa", "ALL": "All countries (weighted mean)",
}  # fmt: skip
PALETTE = ["#4c72b0", "#8172b2", "#64b5cd", "#dd8452", "#c44e52"]


def plot_event_study(es: pd.DataFrame, title: str, path) -> None:
    es = es.sort_values("k")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.axhline(0, color="grey", lw=0.8)
    ax.axvline(0, color="grey", lw=0.8, ls="--")
    ax.errorbar(es["k"], es["coef"], yerr=1.96 * es["se"], fmt="o-", ms=3, capsize=2)
    ax.set_xticks(es["k"])
    ax.set_xticklabels(es["period"], rotation=90, fontsize=7)
    ax.set_ylabel("coef. on high exposure x quarter")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _draw_index(ax, idx: pd.DataFrame, cc: str, group: str, label: str) -> None:
    sub_cc = idx[idx["countrycode"] == cc]
    periods = sorted(sub_cc["period"].unique())
    pos = {p: i for i, p in enumerate(periods)}
    groups = sorted(sub_cc[group].dropna().unique())
    for g in groups:
        sub = sub_cc[sub_cc[group] == g].sort_values("period")
        color = PALETTE[int(g) - 1] if len(groups) <= 5 else None
        ax.plot(
            [pos[p] for p in sub["period"]], sub["index"], marker="o", ms=2.5,
            lw=1.6 if g == groups[-1] else 1.0, color=color, label=f"{label} {int(g)}",
        )  # fmt: skip
    ax.axhline(100, color="grey", lw=0.8)
    if "2022Q4" in pos:
        ax.axvline(pos["2022Q4"], color="grey", lw=0.8, ls="--")
    ax.set_xticks(range(len(periods)))
    ax.set_xticklabels(
        [p if p.endswith("Q1") else "" for p in periods], rotation=90, fontsize=7
    )
    ax.set_title(NAMES.get(cc, cc), fontsize=10)


def plot_index(idx: pd.DataFrame, cc: str, path, group: str = "tercile") -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    _draw_index(ax, idx, cc, group, group if group != "group" else "quintile")
    ax.set_ylabel("employment, 2022 = 100")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_index_panel(idx: pd.DataFrame, path, group: str = "group") -> None:
    """One panel per country plus the pooled series, shared y axis."""
    codes = sorted(c for c in idx["countrycode"].unique() if c != "ALL")
    if "ALL" in idx["countrycode"].values:
        codes.append("ALL")
    ncol = 3
    nrow = -(-len(codes) // ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.2 * ncol, 3.1 * nrow), sharey=True)
    for ax, cc in zip(axes.flat, codes):
        _draw_index(ax, idx, cc, group, "quintile")
    for ax in list(axes.flat)[len(codes) :]:
        ax.axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, fontsize=8, frameon=False)
    fig.text(0.01, 0.5, "employment, 2022 = 100", rotation=90, va="center", fontsize=9)
    fig.suptitle(
        "Employment by quintile of generative-AI exposure (ILO 2025 score), 2022 = 100",
        fontsize=11,
    )
    fig.tight_layout(rect=(0.02, 0.05, 1, 0.96))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    tables = OUTPUT / "tables"
    n = 0
    for f in sorted(tables.glob("event_study_*.csv")):
        outcome = f.stem.replace("event_study_", "")
        es = pd.read_csv(f)
        for subset, sub in es.groupby("subset"):
            plot_event_study(
                sub, f"{outcome}, {subset}", FIG / f"es_{outcome}_{subset}.png"
            )
            n += 1
    idx_path = tables / "employment_index.csv"
    if idx_path.exists():
        idx = pd.read_csv(idx_path)
        for cc in sorted(idx["countrycode"].unique()):
            plot_index(idx, cc, FIG / f"emp_index_{cc}.png")
            n += 1
    q5_path = tables / "employment_index_q5.csv"
    if q5_path.exists():
        q5 = pd.read_csv(q5_path)
        for cc in sorted(q5["countrycode"].unique()):
            plot_index(q5, cc, FIG / f"emp_index_q5_{cc}.png", group="group")
            n += 1
        plot_index_panel(q5, FIG / "emp_index_q5_panel.png")
        n += 1
    print(f"{n} figures -> {FIG}")


if __name__ == "__main__":
    main()
