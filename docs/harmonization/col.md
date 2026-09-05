# Colombia: GEIH (monthly, 2022 redesign)

Source: DANE microdata catalogue, one entry per year
(2022: 771, 2023: 782, 2024: 819, 2025: 853, 2026: 900), twelve monthly zips
each with CSV, DTA and SAV versions of the modules. We read the CSV modules
"Características generales, seguridad social en salud y educación" (all
persons), "Fuerza de trabajo", "Ocupados" and "No ocupados", joined on
`DIRECTORIO SECUENCIA_P ORDEN`, and stack the three months of a quarter.

Reference: World Bank GLD `COL_2025_GEIH_V01_M_V01_A_GLD_ALL.do`.

| Target | Source | Recode |
|---|---|---|
| int_month, wave | MES | calendar month; wave `M01`..`M12` inside the quarterly partition |
| hhid, pid | DIRECTORIO-SECUENCIA_P-HOGAR; + ORDEN | |
| weight | FEX_C18 / 3 | monthly factor divided by the number of months stacked |
| urban | CLASE | 1 cabecera -> 1; 2 centros poblados y rural disperso -> 0 |
| subnatid1 | DPTO | 33 departments |
| age, male | P6040, P3271 (1 male) | |
| educat7 | P3042, P3042S1 | GLD years-of-schooling rule, then 7 levels |
| minlaborage | | **15**: DANE's working-age population (PET) since the 2022 redesign; GLD keeps 10 |
| lstatus | OCI, DSI, PET | employed if OCI = 1, unemployed if DSI = 1, else NLF within PET |
| potential_lf | | not yet derived (DANE publishes "fuerza de trabajo potencial") |
| underemployment | P6810 | wants to work more hours -> 1 |
| nlfreason | P6240 | 3 studying -> 1, 4 housework -> 2, 5 disabled -> 4, other -> 5 |
| empstat | P6430 | 1, 2, 3, 8 -> paid employee; 4 -> own account; 5 -> employer; 6, 7 -> unpaid; 9 -> other |
| ocusec | P6430 | 2 government employee -> 1, else 2 |
| industry | RAMA4D_R4 (orig), RAMA2D_R4 | ISIC at 2 digits (CIIU Rev.4 A.C. divisions equal ISIC divisions); 4-digit class correspondence pending |
| occupation | OFICIO_C8 CIUO-08 A.C. | Colombian unit groups mapped to ISCO-08 per GLD (73xx, 8323-4, 9625-6), then validated; 4 digits for >99.9 % |
| wage_no_compen | P6500 | monthly earnings of employees; 0 for unpaid |
| whours | P6850, else P6800 | last week, else usual hours |
| contract | P6440, P6450 | written contract (P6450 = 2) -> 1; verbal or none -> 0 |
| socialsec | P6920 | contributes to pension 1 -> 1, 2 -> 0, pensioned -> NA |
| tenure_months *, tenure_lt12 * | P6426 | months in current job |

Validation: DANE "anexo GEIH" workbook, sheet "Total nacional Trim"
(calendar quarters Ene-Mar, Abr-Jun, Jul-Sep, Oct-Dic) and "Total nacional"
(months). January 2025 harmonized: participation 64.12, unemployment 11.64,
employment 56.66, PET 40,424,866, employed 22,902,835, identical to DANE's
published month.


Archive layouts seen (all handled by `read/col.py`): comma-separated CSVs
(Jan-Apr 2022), semicolon CSVs, `CSV`/`CVS` folders at the top level or under
a month folder, CSV modules zipped inside the archive (`CSV.zip`),
non-breaking spaces in file names (2026), a singular `No ocupado.CSV`
(Mar 2024), and months with only Stata and SPSS files (some late-2025 and
2026 months), read from the `.DTA` files.

Full-panel validation: 18 quarters, 90 of 90 checks pass; participation,
unemployment and employment rates match the anexo to three decimals.
