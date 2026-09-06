# South Africa: QLFS (quarterly, DataFirst public-use files)

Source: DataFirst catalogue entries `zaf-statssa-qlfs-<year>-q<n>-v1`
(ids in `fetch/zaf.py`), downloaded by hand because the portal login uses a
CAPTCHA; each zip holds a worker file as CSV and Stata. The Stata file is
read with pandas (readstat rejects its character set) with numeric codes.
Column names change case between releases and the 2025Q3 questionnaire
dropped `Q415TYPEBUSNS` (sector), so `ocusec` is NA from then on. Earnings
are not in the public file.

References: World Bank GLD `ZAF_2024_QLFS_V01_M_V01_A_GLD_ALL.do` and its
SASCO/SIC correspondence notes.

| Target | Source | Recode |
|---|---|---|
| hhid, pid | UQNO; + PERSONNO | |
| weight | Weight | |
| urban | Geo_type_code | 1 urban -> 1; 2 traditional, 3 farms -> 0 |
| subnatid1 | Province | 9 provinces |
| age, male | Q14AGE, Q13GENDER (1 male) | |
| educat7 | Q17EDUCATION | GLD rule: none/Grade R -> 1; grades 1-6 -> 2; grade 7 -> 3; grades 8-11, NTC I-III -> 4; grade 12, NTC III -> 5; N4-N6, certificates, diplomas -> 6; degrees -> 7 |
| minlaborage | | **15** |
| lstatus | Status | 1 employed -> 1; 2 unemployed (official definition) -> 2; 3 discouraged work-seeker -> 3 with `potential_lf = 1`; 4 other not economically active -> 3 |
| underemployment | Underempl | Stats SA time-related underemployment -> 1 |
| nlfreason | InactReason | 1 student -> 1; 2 home-maker -> 2; 3 health -> 4; 4 too young/old/retired -> 3; 5 discouraged, 6 other -> 5 |
| empstat | Q45WRK4WHOM (+ Q416NRWORKERS from 2025Q3) | to 2025Q2: 1 employee -> 1; 2 employer -> 3; 3 own account -> 4; 4 unpaid household business -> 2. **From 2025Q3 the codes changed meaning** (ICSE-18 style: 1 employee, 2 in own business, 3 helping in a family business, 4 paid apprentice, 5 helping a relative employed elsewhere): 2 is split into employer (3) when Q416 reports employees and own account (4) otherwise; 3, 5 -> 2; 4 -> 1. Found by the distribution-drift check, not by the release notes |
| ocusec | Q415TYPEBUSNS | 1 government, 2 government-controlled business -> 1; else 2; NA from 2025Q3 |
| industry | Q43INDUSTRY, SIC 5 (3 digits, ISIC Rev.3 structure) | `SIC3_TO_ISIC4` / `SIC_DIV_TO_ISIC4` in `harmonize/zaf.py`: Rev.4 division where the Rev.3 to Rev.4 correspondence is one to one (`isic_digits = 2`), section otherwise (`isic_digits = 1`, e.g. SIC 889 business services n.e.c. -> section N) |
| occupation | Q42OCCUPATION, SASCO 2003 (4 digits, ISCO-88 structure with national groups) | ISCO-88 unit groups -> ISCO-08 via the ILO correspondence (`isco88_to_isco08.csv`: whole-group target, else the targets sharing the most leading digits with the source, common prefix); national codes -> SASCO minor group -> ISCO-88 (GLD `sasco2003_to_isco88.csv`) -> common ISCO-08 prefix of the group. 2025Q1: 71 % of employment at 4 digits, 23 % at 3, 5 % at 2, 2 % unmapped |
| wage_no_compen | | **NA**: not released in the public-use file |
| whours | Q419TOTALHRS | hours last week, main job |
| contract | Q411CONTRACTTYPE | written contract 1 -> 1, 2 -> 0 |
| socialsec | Q46PENSION | employer pension contribution 1 -> 1, 2 -> 0 |
| firmsize_l/u | Q416NRWORKERS | bands: 0 employees -> 1; 1 -> 2; 2-4 -> 3-5; 5-9 -> 6-10; 10-19 -> 11-20; 20-49 -> 21-50; 50+ -> 51+ |
| tenure_months *, tenure_lt12 * | Q44YEARSTART, Q44MONTHSTART | months from job start to the quarter's middle month |

Validation: Stats SA "QLFS Trends 2008-<quarter>" workbook (P0211), Table 2,
both sexes, persons **15-64** (population, labour force, employed,
unemployed in thousands), tolerance 0.05 pp; the validation therefore uses
`population = "15-64"`. 18 quarters 2022Q1-2026Q2: 90 of 90 checks pass,
rates identical to Stats SA's to three decimals.
