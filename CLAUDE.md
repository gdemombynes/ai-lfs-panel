# CLAUDE.md

## What this is

`lfspanel` builds a harmonized labor force survey (LFS) panel for low- and
middle-income countries, then uses it to look for employment shifts linked to
generative-AI adoption. Three layers, identical signatures per country:

- `lfspanel.fetch.<ccc>`: `fetch_period(period) -> [FetchResult]` into
  `data/raw/<ccc>/<survey>/<period>/`, checksummed in `data/raw/manifest.csv`.
- `lfspanel.read.<ccc>`: `read_raw(period) -> DataFrame` with original variable
  names, limited to `resources/keep_lists/<ccc>.txt`.
- `lfspanel.harmonize.<ccc>`: `harmonize(raw, period) -> DataFrame` in the
  GLD-named target schema (`lfspanel.schema`), one Parquet per country-quarter
  under `data/processed/harmonized/`, queried through DuckDB views.

Reference implementation: Brazil (`fetch/bra.py`, `read/bra.py`,
`harmonize/bra.py`). Copy its shape for every other country.

## Setup and commands

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest              # tests (fixtures only, no network, no raw data)
ruff check .        # lint
ruff format .       # format
python scripts/01_fetch.py --country bra --periods 2025Q1:2025Q4 --docs
python scripts/10_harmonize.py --country bra --periods 2025Q1:2025Q4
python scripts/11_build_duckdb.py
python scripts/03_fetch_official.py --country bra --periods 2022Q1:2026Q2
python scripts/20_validate_official.py --country bra
```

## Conventions

- Import as `from lfspanel.<module> import ...`. Never modify `sys.path`.
- Python 3.9 compatible code (no `X | Y` unions, no `match`). Wheels only on
  this Mac: pin `pyreadstat<1.3`.
- The target schema is the World Bank GLD dictionary plus the starred
  additions listed in `docs/schema.md`. Any deviation from a GLD recode must be
  written down in `docs/harmonization/<ccc>.md` with the reason.
- Every raw file has a row in `docs/data-inventory.md`: status (HAVE / NEED /
  MANUAL), source URL, retrieved date, licence, variables used.
- `data/raw/` is immutable. To refresh a file, re-download with `--force`; the
  manifest keeps the new checksum. Never edit raw files in place.
- Scripts are numbered in run order and must be re-runnable from scratch.
- Every function in `src/lfspanel/` gets a test in `tests/`. Tests run on
  small fixtures in `tests/fixtures/`, never on the real microdata.
- Validation is not optional: a new country-quarter is done only when
  `20_validate_official.py` passes against the published headline rates.
- Secrets only via `.env` (see `.env.example`); never in code or commits.
- `pathlib.Path` for paths; `pyproject.toml` is the single dependency source.
