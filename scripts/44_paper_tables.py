# ruff: noqa: E501
import duckdb
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

R = "/Users/gabriel/Projects/ai-lfs-panel/"
T = R + "output/tables/"
F = R + "output/figures/"

# ------------------------------------------------------------------ data
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
    "ALL": "Pooled",
}
SURVEY = {
    "BRA": "PNAD Contínua",
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
NOTE1 = {
    "ARG": "31 urban agglomerations only; CNO 2017 crosswalk at 2 digits",
    "MEX": "SINCO crosswalk reliable at 2 digits; tenure asked in first quarters only",
    "PHL": "PSOC published at 2 digits; alternate expanded rounds; 2025Q3 missing",
    "BOL": "COB 2009 first four digits follow ISCO; a quarter of codes stop at 2",
    "URY": "Person-months (weight/3); tenure for first interviews only",
    "GEO": "Small survey; 92 % of 3-digit cells under the floor",
    "ZAF": "SASCO via ISCO-88; status question changed 2025Q3",
    "COL": "Starts at the 2022 redesign, no 2021 pre-period",
    "PER": "No tenure; national file only",
    "ECU": "",
    "BRA": "Reweighted Aug 2025 (Census 2022), one vintage kept",
    "IND": "Annex only: 2025 redesign, first visits only before 2025Q2, NCO-2004 in 2021H1",
    "NGA": "Not in estimates: no pre-period",
}

con = duckdb.connect(R + "data/processed/panel.duckdb", read_only=True)
t1 = (
    con.execute("""
select countrycode, min(period) p_first, max(period) p_last, count(distinct period) nq,
  count(*)/count(distinct period) emp_per_q,
  100*sum(weight*cast(occup_isco_digits>=3 as int))/sum(weight) pct_3d,
  100*sum(weight*cast(tenure_lt12 is not null as int))/sum(weight) pct_tenure,
  min(minlaborage) minage
from employed where source='own' group by 1""")
    .df()
    .set_index("countrycode")
)
con.close()
cs = pd.read_csv(T + "cells_summary.csv").set_index("countrycode")

did = {
    k: pd.read_csv(T + f).set_index("subset")
    for k, f in [
        ("q5", "did_log_emp.csv"),
        ("t3", "did_log_emp_high.csv"),
        ("d10", "did_log_emp_high_d10.csv"),
    ]
}
did_ind = pd.read_csv(T + "did_log_emp_IND_to2024Q4.csv").set_index("subset")
es_emp = pd.read_csv(T + "event_study_log_emp.csv")
es_nh = pd.read_csv(T + "event_study_new_hire_share.csv")
did_nh = pd.read_csv(T + "did_new_hire_share.csv").set_index("subset")
q5 = pd.read_csv(T + "employment_index_q5.csv")
sec = pd.read_csv(T + "itbpo_by_country.csv")

# ------------------------------------------------------------------ docx helpers
doc = Document()
sec0 = doc.sections[0]
sec0.page_width, sec0.page_height = Inches(8.5), Inches(11)
for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec0, m, Inches(0.9))
st = doc.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(10.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
for lvl, size in ((1, 14), (2, 12)):
    h = doc.styles[f"Heading {lvl}"]
    h.font.name = "Calibri"
    h.font.size = Pt(size)
    h.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    h.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")


def para(text, italic=False, size=None, bold=False, after=6, grey=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.italic = italic
    r.bold = bold
    if size:
        r.font.size = Pt(size)
    if grey:
        r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    p.paragraph_format.space_after = Pt(after)
    return p


def eq(parts, after=4):
    """parts: list of (text, kind) with kind in {'n','sub','i'}; renders an indented equation line."""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.4)
    p.paragraph_format.space_after = Pt(after)
    for text, kind in parts:
        r = p.add_run(text)
        r.font.name = "Cambria Math"
        r.font.size = Pt(11)
        if kind == "sub":
            r.font.subscript = True
        if kind == "i":
            r.italic = True
    return p


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def table(header, rows, widths, size=8.5, align_right_from=1, caption=None, note=None):
    if caption:
        para(caption, bold=True, after=3)
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.autofit = False
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.width = Inches(widths[i])
        shade(c, "E7EEF5")
        p = c.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.size = Pt(size)
        if i >= align_right_from:
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].width = Inches(widths[i])
            p = cells[i].paragraphs[0]
            bold = isinstance(v, tuple)
            txt = v[0] if bold else v
            r = p.add_run("" if txt is None else str(txt))
            r.font.size = Pt(size)
            r.bold = bold
            if i >= align_right_from:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(0)
    if note:
        para(note, italic=True, size=8.5, grey=True, after=10)
    else:
        doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def figure(path, caption, width=6.5):
    doc.add_picture(path, width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    para(caption, italic=True, size=8.5, grey=True, after=10)


def cs_(c, s, d=3):
    return f"{c:+.{d}f} ({s:.{d}f})"


# ------------------------------------------------------------------ text
para(
    "Generative AI exposure and employment in eleven labour force surveys: tables and specifications",
    bold=True,
    size=15,
    after=2,
)
para(
    "Draft exhibits for the paper outline, generated 16 September 2026 from the ai-lfs-panel repository (commit 6f61062 and later). Tables 1 and 2 follow the outline; Figures 1 to 5 are shown with the plotted values as tables beneath them. All estimates use the top employment-weighted exposure quintile as the treated group unless stated.",
    italic=True,
    grey=True,
    after=10,
)

doc.add_heading("1. Data and cells", level=1)
para(
    "The panel harmonises the quarterly labour force surveys of eleven countries to one schema based on the World Bank Global Labor Database dictionary. Occupation is coded to ISCO-08 and industry to ISIC Rev. 4 at the finest level each survey supports. Each country-quarter is validated against the statistical office's published participation, employment and unemployment rates before it enters the panel. India is harmonised but held in an annex; Nigeria has no pre-period and enters only the sector descriptives."
)
para(
    "The unit of analysis is the cell c = (country, occupation o, age group a, sex s) observed in quarter t. Occupation is ISCO-08 at three digits where at least 90 percent of a country's employment resolves to three digits, and two digits otherwise (Argentina, Mexico, Bolivia, the Philippines). Age groups are 15 to 21, 22 to 25, 26 to 29, 30 to 49 and 50 and over; workers under 15 are excluded everywhere even where the survey's labour age is lower. The sample of cells is fixed at the baseline year 2022: a cell enters if its unweighted count averages at least 30 observations over the four quarters of 2022, and it is then kept in every quarter, with zero employment where absent, so selection never depends on later outcomes."
)
para(
    "Exposure is the ILO generative-AI occupational exposure score (Gmyrek, Berg and Bescond 2025), defined for 427 ISCO-08 unit groups and aggregated to minor and sub-major groups with pooled 2022 employment weights from the countries with four-digit codes. Occupations are ranked by score and split into employment-weighted quantiles at each digit level, so that each quintile holds one fifth of baseline employment. The treated group is the top quintile (23 percent of employment, led by shop salespersons, general and numerical clerks, and finance and administrative associate professionals). The top tercile (35 percent) and the top decile (10 percent) are reported as robustness cuts."
)

doc.add_heading("2. Specifications", level=1)
para(
    "Outcomes per cell and quarter are log weighted employment, and the new-hire share: the weighted fraction of employed persons in the cell who started their current job within the previous twelve months, defined only where the survey asks tenure."
)
para(
    "Event study. The reference quarter is 2022Q4, the last full quarter before generative AI tools were widely available. With k indexing quarters relative to the reference (k = 0 at 2022Q4), the estimating equation is",
    after=3,
)
eq(
    [
        ("y", "i"),
        ("c,t", "sub"),
        (" = Σ", "n"),
        ("k≠0", "sub"),
        (" β", "i"),
        ("k", "sub"),
        (" · 1[t = k] · High", "n"),
        ("o", "sub"),
        (" + α", "n"),
        ("c", "sub"),
        (" + γ", "n"),
        ("country, a, s, t", "sub"),
        (" + ε", "n"),
        ("c,t", "sub"),
    ]
)
para(
    "where High_o is one for occupations in the top exposure quintile, α_c is a cell fixed effect and γ absorbs every country by age group by sex by quarter combination, so that seasonality, the post-pandemic recovery and macroeconomic shocks specific to a country and demographic group are removed. The β_k trace the path of the treated cells relative to the untreated ones, normalised to zero at 2022Q4. Regressions are weighted by the cell's 2022 mean employment, and standard errors are clustered by country by occupation (655 clusters in the pooled sample)."
)
para(
    "Difference in differences. The single post-period coefficient replaces the quarter interactions:",
    after=3,
)
eq(
    [
        ("y", "i"),
        ("c,t", "sub"),
        (" = δ · Post", "n"),
        ("t", "sub"),
        (" · High", "n"),
        ("o", "sub"),
        (" + α", "n"),
        ("c", "sub"),
        (" + γ", "n"),
        ("country, a, s, t", "sub"),
        (" + ε", "n"),
        ("c,t", "sub"),
    ]
)
para(
    "with Post_t = 1 from 2023Q1 onward. Table 2 reports δ for the pooled sample, for young (15 to 29) and older cells separately, and country by country with the fixed effects re-estimated within each country."
)
para("Triple difference. Adding the interaction with the young indicator,", after=3)
eq(
    [
        ("y", "i"),
        ("c,t", "sub"),
        (" = δ · Post", "n"),
        ("t", "sub"),
        (" · High", "n"),
        ("o", "sub"),
        (" + θ · Post", "n"),
        ("t", "sub"),
        (" · High", "n"),
        ("o", "sub"),
        (" · Young", "n"),
        ("a", "sub"),
        (" + α", "n"),
        ("c", "sub"),
        (" + γ", "n"),
        ("country, a, s, t", "sub"),
        (" + ε", "n"),
        ("c,t", "sub"),
    ]
)
para(
    "where Post × Young itself is absorbed by γ, and θ measures whether young cells in exposed occupations moved differently from older cells in the same occupations."
)
para(
    "Continuous exposure replaces High_o with the employment-weighted score. The employment index in Figure 2 is descriptive: employment summed over all cells in an exposure quintile, divided by the quintile's 2022 mean, with the pooled series summing the countries observed in each quarter."
)

# ------------------------------------------------------------------ Table 1
doc.add_heading(
    "3. Table 1. Surveys, windows, sample sizes and occupation depth", level=1
)
rows = []
for cc in POOL + ["IND", "NGA"]:
    r = t1.loc[cc]
    c = cs.loc[cc]
    ten = (
        "yes"
        if r.pct_tenure >= 90
        else (
            "first quarters"
            if cc == "MEX"
            else (
                "first interviews"
                if cc == "URY"
                else ("partial" if r.pct_tenure > 0 else "no")
            )
        )
    )
    rows.append(
        [
            NAMES[cc],
            SURVEY[cc],
            f"{r.p_first}–{r.p_last}",
            f"{int(r.nq)}",
            f"{int(round(r.emp_per_q, -2)):,}",
            f"{int(r.minage)}",
            f"{int(c.digits)}",
            f"{r.pct_3d:.0f}",
            f"{int(c.occupations)}",
            f"{100 * c.small_share:.0f}",
            ten,
            NOTE1[cc],
        ]
    )
table(
    [
        "Country",
        "Survey",
        "Quarters",
        "N q",
        "Employed per quarter",
        "Min. age",
        "Cell digits",
        "% at 3+ digits",
        "Occupations in cells",
        "% cells under floor",
        "Tenure",
        "Notes",
    ],
    rows,
    [0.75, 0.6, 0.85, 0.3, 0.6, 0.35, 0.4, 0.45, 0.55, 0.45, 0.55, 1.5],
    size=7.5,
    align_right_from=2,
    note="Employed per quarter is the unweighted count of employed persons in the harmonised file, rounded. Cell digits is the ISCO level used in the cell analysis; % at 3+ digits is the employment-weighted share of workers whose occupation code resolves to three or more ISCO-08 digits. Occupations in cells and the share of cells under the 30-observation floor refer to the baseline year 2022. India and Nigeria are outside the pooled estimates.",
)

# ------------------------------------------------------------------ Table 2
doc.add_heading(
    "4. Table 2. Post × high exposure, log employment, three treatment cuts", level=1
)


def row_for(sub, label):
    out = [label]
    for k in ("q5", "t3", "d10"):
        d = did[k].loc[sub]
        d = d[d.term == "post_x_treat"] if isinstance(d, pd.DataFrame) else d
        if isinstance(d, pd.DataFrame):
            d = d.iloc[0]
        out.append(cs_(d.coef, d.se))
    d = did["q5"].loc[sub]
    d = d[d.term == "post_x_treat"].iloc[0] if isinstance(d, pd.DataFrame) else d
    out += [f"{int(d.n_cells):,}", f"{int(d.n_clusters)}"]
    return out


rows = [
    row_for(
        "all", ("All cells, eleven countries (δ, with the youth interaction below)",)
    ),
    row_for("young", "  young cells only (15–29)"),
    row_for("older", "  older cells only (30+)"),
]
tri = [("  Post × High × Young (triple difference)",)]
for k in ("q5", "t3", "d10"):
    d = did[k].loc["all"]
    d = d[d.term == "post_x_treat_x_young"].iloc[0]
    tri.append(cs_(d.coef, d.se))
tri += ["", ""]
rows.append(tri)
order = sorted(POOL, key=lambda c: -did["q5"].loc[f"country_{c}"].coef)
for cc in order:
    rows.append(row_for(f"country_{cc}", NAMES[cc]))
d = did_ind.loc["all"]
d = d[d.term == "post_x_treat"].iloc[0]
rows.append(
    [
        "India, annex (2021Q3–2024Q4, own fixed effects)",
        cs_(d.coef, d.se),
        "−0.052 (0.158)",
        "",
        f"{int(d.n_cells):,}",
        f"{int(d.n_clusters)}",
    ]
)
table(
    [
        "Sample",
        "Top quintile (primary)",
        "Top tercile",
        "Top decile",
        "Cells (quintile)",
        "Clusters",
    ],
    rows,
    [2.4, 1.2, 1.1, 1.1, 0.8, 0.6],
    size=8.5,
    note="Coefficient δ on Post × High with standard errors in parentheses, clustered by country × occupation. Post = 2023Q1 onward; reference 2022Q4. The all-cells row is the triple-difference specification, so its δ is the effect for older cells and equals the older-only row; the effect for young cells is δ + θ, which matches the young-only row. Cell fixed effects and country × age group × sex × quarter fixed effects; weights are 2022 mean cell employment. Country rows re-estimate the model within the country. The India tercile figure is from the separate India run; its decile variant was not run. Countries sorted by the quintile estimate.",
)

# ------------------------------------------------------------------ Figure 1 as table
doc.add_heading(
    "5. Figure 1. Event-study coefficients, log employment, pooled sample", level=1
)
figure(
    F + "es_log_emp_all.png",
    "Figure 1. Coefficients on high exposure (top quintile) × quarter, log cell employment, eleven countries pooled, with 95 percent confidence bands; reference 2022Q4 (dashed line).",
)
figure(
    F + "es_log_emp_young.png",
    "Figure 1b. Same specification, cells of workers aged 15 to 29 only.",
)
para("The same coefficients as a table:", bold=True, after=3)


def es_rows(es, subsets, d=3):
    per = es[es.subset == "all"].sort_values("k")[["k", "period"]]
    rows = []
    for _, p in per.iterrows():
        row = [p.period, f"{int(p.k):+d}"]
        for s in subsets:
            x = es[(es.subset == s) & (es.period == p.period)]
            row.append(
                "0 (ref.)"
                if int(p.k) == 0
                else (cs_(x.coef.iloc[0], x.se.iloc[0], d) if len(x) else "")
            )
        rows.append(row)
    return rows


table(
    ["Quarter", "k", "All cells", "Young (15–29)", "Older (30+)"],
    es_rows(es_emp, ["all", "young", "older"]),
    [0.9, 0.5, 1.5, 1.5, 1.5],
    size=8.5,
    note="β_k from the event-study equation with the top-quintile treatment; standard errors in parentheses. 2021 quarters cover the countries observed then (Brazil, Mexico, Argentina, Bolivia, Georgia and the Philippines from 2021Q1; Ecuador and Uruguay from 2021Q3); 2026 quarters cover the countries already released.",
)

# ------------------------------------------------------------------ Figure 2 as table
doc.add_heading(
    "6. Figure 2. Employment index by exposure quintile, 2022 = 100", level=1
)
figure(
    F + "emp_index_q5_panel.png",
    "Figure 2. Employment by quintile of generative-AI exposure, each quintile indexed to its 2022 mean, by country and pooled. Quintile 5 (red) is the most exposed.",
)
para("Selected values as a table:", bold=True, after=3)
rows = []
for cc in ["ALL"] + POOL:
    d = q5[q5.countrycode == cc]
    last = d.period.max()
    for per in ["2023Q4", "2024Q4", last]:
        x = d[d.period == per].set_index("group")["index"]
        if len(x) == 0:
            continue
        rows.append(
            [NAMES[cc] if per == "2023Q4" else "", per]
            + [f"{x.get(g, float('nan')):.1f}" for g in (1, 2, 3, 4, 5)]
        )
table(
    ["Country", "Quarter", "Q1 (least exposed)", "Q2", "Q3", "Q4", "Q5 (most exposed)"],
    rows,
    [1.1, 0.8, 1.1, 0.8, 0.8, 0.8, 1.1],
    size=8.5,
    note="Employment summed over all cells in the quintile, divided by its 2022 mean. Quintiles are employment-weighted at the 2022 baseline and defined at each country's cell digit level. The pooled series sums the countries observed in each quarter. Bolivia and Georgia are at two and three digits respectively with few cells, and their indices are noisy.",
)

# ------------------------------------------------------------------ Figure 3 as table
doc.add_heading("7. Figure 3. Event-study coefficients, new-hire share", level=1)
figure(
    F + "es_new_hire_share_young.png",
    "Figure 3. Coefficients on high exposure × quarter for the new-hire share (workers in their job under 12 months), cells of workers aged 15 to 29, seven countries with a tenure question; 95 percent bands.",
)
figure(F + "es_new_hire_share_all.png", "Figure 3b. Same outcome, all cells.")
figure(
    F + "es_new_hire_share_panel_country_young.png",
    "Figure 3c. New-hire share event study by country, cells of workers aged 15 to 29. Each panel re-estimates the model within the country; 95 percent bands. South Africa has 8 clusters and Argentina 13, so their bands are wide.",
    width=6.8,
)
figure(
    F + "es_new_hire_share_panel_country.png",
    "Figure 3d. New-hire share event study by country, all cells.",
    width=6.8,
)
para("The same coefficients as a table:", bold=True, after=3)
rows = es_rows(es_nh, ["all", "young", "older"], d=4)
table(
    ["Quarter", "k", "All cells", "Young (15–29)", "Older (30+)"],
    rows,
    [0.9, 0.5, 1.5, 1.5, 1.5],
    size=8.5,
    note="Outcome: weighted share of employed persons in the cell who started their current job within 12 months. Seven countries with a tenure question: Brazil, Colombia, Ecuador, Argentina, South Africa (all quarters), Uruguay (first interviews), Mexico (first quarters). Coefficients in share points; multiply by 100 for percentage points.",
)
d_all = did_nh.loc["all"]
dy = did_nh.loc["young"]
do = did_nh.loc["older"]
rows = [
    [
        "All cells",
        cs_(
            d_all[d_all.term == "post_x_treat"].coef.iloc[0],
            d_all[d_all.term == "post_x_treat"].se.iloc[0],
            4,
        ),
    ],
    ["Young (15–29)", cs_(dy.coef, dy.se, 4)],
    ["Older (30+)", cs_(do.coef, do.se, 4)],
    [
        "Post × High × Young",
        cs_(
            d_all[d_all.term == "post_x_treat_x_young"].coef.iloc[0],
            d_all[d_all.term == "post_x_treat_x_young"].se.iloc[0],
            4,
        ),
    ],
]
for cc in ["BRA", "URY", "COL", "ARG", "MEX", "ECU", "ZAF"]:
    x = did_nh.loc[f"country_{cc}"]
    y = did_nh.loc[f"country_young_{cc}"]
    rows.append([NAMES[cc], cs_(x.coef, x.se, 4), cs_(y.coef, y.se, 4)])
for r_ in rows[:4]:
    r_.append("")
table(
    ["Sample", "Post × High, all cells in sample", "Post × High, young cells only"],
    rows,
    [2.4, 1.6, 1.6],
    size=8.5,
    note="Difference in differences for the new-hire share, same specification as Table 2; as there, the all-cells δ comes from the triple-difference model and equals the older-cell effect.",
)

# ------------------------------------------------------------------ Figure 4 as table
doc.add_heading(
    "8. Figure 4. IT and business-process services: headcount and under-25 share",
    level=1,
)
figure(
    F + "itbpo_by_country.png",
    "Figure 4. Employment in ISIC 62, 63 and 82 indexed to 2022 (sector, its clerical and service occupations, and all employment) and the under-25 share of sector employment against the economy-wide share, annual averages.",
    width=6.8,
)
para("Summary values as a table:", bold=True, after=3)
rows = []
for cc in [
    "BRA",
    "COL",
    "MEX",
    "ARG",
    "ECU",
    "PER",
    "URY",
    "BOL",
    "ZAF",
    "GEO",
    "PHL",
    "IND",
]:
    s = sec[sec.countrycode == cc].sort_values("yr")
    b = s[s.yr == 2022].iloc[0]
    last = s.iloc[-1]
    rows.append(
        [
            NAMES[cc] + {"ZAF": " (ISIC 62 only)", "MEX": " (ENOE 5611)"}.get(cc, ""),
            f"{int(last.yr)}",
            f"{int(b.n_itbpo):,}",
            f"{b.itbpo_share_pct:.1f}",
            f"{last.itbpo_idx:.0f}",
            f"{last.emp_all_idx:.0f}",
            f"{b.u25_itbpo:.1f}",
            f"{last.u25_itbpo:.1f}",
            f"{last.u25_itbpo - b.u25_itbpo:+.1f}",
            f"{b.u25_all:.1f}",
            f"{last.u25_all:.1f}",
            f"{last.u25_all - b.u25_all:+.1f}",
        ]
    )
table(
    [
        "Country",
        "Latest year",
        "Sample workers 2022",
        "Share of employment 2022, %",
        "Sector headcount, latest (2022=100)",
        "All employment, latest (2022=100)",
        "Under-25 share, 2022",
        "Under-25 share, latest",
        "Change, pts",
        "Under-25 share all, 2022",
        "Under-25 share all, latest",
        "Change, pts",
    ],
    rows,
    [1.05, 0.45, 0.55, 0.55, 0.6, 0.6, 0.5, 0.5, 0.45, 0.5, 0.5, 0.45],
    size=7.5,
    note="Sector = ISIC Rev. 4 divisions 62 (computer programming and consultancy), 63 (information services) and 82 (office and business support, including call centres). Annual averages of quarters; the latest year may be partial (2026 has one or two quarters). Sample workers is the unweighted count of sector workers in 2022. Bolivia (290 workers) and Georgia (92) are too small for the under-25 share to be reliable. India's 2025 sample reflects the enlarged PLFS.",
)

# ------------------------------------------------------------------ Figure 5 as table
doc.add_heading(
    "9. Figure 5. Occupation split within IT and business-process services, 2022 = 100",
    level=1,
)
figure(
    F + "itbpo_occupation_split.png",
    "Figure 5. Within the sector, employment in professional and technical occupations (ISCO 1 to 3) and in clerical and service occupations (ISCO 4 and 5), indexed to 2022, against all employment.",
    width=6.8,
)
para("The same values as a table:", bold=True, after=3)
rows = []
for cc in [
    "BRA",
    "COL",
    "MEX",
    "ARG",
    "ECU",
    "PER",
    "URY",
    "BOL",
    "ZAF",
    "GEO",
    "PHL",
    "IND",
]:
    s = sec[sec.countrycode == cc].sort_values("yr")
    row = [NAMES[cc] + {"ZAF": " (ISIC 62 only)", "MEX": " (ENOE 5611)"}.get(cc, "")]
    for yr in (2023, 2024, 2025, 2026):
        x = s[s.yr == yr]
        row += [
            f"{x.itbpo_prof_idx.iloc[0]:.0f}" if len(x) else "",
            f"{x.itbpo_cler_idx.iloc[0]:.0f}" if len(x) else "",
        ]
    rows.append(row)
table(
    [
        "Country",
        "2023 prof.",
        "2023 cler.",
        "2024 prof.",
        "2024 cler.",
        "2025 prof.",
        "2025 cler.",
        "2026 prof.",
        "2026 cler.",
    ],
    rows,
    [1.5, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65],
    size=8,
    note="Within the sector, prof. = ISCO major groups 1 to 3 (managers, professionals, technicians); cler. = major groups 4 and 5 (clerical support, service and sales workers, which contain call-centre agents and back-office staff). Indexed to the 2022 annual average. 2026 covers one or two quarters.",
)

doc.add_heading("10. Reading notes", level=1)
for t_ in [
    "Table 2: the pooled coefficient is small and imprecise under every cut; the sign is positive. Ecuador and Uruguay are the two countries with a negative estimate that survives the choice of cut. Georgia's swing from +0.09 to −0.21 across cuts reflects 25 clusters and is not informative.",
    "Figure 1: the pre-period coefficients lie within 0.014 of zero with standard errors around 0.03 in 2021 and 0.01 to 0.02 in 2022; the post-period path reaches 0.02 by 2024 and 0.03 in 2025. The young and older paths are alike.",
    "Figure 2: in the pooled index the middle quintiles grow fastest (Q3 and Q4 at 110 to 113 by 2026Q2), the top quintile follows at 108, and the two least exposed quintiles are flat. This is the composition shift toward clerical, sales and professional work that the pooled coefficient in Table 2 reflects. Ecuador is the exception, with the top quintile at 89 to 92.",
    "Figure 3: the new-hire share among young workers in exposed occupations sits 1.1 to 2.2 points below the reference in every quarter from 2023Q2 to 2025Q4; the older path is about half that. Brazil and Uruguay drive the country estimates. The share can fall because fewer young workers were hired or because young incumbents stayed longer; the cells cannot separate the two.",
    "Figures 4 and 5: the under-25 share of the sector fell in every country with a usable sample, by 2 to 12 points, against 0 to 2 points economy-wide; professional occupations within the sector grew everywhere except Georgia and India's 2025, while clerical and service occupations fell in Brazil, Ecuador, Peru, Argentina, Uruguay and Bolivia. These are composition measures and are consistent with slowed entry and with ageing in place.",
]:
    doc.add_paragraph(t_, style="List Bullet").paragraph_format.space_after = Pt(4)

doc.save(R + "docs/design/paper-tables-draft.docx")
print("written")
