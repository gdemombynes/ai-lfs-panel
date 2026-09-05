# Argentina: EPH continua (quarterly, 31 urban agglomerations)

Source: INDEC `EPH_usu_{q}_Trim_{yyyy}_txt.zip`, file `usu_individual_T{q}{yy}.txt`
(semicolon-separated, quoted header). INDEC answers HTTP 200 with an HTML page
for quarters not yet released, so the fetcher checks the zip signature first.
`CAT_INAC` was dropped from the 2026Q1 file onward; the reader fills it with
blanks (`nlfreason` becomes NA).

Coverage: urban agglomerations only (`urban = 1` by construction, about
29-30 million people, 63 % of the population). INDEC publishes rates with the
whole population as the base, so `population = "all"` in
`resources/official/arg_headline.csv` and validation uses `min_age = 0`.

| Target | Source | Recode |
|---|---|---|
| hhid, pid | CODUSU-NRO_HOGAR; + COMPONENTE | |
| weight | PONDERA | person weight |
| subnatid1 | REGION | 1 GBA, 40 NOA, 41 NEA, 42 Cuyo, 43 Pampeana, 44 Patagonia |
| age, male | CH06 (-1 for infants clipped to 0), CH04 (1 male) | |
| educat7 | NIVEL_ED | 7 no education -> 1; 1 primary incomplete -> 2; 2 -> 3; 3 secondary incomplete -> 4; 4 -> 5; 5, 6 tertiary/university -> 7 |
| minlaborage | | **10** (ESTADO is coded from age 10; INDEC's PET) |
| lstatus | ESTADO | 1 employed, 2 unemployed, 3 inactive; 4 (under 10) -> NA |
| underemployment | INTENSI | 3, 4 (underemployed, seeking or not) -> 1 |
| nlfreason | CAT_INAC | 1 retired -> 3, 2 rentier -> 5, 3 student -> 1, 4 housework -> 2, 5 minor -> 5, 6 disabled -> 4, 7 other -> 5 |
| empstat | CAT_OCUP | 1 employer -> 3, 2 own account -> 4, 3 employee -> 1, 4 unpaid family -> 2, 9 -> 5 |
| ocusec | PP04A | 1 state -> 1; 2 private, 3 other -> 2 |
| industry | PP04B_COD, CAES Mercosur 1.0 | two-digit divisions equal ISIC Rev.4 divisions (`isic_digits = 2`); INDEC's own commerce divisions 40 and 48 map to section G (`4700`, `isic_digits = 1`) |
| occupation | PP04D_COD, CNO 2017 (5 digits) | `cno2017_to_isco08_2d.csv` (occupationcross, 562 codes) to ISCO-08 **2 digits**; codes mapping to 0000/9900 (ill-defined) -> NA; about 5 % of CNO codes are not in the crosswalk |
| wage_no_compen | P21 | monthly income from the main job (> 0); 0 for unpaid |
| whours | PP3E_TOT | hours last week in the main job; 999 -> NA |
| contract | | not asked |
| socialsec | PP07H | pension contribution deducted (employees): 1 -> 1, 2 -> 0 |
| firmsize_l/u | PP04C | 12 size bands (1 .. 501+) |
| tenure_months *, tenure_lt12 * | PP07A (employees), PP05H (self-employed) | bands: < 1 month, 1-3, 3-6, 6-12 -> `tenure_lt12 = 1`; 1-5 years, > 5 -> 0; midpoints in months |

Validation: `apis.datos.gob.ar` series API, series 49.2_TAEP_0_0_37 (total
population), 49.2_TAEP_0_0_25 (economically active) and 49.2_TAEO_0_0_30
(employed), thousands, tolerance 0.06 pp. 17 quarters 2022Q1-2026Q1: 85 of 85
checks pass; participation, unemployment and employment rates within 0.005 pp
of INDEC's figures (2026Q2 not yet released as of 2026-09-05).
