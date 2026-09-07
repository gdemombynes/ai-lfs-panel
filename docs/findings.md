# Findings (first pass, nine countries pooled plus India, 2026-09-07)

Question: since generative AI became widely available (reference quarter
2022 Q4), has employment in AI-exposed occupations grown more slowly than in
less exposed occupations, and is any gap concentrated among young workers?
Design and caveats: `docs/design/analysis-plan.md`.

Sample: Brazil, Mexico, Colombia, Argentina (urban), Ecuador, Peru, South
Africa, Georgia and the Philippines in the pooled estimates, with India
reported on its own (see below), 2021 Q1 to 2026 Q2 (Brazil, Mexico, Argentina and
Georgia start in 2021 Q1, Ecuador in 2021 Q3, the rest in 2022 Q1; 2026 Q1
for Argentina and Ecuador, 2025 Q4 for Georgia and the Philippines, whose July 2025 round is not
released). Seven pre-treatment quarters are available for the countries with
2021 data. Cells are country x
quarter x ISCO-08 occupation (3 digits; 2 digits for Argentina and Mexico) x
age group x sex, fixed at cells averaging at least 30 observations in 2022,
with zero employment where a cell is absent. Exposure: ILO 2025 GenAI scores
(Gmyrek et al., ILO WP 140), employment-weighted terciles at each digit level;
"high" = top tercile (35 % of employment). Estimates: cell and country x age
x sex x quarter fixed effects, baseline-employment weights, standard errors
clustered by country x occupation (544 clusters).

## Employment

High-exposure occupations did **not** lose employment relative to the rest.
Pooled, employment in high-exposure cells is 1.9 % higher after 2022 Q4
(difference in differences 0.019, SE 0.020; the Philippines adds noise
because its quarters alternate between regular and expanded survey rounds), and the event study rises from
about zero in 2023 to 4-5 % by 2025-2026 (`output/tables/event_study_log_emp.csv`,
`output/figures/es_log_emp_all.png`). With the 2021 quarters added the
pre-period is flat: the seven pre-treatment coefficients lie between -0.018
and +0.009, none distinguishable from zero. The continuous-exposure version gives the
same sign (0.12 log points per unit of score, SE 0.04).

The pooled result hides opposite country patterns:

| Country | Post x high (log employment) | SE |
|---|---|---|
| Peru | +0.105 | 0.044 |
| Brazil | +0.037 | 0.020 |
| Mexico | +0.029 | 0.019 |
| Philippines | +0.007 | 0.089 |
| Georgia | -0.005 | 0.095 |
| South Africa | +0.030 | 0.042 |
| Argentina | -0.014 | 0.038 |
| Colombia | -0.025 | 0.031 |
| Ecuador | -0.070 | 0.026 |

Ecuador is the only country where high-exposure employment fell relative to
the rest; Colombia is negative but imprecise. South Africa is positive but
imprecise: its 3-digit cells are thin (85 % fall under the 30-observation
floor), leaving 46 occupations and 1,836 cell-quarters, and the event-study
path is negative on average (-0.06) while the difference in differences is
+0.03, so the sign is not settled. Georgia's survey is small (about 14,000
persons a quarter), leaving 25 occupations and 900 cell-quarters, and its
estimate is uninformative. The Philippines carries occupation at two digits
only and its January and July rounds in some years are expanded samples
with a different composition (employee share 4 to 6 points higher than in
the regular rounds), which the drift check flags; its estimate is likewise
uninformative until the round design is handled as a break. Brazil's index by tercile
(`output/figures/emp_index_BRA.png`) shows the top two terciles up 9-11 %
by 2026 against 1 % for the least exposed tercile, consistent with a
continued shift of employment toward clerical, professional and service
occupations rather than displacement.

India (`output/tables/did_log_emp_withIND.csv`, country subset) is kept out
of the pooled estimates: its baseline employment would carry half of the
pooled weight and its pre-2025 quarters are first-visit samples of about
40,000 employed persons at 3-digit occupation, so the India rows would
dominate a pooled coefficient with noise rather than information (pooled
with India: -0.041, SE 0.124). Two rules in `analysis.build_cells` keep the
India series comparable across its breaks: cells start in 2021Q3, because
the first half of 2021 is coded in NCO-2004, and from 2025Q2 only
first-visit records enter, reweighted to the full sample's population by
quarter and sector, because the 2025 quarterly file pools first visits with
three revisits while every earlier file holds first visits only
(`FIRST_VISIT_RULES`, `MIN_PERIOD`). The 2025 sampling redesign itself
remains a level break that the fixed effects absorb only if it is uniform
across occupations.

