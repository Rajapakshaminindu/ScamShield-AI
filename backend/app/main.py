import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.schemas import (
    TextAnalysisRequest,
    URLAnalysisRequest,
    ScamAnalysisResponse,
    ChatFollowupRequest,
    ChatFollowupResponse
)
from backend.app.ai_service import (
    analyze_text,
    analyze_url,
    analyze_image_bytes,
    analyze_audio_bytes,
    chat_followup
)
from backend.app.config import PORT, HOST

app = FastAPI(
    title="ScamShield AI API",
    description="Multimodal scam detection and explainable cyber protection platform powered by Alibaba Cloud Qwen.",
    version="1.0.0"
)

# Enable CORS for cross-origin frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ScamShield AI",
        "version": "1.0.0"
    }

@app.post("/api/analyze/text", response_model=ScamAnalysisResponse)
def api_analyze_text(payload: TextAnalysisRequest):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    return analyze_text(payload.text)

@app.post("/api/analyze/url", response_model=ScamAnalysisResponse)
def api_analyze_url(payload: URLAnalysisRequest):
    if not payload.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty.")
    return analyze_url(payload.url)

@app.post("/api/analyze/screenshot", response_model=ScamAnalysisResponse)
async def api_analyze_screenshot(file: UploadFile = File(...)):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    return analyze_image_bytes(contents, file.filename or "screenshot.png")

@app.post("/api/analyze/voice", response_model=ScamAnalysisResponse)
async def api_analyze_voice(file: UploadFile = File(...)):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")
    return analyze_audio_bytes(contents, file.filename or "voice_recording.mp3")

@app.post("/api/chat/followup", response_model=ChatFollowupResponse)
def api_chat_followup(payload: ChatFollowupRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    return chat_followup(payload.message, payload.scan_context, payload.chat_history)

# Mount frontend directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=HOST, port=PORT, reload=True)
