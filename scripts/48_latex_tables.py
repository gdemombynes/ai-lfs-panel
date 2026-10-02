# ruff: noqa: E501
"""LaTeX floats for the paper: Tables 1 to 4 as ``\\input`` fragments.

    python scripts/48_latex_tables.py [--no-check]

Writes output/latex/tab_surveys.tex (Table 1), tab_country.tex (Table 2),
tab_newhire.tex (Table 3), tab_robust.tex (Table 4), tab_sector.tex (Table 5)
and figures.tex (every
figure float, images referenced as \\tabfig/<file> and copied from
output/figures/ next to it), plus the estimates
behind Tables 3 and 4 as output/tables/robust_log_emp.csv and
sector_did.csv and the sector cells as data/processed/cells/sector_cells.parquet.
Table 1 reads the panel database; Tables 2, 3 and 4 are estimated here (Table
2's runs go to output/tables/country_log_emp.csv). Unless --no-check is
given, every fragment is compiled in a throwaway document with the paper's
packages and the four tables are saved together as output/latex/preview.pdf.
Copy the fragments to lfs-paper/tab_fig/<version>/ afterwards.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from typing import Dict, List, Sequence, Tuple

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
    figure_float,
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
FIGURES = OUTPUT / "figures"
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
        "coef_young_total": float(d.loc["post_x_treat_young", "coef"]),
        "se_young_total": float(d.loc["post_x_treat_young", "se"]),
        "n_cells": int(d["n_cells"].iloc[0]),
        "n_clusters": int(d["n_clusters"].iloc[0]),
    }


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
def country_estimates(cells: pd.DataFrame, exposure: pd.DataFrame) -> pd.DataFrame:
    """Triple-difference runs for the pooled sample, each country and India."""
    pool = event_study_frame(cells[cells["countrycode"].isin(POOL)], exposure)
    records: List[Dict[str, object]] = []

    def add(subset: str, fr: pd.DataFrame) -> None:
        rec: Dict[str, object] = {"subset": subset}
        rec.update(_did(fr))
        # share of cell employment in top-quintile occupations, 2025 (or the
        # last year observed when 2025 is absent, as for India)
        years = fr["period"].str[:4]
        year = "2025" if (years == "2025").any() else years.max()
        yr = fr[years == year]
        rec["share_year"] = year
        rec["share_high"] = float(
            (yr["emp"] * yr[PRIMARY_TREAT]).sum() / yr["emp"].sum()
        )
        records.append(rec)
        print(
            f"  {subset:12s} delta {rec['coef']:+.4f} ({rec['se']:.4f})  "
            f"theta {rec['coef_young']:+.4f} ({rec['se_young']:.4f})  "
            f"young {rec['coef_young_total']:+.4f} ({rec['se_young_total']:.4f})  "
            f"G={rec['n_clusters']}"
        )

    print("Table 2: pooled and by country")
    add("all", pool)
    for cc in POOL:
        add(f"country_{cc}", pool[pool["countrycode"] == cc])
    ind = cells[(cells["countrycode"] == "IND") & (cells["period"] <= IND_END)]
    add("country_IND", event_study_frame(ind, exposure))
    return pd.DataFrame(records)


def table_country(est: pd.DataFrame) -> str:
    e = est.set_index("subset")

    def line(label: str, r: pd.Series, which: str, counts: bool) -> List[str]:
        coef, se = r[f"coef{which}"], r[f"se{which}"]
        top, bottom = coef_lines(coef, se, int(r["n_clusters"]))
        cell = f"{top} {bottom}" if top else "n.a."
        if counts:
            share = f"{100 * r['share_high']:.1f}"
            if r["share_year"] != "2025":
                share += "$^{\\dagger}$"
            return [
                label,
                cell,
                share,
                int_fmt(r["n_cells"]),
                int_fmt(r["n_clusters"]),
            ]
        return [label, cell, "", "", ""]

    rows: List[Sequence[str]] = []
    rows.append(panel("Pooled, eleven countries"))
    r = e.loc["all"]
    rows.append(line(r"Post $\times$ High exposure ($\delta$)", r, "", True))
    rows.append(
        line(
            r"Post $\times$ High exposure $\times$ Young ($\theta$)", r, "_young", False
        )
    )
    rows.append(
        line(
            r"Post $\times$ High exposure, young cells ($\delta + \theta$)",
            r,
            "_young_total",
            False,
        )
    )
    rows.append(panel(r"By country, sorted by $\delta$"))
    order = sorted(POOL, key=lambda c: -e.loc[f"country_{c}", "coef"])
    for cc in order:
        r = e.loc[f"country_{cc}"]
        rows.append(line(NAMES[cc] + r" ($\delta$)", r, "", True))
        rows.append(
            line(r"\quad young cells ($\delta + \theta$)", r, "_young_total", False)
        )
    rows.append(panel("Annex"))
    r = e.loc["country_IND"]
    rows.append(line(f"India, 2021Q3--{IND_END} ($\\delta$)", r, "", True))
    rows.append(
        line(r"\quad young cells ($\delta + \theta$)", r, "_young_total", False)
    )
    header = [
        ["", "Coefficient (SE)", "Exposed share", "Cells", "Clusters"],
        ["", "", r"of 2025 emp., \%", "", ""],
    ]
    other_year = sorted(
        {r["share_year"] for _, r in e.iterrows() if r["share_year"] != "2025"}
    )
    dagger = (
        r"$^{\dagger}$ " + " and ".join(other_year) + ", the last year observed. "
        if other_year
        else ""
    )
    missing = [
        NAMES[s.replace("country_", "")]
        for s, r in e.iterrows()
        if s.startswith("country_") and pd.isna(r["coef_young_total"])
    ]
    not_identified = (
        "n.a.: no young cell reaches the 2022 floor in "
        + ", ".join(missing)
        + r", so $\theta$ and $\delta + \theta$ are not identified there. "
        if missing
        else ""
    )
    notes = (
        r"Each block is one triple-difference regression of log cell employment: "
        r"$y_{it} = \delta\,\text{Post}_t \times \text{High}_{o} + \theta\,\text{Post}_t \times \text{High}_{o} \times \text{Young}_{a} + \alpha_i + \gamma_{c,a,s,t} + \varepsilon_{it}$, "
        r"where High marks occupations in the top employment-weighted quintile of the ILO generative-AI exposure score at the country's ISCO digit level and Young marks cells aged 15 to 29. "
        r"$\delta$ is the post-period effect for cells aged 30 and over, $\theta$ the additional effect for young cells and $\delta + \theta$ the effect for young cells, with its standard error from the same regression re-parameterised with separate older and young treatment dummies. "
        + SPEC_NOTE
        + " "
        r"Country blocks re-estimate the model within the country. "
        r"Exposed share is the share of the sample's 2025 cell employment in top-quintile occupations. "
        + dagger
        + r"India is estimated on its urban sample to 2024Q4, before the PLFS redesign, and is not in the pooled sample. "
        + not_identified
        + STARS_NOTE
    )
    return table_float(
        "tab:country",
        r"Post $\times$ high exposure and log employment, pooled and by country",
        "lcrrr",
        header,
        rows,
        notes=notes,
        size=r"\footnotesize",
        tabcolsep="5pt",
    )


# ------------------------------------------------------------------ Table 3
def newhire_estimates(cells: pd.DataFrame, exposure: pd.DataFrame) -> pd.DataFrame:
    """Plain difference in differences on the new-hire share, pooled and by country."""
    frame = event_study_frame(cells[cells["countrycode"].isin(POOL)], exposure)
    frame = frame[frame["new_hire_share"].notna()]
    records: List[Dict[str, object]] = []

    def add(subset: str, fr: pd.DataFrame) -> None:
        if len(fr) < 100:
            return
        d = estimate_did(fr, outcome="new_hire_share").iloc[0]
        base = fr[fr["period"].str.startswith("2022")]
        share = float(
            (base["new_hire_share"] * base["emp_base"]).sum() / base["emp_base"].sum()
        )
        rec = {
            "subset": subset,
            "coef": float(d.coef),
            "se": float(d.se),
            "share_2022": share,
            "n_cells": int(d.n_cells),
            "n_clusters": int(d.n_clusters),
        }
        records.append(rec)
        print(
            f"  {subset:12s} delta {rec['coef']:+.4f} ({rec['se']:.4f})  "
            f"2022 share {100 * share:.1f}%  G={rec['n_clusters']}"
        )

    print("Table 3: new-hire share, all cells")
    add("all", frame)
    for cc in POOL:
        add(f"country_{cc}", frame[frame["countrycode"] == cc])
    return pd.DataFrame(records)


def table_newhire(est: pd.DataFrame) -> str:
    e = est.set_index("subset")

    def line(label: str, r: pd.Series) -> List[str]:
        top, bottom = coef_lines(r["coef"], r["se"], int(r["n_clusters"]), 4)
        return [
            label,
            f"{top} {bottom}",
            f"{100 * r['share_2022']:.1f}",
            int_fmt(r["n_cells"]),
            int_fmt(r["n_clusters"]),
        ]

    countries = [c for c in POOL if f"country_{c}" in e.index]
    rows: List[Sequence[str]] = []
    rows.append(panel(f"Pooled, {len(countries)} countries with a tenure question"))
    rows.append(line(r"Post $\times$ High exposure ($\delta$)", e.loc["all"]))
    rows.append(panel(r"By country, sorted by $\delta$"))
    for cc in sorted(countries, key=lambda c: -e.loc[f"country_{c}", "coef"]):
        rows.append(line(NAMES[cc], e.loc[f"country_{cc}"]))
    header = [
        ["", "Coefficient (SE)", "New-hire share", "Cells", "Clusters"],
        ["", "", r"2022, \%", "", ""],
    ]
    names = ", ".join(NAMES[c] for c in countries)
    notes = (
        r"Difference in differences on the cell's new-hire share, the weighted fraction of its employed persons who started their current job within the previous twelve months, in share points (multiply by 100 for percentage points): "
        r"$s_{it} = \delta\,\text{Post}_t \times \text{High}_{o} + \alpha_i + \gamma_{c,a,s,t} + \varepsilon_{it}$, "
        r"where High marks occupations in the top employment-weighted quintile of the ILO generative-AI exposure score at the country's ISCO digit level. "
        + SPEC_NOTE
        + " "
        + f"Sample: {names}, the countries whose survey asks job tenure; Uruguay asks it at first interviews only and Mexico in first-interview quarters only, so their shares rest on part of each cell. "
        r"Country rows re-estimate the model within the country. New-hire share 2022 is the employment-weighted mean of the outcome over the sample's 2022 cell-quarters. "
        + STARS_NOTE
    )
    return table_float(
        "tab:newhire",
        r"Post $\times$ high exposure and the new-hire share, all cells",
        "lcrrr",
        header,
        rows,
        notes=notes,
        tabcolsep="5pt",
    )


# ------------------------------------------------------------------ Table 4
def robustness_estimates(
    con, cells: pd.DataFrame, exposure: pd.DataFrame
) -> pd.DataFrame:
    """Every row of Table 4 as a record: label, group, estimates and counts."""
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

    print("Table 4: treatment definition")
    add("treatment", "Top quintile (baseline)", frame)
    add("treatment", "Top tercile", frame, "high")
    add("treatment", "Top decile", frame, "high_d10")
    sd = float(frame.drop_duplicates("cell")["score_w"].std())
    cont = frame.assign(score_sd=frame["score_w"] / sd)
    add("treatment", "Continuous score (per standard deviation)", cont, "score_sd")

    print("Table 4: cells and sample")
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

    print("Table 4: leave one country out")
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


# ------------------------------------------------------------------ Table 5
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

    print("Table 5: sector difference in differences")
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


# ------------------------------------------------------------------ Figures
ES_NOTE = (
    r"Coefficients $\beta_k$ on 1[quarter $= k$] $\times$ High (top exposure quintile) with 95 percent confidence bands; "
    r"reference 2022Q4 (dashed line). Cell fixed effects and country $\times$ age group $\times$ sex $\times$ quarter fixed effects; "
    r"weights are mean 2022 cell employment; standard errors clustered by country $\times$ occupation."
)
FIGURES_SPEC = [
    dict(
        label="fig:es_pooled",
        caption="Event-study coefficients, log cell employment, eleven countries pooled",
        panels=[
            ("es_log_emp_all.png", "All cells"),
            ("es_log_emp_young.png", "Cells aged 15--29"),
        ],
        width=r"0.49\textwidth",
        per_row=2,
        notes=ES_NOTE
        + " 2021 quarters cover the countries observed then (Brazil, Mexico, Argentina, Bolivia, Georgia and the Philippines from 2021Q1; Ecuador and Uruguay from 2021Q3); 2026 quarters cover the countries already released.",
    ),
    dict(
        label="fig:index",
        caption="Employment by quintile of generative-AI exposure, 2022 $=$ 100, by country and pooled",
        panels=[("emp_index_q5_panel.png", None)],
        width=r"0.92\textwidth",
        notes=r"Employment summed over all cells in the quintile, divided by its 2022 mean. Quintiles are employment-weighted at the 2022 baseline and defined at each country's cell digit level; quintile 5 is the most exposed. The pooled series is the employment-weighted mean of the country indices over the countries observed in each quarter. Bolivia and Georgia have few cells and noisy indices.",
    ),
    dict(
        label="fig:newhire",
        caption="Event-study coefficients, new-hire share",
        panels=[
            ("es_new_hire_share_young.png", "Cells aged 15--29"),
            ("es_new_hire_share_all.png", "All cells"),
        ],
        width=r"0.49\textwidth",
        per_row=2,
        notes=r"Outcome: weighted share of employed persons in the cell who started their current job within the previous twelve months, in share points. Seven countries with a tenure question: Brazil, Colombia, Ecuador, Argentina, South Africa (all quarters), Uruguay (first interviews) and Mexico (first-interview quarters). "
        + ES_NOTE,
    ),
    dict(
        label="fig:newhire_country",
        caption="New-hire share event study by country",
        panels=[
            ("es_new_hire_share_panel_country_young.png", "Cells aged 15--29"),
            ("es_new_hire_share_panel_country.png", "All cells"),
        ],
        width=r"\textwidth",
        per_row=1,
        notes=r"Each panel re-estimates the model within the country; 95 percent bands. South Africa has 8 clusters and Argentina 13, so their bands are wide.",
    ),
    dict(
        label="fig:youthshare",
        caption="IT and business-process services: employment and under-25 share, annual averages",
        panels=[("itbpo_by_country.png", None)],
        width=r"\textwidth",
        notes=r"Sector $=$ ISIC Rev.\ 4 divisions 62 (computer programming and consultancy), 63 (information services) and 82 (office and business support, including call centres); South Africa 62 only; Mexico ENOE code 5611. Top row: employment in the sector, in its clerical and service occupations (ISCO 4 and 5) and in the whole economy, indexed to 2022. Bottom row: under-25 share of sector employment against the economy-wide share. Annual averages of quarters; the latest year may be partial. Bolivia (290 sector workers in 2022) and Georgia (92) are too small for the share to be reliable.",
    ),
    dict(
        label="fig:itbpo_quarterly",
        caption="IT and business-process services, quarterly, countries with sufficient sector sample",
        panels=[("itbpo_quarterly.png", None)],
        width=r"\textwidth",
        notes=r"Brazil, Colombia, the Philippines, India and Uruguay, and a pooled series over Brazil, Colombia, the Philippines and Uruguay for quarters where all four are observed (India is left out of the pool: its block is four times the others combined and its sample design changes in 2025). Dashed line at 2022Q4. India before 2025Q2 is first-visit records only.",
    ),
    dict(
        label="fig:phl",
        caption="Philippines: the harmonised LFS against recent official and industry tabulations",
        panels=[("phl_sector_leading.png", None)],
        width=r"\textwidth",
        notes=r"Left: PSA OpenSTAT monthly employment by industry section (J information and communication; N administrative and support, which contains call centres) against the same sections in the harmonised LFS. Centre: the ISIC 62, 63 and 82 block from the harmonised LFS against IBPAP's end-year full-time headcount for the IT-BPM industry (2021 to 2025; 2026 and 2027 forecasts hollow). Right: the under-25 share of the block by quarter.",
    ),
    dict(
        label="fig:split",
        caption="Occupation split within IT and business-process services, 2022 $=$ 100",
        panels=[("itbpo_occupation_split.png", None)],
        width=r"\textwidth",
        notes=r"Within the sector, employment in professional and technical occupations (ISCO major groups 1 to 3) and in clerical and service occupations (major groups 4 and 5), indexed to the 2022 annual average, against all employment. 2026 covers one or two quarters.",
    ),
    dict(
        label="fig:es_country",
        caption="Event-study coefficients, log cell employment, by country",
        panels=[
            ("es_log_emp_panel_country.png", "All cells"),
            ("es_log_emp_panel_country_young.png", "Cells aged 15--29"),
        ],
        width=r"\textwidth",
        per_row=1,
        notes=r"Each panel re-estimates the model within the country; 95 percent bands. "
        + ES_NOTE,
    ),
    dict(
        label="fig:india",
        caption="India (annex): event-study coefficients, log cell employment, urban sample, 2021Q3 to 2024Q4",
        panels=[
            ("es_log_emp_IND_to2024Q4_all.png", "All cells"),
            ("es_log_emp_IND_to2024Q4_young.png", "Cells aged 15--29"),
        ],
        width=r"0.49\textwidth",
        per_row=2,
        notes=r"PLFS urban first-visit records, three-digit cells; the series stops before the 2025 redesign. "
        + ES_NOTE,
    ),
]


def figures_fragment() -> Tuple[str, List[str]]:
    """All figure floats in one file, and the image files they reference."""
    parts = [
        "% Figures for the paper, generated by scripts/48_latex_tables.py.\n"
        "% Images are referenced as \\tabfig/<file>; copy the PNG files next to this file.\n"
    ]
    used: List[str] = []
    for spec in FIGURES_SPEC:
        spec = dict(spec)
        used += [name for name, _ in spec["panels"]]
        parts.append(figure_float(**spec))
    return "\n".join(parts), used


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
    con = duckdb_connect(read_only=True)
    try:
        print("Table 1")
        tab1 = table_surveys(con, cells_summary)

        est = country_estimates(cells, exposure)
        est.to_csv(TABLES / "country_log_emp.csv", index=False)
        tab2 = table_country(est)

        nh = newhire_estimates(cells, exposure)
        nh.to_csv(TABLES / "country_new_hire_share.csv", index=False)
        tab3 = table_newhire(nh)

        rob = robustness_estimates(con, cells, exposure)
        rob.to_csv(TABLES / "robust_log_emp.csv", index=False)
        tab4 = table_robust(rob)

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
    tab5 = table_sector(sec)

    figs, used = figures_fragment()
    for name in used:
        shutil.copyfile(FIGURES / name, LATEX / name)
    paths = [
        write_fragment(LATEX / "tab_surveys.tex", tab1),
        write_fragment(LATEX / "tab_country.tex", tab2),
        write_fragment(LATEX / "tab_newhire.tex", tab3),
        write_fragment(LATEX / "tab_robust.tex", tab4),
        write_fragment(LATEX / "tab_sector.tex", tab5),
        write_fragment(LATEX / "figures.tex", figs),
    ]
    for p in paths:
        print(f"wrote {p}")
    print(f"copied {len(used)} figure files to {LATEX}")
    if args.no_check:
        return
    try:
        ok, messages = compile_check(
            paths,
            pdf_out=LATEX / "preview.pdf",
            preamble=rf"\newcommand{{\tabfig}}{{{LATEX}}}",
        )
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
