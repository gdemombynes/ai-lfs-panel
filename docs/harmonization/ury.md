# Uruguay: Encuesta Continua de Hogares (INE monthly bases)

Source: INE's NADA catalogue (one entry per year, ids in `fetch/ury.py`),
open download behind a terms-of-use form (research use, no redistribution,
cite INE, send INE a copy of publications; accepted by the user on
2026-09-07 and re-posted by the fetcher for each entry). Each year ships
twelve monthly bases `ECH_MM_YY.csv` (2022-2024) or `ECH_MM_YYYY.csv`
(2025), an implantation base, the variable dictionary and questionnaires.
The 2021 second-half monthly bases come inside a RAR that `bsdtar` unpacks
(`extract_archive`); the 2021 first half is the previous annual design and
is not used. `read/ury.py` stacks the three monthly bases of a quarter and
merges the job start date from the implantation base (asked at the first
interview only). Variable names are matched case-insensitively: 2021-2022
use `region_4`, `niv_edu`, `w`; 2022 has no interview-round variable.

Design: rotating panel since July 2021, each household interviewed up to
six times in consecutive months (`ronda`), persons aged 14 and over only,
monthly weight `W` summing to the 14+ population. Sample about 10,300
households and 20,800 persons a month from 2022; July-December 2021 ramps up
from 4,000 to 20,000 persons as the panel fills. A quarter therefore holds
person-months: the same person can appear in up to three months, so `pid`
carries the month and `weight = W / months present`, which makes each
quarter sum to the population once and the quarter's rates the average of
INE's monthly rates.

| Target | Source | Recode |
|---|---|---|
| int_month | mes | |
| hhid, pid, rotation_group, visit_no | anio-ID; + nper + mes; GR; ronda (NA in 2021-2022) | |
| weight | W / 3 (or / months present) | monthly weight |
| urban | REGION_4 (1 Montevideo, 2 towns 5000+, 3 towns under 5000, 4 rural) | 1-3 -> 1, 4 -> 0; `region` as fallback (3 -> 0) |
| subnatid1 | dpto | 19 departments |
| age, male | e27, e26 (1 man) | |
| educat7 | years passed by level (e51_2 primary, e51_4_a/b lower secondary, e51_5/6 upper secondary, e51_8/9 tertiary non-university, e51_10/11 university) and completion flags (e197_1 primary, e201_1c/d upper secondary) | 1 none; 2 primary incomplete; 3 primary complete; 4 secondary incomplete; 5 secondary complete; 6 tertiary non-university; 7 university |
| minlaborage | | **14** (the base holds persons 14+) |
| lstatus | POBPCOAC | 2 -> 1; 3 (first-time seekers), 4, 5 (on unemployment insurance) -> 2; 6-11 -> 3 |
| underemployment | SUBEMPLEO | 1 -> 1 |
| nlfreason | POBPCOAC | 7 student -> 1; 6 domestic -> 2; 9, 10 pensioner/retired -> 3; 8, 11 -> 5 |
| empstat | f73 | 1, 2, 8 employees -> 1; 7 unpaid family -> 2; 4 employer -> 3; 5, 6 (to 2024), 9 (2025) own account -> 4; 3 cooperative member -> 5 |
| ocusec | f73 | 2 public employee -> 1, else 2 |
| industry | f72_2, CIIU Rev.4 | identity, `isic_digits = 4` |
| occupation | f71_2, CIUO-08 | identity, validated against the ISCO-08 structure (99.9 % at 4 digits) |
| wage_no_compen | | **NA**: earnings are in the implantation base only |
| whours | f85 | usual weekly hours, main job |
| socialsec | f82 | contributes to a pension fund: 1 -> 1, 2 -> 0 |
| contract, firmsize | | **NA** (firm size in the implantation base only) |
| tenure_months, tenure_lt12 | f307 (year started), f308 (month, 0 when not recalled), implantation base | exact when the month is known; with the month unknown, a start two or more years back is at least 12 months and a start this year under 12, a start last year is left missing. Available for first interviews only, about 20 % of person-months |

Validation: INE's monthly "Actividad, Empleo y Desempleo" publication pages
on gub.uy state the month's activity, employment and unemployment rates
(persons 14+, whole country); `official.informes_ury` scrapes them and
averages the three months of a quarter (tolerance 0.15 pp; 0.4 pp for
2022Q1-Q2, whose monthly bases INE re-issued on 2022-11-22 with a corrected
POBPCOAC after the reports had been published; 0.8 pp for 2021Q3-Q4, the
panel's start-up months, where the archived bases put participation and
employment 0.7 pp above the published rates while unemployment matches).
Results (`output/tables/validation_official_ury.csv`): 54 of 54 checks
pass; from 2022Q2 onward every quarter is within 0.09 pp of INE's monthly
rates, 2022Q1 within 0.33 pp.

Encoding: the monthly bases switch between latin-1 (2021 to mid-2022, March
to December 2025) and UTF-8 (mid-2022 to February 2025); the reader detects
it per file. Rotation groups (`GR`) renumber every quarter by design and
show up in the codebook-drift report as code changes.
