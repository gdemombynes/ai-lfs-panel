# Data inventory

One row per raw file family. Status: HAVE (on disk, in `data/raw/manifest.csv`),
NEED (not yet fetched), MANUAL (must be downloaded by hand). Add a row before
using any new raw file.

| Status | File(s) | Source | Retrieved | Licence / terms | Used for |
|---|---|---|---|---|---|
| HAVE | `bra/pnadc/2025Q1/PNADC_012025.zip` (212 MB) | IBGE FTP, PNAD Contínua trimestral, 2025 Q1 (Census-2022 weights vintage, posted 2025-08-15) | 2026-09-05 | Public, IBGE open data | Brazil harmonization, validation |
| HAVE | `bra/pnadc/{2022Q1..2026Q2}/PNADC_QQYYYY[_YYYYMMDD].zip` (18 files, 3.9 GB) | same; 2022-2024 files carry the 2025-08-15 release suffix, 2024Q2 re-issued 2026-03-24 | 2026-09-05 | same | Brazil panel 2022Q1-2026Q2, all quarters validated (90/90 checks) |
| HAVE | `bra/pnadc/docs/*` (dictionary, SAS input, COD and CNAE structures, deflators) | IBGE FTP `Documentacao/` | 2026-09-05 | Public | Layout parsing, classification notes |
| HAVE (resource) | `resources/crosswalks/isco08_structure.csv` | ILO, "ISCO-08 EN Structure and definitions.xlsx" | 2026-09-05 | ILO, free reuse with attribution | ISCO code validation |
| HAVE (resource) | `resources/official/bra_headline.csv` | IBGE SIDRA API table 4092 | 2026-09-05 | Public | Validation |
| NEED | ILO GenAI exposure scores (`Final_Scores_ISCO08_Gmyrek_et_al_2025.xlsx`) | github.com/pgmyrek/2025_GenAI_scores_ISCO08 | | ILO WP140, cite Gmyrek et al. 2025 | Exposure layer (M4) |
| NEED | Mexico ENOE quarterly zips 2022Q1-2026Q2 | INEGI | | Open | M2 |
| NEED | Colombia GEIH monthly zips 2022M01-2026M06 | DANE microdata catalogue | | Open | M2 |
| NEED | Argentina EPH quarterly zips | INDEC | | Open | M2 |
| NEED | Ecuador ENEMDU quarterly SPSS zips | INEC | | Open | M2 |
| NEED | Peru ENAHO quarterly module 500 (+02, 03) | INEI | | Open | M2 |
| MANUAL | South Africa QLFS quarterly Stata files | DataFirst (account + access form) | | CC-BY, cite Stats SA and DataFirst | M3 |
| NEED | India PLFS quarterly unit-level files | MoSPI microdata API (key in `.env`) | | MoSPI terms | M3 |
| MANUAL | GLD harmonized `.dta` for BRA, MEX, COL, ZAF, IND | World Bank GLD server / datalibweb (staff access) | | World Bank internal; do not redistribute | Backfill 2018-2021, validation |
