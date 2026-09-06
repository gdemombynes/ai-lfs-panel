# Nigeria: Labour Force Survey (NLFS, quarterly since 2022 Q4, ICLS-19)

Source: NBS microdata catalogue (login; ids in `fetch/nga.py`), downloaded by
hand into `data/raw/nga/nlfs/<YYYYQn>/`. Formats differ by release: SPSS for
2024Q1 (needs an explicit UTF-8 flag), Stata for 2024Q3 and 2024Q4 (read with
pandas, since readstat rejects the character set), and zips of Stata files
from 2025Q1. Not yet on disk: 2022Q4, 2023Q1-Q3 and 2024Q2. The NBS
questionnaire follows the 19th ICLS, so subsistence farmers are outside
employment; that is also the basis of NBS's published rates.

Reference: World Bank GLD `NGA_2024_LFS_V02_M_V01_A_GLD_ALL.do` and its
"Converting between ICLS definitions" note.

| Target | Source | Recode |
|---|---|---|
| int_month | interviewdate | |
| hhid, pid | interview_key; + hhroster_id | |
| weight | popw | quarterly population weight (sums to about 217 million) |
| urban | id5_sector | 1 urban -> 1, 2 rural -> 0 |
| subnatid1 | id1_zone | six geopolitical zones |
| age, male | dc5, dc3 (1 male) | |
| educat7 | ed7 (highest qualification) | GLD rule: none -> 1; FSLC -> 3; MSLC, JSS -> 4; SSCE/O level -> 5; A level, NCE/ND/nursing, tech/prof, vocational -> 6; degree and above -> 7 |
| minlaborage | | **15** |
| lstatus | atw1, agf1b_4, agf2a-d (employed); um1_1, um1_2, um4, um9, um10a, um10b | employed = paid work for others, a non-farm job or business, or farming whose products are mainly sold; unemployed = searched in the last four weeks or has a job arranged, and available now or within two weeks; else NLF. Reproduces NBS 2024Q1 (77.3 / 5.3 / 73.2) within 0.06 pp; the GLD rule without future starters and two-week availability gives 5.1 % unemployment |
| potential_lf | um1_*, um10a | searching but not available, or available but not searching |
| underemployment | sjj7 | wants more hours -> 1 |
| nlfreason | um7 | retired/too old -> 3; disabled -> 4; else 5 |
| empstat | mjj4, mjj6, mjj8b_9 | 1 employee -> 1; 2 own business -> 4, or 3 (employer) when it hires paid employees; 3 helping household business -> 2; 4 apprentice -> 5, or 1 when paid; 5 helping a relative employed elsewhere -> 5 |
| ocusec | mjj8a | government, state-owned enterprise -> 1; else 2; self-employed without answer -> 2 |
| industry | mjj3cclean, ISIC Rev.4 | identity, 4 digits (leading zeros restored) |
| occupation | mjj2cclean, ISCO-08 | identity, 4 digits; > 99 % at 4 digits |
| wage_no_compen | | **NA** for now (sjj12 with unit sjj10 not yet crosswalked) |
| whours | mjj12 | usual hours per week, main job |
| contract | mjj8c | written or oral agreement -> 1; none -> 0 |
| socialsec | mjj8l_1 | employer pension contribution -> 1 |
| tenure_months *, tenure_lt12 * | mjj10, mjj11 | months from job start to the interview date |

Drift check (first run): the urban share of the population swings between
42 % and 58 % across 2024Q3-2025Q1, and the agriculture share of employment
moves by 8 points between 2024Q1 and 2024Q3 (2024Q2 is missing, and Q3 is
the farming season). Both point to quarter-specific weighting rather than a
code change; treat Nigeria's quarters as noisy until NBS's own quarterly
rates for 2024Q3 onward can be checked.

Validation: NBS quarterly reports (PDF), headline participation, unemployment
and employment-to-population rates, persons 15+, tolerance 0.06 pp. 2024Q1:
3 of 3 checks pass. Reports for 2024Q3 onward were not found on the NBS site;
those quarters are unvalidated until NBS posts them.
