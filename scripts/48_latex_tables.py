# ruff: noqa: E501
"""LaTeX floats for the paper: Tables 1 to 4 as ``\\input`` fragments.

    python scripts/48_latex_tables.py [--no-check]

Writes output/latex/tab_surveys.tex (Table 1), tab_country.tex (Table 2),
tab_robust.tex (Table 3) and tab_sector.tex (Table 4), plus the estimates
behind Tables 3 and 4 as output/tables/robust_log_emp.csv and
sector_did.csv and the sector cells as data/processed/cells/sector_cells.parquet.
Tables 1 and 2 read the panel database and the did_log_emp*.csv files from
41_event_study.py; Tables 3 and 4 are estimated here. Unless --no-check is
given, every fragment is compiled in a throwaway document with the paper's
packages and the four tables are saved together as output/latex/preview.pdf.
Copy the fragments to lfs-paper/tab_fig/<version>/ afterwards.
"""

from __future__ import annotations

import argparse
import sys
from typing import Dict, List, Optional, Sequence

import pandas as pd

from lfspanel.analysis import (
    CELLS_PATH,
    PRIMARY_TREAT,
    aggregate_cells,
    build_cells,
    cell_depth,
    estimate_did,
    event_study_frame,
    placebo_frame,
)
from lfspanel.config import OUTPUT
from lfspanel.exposure import load_exposure_table
from lfspanel.latex import (
    MIDRULE,
    coef_lines,
    compile_check,
    escape,
    int_fmt,
    panel,
    table_float,
    write_fragment,
)
from lfspanel.sector import (
    CONTROLS,
    SECTOR_CELLS_PATH,
    build_sector_cells,
    sector_frame,
)
from lfspanel.store import duckdb_connect

LATEX = OUTPUT / "latex"
TABLES = OUTPUT / "tables"
NAMES = {
    "BRA": "Brazil",
    "MEX": "Mexico",
    "COL": "Colombia",
    "ARG": "Argentina",
    "ECU": "Ecuador",
    "PER": "Peru",
    "URY": "Uruguay",
    "BOL": "Bolivia",
    "ZAF": "South Africa",
    "GEO": "Georgia",
    "PHL": "Philippines",
    "IND": "India",
    "NGA": "Nigeria",
}
SURVEY = {
    "BRA": "PNADC",
    "MEX": "ENOE",
    "COL": "GEIH",
    "ARG": "EPH",
    "ECU": "ENEMDU",
    "PER": "EPEN",
    "URY": "ECH",
    "BOL": "ECE",
    "ZAF": "QLFS",
    "GEO": "LFS",
    "PHL": "LFS",
    "IND": "PLFS",
    "NGA": "NLFS",
}
POOL = ["BRA", "MEX", "COL", "ARG", "ECU", "PER", "URY", "BOL", "ZAF", "GEO", "PHL"]
EXPORTERS = ["BRA", "COL", "PHL"]
IND_END = "2024Q4"
NOTE1 = {
    "ARG": "31 urban agglomerations only; CNO 2017 crosswalk reliable at two digits.",
    "MEX": "SINCO crosswalk reliable at two digits; tenure asked in first-interview quarters only.",
    "PHL": "PSOC published at two digits; expanded rounds alternate with regular rounds; 2025Q3 missing.",
    "BOL": "COB 2009 follows ISCO in its first four digits; a quarter of codes stop at two.",
    "URY": "Person-months (weight divided by three); tenure for first interviews only.",
    "GEO": "Small survey; 92 percent of three-digit cells fall under the floor.",
    "ZAF": "SASCO mapped through ISCO-88; the employment status question changed in 2025Q3.",
    "COL": "Starts at the 2022 redesign, so no 2021 pre-period.",
    "PER": "No tenure question; national file.",
    "BRA": "Reweighted in August 2025 to the 2022 Census; one vintage kept.",
    "IND": "Annex only: 2025 redesign; first visits only before 2025Q2; NCO-2004 codes in 2021H1.",
    "NGA": "Not in the estimates: no pre-period.",
}
STARS_NOTE = (
    r"Standard errors in parentheses, clustered by country $\times$ occupation; "
    r"$^{*}$ $p<0.10$, $^{**}$ $p<0.05$, $^{***}$ $p<0.01$ from the cluster-robust "
    r"$t$ statistic with $G-1$ degrees of freedom."
)
SPEC_NOTE = (
    r"Post $=1$ from 2023Q1 onward (reference 2022Q4). Cell fixed effects and "
    r"country $\times$ age group $\times$ sex $\times$ quarter fixed effects; "
    r"weights are mean 2022 cell employment."
)


