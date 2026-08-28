---
kind: error_handling
name: FastAPI HTTPException + Graceful Fallback Pattern for External AI Service Failures
category: error_handling
scope:
    - '**'
source_files:
    - backend/app/main.py
    - backend/app/ai_service.py
    - backend/app/rule_engine.py
    - backend/app/schemas.py
---

## Overview

The ScamShield AI backend uses a two-tier error handling strategy:
1. **Request-level validation errors** are surfaced to clients via FastAPI's `HTTPException`.
2. **External service (Alibaba Cloud Qwen LLM) failures** are caught with broad `except Exception` blocks and silently degraded into a built-in heuristic fallback, so the API always returns a valid `ScamAnalysisResponse` even when the AI is unavailable.

There is no centralized error module, custom exception classes, or structured logging — errors are handled inline at the call sites.

## Request Validation Errors

In `backend/app/main.py`, route handlers validate inputs before delegating to business logic and raise `fastapi.HTTPException(status_code=400, detail="...")` for malformed requests:
- Empty text payloads → `"Text cannot be empty."`
- Empty URL payloads → `"URL cannot be empty."`
- Empty uploaded files (screenshot/voice) → `"Uploaded file is empty."` / `"Uploaded audio file is empty."`

These are the only user-facing error responses in the codebase; FastAPI's default JSON error envelope (`{"detail": "..."}`) is used without customization.

## External Service Failure Handling (Graceful Degradation)

`backend/app/ai_service.py` wraps every call to the Alibaba Cloud DashScope/Qwen OpenAI-compatible client in `try/except Exception` blocks:

| Function | What it catches | Fallback behavior |
|---|---|---|
| `analyze_text()` | Any exception from `client.chat.completions.create()` or `json.loads()` | Calls `generate_fallback_analysis(text)` using regex heuristics |
| `analyze_url()` | Same as above | Calls `generate_fallback_analysis(f"Suspicious URL submitted: {url}")` |
| `analyze_image_bytes()` | Same as above | Falls through to a hardcoded OCR sample string and runs heuristic analysis |

Each catch block logs the error via `print(f"Error ...: {e}. Falling back to heuristic analysis.")` and then returns a fully-formed `ScamAnalysisResponse`. The caller never sees an exception — the response body is identical whether the AI succeeded or failed.

Additionally, `get_ai_client()` returns `None` when `DASHSCOPE_API_KEY` is missing, unset, or still contains the placeholder value `"your_dashscope"`. In that case, all four analysis functions skip the AI entirely and go straight to `generate_fallback_analysis()`, making the system usable out-of-the-box without credentials.

## Heuristic Engine as Error Recovery Path

`backend/app/rule_engine.py` implements the fallback path: `analyze_text_heuristics()` applies regex-based rules (sensitive data patterns, urgency cues, lure phrases, suspicious domains/TLDs, IP-as-host URLs) and produces a `DetectedIndicator[]` list plus a capped score (min 100). `generate_fallback_analysis()` maps that score into a full `ScamAnalysisResponse` with risk level, scam type classification, explanations, dos/don'ts. This means external AI failure is treated as a normal operational mode rather than an error state from the client's perspective.

## Frontend Error Handling

The frontend (`frontend/app.js`) is not included in this analysis scope, but the backend exposes a `/api/health` endpoint returning `{status: "healthy", service: "ScamShield AI", version: "1.0.0"}` which can be used for liveness checks.

## Conventions Observed

- **No custom exception types**: All domain errors use `fastapi.HTTPException`; library/runtime errors are caught as bare `Exception`.
- **No global exception handler**: There is no `@app.exception_handler` registered to customize error responses.
- **Silent degradation over propagation**: External AI failures are swallowed and converted to heuristic results — exceptions never bubble up to the HTTP layer for these paths.
- **Print-based logging**: Errors are logged to stdout via `print()` rather than a structured logger; there is no log level configuration.
- **Pydantic models enforce response shape**: `schemas.py` defines `ScamAnalysisResponse` with field constraints (e.g., `risk_score` ge=0 le=100), so even fallback responses must conform to the same contract.
- **Heuristic fallback is first-class**: The absence of an API key is treated as expected configuration, not an error condition — the system degrades gracefully rather than failing fast.