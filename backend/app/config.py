import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend/.env explicitly, regardless of the process's current
# working directory (load_dotenv() alone only searches cwd and its parents,
# which misses backend/.env when the app is started from the repo root, e.g.
# `uvicorn backend.app.main:app`).
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL_NAME = os.getenv("QWEN_MODEL_NAME", "qwen-plus")
QWEN_VL_MODEL_NAME = os.getenv("QWEN_VL_MODEL_NAME", "qwen-vl-plus")
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-scamshield-2025")
