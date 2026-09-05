# Data Project Template

A starter layout for Python data-analysis projects. Fork it, rename the
package, and start working.

## Layout

```
.
├── src/analysis/       # Reusable Python code, installed as a package
├── data/
│   ├── raw/            # Original, immutable inputs (not committed)
│   ├── processed/      # Cleaned and transformed data (not committed)
│   └── external/       # Third-party data (not committed)
├── notebooks/          # Jupyter notebooks for exploration
├── docs/               # Notes, references, write-ups
├── tests/              # pytest tests for src/
├── CLAUDE.md           # Conventions for Claude Code
└── pyproject.toml      # Package metadata, dependencies, tool config
```

## Setup

```bash
git clone https://github.com/gdemombynes/data-project-template.git
cd data-project-template
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

The editable install means `from analysis.utils import load_data` works
from notebooks, scripts, and tests without any path hacks.

## Everyday commands

```bash
pytest                 # run tests
ruff check .           # lint
ruff format .          # format
jupyter lab            # open notebooks
```

## Workflow

1. Drop raw inputs in `data/raw/`. They stay out of git.
2. Explore in `notebooks/`. Clear outputs before committing.
3. Move anything reused more than once into `src/analysis/`.
4. Write a test in `tests/` for each function in `src/analysis/`.
5. Write up findings in `docs/`.

## Starting a new project from this template

1. Click **Use this template** on GitHub, or fork it.
2. Rename `src/analysis` to something project-specific and update the
   `name` field in `pyproject.toml`.
3. Replace this README with a description of the project.

## License

MIT. See [LICENSE](LICENSE).