def _did(frame: pd.DataFrame, treat: str = PRIMARY_TREAT) -> Dict[str, float]:
    """One triple-difference run as a flat record."""
    d = estimate_did(frame, treat=treat, triple=True).set_index("term")
    return {
        "coef": float(d.loc["post_x_treat", "coef"]),
        "se": float(d.loc["post_x_treat", "se"]),
        "coef_young": float(d.loc["post_x_treat_x_young", "coef"]),
        "se_young": float(d.loc["post_x_treat_x_young", "se"]),
        "n_cells": int(d["n_cells"].iloc[0]),
        "n_clusters": int(d["n_clusters"].iloc[0]),
    }


def _pick(
    did: pd.DataFrame, subset: str, term: str = "post_x_treat"
) -> Optional[pd.Series]:
    x = did[(did["subset"] == subset) & (did["term"] == term)]
    return x.iloc[0] if len(x) else None


# ------------------------------------------------------------------ Table 1
def table_surveys(con, cells_summary: pd.DataFrame) -> str:
    t1 = (
        con.execute(
            """
            SELECT countrycode, min(period) AS p_first, max(period) AS p_last,
                   count(DISTINCT period) AS nq,
                   count(*) / count(DISTINCT period) AS emp_per_q,
                   100 * sum(weight * CAST(occup_isco_digits >= 3 AS INT)) / sum(weight) AS pct_3d,
                   100 * sum(weight * CAST(tenure_lt12 IS NOT NULL AS INT)) / sum(weight) AS pct_tenure,
                   min(minlaborage) AS minage
            FROM employed WHERE source = 'own' GROUP BY 1
            """
        )
        .df()
        .set_index("countrycode")
    )
    cs = cells_summary.set_index("countrycode")
    rows: List[Sequence[str]] = []
    note_items: List[str] = []
    letters = iter("abcdefghijklmnopqrstuvwxyz")
    for cc in POOL + ["IND", "NGA"]:
        r = t1.loc[cc]
        c = cs.loc[cc]
        if r.pct_tenure >= 90:
            tenure = "yes"
        elif cc in ("MEX", "URY"):
            tenure = "first int."
        elif r.pct_tenure > 0:
            tenure = "partial"
        else:
            tenure = "no"
        name = NAMES[cc]
        if NOTE1.get(cc):
            letter = next(letters)
            name += f"$^{{{letter}}}$"
            note_items.append(f"$^{{{letter}}}$ {NOTE1[cc]}")
        rows.append(
            [
                name,
                SURVEY[cc],
                f"{r.p_first}--{r.p_last} ({int(r.nq)})",
                int_fmt(round(r.emp_per_q, -2)),
                f"{int(r.minage)}",
                f"{int(c.digits)}",
                f"{r.pct_3d:.0f}",
                f"{int(c.occupations)}",
                f"{100 * c.small_share:.0f}",
                tenure,
            ]
        )
        if cc == POOL[-1]:
            rows.append(MIDRULE)
    header = [
        [
            "Country",
            "Survey",
            "Quarters",
            "Employed",
            "Min.",
            "Cell",
            r"\% at 3+",
            "Occup.",
            r"\% cells",
            "Tenure",
        ],
        [
            "",
            "",
            "(number)",
            "per quarter",
            "age",
            "digits",
            "digits",
            "in cells",
            "under floor",
            "",
        ],
    ]
    notes = (
        "Quarters gives the first and last quarter in the panel and, in parentheses, the number of quarters. "
        "PNADC is Brazil's Pesquisa Nacional por Amostra de Domic\\'ilios Cont\\'inua. "
        "Employed per quarter is the unweighted count of employed persons in the harmonised file, rounded to hundreds. "
        "Cell digits is the ISCO-08 level of the analysis cells (three where at least 90 percent of employment resolves to three digits, else two); "
        r"\% at 3+ digits is the employment-weighted share of workers whose occupation code resolves to three or more digits. "
        "Occupations in cells and the share of cells under the 30-observation floor refer to the baseline year 2022. "
        "Tenure says whether the survey asks job tenure, which defines the new-hire share. "
        "India and Nigeria are outside the pooled estimates."
    )
    return table_float(
        "tab:surveys",
        "Surveys, windows, sample sizes and occupation depth",
        "lllrrrrrrl",
        header,
        rows,
        notes=notes,
        note_items=note_items,
        size=r"\scriptsize",
        tabcolsep="4pt",
    )


