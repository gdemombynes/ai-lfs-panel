# Target schema

Variable names, codes and meanings follow the World Bank Global Labor Database
(GLD) dictionary (`GLD_Dictionary_v01.xlsx` in github.com/worldbank/gld) so
that our own harmonization and GLD files can be stacked. Columns marked * are
additions. The authoritative list with dtypes is `lfspanel.schema.TARGET_SCHEMA`.

| Column | Type | Meaning |
|---|---|---|
| countrycode | string | ISO3 |
| source * | string | `own` (this repo) or `gld` (World Bank harmonized file) |
| period * | string | Calendar quarter `YYYYQn`; the partition key |
| year, int_year, int_month | int | Reference year; interview year and month (NA when the survey does not record the month) |
| wave | string | `Q1`..`Q4` or `M01`..`M12` |
| hhid, pid | string | Household and person ids as concatenated survey keys |
| rotation_group *, visit_no * | string, int | Rotation panel identifiers when the survey is a panel |
| weight | float | Person weight for the reference quarter (sums to the population) |
| urban | int | 1 urban, 0 rural |
| subnatid1 | string | First subnational level, `code - name` |
| age, male | int | Age in years; 1 male 0 female |
| educat4, educat7 | int | GLD education levels |
| minlaborage * | int | Age from which the labor module applies |
| lstatus | int | 1 employed, 2 unemployed, 3 not in the labor force (NA below `minlaborage`) |
| potential_lf | int | Potential labor force, NLF only |
| underemployment | int | Time-related underemployment, employed only |
| nlfreason | int | 1 student, 2 housekeeper, 3 retired, 4 disabled, 5 other |
| empstat | int | 1 paid employee, 2 non-paid employee, 3 employer, 4 self-employed, 5 other |
| ocusec | int | 1 public, 2 private, 3 state-owned, 4 public or SOE undistinguished |
| industry_orig | string | National industry code as in the survey |
| industrycat_isic | string | ISIC Rev.4, four characters, trailing zeros beyond the reliable digits |
| isic_digits * | int | Reliable ISIC digits in `industrycat_isic` |
| industrycat10, industrycat4 | int | GLD 10- and 4-category industry groups |
| occup_orig | string | National occupation code as in the survey |
| occup_isco | string | ISCO-08, four characters, trailing zeros beyond the reliable digits |
| occup_isco_digits * | int | Reliable ISCO digits: 4 = unit group, 3 = minor, 2 = sub-major, 1 = major |
| occup | int | ISCO major group (0 = armed forces) |
| occup_skill | int | 1 low (9), 2 medium (4-8), 3 high (1-3) |
| wage_no_compen, unitwage | float, int | Last wage payment in the main job and its time unit (5 = monthly) |
| whours | float | Hours worked last week in the main job |
| contract | int | 1 written contract or formal registration |
| socialsec | int | 1 contributes to social security |
| firmsize_l, firmsize_u | int | Firm size bracket |
| tenure_months * | float | Months in the current main job (band midpoint when banded) |
| tenure_lt12 * | int | 1 if in the current main job for under 12 months (hiring proxy) |
| source_file *, raw_release *, harmonize_version * | string | Provenance |

## Rules enforced by `validate_frame`

- All columns present in this order and with these dtypes.
- Coded variables inside their domains; weights present and positive.
- `lstatus` is NA below `minlaborage`.
- Job characteristics (occupation, industry, hours, contract, tenure, ...) are
  NA unless `lstatus == 1`.
- `occup_isco` and `industrycat_isic` are always four characters and `occup`
  equals the first digit of `occup_isco`.

## ISCO code handling

`lfspanel.crosswalks.map_isco_codes` validates national ISCO-08-based codes
against the ILO structure (`resources/crosswalks/isco08_structure.csv`, 436
unit groups). A code that is not a unit group is truncated to its deepest valid
parent and `occup_isco_digits` records the depth, so analyses can choose the
digit level per country without guessing.
