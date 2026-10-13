"""
Integration tests for FastAPI endpoints.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ScamShield AI"

def test_unauthenticated_scan_access():
    response = client.post("/api/analyze/text", json={"text": "Hello world"})
    assert response.status_code == 401

    response = client.post("/api/analyze/url", json={"url": "https://example.com"})
    assert response.status_code == 401

def test_user_registration_login_and_scan_flow():
    unique_id = uuid.uuid4().hex[:8]
    username = f"user_{unique_id}"
    email = f"user_{unique_id}@test.com"
    password = "StrongPassword123!"

    # 1. Register new user
    reg_response = client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    assert reg_response.status_code == 200
    token = reg_response.json()["token"]
    assert len(token) > 20

    # 2. Login
    login_response = client.post("/api/auth/login", json={
        "username": username,
        "password": password
    })
    assert login_response.status_code == 200
    assert login_response.json()["username"] == username

    # 3. Authenticated Text Analysis
    headers = {"Authorization": f"Bearer {token}"}
    scan_response = client.post(
        "/api/analyze/text",
        headers=headers,
        json={"text": "URGENT: Your account has been suspended! Send your OTP immediately to verify."}
    )
    assert scan_response.status_code == 200
    result = scan_response.json()
    assert "risk_score" in result
    assert result["risk_score"] > 50
    assert len(result["detected_indicators"]) > 0

    # 4. Authenticated URL Analysis
    url_response = client.post(
        "/api/analyze/url",
        headers=headers,
        json={"url": "https://bit.ly/fake-banking-update"}
    )
    assert url_response.status_code == 200
    assert "risk_score" in url_response.json()

def test_scan_empty_input_validation():
    # Login as admin or registered user
    unique_id = uuid.uuid4().hex[:8]
    reg_response = client.post("/api/auth/register", json={
        "username": f"val_{unique_id}",
        "email": f"val_{unique_id}@test.com",
        "password": "Password123!"
    })
    token = reg_response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Empty text
    res = client.post("/api/analyze/text", headers=headers, json={"text": "   "})
    assert res.status_code == 400

    # Empty URL
    res = client.post("/api/analyze/url", headers=headers, json={"url": "   "})
    assert res.status_code == 400