# ------------------------------------------------------------------ Table 2
def table_country(
    did: Dict[str, pd.DataFrame], india: Dict[str, Dict[str, float]]
) -> str:
    cuts = ["q5", "t3", "d10"]

    def coef_row(
        label: str, subset: str, term: str = "post_x_treat", counts: bool = True
    ):
        top, bottom = [label], [""]
        for k in cuts:
            x = _pick(did[k], subset, term)
            if x is None:
                top.append("")
                bottom.append("")
                continue
            a, b = coef_lines(x.coef, x.se, int(x.n_clusters))
            top.append(a)
            bottom.append(b)
        x = _pick(did["q5"], subset)
        if counts and x is not None:
            top += [int_fmt(x.n_cells), int_fmt(x.n_clusters)]
        else:
            top += ["", ""]
        bottom += ["", ""]
        return [top, bottom]

    rows: List[Sequence[str]] = []
    rows += coef_row(r"All cells, eleven countries ($\delta$)", "all")
    rows += coef_row(
        r"\quad Post $\times$ High $\times$ Young ($\theta$)",
        "all",
        "post_x_treat_x_young",
        counts=False,
    )
    rows += coef_row(r"\quad Young cells only (15--29)", "young")
    rows += coef_row(r"\quad Older cells only (30+)", "older")
    rows.append(MIDRULE)
    order = sorted(POOL, key=lambda c: -_pick(did["q5"], f"country_{c}").coef)
    for cc in order:
        rows += coef_row(NAMES[cc], f"country_{cc}")
    rows.append(MIDRULE)
    top, bottom = [f"India, annex (2021Q3--{IND_END})"], [""]
    for k in cuts:
        a, b = coef_lines(india[k]["coef"], india[k]["se"], india[k]["n_clusters"])
        top.append(a)
        bottom.append(b)
    top += [int_fmt(india["q5"]["n_cells"]), int_fmt(india["q5"]["n_clusters"])]
    bottom += ["", ""]
    rows += [top, bottom]
    header = [
        ["", r"\multicolumn{3}{c}{Treated group: top exposure}", "Cells", "Clusters"],
        ["", "quintile", "tercile", "decile", "", ""],
    ]
    notes = (
        r"Coefficient $\delta$ on Post $\times$ High in the log of cell employment, where High marks occupations in the top employment-weighted quintile (primary), tercile or decile of the ILO generative-AI exposure score. "
        + SPEC_NOTE
        + " "
        + r"The all-cells row is the triple-difference specification, so its $\delta$ is the effect for older cells and $\theta$ the additional effect for young cells; the young-only and older-only rows re-estimate the model within each age range. "
        r"Country rows re-estimate the model within the country, sorted by the quintile estimate. Cells and clusters refer to the quintile run; the tercile and decile runs use the same cells. "
        r"India is estimated separately on its urban sample to 2024Q4, before the PLFS redesign. "
        + STARS_NOTE
    )
    return table_float(
        "tab:country",
        r"Post $\times$ high exposure and log employment: three treatment cuts",
        "lcccrr",
        header,
        rows,
        notes=notes,
        header_rules=[r"\cmidrule(lr){2-4}"],
        tabcolsep="5pt",
    )


