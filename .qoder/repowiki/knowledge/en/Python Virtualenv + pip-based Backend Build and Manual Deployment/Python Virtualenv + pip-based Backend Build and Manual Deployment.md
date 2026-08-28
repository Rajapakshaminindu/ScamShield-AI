---
kind: build_system
name: Python Virtualenv + pip-based Backend Build and Manual Deployment
category: build_system
scope:
    - '**'
source_files:
    - README.md
    - backend/requirements.txt
    - backend/.env.example
    - backend/app/main.py
---

## What system/approach is used

This repository has no formal build system (no Makefile, Dockerfile, CI pipeline, or packaging scripts). The project is a small Python FastAPI service plus a static HTML/CSS/JS frontend. Development and deployment are performed manually via the Python standard library `venv` module and `pip`, with the application launched directly through `uvicorn`. The README documents the entire flow as shell commands rather than automated steps.

## Key files and packages

- `backend/requirements.txt` — declares all runtime dependencies for the backend (`fastapi`, `uvicorn`, `pydantic`, `python-multipart`, `requests`, `openai`, `python-dotenv`). This is the single source of truth for Python package versions (using `>=` lower bounds).
- `backend/.env.example` — template for environment variables consumed at runtime by `python-dotenv` (DashScope API key, base URL, model name, server host/port).
- `backend/app/main.py` — FastAPI entrypoint; the app is started with `python -m uvicorn backend.app.main:app --reload --port 8000`.
- `README.md` — contains the authoritative quick-start instructions that define how to create a virtual environment, install dependencies, configure secrets, and run the server.
- `venv/` — the generated Python virtual environment directory (checked into the repo per `.gitignore` being absent for it), which pins the installed dependency tree on disk.
- `frontend/` — plain `index.html`, `style.css`, and `app.js`; no build step, bundler, or asset pipeline exists.

## Architecture and conventions

- **Dependency management**: A flat `backend/requirements.txt` lists all third-party packages. There is no `pyproject.toml`, `setup.py`, `Pipfile`, or lock file (e.g., `requirements.lock`). Version pinning uses minimum-version operators (`>=`) rather than exact pins.
- **Environment configuration**: Runtime configuration is loaded from an `.env` file via `python-dotenv`. The example env file lives in `backend/.env.example` and users copy it to `.env` at the project root or inside `backend/` before running.
- **Application lifecycle**: No process manager or containerization is present. The recommended way to start the service is `python -m uvicorn backend.app.main:app --reload --port 8000`, where `--reload` enables hot-reload during development.
- **Frontend delivery**: The frontend is served as static files by the same Uvicorn instance (FastAPI serves `index.html` at `/`); there is no separate build, transpilation, or asset optimization step.
- **Virtual environment**: The repo ships a committed `venv/` directory alongside the code, indicating developers are expected to activate it via `source venv/bin/activate` (Linux/macOS) or `..\venv\Scripts\activate` (Windows) before running.

## Conventions and constraints

- **No automated build/test/release pipeline**: There are no Makefiles, Dockerfiles, GitHub Actions workflows, shell scripts, or packaging manifests. All build-like actions are manual shell commands documented in `README.md`.
- **Dependencies must be installed from `backend/requirements.txt`**: The README prescribes `pip install -r backend/requirements.txt` as the only supported installation method.
- **Secrets are not versioned**: Users must create their own `.env` file from `backend/.env.example`; the example file is committed but real credentials are never checked in.
- **Server defaults**: If no `PORT`/`HOST` env vars are set, the README hardcodes port `8000` and binds to `localhost`; the `.env.example` shows `HOST=0.0.0.0` and `PORT=8000` as the intended production overrides.
- **Offline fallback mode**: When `DASHSCOPE_API_KEY` is absent, the backend automatically runs in heuristic-only mode, so the "build" succeeds even without cloud credentials.
- **Frontend has zero build tooling**: No npm/yarn/pip/build script exists for the frontend; files are served as-is.

Because this is a minimal academic/personal project, the build system is intentionally informal — essentially "run these commands in order." There is no reproducible artifact, container image, or CI gate.