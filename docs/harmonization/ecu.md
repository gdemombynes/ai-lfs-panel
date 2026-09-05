# Ecuador: ENEMDU (quarterly)

Source: INEC `EMPLEO/{yyyy}/<quarter folder>/1_BDD_ENEMDU_{yyyy}_{roman}_TRIMESTRE_SPSS.zip`,
person file `.sav`. Folder names: `Trimestre_{roman}` from 2023; in 2022
one name per quarter (`Trimestre-enero-marzo-2022`, `Trimestre%1F_abril_junio_2022`
with a stray control character, `Trimestre_III_2022`, `Trimestre%1F_IV_2022`);
`fetch/ecu.py` tries every pattern. National coverage, urban and rural.

Reference: INEC "Metodología de empleo según condición de actividad";
`condact` is INEC's own classification.

| Target | Source | Recode |
|---|---|---|
| int_month | mes | interview month |
| hhid, pid, rotation_group | id_hogar, id_persona, panelm | |
| weight | fexp | |
| urban | area | 1 urban -> 1, 2 rural -> 0 |
| subnatid1 | ciudad (first two digits) | 24 provinces + "Zonas no delimitadas" |
| age, male | p03, p02 (1 male) | |
| educat7 | p10a (level), p10b (grade) | pre-school/literacy centre -> 1; primaria/básica by grade -> 2, 3, 4; secundaria/bachillerato by grade -> 4, 5; superior no universitario -> 6; superior universitario, post-grado -> 7 |
| minlaborage | | **15** (INEC's PET) |
| lstatus | condact | 1-6 employed (adequate, underemployed by hours or income, other non-full, unpaid, unclassified) -> 1; 7 open and 8 hidden unemployment -> 2; 9 -> 3 |
| underemployment | condact | 2 (subempleo por insuficiencia de tiempo) -> 1 |
| nlfreason | | not derived |
| empstat | p42 | 1-4, 10 employees (government, private, day labourer, domestic, other) -> 1; 5 employer -> 3; 6 own account -> 4; 7, 8, 9 unpaid family/other -> 2 |
| ocusec | p42 | 1 government -> 1, else 2 |
| industry | p40, CIIU Rev.4 | identity, 4 digits |
| occupation | p41, CIUO-08 | identity, 4 digits; 3-digit values are minor groups (right-padded) except armed-forces 110/210/310 (leading zero lost) |
| wage_no_compen | p66 | monthly income from the main job; 0 for unpaid |
| whours | p24 | hours last week, main job |
| contract | p43 | 1-3 (nombramiento, contrato permanente/indefinido, temporal) -> 1; 4-6 (por obra, por horas, jornal, verbal) -> 0 |
| socialsec | p05a | 1-4 (IESS general, voluntario, campesino, ISSFA/ISSPOL) -> 1; 5-10 -> 0 |
| firmsize_l/u | p47a, p47b | exact count when under 100 (p47a = 1), else 100+ |
| tenure_months *, tenure_lt12 * | p45 | completed years in the job: 0 -> `tenure_lt12 = 1`; months = 12 x years + 6 |

Validation: INEC "Tabulados Mercado Laboral" workbook of the newest quarter,
sheet "1. Poblaciones", national column (PET 15+, PEA, Empleo, Desempleo),
tolerance 0.05 pp. 17 quarters 2022Q1-2026Q1: 85 of 85 checks pass, rates
identical to INEC's to three decimals (2026Q2 not yet published as of
2026-09-05).
