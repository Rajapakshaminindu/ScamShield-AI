---
kind: dependency_management
name: Python Dependencies via requirements.txt with Loose Version Pinning
category: dependency_management
scope:
    - '**'
source_files:
    - backend/requirements.txt
---

## Dependency Management Approach

This repository uses Python's standard `requirements.txt` file located at `backend/requirements.txt` to declare third-party dependencies. There is no virtual environment lockfile (e.g., `Pipfile.lock`, `poetry.lock`, `pip-tools` pinning) and no vendoring strategy — dependencies are resolved at install time from PyPI.

## Key Files

- `backend/requirements.txt` — the sole dependency manifest, listing 8 packages:
  - `fastapi>=0.110.0`
  - `uvicorn>=0.29.0`
  - `pydantic>=2.6.0`
  - `python-multipart>=0.0.9`
  - `requests>=2.31.0`
  - `openai>=1.20.0`
  - `python-dotenv>=1.0.0`

The root-level `venv/` directory appears to be a generated virtual environment artifact (not checked in as a source of truth for versions).

## Architecture and Conventions

- **Single manifest**: All backend dependencies are declared in one flat `requirements.txt`; there are no per-package subdirectories or split manifests.
- **Loose version constraints**: Every package uses a minimum-version constraint (`>=X.Y.Z`) rather than exact pins (`==`). This means installs will pull the latest compatible minor/patch release, which can lead to non-deterministic builds across environments.
- **No private registry configuration**: There is no `pip.conf`, `.pypirc`, or `--index-url` usage observed; dependencies resolve against the default PyPI index.
- **No lockfile**: Without a lockfile, reproducibility depends on external tooling not present in this repo.
- **Frontend has no dependency manifest**: The `frontend/` directory contains only vanilla HTML/CSS/JS files (`index.html`, `app.js`, `style.css`) and declares no npm/pnpm/yarn dependencies.

## Constraints and Rules Observed

- All backend dependencies use minimum-version pinning (`>=`), not exact pins — this is the consistent pattern across every entry in `requirements.txt`.
- No transitive dependency management tool (e.g., pip-tools, Poetry, Pipenv) is used; direct dependency declarations are the single source of truth.
- The project does not vendor third-party code into a `vendor/` or `lib/` directory under version control.
- Environment variables for secrets (e.g., API keys consumed by `openai` and `python-dotenv`) are kept out of source via `.env.example` and `.gitignore`, but secret values themselves are not managed through a dependency-aware mechanism.