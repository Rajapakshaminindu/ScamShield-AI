---
kind: configuration_system
name: Environment-Based Configuration via python-dotenv
category: configuration_system
scope:
    - '**'
source_files:
    - backend/app/config.py
    - backend/.env.example
    - backend/app/main.py
---

## What system/approach is used

The backend uses a minimal, environment-variable-driven configuration system built on `python-dotenv`. There is no YAML/JSON/TOML config file parsing, no settings module hierarchy, and no runtime feature-flag framework. All runtime behavior is controlled by reading environment variables at import time.

## Key files and packages

- `backend/app/config.py` — the single source of truth for configuration. It calls `load_dotenv()` (from the `dotenv` package) to load `.env`, then exposes module-level constants derived from `os.getenv(...)` with defaults.
- `backend/.env.example` — template documenting every supported variable; copied into `.env` by developers.
- `backend/app/main.py` — consumes `HOST` and `PORT` from `config.py` when launching uvicorn via `uvicorn.run(..., host=HOST, port=PORT)`.
- `backend/requirements.txt` — declares the `dotenv` dependency used to parse `.env`.

## Architecture and conventions

1. **Single-file config module.** `config.py` is a flat list of top-level constants (`DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL`, `QWEN_MODEL_NAME`, `QWEN_VL_MODEL_NAME`, `PORT`, `HOST`). Any module that needs configuration imports these names directly rather than calling `os.getenv` itself.
2. **Env-first, default-second.** Every value is read via `os.getenv("VAR", <default>)`, so the app runs without a `.env` file but falls back to sensible defaults (e.g. `qwen-plus` model, `8000` port, `0.0.0.0` host, DashScope international base URL).
3. **Type coercion in config layer.** Only `PORT` is cast to `int`; all other values remain strings. Consumers are expected to handle empty strings (e.g. an unset `DASHSCOPE_API_KEY` will propagate as `""`).
4. **No validation or schema enforcement.** The config module does not validate presence, format, or range of any variable. Missing secrets are silently passed through as empty strings.
5. **Secrets live in `.env`.** Sensitive values like `DASHSCOPE_API_KEY` are intended to be placed in a local `.env` file loaded by `load_dotenv()`. The example template is committed under `.env.example` and should not contain real credentials.
6. **Frontend has no equivalent config system.** The frontend (`frontend/app.js`, `index.html`, `style.css`) contains no configuration loader — it communicates with the backend over HTTP using relative paths, so its "configuration" is effectively fixed at build/deploy time.

## Conventions and constraints

- **Variables must be documented in `.env.example`.** The template lists every supported key with comments describing purpose and default values; new configuration keys should be added there alongside code changes.
- **Configuration is loaded once at module import.** Because `load_dotenv()` is called at the top of `config.py`, the `.env` file must exist before any module that imports `config` is imported; otherwise defaults apply.
- **No per-environment config files.** There is no mechanism to switch between `.env.development`, `.env.production`, etc. Environment selection is done by swapping the entire `.env` file or overriding OS-level environment variables.
- **No runtime reload of config.** Changes to `.env` require a process restart since Python caches imported modules.
- **Host/port are exposed only through `config.py`.** `main.py` reads them from `config.PORT` and `config.HOST` rather than parsing CLI flags or FastAPI startup args directly.