On its own India shows no relative employment loss in exposed occupations.
The tercile difference in differences is -0.077 (SE 0.184; -0.052, SE 0.158,
on the comparable 2021Q3-2024Q4 window alone) and the event-study
coefficients for 2023-2024 lie between -0.02 and +0.10 (SE 0.04-0.08); the
2025 quarters sit at -0.00 to -0.14 with standard errors of 0.14-0.17, so
the redesign year adds nothing either way. The top quintile grows faster
than the rest, +0.20 (SE 0.05) with or without 2025, which is India's
expansion of clerical, finance and professional employment rather than a
sign of displacement; the young-worker interaction is -0.05 (SE 0.05). The
employment index by quintile (`output/figures/emp_index_q5_IND.png`) puts
the most exposed quintile at 118 in 2025 (2022 = 100), between the least
exposed quintile (112) and the middle (130).

Young workers (15-29) in high-exposure occupations show no relative
employment loss either (post x high x young 0.014, SE 0.012; young-only
difference in differences +0.038, SE 0.016).

## IT and business-process services: the industry view

Call-centre agents are too narrow a group for most of these surveys, so
`output/tables/itbpo_by_country.csv` and `output/figures/itbpo_by_country.png`
take the industry route: workers whose employer is in ISIC Rev.4 divisions
62 (computer programming and consultancy), 63 (information services, data
processing, hosting) or 82 (office and business support, which contains
call centres). Industry is coded at two digits or better in every country,
so the block is comparable, with two exceptions: South Africa's SIC 88
"business activities" lumps security, cleaning and recruitment into one
group that the crosswalk sends to 82, so South Africa is ISIC 62 only; and
Mexico's ENOE classifier puts computer services inside a single
professional-services code, so Mexico uses its "business support,
employment and secretarial services" code (ENOE 5611) alone. The block is
1 to 2 % of employment in most countries, 4 % in the Philippines, and holds
1,000 to 17,000 sample workers a year, enough for annual shares.

Employment in the block rose faster than total employment where the
sector exports (Philippines +28 % by 2025 against +6 % overall, Colombia
+22 % against +8 %, Brazil +9 % against +6 %, India +9 %, matching the
economy) and fell where it serves the domestic market (Ecuador -13 %, Peru
-14 %, Argentina -12 % to 2025). The split by occupation is the informative
part: within the block, professional and technical occupations grew in
every country while clerical and service occupations, the agents and
back-office staff, fell in Brazil (-12 % by 2026 against +28 % for
professionals), Ecuador (-27 %), Peru (-29 %) and Argentina, and rose only
where the sector as a whole was expanding (Colombia, Philippines, India).

The under-25 share of the block fell in all ten countries, by far more than
in the economy at large:

| Country | Under-25 share of IT-BPO workers, 2022 -> latest | Under-25 share, all employment |
|---|---|---|
| Brazil | 24.7 -> 19.0 (2026) | 14.8 -> 13.8 |
| Colombia | 23.3 -> 16.6 (2026) | 12.9 -> 11.9 |
| Mexico (ENOE 5611) | 22.4 -> 18.6 (2026) | 15.8 -> 14.2 |
| Ecuador | 21.6 -> 11.7 (2026) | 16.3 -> 14.5 |
| Peru | 25.0 -> 15.3 (2026) | 16.1 -> 13.8 |
| Philippines | 20.8 -> 14.7 (2025) | 13.3 -> 11.6 |
| India | 17.4 -> 14.7 (2025) | 11.7 -> 11.5 |
| Argentina | 13.6 -> 12.4 (2026) | 10.8 -> 10.2 |
| South Africa (ISIC 62) | 9.0 -> 7.5 (2026) | 6.5 -> 6.2 |
| Georgia | 15.9 -> 27.2 (2025; 56 to 92 sample workers) | 5.8 -> 6.2 |

A drop of 3 to 10 points in the youth share of a sector whose headcount is
flat or growing means that entry into it slowed while incumbents stayed,
the same reading as the call-centre cells and the young new-hire share in
the occupation analysis, now visible in every country with a usable
industry code. It is a description, not an estimate: sector growth, the
2024-2025 slowdown in outsourcing demand and generative AI all point the
same way, and the industry block mixes software engineers with agents.
Separating the two occupation groups is the next step, and the block is a
natural treated group for a sector-level difference in differences against
other white-collar service industries.

