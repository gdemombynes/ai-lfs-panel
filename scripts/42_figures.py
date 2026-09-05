"""Event-study and employment-index figures.

    python scripts/42_figures.py

Reads output/tables/event_study_*.csv and employment_index.csv, writes
output/figures/es_<outcome>_<subset>.png and emp_index_<country>.png.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from lfspanel.config import OUTPUT  # noqa: E402

FIG = OUTPUT / "figures"


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


def plot_index(idx: pd.DataFrame, cc: str, path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    for terc, sub in idx[idx["countrycode"] == cc].groupby("tercile"):
        sub = sub.sort_values("period")
        ax.plot(
            sub["period"], sub["index"], marker="o", ms=3, label=f"tercile {int(terc)}"
        )
    ax.axhline(100, color="grey", lw=0.8)
    ax.set_xticks(range(len(sub)))
    ax.set_xticklabels(sub["period"], rotation=90, fontsize=7)
    ax.set_ylabel("employment, 2022 = 100")
    ax.set_title(f"{cc}: employment by GenAI exposure tercile", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
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
    print(f"{n} figures -> {FIG}")


if __name__ == "__main__":
    main()
