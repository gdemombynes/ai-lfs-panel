# India: Periodic Labour Force Survey (MoSPI unit-level releases)

Source: MoSPI microdata portal (NADA), study ids in `fetch/ind.py`, fetched
through the REST API with the key in `.env` (`IND_API`). Two kinds of release
cover the window; `read/ind.py` picks the file by quarter:

| Release | Study | Quarters served | Records | Multiplier |
|---|---|---|---|---|
| `cy2021` .. `cy2024` | calendar-year files (old design) | 2021Q1-2024Q4 | first visit only, rural + urban, quarter label `qtr` | built for annual estimates |
| `cy2025` | calendar-year 2025 (new design, first-visit file) | 2025Q1 only | first visit only, monthly panels | annual |
| `q2025` | quarterly file April-December 2025 (new design) | 2025Q2-2025Q4 | all four visits | quarterly, as in the bulletins |

The 2025 redesign multiplied the sample by about 2.65, moved the survey year
from July-June to the calendar year and made quarterly estimates rural +
urban. Quarter labels in the old files run over the July-June cycle
(`Q3`-`Q6` in 2022 and 2024, `Q7`, `Q8`, `Q1`, `Q2` in 2021 and 2023);
`QUARTER_LABELS` in the reader converts them. Variable names changed three
times (`b6q5_cperv1` style to 2023, descriptive names in 2024, short names
from 2025); `ALIASES` maps every release onto the 2025 names, which are the
canonical names in `resources/keep_lists/ind.txt`. The survey month is only in
the household file before 2025 and is merged in.

## Weights

| Release | `weight` | Reason |
|---|---|---|
| `q2025` | `mult / 100` | MoSPI's quarterly multiplier; reproduces the quarterly bulletins exactly |
| `cy2022`-`cy2024` | `mult / 100`, or `mult / 200` when `nss != nsc` | MoSPI's rule for the calendar-year files is `mult / (no_qtr * 100)` (or 200 with two sub-samples); dropping the division by `no_qtr` (= 4 for nearly every stratum) gives the quarter-level weight, so each quarter sums to the population and the four quarters average to the annual estimate |
| `cy2021` | as above, times 2 | the 2021 file's multipliers are built per half-year panel (README: "estimate for the Half Yearly Panel"), so each quarter sums to half the population without the factor |
| `cy2025` | `mult / 100 * 4` | the 2025 first-visit file spreads the year's population over twelve monthly panels; one quarter holds a quarter of it. Only 2025Q1 uses this rule, marked by `raw_release = "cy2025"` |

Records with a weight above 1,000,000 are dropped (`MAX_WEIGHT`). No genuine
PLFS weight exceeds 0.9 million; the 2022 calendar file has one Assam rural
FSU (10386, July 2022, sub-strata 2 and 3, 28 persons) with multipliers of
1.2 to 23.7 million per person, which alone would add 240 million rural
residents to 2022Q3. With those rows dropped 2022Q3 sums to 1,162 million,
in line with the neighbouring quarters.

## Recodes

| Target | Source | Recode |
|---|---|---|
| int_month | month (2025) / household file `Month of survey` (earlier) | |
| wave | qtr | release quarter label |
| hhid, pid | sector + state + FSU + second-stage stratum + household no.; + person serial | stable across visits |
| rotation_group, visit_no | panel; visit (V1-V4) | |
| urban | sec | 2 -> 1 |
| subnatid1 | st | 36 states / union territories (GLD list) |
| age, male | age, sex (1 male) | |
| educat7 | gedu_lvl | 1-4 -> 1; 5 -> 2; 6 -> 3; 7 -> 4; 8-10 -> 5; 11 -> 6; 12-13 -> 7 (GLD) |
| minlaborage | | **15** (PLFS records status from age 5; GLD uses 5) |
| lstatus | acws (current weekly status) | 11-72 -> 1; **81, 82 -> 2**; 91-99 -> 3. GLD codes 82 (available, not seeking) as inactive and 98 (casual worker sick all week) as employed; MoSPI's published CWS rates need 82 unemployed and 98 inactive, and that is what is used here |
| empstat | acws | 11, 61, 62 -> 4 own account; 12 -> 3 employer; 21 -> 2 helper; 31, 41, 42, 51, 71, 72 -> 1 |
| nlfreason | acws | 91 -> 1; 92, 93 -> 2; 94 -> 3; 95 -> 4; 97-99 -> 5 |
| underemployment | hours available for additional work, 7 days | > 0 -> 1 (NA in 2021) |
| industry | aind_cws, NIC-2008 division | division = ISIC Rev.4 division, `isic_digits = 2` |
| occupation | ocu_cws, NCO-2015 at 3 digits (NCO-2004 in panel P2, i.e. 2021Q1-2021Q2) | NCO-2015 groups are ISCO-08 minor groups; validated against the ISCO-08 structure, 2-digit fallback for codes not in ISCO. NCO-2004 groups are ISCO-88 minor groups and go through the ILO ISCO-88 to ISCO-08 correspondence (`crosswalks.isco88_group_to_isco08`: modal ISCO-08 minor group of the unit groups, widened to 2 or 1 digits when no group covers half of them); about 20 % of 2021H1 codes (e.g. 920 agricultural labourers) resolve only to 2 digits |
| wage_no_compen, unitwage | ern_reg (regular, month); ern_self (self-employed, month); daily wages summed over the week (casual) | monthly (5) or weekly (2); NA in 2021 |
| whours | total hours worked on the 7 days | NA in 2021 |
| potential_lf, ocusec, contract, socialsec, firmsize, tenure | | **NA**: recorded for the usual principal activity only and absent from the quarterly file |