## Treatment definition: terciles, quintiles, deciles

The main results use the top employment-weighted tercile of the ILO score as
"high exposure" (35 % of employment, dominated by shop salespersons and
clerks). Re-running with the top quintile (23 % of employment, still led by
shop salespersons but with clerical and finance groups weighing more) and
the top decile changes little (`output/tables/did_*_high_q5.csv`,
`did_*_high_d10.csv`):

| Treatment | Employment, post x high | Young new-hire share, post x high |
|---|---|---|
| top tercile | +0.019 (0.020) | -0.009 (0.005) |
| top quintile | +0.018 (0.023) | -0.010 (0.005) |
| top decile | +0.031 (0.020) | -0.011 (0.008) |

Employment in exposed occupations is never lower after 2022 Q4 under any
cut, and the fall in the young new-hire share is about one percentage point
under all three, losing precision as the treated group shrinks. The quintile
event study for employment is flat before 2022 Q4 (all pre-period
coefficients within 0.011 of zero) and rises to about 3 % by 2025.

## Hiring margin

The new-hire share (workers in their job under 12 months; Brazil, Colombia,
Ecuador, Argentina, and Mexico first quarters only) tells a different story
for young workers. Among young workers, the new-hire share in high-exposure
occupations is about 1 percentage point lower after 2022 Q4 than at the
reference quarter, in every quarter from 2023 Q2 to 2025 Q4 (coefficients
-0.008 to -0.018, `output/figures/es_new_hire_share_young.png`), with no
change for older workers. The difference in differences against the full
pre-period is smaller than against 2022 alone (-0.009, SE 0.005, versus
-0.015 with a 2022-only pre-period; triple interaction -0.005, SE 0.004),
because the young new-hire share in exposed occupations was rising through
2021 and early 2022 and had already fallen back by 2022 Q4. Read as a break
in a rising trend rather than a level shift, the hiring result is weaker
than the first pass suggested
(`output/figures/es_new_hire_share_young.png`). The effect appears from
2023 Q2 and persists through 2025. By country it is driven by Brazil
(-0.010, SE 0.003); Colombia and Ecuador are flat or slightly positive, and
South Africa points the same way as Brazil (-0.012, SE 0.010; young workers
-0.020, SE 0.030) without the precision to say so.

Read together: employment stocks in exposed occupations kept growing, but
entry of young workers into them slowed in Brazil, the largest labour
market in the sample. This is the pattern Brynjolfsson, Chandar and Chen
(2025) describe for the United States, at a smaller magnitude, and it is
the result to probe first.

## Caveats

- The harmonizers were corrected on 2026-09-06 for a pandas behaviour that
  assigned categories to rows with missing inputs (education in Ecuador,
  Mexico, Colombia and the Philippines; Colombia's contract flag). Headline
  rates were never affected; the exposure results moved by less than one
  standard error.
- Seven pre-treatment quarters for five countries and three for the rest; the
  2021 quarters are still shaped by the pandemic recovery (Mexico's 2021 files
  are the ENOE-N design). The GLD 2018-2020 backfill would give a cleaner
  pre-trend test.
- Occupation depth differs (2 digits for Argentina and Mexico; South Africa's
  SASCO codes reach ISCO-08 at 4 digits for 71 % of employment), and Mexico's
  tenure question is asked in first quarters only.
- "Exposure" is task-based potential, not adoption; timing is a single global
  date. Country adoption indices are the next robustness check.
- Cells fixed at 30 baseline observations drop 40-70 % of cells in the
  smaller surveys (Ecuador, Peru, Argentina); the `--keep-small` variant of
  `41_event_study.py` keeps them.
- India's 2025 redesign is handled at the cell level (first visits only
  from 2025Q2, cells from 2021Q3), which removes the visit-composition and
  classification breaks but not the change of sampling frame; India is
  therefore reported alone.
- Peru's positive effect coincides with strong post-2023 recovery in
  commerce and services; Ecuador's negative effect with its 2024 energy
  crisis. Neither is identified as an AI effect.

Regenerate (pooled tables exclude India with `--exclude IND`; the
`--tag withIND` run adds India's own rows): `python scripts/30_attach_exposure.py && python scripts/40_build_cells.py
&& python scripts/41_event_study.py --outcome log_emp && python scripts/41_event_study.py
--outcome new_hire_share && python scripts/42_figures.py`.