# ------------------------------------------------------------------ Table 3
def robustness_estimates(
    con, cells: pd.DataFrame, exposure: pd.DataFrame
) -> pd.DataFrame:
    """Every row of Table 3 as a record: label, group, estimates and counts."""
    base_cells = cells[cells["countrycode"].isin(POOL)]
    frame = event_study_frame(base_cells, exposure)
    records: List[Dict[str, object]] = []

    def add(
        group: str, label: str, fr: pd.DataFrame, treat: str = PRIMARY_TREAT
    ) -> None:
        rec = {"group": group, "label": label, "treat": treat}
        rec.update(_did(fr, treat))
        records.append(rec)
        print(
            f"  {group:12s} {label:48s} {rec['coef']:+.4f} ({rec['se']:.4f})  cells={rec['n_cells']:,} G={rec['n_clusters']}"
        )

    print("Table 3: treatment definition")
    add("treatment", "Top quintile (baseline)", frame)
    add("treatment", "Top tercile", frame, "high")
    add("treatment", "Top decile", frame, "high_d10")
    sd = float(frame.drop_duplicates("cell")["score_w"].std())
    cont = frame.assign(score_sd=frame["score_w"] / sd)
    add("treatment", "Continuous score (per standard deviation)", cont, "score_sd")

    print("Table 3: cells and sample")
    two = event_study_frame(aggregate_cells(base_cells, 2), exposure)
    add("sample", "Two-digit cells for every country", two)
    add(
        "sample",
        "Cells under 30 observations kept",
        event_study_frame(base_cells, exposure, drop_small=False),
    )
    depth = {cc: d for cc, d in cell_depth(con).items() if cc in POOL}
    urban = build_cells(con, depth, where="e.urban = 1")
    add("sample", "Urban areas only", event_study_frame(urban, exposure))
    formal = build_cells(con, depth, where="e.socialsec = 1")
    formal_frame = event_study_frame(formal, exposure)
    formal_ccs = sorted(formal_frame["countrycode"].unique())
    add("sample", "Social-security contributors only", formal_frame)
    records[-1]["countries"] = ",".join(formal_ccs)
    add("sample", "Placebo: 2022 against 2021, pre-period only", placebo_frame(frame))

    print("Table 3: leave one country out")
    for cc in POOL:
        add("loo", f"Without {NAMES[cc]}", frame[frame["countrycode"] != cc])
    return pd.DataFrame(records)


def table_robust(rob: pd.DataFrame) -> str:
    rows: List[Sequence[str]] = []
    titles = {
        "treatment": "Panel A. Treatment definition",
        "sample": "Panel B. Cells and sample",
        "loo": "Panel C. Leaving one country out",
    }
    for group, title in titles.items():
        rows.append(panel(title))
        for _, r in rob[rob["group"] == group].iterrows():
            a, b = coef_lines(r.coef, r.se, int(r.n_clusters))
            c, d = coef_lines(r.coef_young, r.se_young, int(r.n_clusters))
            rows.append(
                [escape(r.label), a, c, int_fmt(r.n_cells), int_fmt(r.n_clusters)]
            )
            rows.append(["", b, d, "", ""])
    formal = rob[rob["label"].str.startswith("Social-security")]
    formal_ccs = formal["countries"].iloc[0].split(",") if len(formal) else []
    header = [
        [
            "",
            r"Post $\times$ High",
            r"Post $\times$ High $\times$ Young",
            "Cells",
            "Clusters",
        ],
        ["", r"($\delta$)", r"($\theta$)", "", ""],
    ]
    notes = (
        r"Each row is one triple-difference regression of log cell employment on the eleven-country pooled sample (Table~\ref{tab:country}, first row, is the baseline). "
        + SPEC_NOTE
        + " "
        r"The continuous row replaces the High dummy with the employment-weighted exposure score divided by its standard deviation across cells. "
        r"Two-digit cells re-aggregate the three-digit cells of the countries coded at three digits. "
        r"The urban and social-security rows rebuild the cells on the restricted sample and reapply the 2022 floor of 30 observations"
        + (
            "; social-security status is observed in "
            + ", ".join(NAMES[c] for c in formal_ccs)
            + ". "
            if formal_ccs
            else ". "
        )
        + r"The placebo keeps the quarters up to 2022Q4 and treats 2022 as the post period against 2021 (Colombia has no 2021 quarters and drops out). "
        + STARS_NOTE
    )
    return table_float(
        "tab:robust",
        "Robustness of the pooled estimate, log employment",
        "lccrr",
        header,
        rows,
        notes=notes,
        size=r"\scriptsize",
        tabcolsep="5pt",
    )