Series notes: 2021Q1-2025Q1 are first-visit samples of about 100,000 persons
per quarter (290,000 in 2025Q1); 2025Q2 onwards are all-visit samples of about
560,000. The 2025Q1 quarter is the only one with the times-four rule and has
no published quarterly rates. Treat 2025Q2 as a design break: the analysis
layer (`lfspanel.analysis.FIRST_VISIT_RULES`, `MIN_PERIOD`) builds India's
cells from first-visit records only from 2025Q2, reweighted to the full
sample's population by quarter and sector, and starts them in 2021Q3; the
harmonized partitions themselves keep every visit with the official weights
so that validation against the bulletins stays exact.

## Validation

Hand-entered in `resources/official/ind_headline.csv`, all current weekly
status, persons 15+:

- calendar years 2021-2024 (rural, urban, total) from MoSPI's calendar-year
  key-indicator notes, compared with the four quarters pooled (tolerance
  0.15 pp; 0.25 pp for rural 2022, where the Assam FSU's remaining
  sub-stratum still adds a little weight);
- urban quarters 2021Q4-2024Q4 from the PLFS quarterly bulletins (PIB
  releases 1902106, 2005297, 2104358), which use all four visits while our
  files hold first visits only. First-visit participation and employment
  ratios run about 1 pp above the all-visit bulletin in every quarter (a
  known panel-conditioning pattern), unemployment within 0.7 pp, so these rows
  carry tolerances of 2.0 pp (LFPR, WPR) and 0.7 pp (UR) and serve as a
  sanity check rather than a reproduction;
- 2025Q2-2025Q4 (rural, urban, total) from the October-December 2025
  bulletin, statements 1, 2 and 5, tolerance 0.06 pp.

Results (`output/tables/validation_official_ind.csv`): 99 of 100 checks
pass. The four calendar years reproduce MoSPI's published CWS rates to within
0.05 pp in 2021, 2023 and 2024 and within 0.23 pp in 2022; the three 2025
quarters match the bulletin to within 0.05 pp for every rural, urban and
total rate. The one failure is 2021Q4 urban WPR, 2.1 pp above the bulletin
(first-visit sample). 2025Q1 has no published quarterly rate; its annual
2025 counterpart is a usual-status figure and is not comparable.

Codebook drift (`scripts/25_codebook_drift.py`): the raw code changes are the
release boundaries (variable renames, `nss`/`no_qtr` dropped in 2025, visits
V2-V4 appearing in 2025Q2). Distribution flags are the kharif-season swings
in agriculture (industry 1, occupation 6) every third quarter and the 2025Q1
design change in `empstat`.

## Call centres in PLFS

The CWS job carries occupation at 3 digits and industry at 2, so contact
centre clerks (ISCO 4222) cannot be separated from other client-information
workers (ISCO 422) and call centres (NIC 82200) cannot be separated from
office support (NIC 82). The usual principal activity in the first-visit
files does carry a 5-digit NIC code. Workers whose principal industry is
82200 "activities of call centres" (`output/tables/callcentre_ind_nic82200.csv`,
first-visit files, weights as above):

| Year | Sample | Employment | Under 25 | Under 30 | Women | Occupations |
|---|---|---|---|---|---|---|
| 2022 | 87 | 221,000 | 40.7 % | 66.0 % | 38.1 % | 524 other sales (telemarketers), 422, 333 |
| 2023 | 74 | 160,000 | 36.4 % | 77.5 % | 41.2 % | 524, 413, 521 |
| 2024 | 78 | 261,000 | 29.7 % | 70.1 % | 31.4 % | 524, 521, 422 |
| 2025 | 224 | 259,000 | 26.6 % | 64.6 % | 45.4 % | 524, 422, 352 |

PLFS finds a quarter of a million call-centre workers, a fraction of the
industry's own headcounts, and fewer than a hundred sample cases a year before
2025, so the fall in the under-25 share (41 % to 27 %) has a standard error
of about 5 points and is suggestive only. Most of these workers are coded as
sales workers (NCO 524, telemarketers) rather than client-information clerks.
