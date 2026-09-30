# Session notes

Read at the start of every session; update at the end of every session
(progress made, decisions taken, next steps). Keep it short: this is a
handover note, not a log. Dated history goes in git.

Last updated: 2026-09-30

## Related folders

- `~/Projects/ai-lfs-panel` (this repo): harmonised LFS panel, analysis,
  design docs, Eurostat proposal.
- `~/Projects/lfs-paper`: the paper, a git clone of the Overleaf project
  (origin https://git.overleaf.com/6abbd6d15303f68d78c2656f). Cloned
  30 Sep 2026; holds `main.tex` only so far. Push and pull from here use
  the Overleaf token in the macOS keychain.
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
Drive. Person ids link across quarters for eight countries (BRA, ZAF, ARG,
IND from 2025Q2, MEX, URY, BOL, PER); no office publishes longitudinal
weights; re-observation logits are in docs/design/reobservation-diagnostics.docx.

Analysis. Primary treatment is the top employment-weighted quintile of the
ILO exposure score. Pooled post x high on log employment is +0.017
(SE 0.023); young new-hire share is -0.010 (SE 0.005). IT-BPO sector series
annual by country, quarterly for BRA, COL, PHL, URY, IND, with Philippine
PSA and IBPAP leading indicators. Tables 1, 2 and Figures 1 to 5 with
value tables are in docs/design/paper-tables-draft.docx.

Eurostat EU-LFS proposal. LFS only (EU-SILC dropped 25 Sep). Working
file: docs/design/EU LFS proposal draft Sept 12.docx, with a markdown
twin docs/design/eu-lfs-proposal.md for pasting into the portal. Nine
yellow fields remain for the applicant. Reviewed 28 Sep against
Eurostat's "How to apply" guide: two fixes still to make (see next steps).

Candidate countries checked 28 Sep. Costa Rica ECE: 2021 to 2026Q2 on
INEC's catalogue (ids 293, 302, 306, 331, 369, 384), login required, so
the download is the user's. Honduras EPHPM: annual only (July 2025 file
public), fits the annual IT-BPO tabulations, not the quarterly design.

## Next steps

1. Eurostat proposal: (a) settle the eligibility question, since the
   recognised entity is World Bank DEC and the individual researcher's
   unit is outside DEC; (b) consider extending access to 31/12/2031 to
   cover the publication cycle; (c) add applicant notes on confidentiality
   declarations, the frontend-user role, S-CIRCABC delivery and the closing
   declaration; then fill the yellow fields and submit via the portal.
2. Paper: start writing in ~/Projects/lfs-paper from docs/design/
   paper-outline.md and paper-tables-draft.docx. Outline items still to
   produce: sector-level difference in differences (Table 4), occupation
   split within IT-BPO by country (Figure 5), wage margin where wages
   exist, adoption-timing interaction, robustness runs for Table 3.
3. Transition file: per-country, per-quarter-pair re-observation weights
   with interview-number dummies for the eight linkable countries,
   excluding ZAF 2025Q4 to 2026Q1 and MEX pairs from 2025Q4/2026Q1; check
   against published gross flows (BRA, MEX, ZAF).
4. Egypt: locate the ERF files, then build fetch/read/harmonize for
   2021 to 2024.
5. Costa Rica: once the user downloads the INEC bundles, build the
   country modules on the Brazil pattern.
6. Standing watches: Egypt daily (log not being written, check), MoSPI
   hourly, Italy public-use file, ISSDA request.
