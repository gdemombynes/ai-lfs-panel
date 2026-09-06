# ai-lfs-panel

A harmonized labor force survey (LFS) microdata panel for low- and
middle-income countries, built to detect employment shifts that may be linked
to generative-AI adoption.

Key variables are standardized to the World Bank Global Labor Database (GLD)
dictionary: labor status (employed / unemployed / not in the labor force),
industry in ISIC Rev.4, occupation in ISCO-08, plus demographics, weights,
formality and job tenure. Countries in phase 1: Brazil, Mexico, Colombia,
Argentina, Ecuador, Peru, South Africa and India, quarterly from 2022 Q1.

Companion inventory of where LFS microdata are published:
[lfs-microdata-inventory](https://github.com/gdemombynes/lfs-microdata-inventory).

## Status

| Country | Fetch | Read | Harmonize | Validated vs official |
|---|---|---|---|---|
| Brazil (PNAD Contínua) | open FTP | fixed-width via IBGE layout | 2021Q1-2026Q2, 22 quarters | 110/110 checks pass, max gap 0.005 pp (`output/tables/validation_official_bra.csv`) |
| Mexico (ENOE) | INEGI zips, name resolver | SDEM+COE1+COE2 CSV merge | 2021Q1-2026Q2, 22 quarters (2021 = ENOE-N design) | 18/18 checks pass on the 9 quarters with located bulletins, max gap 0.05 pp (`output/tables/validation_official_mex.csv`) |
| Colombia (GEIH) | DANE catalogue, monthly zips | 4 modules (CSV, Stata fallback), 3 months stacked | 2022Q1-2026Q2, 18 quarters | 90/90 checks pass, rates identical to DANE's anexo to 3 decimals (`output/tables/validation_official_col.csv`) |
| Argentina (EPH) | INDEC zips, release check | usu_individual text file | 2021Q1-2026Q1, 21 quarters (urban) | 105/105 checks pass, max gap 0.005 pp on the all-ages base INDEC uses (`output/tables/validation_official_arg.csv`) |
| Ecuador (ENEMDU) | INEC zips, folder-name variants | person .sav | 2021Q3-2026Q1, 19 quarters | 95/95 checks pass, rates identical to INEC's tabulados to 3 decimals (`output/tables/validation_official_ecu.csv`) |
| Peru (EPEN) | INEI zips by survey code | national .dta | 2022Q1-2026Q2, 18 quarters | 90/90 checks pass, max gap 0.001 pp vs INEI's quarterly reports (`output/tables/validation_official_per.csv`) |
| South Africa (QLFS) | DataFirst, manual download (CAPTCHA login) | worker .dta via pandas | 2022Q1-2026Q2, 18 quarters | 90/90 checks pass, rates identical to Stats SA's QLFS Trends (15-64) to 3 decimals (`output/tables/validation_official_zaf.csv`) |
| Georgia (LFS) | Geostat annual zips, quarter ids | ECSTAT .sav per quarter | 2021Q1-2025Q4, 20 quarters | 100/100 checks pass, rates identical to Geostat's quarterly indicators to 3 decimals (`output/tables/validation_official_geo.csv`) |
| India | blocked: MoSPI microdata portal unreachable (hourly check scheduled) | | | |

## Analysis (milestone 4, first pass)

`scripts/30_attach_exposure.py` builds ISCO-08 exposure from the ILO 2025
GenAI task scores, `40_build_cells.py` aggregates the employed view into
country x quarter x occupation x age x sex cells, `41_event_study.py`
estimates event-study and difference-in-differences effects of high exposure
(cell and country x age x sex x quarter fixed effects), and `42_figures.py`
draws them. Results and caveats: `docs/findings.md`.

## Layout

```
src/lfspanel/
  config.py periods.py schema.py crosswalks.py store.py validate.py official.py
  fetch/  read/  harmonize/          # one module per country
  resources/                          # committed reference data
    layouts/      IBGE PNADC SAS input layout
    keep_lists/   raw variables retained per country
    crosswalks/   isco08_structure.csv, national -> ISCO/ISIC maps
    official/     published headline rates used for validation
scripts/  01_fetch.py 03_fetch_official.py 10_harmonize.py 11_build_duckdb.py 20_validate_official.py
data/raw/       immutable downloads + manifest.csv (git-ignored except the manifest)
data/processed/ harmonized/source=<own|gld>/countrycode=<CCC>/period=<YYYYQn>/data.parquet, panel.duckdb
docs/           schema.md, data-inventory.md, harmonization/<ccc>.md
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Build Brazil end to end

```bash
python scripts/01_fetch.py --country bra --periods 2022Q1:2026Q2 --docs   # ~200 MB per quarter
python scripts/10_harmonize.py --country bra --periods 2022Q1:2026Q2
python scripts/11_build_duckdb.py
python scripts/03_fetch_official.py --country bra --periods 2022Q1:2026Q2
python scripts/20_validate_official.py --country bra
```

Query the panel:

```python
import duckdb

con = duckdb.connect("data/processed/panel.duckdb", read_only=True)
con.sql(
    "select period, isco1, sum(weight) as employed from employed group by 1, 2 order by 1, 2"
)
```

## Sources and licences

- Harmonization logic follows the GLD Stata code (MIT): https://github.com/worldbank/gld
- ISCO-08 structure: ILO. ILO GenAI exposure scores: Gmyrek et al. (2025), ILO WP 140.
- Microdata: national statistical offices; terms of each portal apply.

MIT licence for the code. See [LICENSE](LICENSE).
