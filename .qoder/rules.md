# Qoder IDE Rules & Conventions - ScamShield AI

## Project Overview
ScamShield AI is an AI-powered scam detection platform capable of analyzing:
1. Text messages (SMS, WhatsApp, emails)
2. Screenshots / Images (OCR text extraction & phishing visuals)
3. URLs / Links (Domain reputation, shortening & phishing analysis)
4. Voice / Audio recordings (Voice phishing / vishing transcription & analysis)

## Architecture & Technology Stack
- **Backend**: Python 3.13 + FastAPI + Uvicorn + Pydantic
- **AI Model**: Alibaba Cloud Model Studio (Qwen-Plus / Qwen-VL / Qwen-Omni via OpenAI-compatible SDK)
- **Heuristic Engine**: Rule-based detection (`backend/app/rule_engine.py`) for OTP theft, banking urgency, malicious TLDs.
- **Frontend**: Modern responsive web application (HTML5, CSS3, Vanilla JS) served via FastAPI or standalone browser.

## Coding Conventions
- Use type annotations everywhere in Python (`backend/app/`).
- Return structured `ScamAnalysisResponse` Pydantic models from all scan endpoints.
- Keep fallback/mock response mode working gracefully if `DASHSCOPE_API_KEY` is not provided.
- Maintain simple, modular, and well-commented functions.

## Key Endpoints
- `POST /api/analyze/text` -> Analyzes raw message text
- `POST /api/analyze/url` -> Analyzes submitted URL
- `POST /api/analyze/screenshot` -> Analyzes image file
- `POST /api/analyze/voice` -> Analyzes audio file
- `GET /api/health` -> System health check
