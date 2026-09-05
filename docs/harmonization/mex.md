# Mexico: ENOE (quarterly)

Source: INEGI, `https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/microdatos/`.
2020 Q3 to 2022 Q4 ("nueva edición") files are `enoe_n_YYYY_trimN_csv.zip`
with members `ENOEN_*`; from 2023 Q1 they are `enoe_YYYY_trimN_csv.zip` with
`ENOE_*`. Tables used: SDEM (sociodemographic, all residents), COE1 and COE2
(employment questionnaire), merged on
`cd_a ent con v_sel tipo mes_cal n_hog h_mud n_ren`.

Reference: World Bank GLD `MEX_2023_ENOE_V01_M_V01_A_GLD_ALL.do` and its
crosswalks `SINCO_19_ISCO_08.dta`, `SCIAN_18_ISIC_4.dta` (converted to
`resources/crosswalks/sinco2019_to_isco08.csv`, `scian2018_to_isic4.csv`).

Universe: complete interviews (`r_def == 0`) of usual residents
(`c_res != 2`), INEGI's convention for published rates. Minimum labour age 15
(INEGI's "15 y más" release; GLD uses 12).

| Target | Source | Recode |
|---|---|---|
| int_month | mes_cal | month within quarter 1-3 mapped to calendar month; 96 -> NA |
| hhid, pid | cd_a … h_mud; + n_ren | GLD keys |
| visit_no | n_ent | interview number 1-5; rotation group not identified |
| weight | fac_tri | quarterly expansion factor (GLD annualises by quarter shares) |
| urban | t_loc_tri | 1-3 -> 1 (localities of 2,500+), 4 -> 0 |
| subnatid1 | ent | 32 states |
| age, male | eda (99 -> NA), sex (1 male) | |
| educat7 | cs_p13_1, anios_esc | GLD rule: none/preschool 1; primary 2, complete (6 yrs) 3; secondary and preparatoria 4, complete preparatoria (12 yrs) 5; normal/técnica 6; profesional and above 7 |
| lstatus | **clase2** | 1 employed, 2 unemployed, 3-4 NLF (INEGI derived; GLD re-derives from COE p1-p2 with the same result) |
| potential_lf | clase2 | 3 available -> 1, 4 -> 0 |
| underemployment | sub_o | 1 -> 1 |
| nlfreason | c_inac5c | 1 student 2 housework 3 retired 4 disabled 5 other |
| empstat | pos_ocu | 1 -> 1 paid employee, 2 -> 3 employer, 3 -> 4 own account, 4 -> 2 unpaid |
| ocusec | p4b, p4c, p4d1, p4d2, p4a | GLD rule (private if p4b 4, or 5 with p4c 1-2; institutions public if government-administered …) |
| industry | p4a SCIAN 4-digit | `scian2018_to_isic4.csv`; `isic_digits` = significant digits of the ISIC code (many map at 2-3 digits) |
| occupation | p3 SINCO 2019 4-digit | `sinco2019_to_isco08.csv`, then validated against the ISCO-08 structure; about 40 % of employment at 4 digits, the rest at 1-3 because the INEGI correspondence stops at group level; 0.06 % unmapped |
| wage_no_compen | ingocup | monthly labour income, 0 for unpaid workers, NA if 0 |
| whours | hrsocup | hours worked in the reference week, NA if 0 |
| contract | p3j in Q1 (extended questionnaire), p3i otherwise | written contract 1 yes 2 -> 0; only asked of subordinate workers |
| socialsec | imssissste | 1 IMSS, 2 ISSSTE, 3 other -> 1; 4 none -> 0 (GLD leaves NA) |
| tenure_months * | p3r, p3r_anio, p3r_mes | **first quarters only** (extended questionnaire): job started this year (1) / last year (2) with month, or earlier (3) with year; unknown month set to June; NA in Q2-Q4 |
| tenure_lt12 * | same | 1 if under 12 months; 0 for p3r = 3; NA outside Q1, so the hiring proxy for Mexico is annual |
| firmsize | | not filled yet (p3g_tot bands available) |

Validation: INEGI quarterly bulletin (population 15+): 2025 Q1 participation
59.2 %, unemployment 2.5 %, employed 59.0 million; harmonized 59.15 / 2.46 /
59.0 million.

Known limits: INEGI's SINCO-ISCO correspondence is coarse; use
`occup_isco_digits` before pooling with 4-digit countries. Firm size not yet
harmonized. Tenure exists only in first quarters. From 2025 Q3 the geography
codes are named `cve_ent`, `cve_mun`, `cve_loc`, `cve_ageb` (reader renames
them); some 2022 files carry a UTF-8 byte-order mark on the first column.
Quarterly bulletins for 2022 Q1 to 2023 Q3 and 2024 Q2 to Q3 have not been
located, so those quarters are validated only through the GLD comparison.
