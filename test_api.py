import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app, API_KEY

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200

def test_check_key_valid():
    response = client.get("/api/check_key", headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert response.json()["status"] == "valid"

def test_check_key_invalid():
    response = client.get("/api/check_key", headers={"X-API-Key": "wrong_key"})
    assert response.status_code == 403

def test_analyze_candidate_missing_key():
    response = client.post("/api/analyze/candidate", json={})
    assert response.status_code == 403

def test_analyze_candidate_success():
    # Подменяем ask_llm в том месте, где он используется
    with patch("core.analyzers.ask_llm") as mock_ask:
        mock_ask.return_value = "Mock report from DeepSeek"
        payload = {
            "transcribed_text": "Я опытный Python разработчик",
            "vacancy_text": "Нужен Python разработчик",
            "resume_text": "Python, FastAPI",
            "profession": "Python разработчик"
        }
        response = client.post("/api/analyze/candidate", json=payload, headers={"X-API-Key": API_KEY})
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert "report" in response.json()
        assert response.json()["report"]["full_report"] == "Mock report from DeepSeek"

def test_transcribe_no_audio():
    response = client.post("/api/transcribe", headers={"X-API-Key": API_KEY})
    assert response.status_code == 422
