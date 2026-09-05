# Peru: EPEN (Encuesta Permanente de Empleo Nacional, quarterly)

Source: INEI `srienaho/descarga/STATA/{code}-Modulo76.zip`, one Stata file
`Nacional EPEN Trim. <months> <year>.dta` per calendar quarter. The survey
code of each release is recorded by hand in `fetch/per.py` (`SURVEY_CODES`,
2022Q1 = 855 ... 2026Q2 = 1043); the harmonizer checks that the interview
months in the file belong to the requested quarter. The EPEN replaced the
quarterly ENAHO employment module in 2022; the quarterly ENAHO files no
longer carry module 05.

| Target | Source | Recode |
|---|---|---|
| int_month | MES | |
| hhid, pid | CONGLOMERADO-SELVIV-HOGAR; + C201 | |
| weight | FAC_T300 | quarterly employment weight, defined only for persons 14+ who answered the module; others dropped (children, non-residents, 932 unclassified rows in 2023Q2) |
| urban | AREA | 1 urban -> 1, 2 rural -> 0 |
| subnatid1 | | **NA**: the national file has no department code (only the 27 main cities from 2024Q2) |
| age, male | C208, C207 (1 male) | |
| educat7 | C366 | sin nivel, inicial -> 1; primaria incompleta, básica especial -> 2; primaria completa -> 3; secundaria incompleta -> 4; completa -> 5; superior no universitaria -> 6; universitaria, posgrado -> 7 |
| minlaborage | | **14** (INEI's PET) |
| lstatus | OCUP300 | 1 ocupado -> 1; 2 desempleo abierto -> 2; 3 desempleo oculto -> 3 with `potential_lf = 1` (INEI's unemployment rate counts open unemployment only); 4 inactivo -> 3 |
| underemployment | P209H | wanted and was available to work more hours -> 1 |
| nlfreason | C353 | 4 studying -> 1; 5 housework -> 2; 6 pension/rents -> 3; 7 ill or disabled -> 4; other -> 5 |
| empstat | C310 | 1 employer -> 3; 2 own account -> 4; 3 employee, 6 domestic worker, 7 paid apprentice -> 1; 4, 5, 9, 10 unpaid family, 8 unpaid intern -> 2 |
| ocusec | C311 | 1 armed forces/police, 2 public administration, 3 public firm -> 1; 4-6 -> 2 |
| industry | C309_COD, CIIU Rev.4 | identity, 4 digits (leading zeros restored) |
| occupation | C308_COD, CNO 2015 | ISCO-08 structure; national unit groups without an ISCO match truncated to the parent (about 12 % at 3 or 2 digits) |
| wage_no_compen | INGTOTP | monthly income from the main job (imputed by INEI); 0 for unpaid |
| whours | C318_T | hours last week, main job |
| contract | | not in the national module |
| socialsec | C364_1..3 | affiliated to a pension system (AFP, SNP 19990, DL 20530) -> 1, else 0 |
| firmsize_l/u | C317, C317A | bands 1-20, 21-50, 51-100, 101-500, 501+; exact count in the first band |
| tenure_months *, tenure_lt12 * | | **NA**: no tenure question in the EPEN |

Validation: INEI quarterly reports "Comportamiento de los indicadores del
mercado laboral a nivel nacional y 27 ciudades" (PDF via gob.pe, ids in
`official.py`), tables 1.1 (PET, PEA) and 1.7 (población ocupada), each
report giving the quarter and the same quarter a year earlier; tolerance
0.05 pp. Persons 14+. 18 quarters 2022Q1-2026Q2: 90 of 90 checks pass,
rates within 0.001 pp of INEI's.