# ------------------------------------------------------------------ Table 4
OUTCOMES = [
    ("log_emp", ("Log", "employment")),
    ("young_share", ("Share", "aged 15--29")),
    ("u25_share", ("Share", "under 25")),
    ("cler_share", ("Clerical and", "service share")),
    ("log_cler_emp", ("Log clerical and", "service employment")),
]


def sector_estimates(scells: pd.DataFrame) -> pd.DataFrame:
    records: List[Dict[str, object]] = []

    def add(
        group: str, label: str, sub: pd.DataFrame, controls: Sequence[str] = CONTROLS
    ) -> None:
        fr = sector_frame(sub, controls=controls)
        rec: Dict[str, object] = {
            "group": group,
            "label": label,
            "controls": "+".join(controls),
        }
        for outcome, _ in OUTCOMES:
            d = estimate_did(fr, outcome=outcome, treat="treated").iloc[0]
            rec[f"{outcome}_coef"] = float(d.coef)
            rec[f"{outcome}_se"] = float(d.se)
            rec[f"{outcome}_n_cells"] = int(d.n_cells)
            rec[f"{outcome}_n_clusters"] = int(d.n_clusters)
        records.append(rec)
        print(
            f"  {label:52s} log_emp {rec['log_emp_coef']:+.3f} ({rec['log_emp_se']:.3f})  young {rec['young_share_coef']:+.4f} ({rec['young_share_se']:.4f})  G={rec['log_emp_n_clusters']}"
        )

    print("Table 4: sector difference in differences")
    pool = scells[scells["countrycode"].isin(POOL)]
    add("sample", "Eleven countries", pool)
    ind = scells[(scells["countrycode"] == "IND") & (scells["period"] <= IND_END)]
    add("sample", f"Eleven countries plus India (to {IND_END})", pd.concat([pool, ind]))
    add(
        "sample",
        "Without South Africa and Mexico",
        pool[~pool["countrycode"].isin(["ZAF", "MEX"])],
    )
    add("controls", "Finance and insurance only", pool, ("finance",))
    add("controls", "Professional and technical services only", pool, ("profserv",))
    add("controls", "Public administration only", pool, ("pubadmin",))
    add(
        "exporters",
        "Brazil, Colombia and the Philippines",
        pool[pool["countrycode"].isin(EXPORTERS)],
    )
    add(
        "exporters", "Other eight countries", pool[~pool["countrycode"].isin(EXPORTERS)]
    )
    return pd.DataFrame(records)


