# Session notes

Read at the start of every session; update at the end of every session
(progress made, decisions taken, next steps). Keep it short: this is a
handover note, not a log. Dated history goes in git.

Last updated: 2026-10-02

## Related folders

- `~/Projects/ai-lfs-panel` (this repo): harmonised LFS panel, analysis,
  design docs, Eurostat proposal.
- `~/Projects/lfs-paper`: the paper, a git clone of the Overleaf project
  (origin https://git.overleaf.com/6abbd6d15303f68d78c2656f). Has its own
  CLAUDE.md (pull before any edit, push after every commit, single branch,
  changes marked with `\add{}` in red and `\del{}` struck through) and
  NOTES.md. `main.tex` holds the section skeleton from
  docs/design/paper-outline.md, a proposed-exhibits list and
  `references.bib` (50 entries). Quy-Toan Do edits on Overleaf.
- TeX: TeX Live 2026 (full scheme) installed 30 Sep 2026 in
  ~/texlive/2026, user-owned, no MacTeX GUI apps; binaries on PATH via
  ~/.zshrc (texlive/2026/bin/universal-darwin). Update packages with
  `tlmgr update --self --all`. The paper compiles with `latexmk -pdf`.
- Google Drive, folder Claude/ai-lfs-panel: copies of literature.md,
  paper-outline.md and eu-lfs-proposal.md. A stale "EU LFS proposal.docx"
  sits at the Drive root (pre-revision, includes SILC); the docx cannot be
  replaced through the Drive connector, only text files can.

## Where things stand

Data. Eleven countries in the pooled quarterly panel (ARG, BOL, BRA, COL,
ECU, GEO, MEX, PER, PHL, URY, ZAF), 2021Q1 to the latest quarter each,
validated against official rates. India harmonised but kept as an annex
(2025 redesign). Nigeria has no pre-period. Egypt: ERF access obtained
for 2021 to 2024, but the files have not been found on this Mac or in
Drive. Costa Rica ECE 2021 to 2026Q2 is on INEC's catalogue (ids 293,
302, 306, 331, 369, 384; login needed, user downloads); Honduras EPHPM is
annual only. Person ids link across quarters for eight countries; no
office publishes longitudinal weights; re-observation logits are in
docs/design/reobservation-diagnostics.docx.

Analysis. Primary treatment is the top employment-weighted quintile of the
ILO exposure score. Pooled post x high on log employment is +0.017
(SE 0.023); young new-hire share is -0.010 (SE 0.005). IT-BPO sector series
annual by country, quarterly for BRA, COL, PHL, URY, IND. Tables 1, 2 and
Figures 1 to 5 with value tables are in docs/design/paper-tables-draft.docx
(built by scripts/44_paper_tables.py).

Literature. docs/design/literature.md now covers the Imas and Schaal
review of 29 Sep 2026 (26 papers added 30 Sep); the same papers are in
lfs-paper/references.bib with marked bullets in the paper's Introduction
and Interpretation.

Eurostat EU-LFS proposal. LFS only. Working file:
docs/design/EU LFS proposal draft Sept 12.docx, markdown twin
docs/design/eu-lfs-proposal.md. Reviewed 28 Sep against Eurostat's
"How to apply" guide: see next steps.

## In progress: LaTeX tables for the paper (planned 2 Oct, not started)

Decisions taken with the user: build Tables 1 to 4 in this repo as
complete LaTeX floats (threeparttable, booktabs, caption, label, notes)
that `\input` into the paper with one line; labels tab:surveys,
tab:country, tab:robust, tab:sector; coefficients with SE in parentheses
and stars at 10, 5 and 1 percent from the cluster-robust t statistic;
Table 3 and Table 4 with new estimation; alternative exposure indices
stay out until a SOC-ISCO crosswalk exists. Output to a new
`output/latex/` directory, copied later to lfs-paper/tab_fig/v1/.

What exists to reuse (from the 2 Oct exploration):
- scripts/44_paper_tables.py: constants NAMES, SURVEY, POOL, NOTE1; the
  Table 1 DuckDB query (view `employed`, source='own'); `cs_()` formatter;
  `row_for()` for Table 2; finished note strings for every table.
- Table 2 inputs on disk: did_log_emp.csv (quintile), did_log_emp_high.csv
  (tercile), did_log_emp_high_d10.csv (decile), did_log_emp_IND_to2024Q4.csv;
  columns term,coef,se,n_cells,n_clusters,subset; term post_x_treat and,
  for subset all, post_x_treat_x_young. Tercile and decile runs lack
  country_young rows. The India tercile cell in 44 is a hard-coded string;
  re-derive it.
- analysis.py: estimate_did / estimate_event_study are pure functions over
  event_study_frame(cells, exposure); Table 3 rows can loop over modified
  frames in one script instead of rerunning 41_event_study.py. Options
  that exist: --treat score_w (continuous), --exclude cc (leave-one-out),
  --keep-small. Do not exist: 2-digit cells for all (re-aggregate
  cells.parquet to isco[:2] in-script or override `depth` in
  build_cells), urban only and formal only (cells.parquet has no urban or
  socialsec dimension; needs a build_cells variant). No stars or p-values
  are computed anywhere; derive from coef/se. The event-study k=0 row has
  blank n_cells.
- Table 4: no sector-level regression exists; 43_itbpo_sector.py is
  descriptive SQL (ISIC 62+63 it, 82 bpo; ZAF 62 only; MEX industry_orig
  5611). Build sector cells (country x quarter x industry group x age x
  sex) with treated = IT-BPO and controls = finance 64-66, professional
  services 69-75, public administration 84, then reuse demean/wls_cluster
  for youth share and clerical employment outcomes.

## Next steps

1. Write scripts/48_latex_tables.py (and a sector-cell builder for
   Table 4) per the plan above; verify each fragment compiles standalone
   with TeX Live; commit here, then copy to lfs-paper/tab_fig/v1/ and
   point the \tabfig macros at it.
2. Eurostat proposal: (a) settle the eligibility question (recognised
   entity is World Bank DEC, individual researcher's unit is outside DEC);
   (b) consider extending access to 31/12/2031; (c) add applicant notes on
   confidentiality declarations, frontend-user role, S-CIRCABC delivery and
   the closing declaration; fill the yellow fields; submit via the portal.
3. Paper: replace the outline bullets in lfs-paper/main.tex with prose,
   section by section, under the change-marking rules; verify the 11
   CHECK entries in references.bib.
4. Transition file: per-country, per-quarter-pair re-observation weights
   with interview-number dummies for the eight linkable countries,
   excluding ZAF 2025Q4 to 2026Q1 and MEX pairs from 2025Q4/2026Q1; check
   against published gross flows (BRA, MEX, ZAF).
5. Egypt: locate the ERF files, then build fetch/read/harmonize for
   2021 to 2024. Costa Rica: once the user downloads the INEC bundles,
   build the country modules on the Brazil pattern.
6. Standing watches: Egypt daily (log not being written, check), MoSPI
   hourly, Italy public-use file, ISSDA request.
