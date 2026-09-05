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
| HAVE (in progress) | `mex/enoe/{2022Q1..2026Q2}/enoe[_n]_YYYY_trimN_csv.zip` (~40 MB each) | INEGI ENOE microdatos; `_n_` naming through 2022, members ENOEN_/ENOE_ | 2026-09-05 | Open (INEGI open data) | Mexico panel |
| HAVE | `mex/enoe/docs/bulletins/*.pdf` | INEGI quarterly ENOE press bulletins (2023Q4 onward located) | 2026-09-05 | Public | Mexico validation |
| HAVE (resource) | `resources/crosswalks/sinco2019_to_isco08.csv`, `scian2018_to_isic4.csv` | World Bank GLD MEX ENOE utilities (converted from .dta) | 2026-09-05 | MIT (GLD) | Mexico occupation and industry |
| HAVE (in progress) | `col/geih/{2022M01..2026M06}/*.zip` (~60 MB each, CSV+DTA+SAV) | DANE microdata catalogue entries 771/782/819/853/900, download/<resource> | 2026-09-05 | Open (DANE) | Colombia panel |
| HAVE | `col/geih/docs/anex-GEIH-<mmm><yyyy>.xlsx` | DANE anexo GEIH, national monthly and quarterly series | 2026-09-05 | Public | Colombia validation |
| NEED | Argentina EPH quarterly zips | INDEC | | Open | M2 |
| NEED | Ecuador ENEMDU quarterly SPSS zips | INEC | | Open | M2 |
| NEED | Peru ENAHO quarterly module 500 (+02, 03) | INEI | | Open | M2 |
| MANUAL | South Africa QLFS quarterly Stata files | DataFirst (account + access form) | | CC-BY, cite Stats SA and DataFirst | M3 |
| NEED | India PLFS quarterly unit-level files | MoSPI microdata API (key in `.env`) | | MoSPI terms | M3 |
| MANUAL | GLD harmonized `.dta` for BRA, MEX, COL, ZAF, IND | World Bank GLD server / datalibweb (staff access) | | World Bank internal; do not redistribute | Backfill 2018-2021, validation |
