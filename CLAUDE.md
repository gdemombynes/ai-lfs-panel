# CLAUDE.md

## What this is

A Python data-analysis project. Reusable code lives in `src/analysis/`
and is installed as an editable package. Notebooks are for exploration only.

## Setup and commands

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest              # tests
ruff check .        # lint
ruff format .       # format
```

## Conventions

- Import project code as `from analysis.<module> import ...`. Never modify
  `sys.path`.
- Every function in `src/analysis/` gets a test in `tests/`.
- Raw data in `data/raw/` is immutable. Write derived files to
  `data/processed/`. Neither is committed.
- Do not commit notebook outputs.
- Use `pathlib.Path`, not string concatenation, for file paths.
- Keep `pyproject.toml` as the single source of dependencies. There is no
  `requirements.txt`.

## When starting a new project from this template

Rename the `analysis` package and update `name` in `pyproject.toml`,
then rewrite `README.md` for the project.
