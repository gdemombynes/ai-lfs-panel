# Georgia: Labour Force Survey (Geostat annual database, quarterly identifiers)

Source: one zip per year from geostat.ge (media ids in `fetch/geo.py`), with
`LFS_ECSTAT_ENG_<year>.sav` (persons 15+, labour module) and a demographic
file. `read/geo.py` keeps the ECSTAT file and selects the quarter by
`QuarterNo` (103 = 2022Q1, +1 per quarter). The 2022-2024 files spell the
industry variable `Brunch`; the reader maps it to `Branch`. The public file
covers persons 15+ only, so `population = "15+"` throughout.

| Target | Source | Recode |
|---|---|---|
| int_month | Month | |
| hhid, pid, rotation_group | UID; + MemberNo; DiaryID (household id across quarters) | |
| weight | P_Weights | |
| urban | Urban_Rural | 1 urban -> 1, 2 rural -> 0 |
| subnatid1 | Region | 11 regions |
| age, male | Age, Sex (2 men) | |
| educat7 | Education | illiterate/no education/pre-primary -> 1; primary -> 3; lower secondary, vocational without secondary -> 4; upper secondary, vocational with secondary certificate -> 5; post-secondary vocational, higher professional -> 6; bachelor, master -> 7 |
| minlaborage | | **15** |
| lstatus | Employed, Unemployed (Geostat ILO flags) | employed -> 1; unemployed -> 2; else 3 |
| potential_lf | Potential_Labour_Force_PLF | 1 -> 1 within NLF |
| underemployment | Time_related_underemployment_TRU | 1 -> 1 |
| nlfreason | OutsidetheLabourForce_* flags | student -> 1; homemaker -> 2; pensioner -> 3; disabled -> 4; other -> 5 |
| empstat | Status | 1 employee, 4 apprentice -> 1; 2 own business -> 4; 3, 5 family helpers -> 2; 97 -> 5 (Geostat does not separate employers from own-account workers) |
| ocusec | Sector_ownership | 1 state -> 1; else 2 |
| industry | Branch, NACE Rev.2 (up to 4 digits, leading zero lost) | division = ISIC Rev.4 division, `isic_digits = 2` |
| occupation | Occupation, ISCO-08 (4 digits, leading zero lost for armed forces) | identity; > 90 % at 4 digits |
| wage_no_compen | | **NA**: earnings published in bands only (B24_B25) |
| whours | M_Actually_worked | hours last week, main job |
| contract | B12_Agreement_type | written 1 -> 1, oral 2 -> 0 |
| socialsec | Informal_employment | Geostat's informal-employment flag inverted (non-agricultural only) |
| firmsize_l/u | B26_Employed_at_local_unit | bands 1, 2-4, 5-10, 11-19, 20-49, 50+ |
| tenure_months *, tenure_lt12 * | | **NA**: no start date for the current job |

Validation: Geostat "Labour Force Indicators (quarterly)" workbook
(`30-Labour-Force-Indicators-Q.XLSX`), persons 15+, thousands, tolerance
0.05 pp. 16 quarters 2022Q1-2025Q4: 80 of 80 checks pass, rates identical to
Geostat's to three decimals. 2026 quarters arrive with the 2026 annual
database (mid-2027).
