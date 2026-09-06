# Data inventory

One row per raw file family. Status: HAVE (on disk, in `data/raw/manifest.csv`),
NEED (not yet fetched), MANUAL (must be downloaded by hand). Add a row before
using any new raw file.

| Status | File(s) | Source | Retrieved | Licence / terms | Used for |
|---|---|---|---|---|---|
| HAVE | `bra/pnadc/2025Q1/PNADC_012025.zip` (212 MB) | IBGE FTP, PNAD Contínua trimestral, 2025 Q1 (Census-2022 weights vintage, posted 2025-08-15) | 2026-09-05 | Public, IBGE open data | Brazil harmonization, validation |
| HAVE | `bra/pnadc/{2021Q1..2026Q2}/PNADC_QQYYYY[_YYYYMMDD].zip` (22 files, 4.6 GB) | same; 2022-2024 files carry the 2025-08-15 release suffix, 2024Q2 re-issued 2026-03-24 | 2026-09-05 | same | Brazil panel 2022Q1-2026Q2, all quarters validated (90/90 checks) |
| HAVE | `bra/pnadc/docs/*` (dictionary, SAS input, COD and CNAE structures, deflators) | IBGE FTP `Documentacao/` | 2026-09-05 | Public | Layout parsing, classification notes |
| HAVE (resource) | `resources/crosswalks/isco08_structure.csv` | ILO, "ISCO-08 EN Structure and definitions.xlsx" | 2026-09-05 | ILO, free reuse with attribution | ISCO code validation |
| HAVE (resource) | `resources/official/bra_headline.csv` | IBGE SIDRA API table 4092 | 2026-09-05 | Public | Validation |
| HAVE | `external/exposure/Final_Scores_ISCO08_Gmyrek_et_al_2025.xlsx`, `4digits_with_tasks.xlsx` (task-level scores and ILO exposure categories, 427 unit groups) | github.com/pgmyrek/2025_GenAI_scores_ISCO08 | 2026-09-05 | ILO WP 140, cite Gmyrek et al. 2025 | Exposure layer (`lfspanel.exposure`) |
| HAVE | `mex/enoe/{2021Q1..2026Q2}/enoe[_n]_YYYY_trimN_csv.zip` (22 files, 0.8 GB; 2021 = ENOE-N pandemic design) | INEGI ENOE microdatos; `_n_` naming through 2022, members ENOEN_/ENOE_ | 2026-09-05 | Open (INEGI open data) | Mexico panel |
| HAVE | `mex/enoe/docs/bulletins/*.pdf` | INEGI quarterly ENOE press bulletins (2023Q4 onward located) | 2026-09-05 | Public | Mexico validation |
| HAVE (resource) | `resources/crosswalks/sinco2019_to_isco08.csv`, `scian2018_to_isic4.csv` | World Bank GLD MEX ENOE utilities (converted from .dta) | 2026-09-05 | MIT (GLD) | Mexico occupation and industry |
| HAVE | `col/geih/{2022M01..2026M06}/*.zip` (54 files, 3.7 GB, CSV+DTA+SAV; three archive layouts) | DANE microdata catalogue entries 771/782/819/853/900, download/<resource> | 2026-09-05 | Open (DANE) | Colombia panel |
| HAVE | `col/geih/docs/anex-GEIH-<mmm><yyyy>.xlsx` | DANE anexo GEIH, national monthly and quarterly series | 2026-09-05 | Public | Colombia validation |
| HAVE | `arg/eph/{2021Q1..2026Q1}/EPH_usu_{q}_Trim_{yyyy}_txt.zip` (21 files, 65 MB) | INDEC `ftp/cuadros/menusuperior/eph/`; 2026Q2 not yet released | 2026-09-05 | Open (INDEC) | Argentina panel |
| HAVE (resource) | `resources/official/arg_headline.csv` | datos.gob.ar series API (INDEC EPH series 49.2_TAEP_0_0_37/25, 49.2_TAEO_0_0_30) | 2026-09-05 | Public | Argentina validation |
| HAVE (resource) | `resources/crosswalks/cno2017_to_isco08_2d.csv` | occupationcross (`data-raw/cross/cno17-isco08.xlsx`), CNO 2017 to ISCO-08 2 digits | 2026-09-05 | Open source | Argentina occupations |
| HAVE | `ecu/enemdu/{2021Q3..2026Q1}/1_BDD_ENEMDU_{yyyy}_{roman}_TRIMESTRE_SPSS.zip` (19 files, 138 MB; 2021Q1-Q2 exist only as monthly files under other names) | INEC `documentos/web-inec/EMPLEO/{yyyy}/<quarter folder>/`; 2026Q2 not yet published | 2026-09-05 | Open (INEC) | Ecuador panel |
| HAVE | `ecu/enemdu/docs/{yyyy}_{roman}_trimestre_Tabulados_Mercado_Laboral.xlsx` | INEC tabulados, newest quarter (all quarters since 2007 in one sheet) | 2026-09-05 | Public | Ecuador validation |
| HAVE | `per/epen/{2022Q1..2026Q2}/{code}-Modulo76.zip` (18 files, 130 MB) | INEI srienaho, EPEN "Nacional-Trim" module 76; survey codes in `fetch/per.py` | 2026-09-05 | Open (INEI) | Peru panel |
| HAVE | `per/epen/docs/informe_{period}.pdf` (2023Q1-2026Q2) | INEI quarterly reports via gob.pe publication pages (CDN links resolved at run time) | 2026-09-05 | Public | Peru validation (each report also covers the year-earlier quarter) |
| HAVE (manual) | `zaf/qlfs/{2022Q1..2026Q2}/qlfs-<year>-q<n>-v1.zip` (18 files, 92 MB) | DataFirst catalogue (login with CAPTCHA, ids in `fetch/zaf.py`), downloaded by hand | 2026-09-06 | CC-BY, cite Stats SA and DataFirst | South Africa panel |
| HAVE | `zaf/qlfs/docs/QLFS_Trends_2008-<quarter>.xlsx` | Stats SA P0211 QLFS Trends workbook | 2026-09-06 | Public | South Africa validation |
| HAVE (resource) | `resources/crosswalks/isco88_to_isco08.csv` | ILO correspondence ISCO-88 to ISCO-08 (`external/crosswalks/Correspondence_EN_ISCO_88_to_ISCO_08.xlsx`), built by `scripts/91_build_zaf_crosswalks.py` | 2026-09-06 | ILO | South Africa occupations |
| HAVE (resource) | `resources/crosswalks/sasco2003_to_isco88.csv` | World Bank GLD `isco88_sasco03_mapping.dta` (Support/B - Country Survey Details/ZAF) | 2026-09-06 | MIT (GLD) | South Africa occupations |
| HAVE | `geo/lfs/{2021..2025}/Labour-Force-Survey*.zip` (5 files, 17 MB; ECSTAT + demographic SPSS) | Geostat LFS databases page, media ids in `fetch/geo.py` | 2026-09-06 | Open (Geostat) | Georgia panel |
| HAVE | `geo/lfs/docs/30-Labour-Force-Indicators-Q.xlsx` | Geostat quarterly labour force indicators | 2026-09-06 | Public | Georgia validation |
| HAVE (manual) | `phl/lfs/{2021M01..2025M10}/PHL-PSA-LFS-<yyyy>-<mm>-PUF.zip` (19 files, 190 MB; July 2025 not yet released) | PSADA public-use files (login + Cloudflare), full-sample rounds Jan/Apr/Jul/Oct | 2026-09-06 | PSA terms of use | Philippines panel |
| HAVE (resource) | `resources/official/phl_headline.csv` | PSA OpenSTAT PXWeb API, table 0011B3FKEI1 (via curl: TLS 1.3 only) | 2026-09-06 | Public | Philippines validation |
| HAVE (manual) | `nga/nlfs/{2024Q1,2024Q3,2024Q4,2025Q1,2025Q2}/` (SPSS, Stata, zips; 830 MB) | NBS microdata catalogue (login), ids in `fetch/nga.py`; 2022Q4-2023Q3 and 2024Q2 still to download | 2026-09-06 | NBS terms of use | Nigeria panel |
| HAVE | `nga/nlfs/docs/NLFS_Q1_2024_Report.pdf`, `NLFS_Q2_2024.pdf` | NBS quarterly reports | 2026-09-06 | Public | Nigeria validation (hand-entered `resources/official/nga_headline.csv`) |
| NEED | India PLFS quarterly unit-level files | MoSPI microdata API (key in `.env`) | | MoSPI terms | M3 |
| MANUAL | GLD harmonized `.dta` for BRA, MEX, COL, ZAF, IND | World Bank GLD server / datalibweb (staff access) | | World Bank internal; do not redistribute | Backfill 2018-2021, validation |
