# Findings (first pass, eight countries, 2026-09-06)

Question: since generative AI became widely available (reference quarter
2022 Q4), has employment in AI-exposed occupations grown more slowly than in
less exposed occupations, and is any gap concentrated among young workers?
Design and caveats: `docs/design/analysis-plan.md`.

Sample: Brazil, Mexico, Colombia, Argentina (urban), Ecuador, Peru, South
Africa and Georgia, 2021 Q1 to 2026 Q2 (Brazil, Mexico, Argentina and
Georgia start in 2021 Q1, Ecuador in 2021 Q3, the rest in 2022 Q1; 2026 Q1
for Argentina and Ecuador, 2025 Q4 for Georgia). Seven pre-treatment
quarters are available for the countries with 2021 data. Cells are country x
quarter x ISCO-08 occupation (3 digits; 2 digits for Argentina and Mexico) x
age group x sex, fixed at cells averaging at least 30 observations in 2022,
with zero employment where a cell is absent. Exposure: ILO 2025 GenAI scores
(Gmyrek et al., ILO WP 140), employment-weighted terciles at each digit level;
"high" = top tercile (35 % of employment). Estimates: cell and country x age
x sex x quarter fixed effects, baseline-employment weights, standard errors
clustered by country x occupation (504 clusters).

## Employment

High-exposure occupations did **not** lose employment relative to the rest.
Pooled, employment in high-exposure cells is 2.2 % higher after 2022 Q4
(difference in differences 0.022, SE 0.013), and the event study rises from
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
| Georgia | +0.042 | 0.077 |
| South Africa | +0.030 | 0.042 |
| Argentina | +0.013 | 0.026 |
| Colombia | -0.025 | 0.031 |
| Ecuador | -0.070 | 0.026 |

Ecuador is the only country where high-exposure employment fell relative to
the rest; Colombia is negative but imprecise. South Africa is positive but
imprecise: its 3-digit cells are thin (85 % fall under the 30-observation
floor), leaving 46 occupations and 1,836 cell-quarters, and the event-study
path is negative on average (-0.06) while the difference in differences is
+0.03, so the sign is not settled. Georgia's survey is small (about 14,000
persons a quarter), leaving 25 occupations and 720 cell-quarters, and its
estimate is uninformative. Brazil's index by tercile
(`output/figures/emp_index_BRA.png`) shows the top two terciles up 9-11 %
by 2026 against 1 % for the least exposed tercile, consistent with a
continued shift of employment toward clerical, professional and service
occupations rather than displacement.

Young workers (15-29) in high-exposure occupations show no relative
employment loss either (post x high x young 0.014, SE 0.012; young-only
difference in differences +0.038, SE 0.016).

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
- Peru's positive effect coincides with strong post-2023 recovery in
  commerce and services; Ecuador's negative effect with its 2024 energy
  crisis. Neither is identified as an AI effect.

Regenerate: `python scripts/30_attach_exposure.py && python scripts/40_build_cells.py
&& python scripts/41_event_study.py --outcome log_emp && python scripts/41_event_study.py
--outcome new_hire_share && python scripts/42_figures.py`.
