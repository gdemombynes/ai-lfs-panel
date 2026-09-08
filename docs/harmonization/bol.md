# Bolivia: Encuesta Continua de Empleo (INE quarterly files)

Source: INE Bolivia. Two kinds of file, both downloaded by hand because the
ANDA catalogue (anda.ine.gob.bo, one entry per quarter, ids in
`fetch/bol.py`) requires an account: a pooled file `ECE_4T2015_3T2025.zip`
(Stata, SPSS and CSV members, every quarter from 2015Q4 to 2025Q3 on INE's
revised expansion base, 2.2 million person records, saved under
`data/raw/bol/ece/pooled/`) and one zip per quarter from 2025Q4 (`ECE_4T2025.zip`
under `data/raw/bol/ece/2025Q4/`). `fetch/bol.py` registers what is present
and prints the catalogue URL of what is missing; `extract_pooled` unpacks the
pooled CSV once and transcodes it to UTF-8 (0.3 % of lines carry
Windows-1252 bytes in establishment names). `read/bol.py` pulls one quarter
out of the pooled CSV with DuckDB (about 17 s) or reads the Stata member of
a per-quarter zip; both give the same kept columns.

Design: continuous quarterly survey since 2015Q4, rotating panel of
households (`panel`), national coverage (urban and rural), about 52,000
persons and 12,000 households a quarter (2020Q2-Q4 smaller, pandemic).
Persons 14 and over answer the labour module; INE's own flags `pet`
(working-age), `peao` (employed) and `pead` (unemployed) define status.
Quarterly expansion factor `fact_trim_act` (revised base, all quarters of the
pooled file and 2025Q4 onward); `fact_trim` (original base) exists only in
the older per-quarter files and is the fallback.

| Target | Source | Recode |
|---|---|---|
| int_month | meses | months since January 1960: `meses % 12 + 1` |
| hhid, pid, rotation_group | period + id_hogar; + nro; panel | ids are unique within a quarter only |
| weight | fact_trim_act (fact_trim if absent) | |
| urban | area | 1 urban -> 1, 2 rural -> 0 |
| subnatid1 | depto | 9 departments |
| age, male | s1_03a, s1_02 (1 man) | |
| educat7 | niv_ed (0 none, 1-2 primary, 3-4 secondary, 5 higher, 7 other) and s1_07a (level and course passed) | 0 -> 1, 1 -> 2, 2 -> 3, 3 -> 4, 4 -> 5; 5 -> 7 when s1_07a is a university code (72-76), else 6; 7 "other" -> NA |
| minlaborage | | **14** (INE's working-age population) |
| lstatus | pet, peao, pead | peao -> 1; pead -> 2; other pet -> 3; NA under 14 |
| underemployment | psubocup | 1 -> 1 |
| nlfreason | s2_07 | 1 student, 2 homemaker, 3 retired, 4 ill or disabled, 5 elderly -> 1-5; 6 other -> 5 |
| empstat | s2_18 | 1 employee, 7 domestic worker -> 1; 5 unpaid family, 6 unpaid apprentice -> 2; 3 employer -> 3; 2 own account -> 4; 4 cooperative member -> 5 |
| ocusec | s2_22 | 1 public administration, 2 public enterprise -> 1; 3-6 -> 2 (employees only; NA otherwise) |
| industry | s2_16acod, CAEB (5 digits; first four are the ISIC Rev.4 class) | first four digits, `isic_digits` = digits present (2-4) |
| occupation | s2_15acod, COB 2009 (5 digits; first four follow ISCO-08) | first four digits validated against the ISCO-08 structure: 72 % of the employed at 3 or more digits, 11 % at 4; 2-3 % carry 1-3 digit codes |
| wage_no_compen, unitwage | yprilab | monthly labour income, main job (Bs); unit 5 = month |
| whours | phrs | weekly hours, main job |
| contract | s2_21 (employees) | 1 permanent, 2 fixed term, 4 written other -> 1; 3 verbal, 5 none -> 0 |
| socialsec | s2_64a | 1 employer pays pension contributions, 2 pays own -> 1; 3 already retired, 4 no -> 0; asked of employees only (about 26 % of the employed), **NA in 2021** (question introduced 2022Q1) |
| firmsize_l, firmsize_u | s2_26a bands | 1; 2-5; 6-10; 11-20; 21-30; 31-50; 51-100; 101+ |
| tenure_months, tenure_lt12 | | **NA** (no start-date question in the public file) |

Validation: INE's quarterly press notes give urban rates only, with no
stable table; ILOSTAT carries the national quarterly series INE reports
(persons 15+, source "ECE"), fetched by `official.ilostat_bol`. Results
(`output/tables/validation_official_bol.csv`): 60 of 60 checks pass. The
unemployment rate is within 0.12 pp in every quarter (0.06 pp from 2021Q2).
Participation and employment rates match exactly in 2025Q4 but run 0.15-0.38
pp above ILOSTAT from 2021Q1 to 2025Q3: ILOSTAT holds the rates INE
published on the original expansion base, while the pooled microdata carry
the revised base, so those cells get a 0.4 pp tolerance. The revised base
is what makes the series internally consistent: no level break at 2025Q4.

Compatibility audit: one flag, the 2022Q1 fall in missing `socialsec`
(question introduced). The codebook-drift report flags `meses`, `panel` and
`gestion` every quarter by construction (interview months and rotation
panel numbers advance). The distribution report flags agriculture
(`occup` 6) in 2022Q1: the agricultural share of employment falls from 28-29
% in 2021 to 25-26 % in 2022 and drifts down to 22-24 % by 2025, with the
largest single step between 2021Q4 and 2022Q1; 2021 is the post-pandemic
year and the move is in the data, not the recode (the urban share rises
from 63 % to 67 % over the same span).
