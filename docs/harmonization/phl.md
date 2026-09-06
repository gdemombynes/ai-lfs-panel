# Philippines: Labor Force Survey (PSA public-use files, full-sample rounds)

Source: PSADA public-use files, downloaded by hand (the portal has a
Cloudflare challenge and a login) into `data/raw/phl/lfs/<YYYYMnn>/`. The
survey is monthly since 2021, but only January, April, July and October carry
the full sample (about 44,000 households; some rounds are expanded to
180,000), so each quarter is represented by its first-month round. The CSV
inside the archive is read (`LFS PUF <Month> <Year>.CSV`); some rounds carry a
UTF-8 byte-order mark in the first column name, and the urban flag is
`PUFURB2015` before 2024 and `PUFURB2020` from 2025 (absent in April 2024).

Expanded rounds: July 2021, January 2022, July 2023 and January 2024 carry
about 180,000 households against 44,000 in the regular rounds, and their
weighted composition differs (employee share 4 to 6 points higher), which
the distribution-drift check flags. Treat the alternation as a survey-design
break in any Philippine-only analysis.

Persons 15+ with no labour status (overseas Filipino workers and other
non-household members) are dropped: PSA excludes them from the population
15 and over, and keeping them overstated it by 2.3 %.

| Target | Source | Recode |
|---|---|---|
| int_month | PUFSVYMO | round month |
| hhid, pid | year + month + PUFHHNUM; + PUFC01_LNO | households are renumbered each round |
| weight | PUFPWGTPRV | |
| urban | PUFURB2020 / PUFURB2015 | 1 -> 1, 2 -> 0; NA in April 2024 |
| subnatid1 | PUFREG | 18 regions |
| age, male | PUFC05_AGE, PUFC04_SEX (1 male) | |
| educat7 | PUFC07_GRADE (PSCED 2017, 5 digits) | GLD 2019+ rule: 0xxxx -> 1; 1xxxx elementary -> 2, 10018 graduate -> 3; 2xxxx junior high -> 4, 24015 completed -> 5; 3xxxx senior high -> 4, 34013/35013 graduate -> 5; 4xxxx, 5xxxx -> 6; 6xxxx-8xxxx -> 7 |
| minlaborage | | **15** |
| lstatus | PUFNEWEMPSTAT | 1 employed, 2 unemployed, 3 not in the labour force (2005 definition) |
| underemployment | PUFC20_PWMORE | wants more hours -> 1 |
| nlfreason | PUFC34_WYNOT | 08 schooling -> 1; 07 household duties -> 2; 61 too young/old, 62 retired -> 3; 63 disability, 03 illness -> 4; other -> 5 |
| empstat | PUFC23_PCLASS | 0-2, 5 employees (private household, private establishment, government, paid family) -> 1; 3 self-employed -> 4; 4 employer -> 3; 6 unpaid family -> 2 |
| ocusec | PUFC23_PCLASS | 2 government -> 1, else 2 |
| industry | PUFC16_PKB, PSIC 2009 at 2 digits | = ISIC Rev.4 division, `isic_digits = 2` |
| occupation | PUFC14_PROCC, PSOC 2012 at **2 digits** | ISCO-08 sub-major groups (01-03 armed forces); `occup_isco_digits = 2` |
| wage_no_compen, unitwage | PUFC25_PBASIC | basic pay per day for employees (`unitwage = 1`); 0 for unpaid |
| whours | PUFC19_PHOURS | hours last week, primary job |
| contract, socialsec, firmsize | | **NA**: not in the public-use file (nature of employment PUFC17 kept in the raw extract) |
| tenure_months *, tenure_lt12 * | | **NA** |

Validation: PSA OpenSTAT table "Levels of Key Employment Indicators"
(PXWeb API, `0011B3FKEI1.px`; persons 15+, thousands), the round month's
figures against the quarter, tolerance 0.05 pp. 18 rounds 2021Q1-2025Q4
(July 2025 not yet released): 90 of 90 checks pass, rates identical to PSA's
to three decimals.
