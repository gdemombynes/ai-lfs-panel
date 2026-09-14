# Paper outline (2026-09-14)

Working title: Canaries in Emerging Economies: Generative AI Exposure and
Employment in Eleven Labour Force Surveys, 2021 to 2026

## 1. Introduction
- The claim from US payroll data (Brynjolfsson, Chandar and Chen 2025):
  employment of 22 to 25-year-olds in AI-exposed occupations fell after
  2022, older workers unaffected, read as adjustment at the hiring margin.
  The null in Danish administrative data (Humlum and Vestergaard 2025).
- Why emerging economies are a different test: younger workforces, high
  informality and self-employment, a large traded services sector exposed
  to both AI and offshoring demand, and later, uneven adoption.
- What exists for these countries: job-posting evidence (WDR 2026) and
  single-country studies (Brazil, Philippines); no multi-country survey
  evidence.
- Contribution: a harmonised quarterly panel from eleven national labour
  force surveys; three margins measured with the same code in every
  country (employment stocks, hiring rate of young workers, age
  composition of the IT and business-process sector); a public data
  product.
- Preview of results.

## 2. Data
- 2.1 Surveys. One table: country, survey, quarters in the panel, employed
  persons per quarter, minimum labour age, coverage limits (Argentina
  urban only).
- 2.2 Harmonisation. GLD-based schema; ISCO-08 occupation at three digits
  in eight countries and two in Argentina, Mexico, Bolivia and the
  Philippines; ISIC Rev. 4 industry at two digits or better; tenure in
  seven countries. Crosswalk quality by country (share of employment
  resolving to three digits).
- 2.3 Validation and breaks. Reproduction of published participation,
  employment and unemployment rates by quarter; documented breaks
  (Brazil 2025 reweighting, Colombia 2022 redesign, Philippine expanded
  rounds, Bolivia revised weights, South Africa 2025 status question) and
  how each is handled; the compatibility audit.
- 2.4 Exposure. ILO generative-AI occupational exposure index (Gmyrek,
  Berg and Bescond 2025) at the ISCO unit group, aggregated to minor
  groups with pooled 2022 employment weights; top employment-weighted
  quintile as the treated group (23 percent of employment), tercile and
  decile as checks; alternative indices (Anthropic Economic Index usage,
  Felten-Raj-Seamans, Eloundou et al.) through the SOC-ISCO crosswalk.
- 2.5 Why India is an annex. 2025 redesign (frame, sample, revisits),
  pre-2025 quarterly rural weights not designed for quarterly use, 76
  percent of three-digit cells under the observation floor, NCO-2004 in
  early 2021.

## 3. Empirical design
- Cells: country x quarter x occupation x age group (15-21, 22-25, 26-29,
  30-49, 50+) x sex; floor of 30 observations averaged over 2022; zero
  employment where a cell is absent.
- Outcomes: log employment; new-hire share (in the job under 12 months)
  among the employed in the cell; temporary-contract and part-time
  shares; usual hours.
- Event study around 2022Q4 with cell fixed effects and country x age
  group x sex x quarter fixed effects; difference in differences; triple
  difference with youth; continuous exposure; baseline-employment
  weights; clusters by country x occupation.
- What the fixed effects absorb (seasonality, recovery, macro shocks) and
  what they do not (occupation-specific trends unrelated to AI; adoption
  timing assumed common at 2022Q4).

## 4. Employment stocks
- Pooled event study: flat pre-period, +1.7 percent after 2022Q4 (SE 2.3),
  rising to about 3 percent by 2025.
- Country estimates: Ecuador (-0.11) and Uruguay (-0.05) negative; Brazil,
  Mexico, Peru, Georgia, Philippines, South Africa positive or zero;
  Argentina, Bolivia, Colombia near zero.
- Employment index by exposure quintile, pooled and by country: the top
  quintile grows, the middle quintiles grow faster, the bottom two are
  flat.
- Robustness: treatment cut (quintile, tercile, decile), two-digit cells
  for all, urban only, formal only, alternative indices,
  leave-one-country-out, pre-trends on the 2021 quarters.

## 5. Hiring of young workers
- Definition: share of employed 15 to 29-year-olds in the cell who started
  their job within 12 months; a hiring rate conditional on employment,
  available for Brazil, Colombia, Ecuador, Argentina, Uruguay (first
  interviews), South Africa and Mexico (first quarters).
- Result: about one percentage point lower in exposed occupations from
  2023Q2 through 2025 (-0.010, SE 0.005); smaller fall for older workers
  (-0.006, SE 0.002); a break in a rising 2021-2022 trend rather than a
  level drop.
- By country: Brazil and Uruguay drive it; Colombia negative but
  imprecise; Ecuador and South Africa go the other way.
- What the measure cannot separate: fewer hires versus longer retention of
  young incumbents; discussion of survey tenure versus payroll flows.

## 6. The IT and business-process services sector
- Definition: ISIC 62, 63 and 82 (South Africa 62 only; Mexico ENOE 5611);
  1 to 4 percent of employment; sample sizes by country.
- Headcount: rose where the sector exports (Philippines, Colombia, Brazil,
  India), fell where it serves the domestic market (Ecuador, Peru,
  Argentina).
- Occupation split within the sector: professional and technical
  occupations up in every country; clerical and service occupations down
  in Brazil, Ecuador, Peru and Argentina.
- Age composition: the under-25 share of sector employment fell three to
  ten points in all ten countries with usable codes, against one to two
  points economy-wide. A composition measure, consistent with slowed entry
  but also with ageing in place.
- Identified version: sector-level difference in differences of the youth
  share and of clerical employment against other white-collar service
  industries (finance, professional services, public administration).

## 7. Interpretation
- Three readings consistent with the facts: hiring-margin adjustment with
  incumbents retained; the 2024-2025 outsourcing demand cycle; secular
  ageing and professionalisation of the sector.
- What separates them: timing relative to 2022Q4; the occupation split
  within the sector; country adoption indices; the wage margin where
  available.
- Comparison with the US magnitude and with Denmark; why informality and
  self-employment dilute survey-based effects.

## 8. Conclusion
- What the evidence supports: no displacement of stocks, slower entry of
  young workers into exposed work, concentrated in traded services.
- What Egypt and the EU-LFS would add; the panel as a public good.

## Exhibits
- Table 1 Surveys, windows, sample sizes, occupation depth.
- Table 2 Country estimates, log employment, three treatment cuts.
- Table 3 Robustness (aggregation level, sample restrictions, indices).
- Table 4 Sector difference in differences.
- Figure 1 Pooled event study, log employment.
- Figure 2 Employment index by exposure quintile, pooled and by country.
- Figure 3 Young new-hire share event study.
- Figure 4 Under-25 share of IT-BPO employment by country, 2022 to latest.
- Figure 5 Occupation split within IT-BPO.
- Annex A Harmonisation notes and validation results by country.
- Annex B India: urban sample, 2021Q3-2024Q4, two-digit cells pooled to
  half-years, employment index by quintile, sector youth share.

## Still to do
- Sector-level difference in differences (Table 4).
- Occupation split within IT-BPO at the country level (Figure 5).
- Wage margin where wages exist (Brazil, Colombia, Ecuador, Peru, Uruguay
  implantation base, Bolivia).
- Egypt when the ERF files are located; EU-LFS after Eurostat approval.
- Adoption-timing interaction using the country indices.
