"""
Authentication module — SQLite user store + JWT tokens + password hashing.
"""
import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ---------------------------------------------------------------------------
# Config & Environment Loading
# ---------------------------------------------------------------------------
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "backend" / "scamshield.db"

def _load_env_files():
    """Load .env from both repo root and backend/.env reliably."""
    root_env = BASE_DIR / ".env"
    backend_env = BASE_DIR / "backend" / ".env"
    if root_env.exists():
        load_dotenv(dotenv_path=root_env, override=False)
    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env, override=False)
    load_dotenv()

_load_env_files()

def _get_jwt_secret():
    """Read JWT_SECRET fresh from env each time to avoid reloader mismatch."""
    _load_env_files()
    return os.getenv("JWT_SECRET", "change-me-in-production-scamshield-2025")

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist and synchronize the admin account."""
    _load_env_files()
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    UNIQUE NOT NULL,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'user',
            created_at  TEXT    NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scan_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            input_type  TEXT    NOT NULL,
            risk_score  INTEGER NOT NULL,
            risk_level  TEXT    NOT NULL,
            scam_type   TEXT,
            summary     TEXT,
            created_at  TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Seed / sync admin credentials from environment
    admin_username = (os.getenv("ADMIN_USERNAME", "admin") or "admin").strip()
    admin_email = (os.getenv("ADMIN_EMAIL", "admin@scamshield.ai") or "admin@scamshield.ai").strip()
    admin_password = (os.getenv("ADMIN_PASSWORD", "admin123") or "admin123").strip()

    now = datetime.now(timezone.utc).isoformat()

    # Check if an admin or user matching this username/email exists
    cur.execute(
        "SELECT id, username, email FROM users WHERE role = 'admin' OR username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE ORDER BY (role = 'admin') DESC, id ASC",
        (admin_username, admin_email)
    )
    admin_row = cur.fetchone()

    if admin_row:
        # Always update existing admin account to stay synchronized with environment settings
        cur.execute(
            "UPDATE users SET username = ?, email = ?, password = ?, role = 'admin' WHERE id = ?",
            (admin_username, admin_email, hash_password(admin_password), admin_row["id"])
        )
    else:
        # Insert initial admin account
        cur.execute(
            "INSERT INTO users (username, email, password, role, created_at) VALUES (?, ?, ?, 'admin', ?)",
            (admin_username, admin_email, hash_password(admin_password), now)
        )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Password hashing (SHA-256 + salt)
# ---------------------------------------------------------------------------

def hash_password(password: str, salt: str = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hashed = stored.split("$", 1)
        return hash_password(password, salt) == stored
    except Exception:
        return False



# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        data = jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        # Ensure sub is always an integer
        data["sub"] = int(data["sub"])
        return data
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    payload = decode_token(credentials.credentials)
    return {
        "id": payload["sub"],
        "username": payload["username"],
        "role": payload["role"],
    }


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


# ---------------------------------------------------------------------------
# User CRUD helpers
# ---------------------------------------------------------------------------

def create_user(username: str, email: str, password: str, role: str = "user") -> Optional[int]:
    conn = _get_conn()
    cur = conn.cursor()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cur.execute(
            "INSERT INTO users (username, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, email, hash_password(password), role, now)
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None  # duplicate username or email
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> Optional[dict]:
    if not username or not password:
        return None
    identifier = username.strip()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, email, password, role FROM users WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE",
        (identifier, identifier)
    )
    row = cur.fetchone()
    conn.close()
    if row and verify_password(password, row["password"]):
        return {"id": row["id"], "username": row["username"], "email": row["email"], "role": row["role"]}
    return None



def get_all_users() -> list:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, role, created_at FROM users ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def delete_user(user_id: int) -> bool:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM scan_logs WHERE user_id = ?", (user_id,))
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# ---------------------------------------------------------------------------
# Scan log helpers
# ---------------------------------------------------------------------------

def log_scan(user_id: int, input_type: str, risk_score: int, risk_level: str,
             scam_type: str, summary: str):
    conn = _get_conn()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cur.execute(
        "INSERT INTO scan_logs (user_id, input_type, risk_score, risk_level, scam_type, summary, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, input_type, risk_score, risk_level, scam_type, summary, now)
    )
    conn.commit()
    conn.close()


def get_all_scan_logs(limit: int = 100) -> list:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT sl.id, sl.user_id, u.username, sl.input_type, sl.risk_score,
               sl.risk_level, sl.scam_type, sl.summary, sl.created_at
        FROM scan_logs sl
        JOIN users u ON sl.user_id = u.id
        ORDER BY sl.created_at DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_user_scan_logs(user_id: int, limit: int = 50) -> list:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, input_type, risk_score, risk_level, scam_type, summary, created_at
        FROM scan_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
    """, (user_id, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_admin_stats() -> dict:
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
    regular_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM scan_logs")
    total_scans = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM scan_logs WHERE risk_score >= 60")
    high_risk_scans = cur.fetchone()[0]

    cur.execute("SELECT AVG(risk_score) FROM scan_logs")
    avg_row = cur.fetchone()
    avg_risk = round(avg_row[0], 1) if avg_row and avg_row[0] is not None else 0

    cur.execute("SELECT COUNT(DISTINCT user_id) FROM scan_logs")
    active_users = cur.fetchone()[0]

    conn.close()
    return {
        "total_users": total_users,
        "regular_users": regular_users,
        "total_scans": total_scans,
        "high_risk_scans": high_risk_scans,
        "avg_risk_score": avg_risk,
        "active_users": active_users,
    }


# Initialize DB on import
init_db()
