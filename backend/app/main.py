import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.schemas import (
    TextAnalysisRequest,
    URLAnalysisRequest,
    ScamAnalysisResponse,
    ChatFollowupRequest,
    ChatFollowupResponse,
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserInfo,
    ScanLogEntry,
    AdminStatsResponse,
)
from backend.app.ai_service import (
    analyze_text,
    analyze_url,
    analyze_image_bytes,
    analyze_audio_bytes,
    chat_followup
)
from backend.app.config import PORT, HOST
from backend.app.auth import (
    create_token,
    create_user,
    authenticate_user,
    get_current_user,
    require_admin,
    get_all_users,
    delete_user,
    log_scan,
    get_all_scan_logs,
    get_user_scan_logs,
    get_admin_stats,
)

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

# ---------------------------------------------------------------------------
# Authentication Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/auth/register", response_model=TokenResponse)
def api_register(payload: RegisterRequest):
    user_id = create_user(payload.username, payload.email, payload.password)
    if user_id is None:
        raise HTTPException(status_code=409, detail="Username or email already exists.")
    token = create_token(user_id, payload.username, "user")
    return TokenResponse(token=token, username=payload.username, role="user", user_id=user_id)


@app.post("/api/auth/login", response_model=TokenResponse)
def api_login(payload: LoginRequest):
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = create_token(user["id"], user["username"], user["role"])
    return TokenResponse(token=token, username=user["username"], role=user["role"], user_id=user["id"])


@app.get("/api/auth/me")
def api_get_me(user: dict = Depends(get_current_user)):
    return {"id": user["id"], "username": user["username"], "role": user["role"]}


# ---------------------------------------------------------------------------
# Scan Endpoints — sign-in is mandatory, so every scan is attributed to a user
# ---------------------------------------------------------------------------

def _record_scan(user: dict, input_type: str, result):
    log_scan(user["id"], input_type, result.risk_score, result.risk_level,
             result.scam_type or "", result.summary)


@app.post("/api/analyze/text", response_model=ScamAnalysisResponse)
def api_analyze_text(payload: TextAnalysisRequest, user: dict = Depends(get_current_user)):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    result = analyze_text(payload.text)
    _record_scan(user, "Text / SMS", result)
    return result


@app.post("/api/analyze/url", response_model=ScamAnalysisResponse)
def api_analyze_url(payload: URLAnalysisRequest, user: dict = Depends(get_current_user)):
    if not payload.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty.")
    result = analyze_url(payload.url)
    _record_scan(user, "URL / Link", result)
    return result


@app.post("/api/analyze/screenshot", response_model=ScamAnalysisResponse)
async def api_analyze_screenshot(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    result = analyze_image_bytes(contents, file.filename or "screenshot.png")
    _record_scan(user, "Screenshot", result)
    return result


@app.post("/api/analyze/voice", response_model=ScamAnalysisResponse)
async def api_analyze_voice(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")
    result = analyze_audio_bytes(contents, file.filename or "voice_recording.mp3")
    _record_scan(user, "Voice Audio", result)
    return result

@app.post("/api/chat/followup", response_model=ChatFollowupResponse)
def api_chat_followup(payload: ChatFollowupRequest, user: dict = Depends(get_current_user)):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    return chat_followup(payload.message, payload.scan_context, payload.chat_history)


# ---------------------------------------------------------------------------
# User Scan History
# ---------------------------------------------------------------------------

@app.get("/api/user/scans")
def api_user_scans(user: dict = Depends(get_current_user)):
    return get_user_scan_logs(user["id"])


# ---------------------------------------------------------------------------
# Admin Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/admin/stats", response_model=AdminStatsResponse)
def api_admin_stats(admin: dict = Depends(require_admin)):
    return get_admin_stats()


@app.get("/api/admin/users")
def api_admin_users(admin: dict = Depends(require_admin)):
    return get_all_users()


@app.delete("/api/admin/users/{user_id}")
def api_admin_delete_user(user_id: int, admin: dict = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")
    if not delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found.")
    return {"detail": "User deleted."}


@app.get("/api/admin/scans")
def api_admin_scans(admin: dict = Depends(require_admin), limit: int = 100):
    return get_all_scan_logs(limit)


# Mount frontend directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/login")
    def serve_login():
        return FileResponse(FRONTEND_DIR / "login.html")

    @app.get("/admin")
    def serve_admin():
        return FileResponse(FRONTEND_DIR / "admin.html")

    @app.get("/ads.txt")
    def serve_ads_txt():
        return FileResponse(FRONTEND_DIR / "ads.txt", media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=HOST, port=PORT, reload=True)
