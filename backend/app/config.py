import os
from dotenv import load_dotenv

load_dotenv()

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL_NAME = os.getenv("QWEN_MODEL_NAME", "qwen-plus")
QWEN_VL_MODEL_NAME = os.getenv("QWEN_VL_MODEL_NAME", "qwen-vl-plus")
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")
