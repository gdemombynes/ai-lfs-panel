# Brazil: PNAD Contínua (quarterly)

Source: IBGE, open FTP
`https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/{YYYY}/PNADC_{QQ}{YYYY}.zip`.
Fixed-width text; layout from `Documentacao/Dicionario_e_input_20221031.zip`
(vendored at `resources/layouts/input_PNADC_trimestral_20221031.sas`).
All quarters were re-issued in August 2025 with weights calibrated to Census
2022 population projections; download one vintage for the whole series and
keep `raw_release` (the FTP `Last-Modified` date) on every row.

Reference: World Bank GLD `BRA_2022_PNADC_V01_M_V01_A_GLD_ALL.do`. We follow
its recodes except where noted.

| Target | Source | Recode |
|---|---|---|
| year, wave | Ano, Trimestre | `Q{Trimestre}`; `int_month` NA (quarter files do not carry the interview month) |
| hhid, pid | UPA + V1008 + V1014; + V2003 | as GLD (`id_dom` = UPA+V1008+V1014) |
| rotation_group, visit_no | V1014, V1016 | panel and interview number (1-5) |
| weight | **V1028** | quarterly calibrated weight. GLD's annual file uses V1032 (visit-1 weight); quarterly totals reproduce SIDRA table 4092 to within 0.01 pp |
| urban | V1022 | 1 urban, 2 rural -> 0 |
| subnatid1 | UF | `"31 - Minas Gerais"` |
| age, male | V2009, V2007 | V2007 1 = male |
| educat7 | VD3004 | 1..5 as is; 6 and 7 -> 7 (GLD) |
| educat4 | educat7 | 1->1, 2-3->2, 4-5->3, 6-7->4 |
| lstatus | VD4002, VD4001 | 1 if VD4002=1, 2 if VD4002=2, 3 if VD4001=2; age >= 14 only |
| potential_lf | VD4003 | 1 yes / 2 no, NLF only |
| underemployment | VD4004A | 1 = time-related underemployed, else 0, employed only (GLD leaves this NA) |
| nlfreason | VD4030 | GLD recode 2->1 student, 1->2 housekeeper, 4->3 retired, 3->4 disabled, 5-6->5; retired under 30 set NA |
| empstat | VD4008 | 1-3 -> 1 paid employee, 6 -> 2 unpaid, 4 -> 3 employer, 5 -> 4 self-employed |
| ocusec | V4012 | 2 -> 1 public; 1,3,5,6,7 -> 2 private; 4 -> 4 |
| industry_orig | V4013 | CNAE-Domiciliar 2.0, 5 digits |
| industrycat_isic | V4013 | first two digits + `00` (CNAE 2.0 divisions = ISIC Rev.4 divisions); wholesale codes 48010/48020/48076/48078 -> 4600, other 48xxx -> 4700 (GLD); `isic_digits` = 2 |
| occup_orig | V4010 | COD, 4 digits, ISCO-08 structure |
| occup_isco | V4010 | 6225 -> 6220, 5168 -> 5160, 0200-0512 -> 0000 (GLD); then validated against the ISCO-08 structure, truncating to the deepest valid parent (`occup_isco_digits`) |
| wage_no_compen, unitwage | V403412 | monthly cash earnings usually received, main job; 0 for unpaid workers; unitwage 5 |
| whours | V4039 | hours usually worked per week, main job |
| contract | VD4009 | 1 if VD4009 in 1,3,5,7 (employees and domestic workers with signed carteira, military and statutory public servants) |
| socialsec | V4032 | 1 yes, 2 -> 0 |
| firmsize_l/u | V4018, V40181-3 | exact counts within bands 1-3; band 4 -> lower 51 |
| tenure_months * | V4040, V40401-3 | band 1 (<1 month) 0.5; band 2 months asked; band 3 (1-2 years) 12*years+6; band 4 (2+ years) 12*years |
| tenure_lt12 * | V4040 | 1 if band 1 or 2 |

Validation: `scripts/20_validate_official.py --country bra` against SIDRA
table 4092 (population 14+, labor force, employed, unemployed). 2025 Q1:
participation 62.20, unemployment 7.00, employment level 57.84, all within
0.005 points.

Known limits: no interview month in the quarterly files; ISIC only at 2 digits
until a CNAE-Domiciliar class to ISIC class crosswalk is added; a handful of COD
codes have no ISCO-08 unit group and are carried at 1 or 3 digits (see
`occup_isco_digits`).
