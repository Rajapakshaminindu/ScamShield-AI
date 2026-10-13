"""
Tests for authentication, hashing, and JWT tokens.
"""
import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
import jwt
from backend.app.auth import (
    hash_password,
    verify_password,
    create_token,
    decode_token,
    _get_jwt_secret,
    JWT_ALGORITHM,
)

def test_hash_and_verify_password():
    pwd = "SuperSecretPassword123!"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False

def test_verify_password_invalid_hash_string():
    assert verify_password("pwd", "malformed_hash") is False
    assert verify_password("pwd", "") is False

def test_jwt_token_lifecycle():
    token = create_token(user_id=42, username="testuser", role="user")
    assert isinstance(token, str) and len(token) > 20

    decoded = decode_token(token)
    assert decoded["sub"] == 42
    assert decoded["username"] == "testuser"
    assert decoded["role"] == "user"

def test_jwt_token_invalid():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("invalid.token.signature")
    assert exc_info.value.status_code == 401

def test_jwt_token_expired():
    secret = _get_jwt_secret()
    expired_payload = {
        "sub": "42",
        "username": "testuser",
        "role": "user",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    expired_token = jwt.encode(expired_payload, secret, algorithm=JWT_ALGORITHM)

    with pytest.raises(HTTPException) as exc_info:
        decode_token(expired_token)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()
