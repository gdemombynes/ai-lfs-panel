# Session notes

Read at the start of every session; update at the end of every session
(progress made, decisions taken, next steps). Keep it short: this is a
handover note, not a log. Dated history goes in git.

Last updated: 2026-10-03

## Related folders

- `~/Projects/ai-lfs-panel` (this repo): harmonised LFS panel, analysis,
  design docs, Eurostat proposal.
- `~/Projects/lfs-paper`: the paper, a git clone of the Overleaf project
  (origin https://git.overleaf.com/6abbd6d15303f68d78c2656f). Has its own
  CLAUDE.md (pull before any edit, push after every commit, single branch,
  changes marked with `\add{}` in red and `\del{}` struck through) and
  NOTES.md. Quy-Toan Do edits on Overleaf.
- TeX Live 2026 in ~/texlive/2026 (user-owned, on PATH via ~/.zshrc;
  `tlmgr update --self --all`). The paper compiles with `latexmk -pdf`.
- Google Drive, folder Claude/ai-lfs-panel: copies of literature.md,
  paper-outline.md and eu-lfs-proposal.md (a stale "EU LFS proposal.docx"
  at the Drive root cannot be replaced through the connector).

## Where things stand

Data. Eleven countries in the pooled quarterly panel (ARG, BOL, BRA, COL,
ECU, GEO, MEX, PER, PHL, URY, ZAF), 2021Q1 to the latest quarter each,
validated against official rates. Employment status follows each office's
own classification, harmonised to the GLD coding, not re-derived. India
harmonised but an annex (2025 redesign). Nigeria has no pre-period. Egypt:
ERF access for 2021 to 2024, files not found. Costa Rica ON HOLD: INEC's
NADA catalogue (ids 293, 302, 306, 331, 369, 384, one bundle a year)
needs a login the user could not register for. Person ids link across
quarters for eight countries; no longitudinal weights published.

Exposure. ILO WP 140 (Gmyrek et al. 2025) task scores, 427 unit groups,
from github.com/pgmyrek/2025_GenAI_scores_ISCO08; aggregated to 3, 2, 1
digits with 2022 employment weights from BRA, COL, ECU, PER; treatment is
the top employment-weighted quintile at each country's cell digit level.

Paper exhibits (2 Oct, all in this repo and pushed to lfs-paper
tab_fig/v1/). scripts/48_latex_tables.py writes output/latex/: Table 1
tab_surveys; Table 2 tab_country (quintile only, pooled delta, theta,
delta+theta, then delta and delta+theta per country, alphabetical, with
the top-quintile share of 2025 employment; Georgia n.a., no young cell
reaches the floor); Table 3 tab_newhire (plain DiD on the new-hire share,
all cells, seven tenure countries; the young-cell share was judged a weak
hiring measure and dropped); Table 4 tab_sector (IT-BPO vs finance,
professional services, public administration; log employment and 15-29
share; pooled plus one row per country, at most 4 clusters each); Table 4b
tab_sector_total (same vs all other employment, clustered by cell); annex
Table A1 tab_robust (treatment cuts, continuous score, 2-digit cells,
small cells kept, urban, social-security, 2022-vs-2021 placebo,
leave-one-out; `annex=True` switches numbering, input it last); figures.tex
(8 floats: es_pooled, index, newhire, newhire_country, itbpo_quarterly,
split, es_country, india; images as \tabfig/<file>, copied beside it).
Every fragment starts with `%!TEX root = ../../main.tex` so TeXShop
typesets the paper from a fragment (user's change, 2 Oct). Every fragment
is compiled with TeX Live; output/latex/preview.pdf is the check
(git-ignored). Run time about one minute. Library: lfspanel.latex
(stars from the cluster-robust t with G-1 df, SE to the right of the
coefficient), lfspanel.sector (sector cells incl. a `rest` group),
analysis.aggregate_cells, placebo_frame, estimate_did(triple) returning
delta+theta. Headline numbers: pooled delta +0.017 (0.023), stable under
every cut, placebo 0.001; new-hire share -0.007 (0.002); sector youth
share -0.032 (0.004) with sector employment +0.077 (0.034).

Dropped on 2 Oct: the exporter split (BRA, COL, PHL was a reading of the
outcome, not an external measure), the control-group panel, the under-25
and clerical columns of Table 4, the IT-BPO country-page figures and the
Philippines figure (PNGs still produced by 43 and 45; 45 has --from-csv).

Eurostat EU-LFS proposal submitted 2 Oct 2026; delivery expected about
January 2027 if approved.

## Next steps

1. Paper: replace the outline bullets in lfs-paper/main.tex with prose
   under the change-marking rules, moving each float from the "Draft
   tables and figures" section to where it is cited; fix or drop the
   `fig:youthshare` reference (Table 4's youth-share column replaces it).
   To refresh exhibits: run 48, copy output/latex/*.tex and *.png to
   lfs-paper/tab_fig/v1/, compile, commit, push.
2. Paper: verify the 11 CHECK entries in references.bib; JEL codes and
   keywords; abstract once results settle.
3. Sector: an external export-orientation measure (UNCTAD/WTO computer and
   business services exports over GDP, fixed pre-2023) if an exporter
   split is wanted; a SOC-ISCO crosswalk before any alternative index.
4. Eurostat: watch for the decision; on approval set up S-CIRCABC delivery
   and the confidentiality declarations.
5. Transition file: per-country, per-quarter-pair re-observation weights
   for the eight linkable countries (exclude ZAF 2025Q4-2026Q1 and MEX
   pairs from 2025Q4/2026Q1); check against published gross flows.
6. Egypt: locate the ERF files, then build the modules. Costa Rica: once
   the user has the INEC bundles, build on the Brazil pattern.
7. Standing watches: Egypt daily (log not being written, check), MoSPI
   hourly, Italy public-use file, ISSDA request.
