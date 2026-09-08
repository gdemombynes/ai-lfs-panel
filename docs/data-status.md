# Data status by country (2026-09-07)

"Latest in panel" is the last harmonized quarter; "next" is when the
following quarter is expected from the source. Sample sizes are employed
persons per quarter after harmonization. Occupation digits are the share of
employment coded at 3 or more ISCO-08 digits (the cell analysis uses 3
digits where that share is at least 90 %, else 2). Details and validation
results per country: `docs/harmonization/<ccc>.md`; the machine-generated
audit: `docs/compatibility.md`.

| Country, survey | Window in panel | Latest in panel; next | Employed per quarter | Occupation depth | Main issues |
|---|---|---|---|---|---|
| Brazil, PNAD Contínua | 2021Q1-2026Q2 | 2026Q2; 2026Q3 due Nov 2026 | 200,000 | 99 % at 4 digits | Whole series re-weighted Aug 2025 (Census 2022) and 2024Q2 re-issued Mar 2026: one vintage kept, `raw_release` recorded. Otherwise the reference implementation: tenure, wages, formality all present. |
| Mexico, ENOE | 2021Q1-2026Q2 | 2026Q2; 2026Q3 due Nov 2026 | 175,000 | 61 % at 3, 41 % at 4 digits (SINCO crosswalk) | Occupation reliable at 2 digits only; industry codes group all professional services (incl. IT) into one section-level code; tenure asked in first quarters only; 2021 is the pandemic ENOE-N design; validated on the 9 quarters with located bulletins. |
| Colombia, GEIH | 2022Q1-2026Q2 | 2026Q2; monthly, next month due Sep 2026 | 90,000 | 100 % at 4 digits | Starts at the 2022 redesign, so no 2021 pre-period; wages filled for 53 % of the employed; three monthly files stacked with weight / 3. |
| Argentina, EPH | 2021Q1-2026Q1 | 2026Q1; 2026Q2 due Sep 2026 | 20,000 | 2 digits only (CNO 2017 crosswalk) | Urban agglomerations only (about two thirds of the population); minimum labour age 10; occupation at 2 digits and about 5 % of codes mapped by prefix; 1 % of industry codes at the division only. |
| Ecuador, ENEMDU | 2021Q3-2026Q1 | 2026Q1; 2026Q2 due Aug-Sep 2026 | 35,000 | 100 % at 4 digits | 2021Q1-Q2 exist only as monthly files (not fetched); wages filled for 60 %; small sample so 72 % of 3-digit cells fall under the 30-observation floor. |
| Peru, EPEN | 2022Q1-2026Q2 | 2026Q2; 2026Q3 due Nov 2026 | 40,000 | 95 % at 3, 88 % at 4 digits | National file only (no department), no tenure, no 2021 (would need ENAHO or GLD); a handful of duplicate ids per quarter left as published. |
| South Africa, QLFS | 2022Q1-2026Q2 | 2026Q2; 2026Q3 due Nov 2026 (manual DataFirst download, CAPTCHA login) | 25,000 | 93 % at 3, 71 % at 4 digits (SASCO to ISCO-88 to ISCO-08) | No wages; industry at 1-2 digits with "business services" lumped, so ISIC 82 unusable; status-in-employment question changed 2025Q3 (ICSE-18), recoded; 2021 needs four more files; 85 % of 3-digit cells under the floor. |
| Georgia, LFS | 2021Q1-2025Q4 | 2025Q4; 2026 quarters arrive with the 2026 annual database, mid-2027 | 8,000 | 100 % at 4 digits | Small survey (14,600 persons a quarter): 92 % of 3-digit cells under the floor, country estimates uninformative; persons 15+ only; no tenure, wages in bands only. |
| Philippines, LFS | 2021Q1-2025Q4, 2025Q3 missing | 2025Q4; Jan 2026 round PUF pending on PSADA (manual download, Cloudflare login) | 40,000 (150,000 in expanded rounds) | 2 digits only (PSOC published at 2) | Every other January and July is an expanded round with four times the sample and a different composition (participation 4-5 pts lower, employee share 6 pts higher); July 2025 round not released; no tenure; wages for 56 %; persons 15+ only. |
| Nigeria, NLFS | 2024Q1, 2024Q3-2025Q2 | 2025Q2; 2025Q3-Q4 status unknown; 2022Q4-2023Q3 and 2024Q2 still to download | 20,000 | 100 % at 4 digits | Patchy series with a gap at 2024Q2; only 2024Q1 has a published report to validate against; urban share and agriculture share swing between quarters; no wages. |
| India, PLFS | 2021Q1-2025Q4 | 2025Q4; 2026Q1 unit data not yet on the MoSPI portal | 40,000 (2021-2025Q1, first visits only); 220,000 (2025Q2 on) | 100 % at 3 digits (NCO-2015), never 4 | 2025 redesign: sample times five, all visits and quarterly weights from 2025Q2, new frame from 2025Q1 (handled in cells: first visits only from 2025Q2, comparable series 2021Q3-2024Q4); 2021H1 coded NCO-2004 (mapped via ISCO-88, dropped from cells); industry at 2 digits; no tenure, contract, social security; one corrupt Assam FSU in 2022Q3 dropped. |
| Uruguay, ECH | 2021Q3-2025Q4 | 2025Q4; 2026 first-semester bases due about Sep-Oct 2026 | 35,000 person-months | 99.9 % at 4 digits | Rotating monthly panel: records are person-months (weight / 3); tenure only for first interviews (20 %); no wages (implantation base only); 2021H2 is the panel's ramp-up (published rates 0.7 pp off); 2022H1 bases re-issued after publication (0.3 pp off); files switch encodings. |
| Bolivia, ECE | in progress: 2021Q2-2025Q4 available, 2025Q4 read and harmonized | 2025Q4; 2026Q1 due about Jun 2026 on ANDA (manual download, login) | 30,000 | 72 % at 3, 11 % at 4 digits (COB 2009, ISCO-08 based) | Expansion factors revised from 2025Q4 (`fact_trim_act`, new base) so a level break at 2025Q4 is likely; no tenure; official quarterly rates not yet located for validation; questionnaire versions change (v9 from 2024Q4). |

Not in the panel: Egypt (ERF harmonized files through 2024; 2025 watched
daily), Costa Rica (files to be downloaded by the user), the request-based
countries in `docs/design/candidates.md`.

Cross-country limits that apply to every analysis: minimum labour age
differs (10 Argentina, 14 Brazil, Peru, Uruguay, Bolivia, 15 elsewhere) and
the cell analysis restricts to 15+; tenure, the basis of the new-hire
margin, exists only for Brazil, Colombia, Ecuador, Argentina, Mexico (Q1),
South Africa, Nigeria and Uruguay (first interviews); exposure is attached
at the digit depth each country supports, so the treated group is coarser in
Argentina, Mexico and the Philippines.
