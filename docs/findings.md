# Findings (first pass, six countries, 2026-09-05)

Question: since generative AI became widely available (reference quarter
2022 Q4), has employment in AI-exposed occupations grown more slowly than in
less exposed occupations, and is any gap concentrated among young workers?
Design and caveats: `docs/design/analysis-plan.md`.

Sample: Brazil, Mexico, Colombia, Argentina (urban), Ecuador and Peru,
2022 Q1 to 2026 Q2 (2026 Q1 for Argentina and Ecuador). Cells are country x
quarter x ISCO-08 occupation (3 digits; 2 digits for Argentina and Mexico) x
age group x sex, fixed at cells averaging at least 30 observations in 2022,
with zero employment where a cell is absent. Exposure: ILO 2025 GenAI scores
(Gmyrek et al., ILO WP 140), employment-weighted terciles at each digit level;
"high" = top tercile (35 % of employment). Estimates: cell and country x age
x sex x quarter fixed effects, baseline-employment weights, standard errors
clustered by country x occupation (433 clusters).

## Employment

High-exposure occupations did **not** lose employment relative to the rest.
Pooled, employment in high-exposure cells is 2.4 % higher after 2022 Q4
(difference in differences 0.024, SE 0.012), and the event study rises from
about zero in 2023 to 4-5 % by 2025-2026 (`output/tables/event_study_log_emp.csv`,
`output/figures/es_log_emp_all.png`). Pre-period coefficients are flat
(2022 Q1-Q3 within 0.01 of zero). The continuous-exposure version gives the
same sign (0.12 log points per unit of score, SE 0.04).

The pooled result hides opposite country patterns:

| Country | Post x high (log employment) | SE |
|---|---|---|
| Peru | +0.105 | 0.044 |
| Brazil | +0.037 | 0.020 |
| Mexico | +0.029 | 0.019 |
| Argentina | +0.013 | 0.026 |
| Colombia | -0.025 | 0.031 |
| Ecuador | -0.070 | 0.026 |

Ecuador is the only country where high-exposure employment fell relative to
the rest; Colombia is negative but imprecise. Brazil's index by tercile
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
occupations fell by 1.5 percentage points after 2022 Q4 relative to less
exposed occupations (SE 0.5; triple interaction -0.012, SE 0.005), with no
change for older workers (-0.003, SE 0.003)
(`output/figures/es_new_hire_share_young.png`). The effect appears from
2023 Q2 and persists through 2025. By country it is driven by Brazil
(-0.010, SE 0.003); Colombia and Ecuador are flat or slightly positive.

Read together: employment stocks in exposed occupations kept growing, but
entry of young workers into them slowed in Brazil, the largest labour
market in the sample. This is the pattern Brynjolfsson, Chandar and Chen
(2025) describe for the United States, at a smaller magnitude, and it is
the result to probe first.

## Caveats

- Four pre-treatment quarters only; the GLD 2018-2021 backfill (milestone 3)
  is needed for a real pre-trend test.
- Occupation depth differs (2 digits for Argentina and Mexico), and Mexico's
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
