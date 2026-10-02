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
Drive. Costa Rica ECE 2021 to 2026Q2 is on INEC's NADA catalogue
(sistemas.inec.cr/pad5/index.php/catalog/<id>, ids 293=2021, 302=2022,
306=2023, 331=2024, 369=2025, 384=2026; one bundle per year); access type
is "public" but checked 2 Oct: `get-microdata` redirects to the login
page; the user has not managed to register, so Costa Rica is ON HOLD;
nothing is on this Mac (the ECE_4T2025.zip in Downloads is Bolivia's).
Honduras EPHPM is annual only. Person ids link across quarters for eight countries; no
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

Eurostat EU-LFS proposal. Submitted via the portal (user confirmed
2 Oct 2026). Working file docs/design/EU LFS proposal draft Sept 12.docx,
markdown twin docs/design/eu-lfs-proposal.md. Delivery expected around
January 2027 if approved.

## Done 2 Oct: LaTeX tables for the paper

scripts/48_latex_tables.py writes output/latex/tab_surveys.tex,
tab_country.tex, tab_robust.tex and tab_sector.tex (labels tab:surveys,
tab:country, tab:robust, tab:sector): complete floats (threeparttable,
booktabs, caption, notes) for one-line `\input`. Coefficients carry SE
below and stars at 10/5/1 percent from the cluster-robust t with G-1 df
(`lfspanel.latex`). Table 1 reads the panel database. Table 2 (revised
2 Oct, quintile only, SE to the right): pooled delta, theta and delta+theta,
then delta and delta+theta per country and for India, all estimated
in-script (output/tables/country_log_emp.csv; estimate_did(triple=True)
now returns delta+theta with its own SE; Georgia has no young cell, n.a.;
column with the top-quintile share of 2025 cell employment). figures.tex
holds every figure float (10: fig:es_pooled, fig:index, fig:newhire,
fig:newhire_country, fig:youthshare, fig:itbpo_quarterly, fig:phl,
fig:split, fig:es_country, fig:india) with images as \tabfig/<file>; the
script copies the 15 PNGs into output/latex/ (git-ignored), so that
directory is the drop-in for lfs-paper/tab_fig/v1/. Table 3 (tab:newhire,
added 2 Oct) is the plain DiD on the new-hire share, all cells, pooled
(-0.007, SE 0.002) and for the seven tenure countries, no youth
interaction (decision: the young-cell share is a weak hiring measure
because young cells turn over fast; use the all-cells result only).
Table 4 (treatment cut, continuous score, 2-digit cells, small cells kept,
urban only, social-security contributors only, 2022-vs-2021 placebo,
leave-one-out) and Table 5 (sector DiD on country x quarter x industry
group x sex cells, `lfspanel.sector`; IT-BPO against finance, professional
services and public administration; outcomes log employment, 15-29 and
under-25 shares, clerical share and log clerical employment) are estimated
in the script and saved to output/tables/robust_log_emp.csv and
sector_did.csv. The script compiles every fragment with TeX Live and saves
output/latex/preview.pdf (ignored by git). Run time about one minute.
Headline results: pooled delta stable at +0.01 to +0.02 under every cut
(urban only -0.002, SE 0.013); placebo 0.001 (0.029); sector youth share
-0.032 (0.004) with log employment +0.077 (0.034), pattern holds for every
control group. Alternative exposure indices stay out (no SOC-ISCO crosswalk).

## Next steps

1. Paper repo: pull, create lfs-paper/tab_fig/v1/, copy the four
   fragments from output/latex/ plus the figures, set the \tabfig macros,
   compile, commit and push. Then replace the outline bullets with prose
   (Table 5 now gives the identified sector result for section 6).
2. Eurostat: watch for the decision; on approval, set up the S-CIRCABC
   delivery and the confidentiality declarations.
3. Paper: verify the 11 CHECK entries in references.bib; fix JEL codes
   and keywords; abstract once the results settle.
4. Transition file: per-country, per-quarter-pair re-observation weights
   with interview-number dummies for the eight linkable countries,
   excluding ZAF 2025Q4 to 2026Q1 and MEX pairs from 2025Q4/2026Q1; check
   against published gross flows (BRA, MEX, ZAF).
5. Egypt: locate the ERF files, then build fetch/read/harmonize for
   2021 to 2024. Costa Rica: once the user downloads the INEC bundles,
   build the country modules on the Brazil pattern.
6. Standing watches: Egypt daily (log not being written, check), MoSPI
   hourly, Italy public-use file, ISSDA request.