def table_sector(sec: pd.DataFrame) -> str:
    rows: List[Sequence[str]] = []
    titles = {
        "sample": "Panel A. Sample (controls: finance, professional services, public administration)",
        "controls": "Panel B. Control industries (eleven countries)",
        "exporters": "Panel C. Exporters and others",
    }
    for group, title in titles.items():
        rows.append(panel(title))
        for _, r in sec[sec["group"] == group].iterrows():
            top, bottom = [escape(r.label)], [""]
            for outcome, _ in OUTCOMES:
                digits = 3 if outcome.startswith("log") else 4
                a, b = coef_lines(
                    r[f"{outcome}_coef"],
                    r[f"{outcome}_se"],
                    int(r[f"{outcome}_n_clusters"]),
                    digits,
                )
                top.append(a)
                bottom.append(b)
            top += [int_fmt(r["log_emp_n_cells"]), int_fmt(r["log_emp_n_clusters"])]
            bottom += ["", ""]
            rows += [top, bottom]
    header = [
        [""] + [top for _, (top, _) in OUTCOMES] + ["Cells", "Clusters"],
        [""] + [bottom for _, (_, bottom) in OUTCOMES] + ["", ""],
    ]
    notes = (
        r"Coefficient on Post $\times$ IT-BPO in sector cells (country $\times$ quarter $\times$ industry group $\times$ sex). "
        r"The treated group is IT and business-process services, ISIC Rev.\ 4 divisions 62, 63 and 82 (South Africa 62 only; Mexico ENOE code 5611); controls are finance and insurance (64--66), professional, scientific and technical services (69--75) and public administration (84). "
        r"Shares are weighted fractions of the cell's employment; clerical and service occupations are ISCO-08 major groups 4 and 5. "
        r"Post $=1$ from 2023Q1 onward. Cell fixed effects and country $\times$ sex $\times$ quarter fixed effects; weights are mean 2022 cell employment; cells enter when their mean unweighted 2022 count reaches 30. "
        r"Cells and clusters refer to the log employment column; standard errors are clustered by country $\times$ industry group. "
        r"$^{*}$ $p<0.10$, $^{**}$ $p<0.05$, $^{***}$ $p<0.01$ from the cluster-robust $t$ statistic with $G-1$ degrees of freedom."
    )
    return table_float(
        "tab:sector",
        "IT and business-process services against other white-collar services: sector difference in differences",
        "lcccccrr",
        header,
        rows,
        notes=notes,
        size=r"\scriptsize",
        landscape=True,
    )


# ------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--no-check", action="store_true", help="skip the pdflatex compile check"
    )
    args = ap.parse_args()
    LATEX.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    cells = pd.read_parquet(CELLS_PATH)
    exposure = load_exposure_table()
    cells_summary = pd.read_csv(TABLES / "cells_summary.csv")
    did = {
        k: pd.read_csv(TABLES / f)
        for k, f in [
            ("q5", "did_log_emp.csv"),
            ("t3", "did_log_emp_high.csv"),
            ("d10", "did_log_emp_high_d10.csv"),
        ]
    }
    con = duckdb_connect(read_only=True)
    try:
        print("Table 1")
        tab1 = table_surveys(con, cells_summary)

        print("Table 2: India re-estimated")
        ind_cells = cells[
            (cells["countrycode"] == "IND") & (cells["period"] <= IND_END)
        ]
        ind_frame = event_study_frame(ind_cells, exposure)
        india = {
            k: _did(ind_frame, t)
            for k, t in [("q5", "high_q5"), ("t3", "high"), ("d10", "high_d10")]
        }
        for k, v in india.items():
            print(f"  India {k}: {v['coef']:+.4f} ({v['se']:.4f}) G={v['n_clusters']}")
        tab2 = table_country(did, india)

        rob = robustness_estimates(con, cells, exposure)
        rob.to_csv(TABLES / "robust_log_emp.csv", index=False)
        tab3 = table_robust(rob)

        scells = build_sector_cells(con)
        SECTOR_CELLS_PATH.parent.mkdir(parents=True, exist_ok=True)
        scells.to_parquet(SECTOR_CELLS_PATH, index=False)
        summary = (
            scells.groupby(["countrycode", "sector"])
            .agg(
                quarters=("period", "nunique"),
                n_mean=("n", "mean"),
                small_share=("small", "mean"),
            )
            .reset_index()
        )
        summary.round(3).to_csv(TABLES / "sector_cells_summary.csv", index=False)
    finally:
        con.close()
    sec = sector_estimates(scells)
    sec.to_csv(TABLES / "sector_did.csv", index=False)
    tab4 = table_sector(sec)

    paths = [
        write_fragment(LATEX / "tab_surveys.tex", tab1),
        write_fragment(LATEX / "tab_country.tex", tab2),
        write_fragment(LATEX / "tab_robust.tex", tab3),
        write_fragment(LATEX / "tab_sector.tex", tab4),
    ]
    for p in paths:
        print(f"wrote {p}")
    if args.no_check:
        return
    try:
        ok, messages = compile_check(paths, pdf_out=LATEX / "preview.pdf")
    except RuntimeError as exc:
        print(f"compile check skipped: {exc}")
        return
    for m in messages:
        print("  " + m)
    print("compile check:", "ok" if ok else "FAILED")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
