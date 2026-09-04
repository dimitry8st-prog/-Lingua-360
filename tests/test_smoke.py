import os
import tempfile
from pathlib import Path

tmp = tempfile.TemporaryDirectory()
os.environ["DATABASE_PATH"] = str(Path(tmp.name) / "test.db")
os.environ["VOICE_STORAGE_PATH"] = str(Path(tmp.name) / "voices")

from fastapi.testclient import TestClient
from app.main import app


def test_health_login_dashboard_and_rag():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        login = client.post("/api/auth/login", json={"email": "demo@lingua.local", "password": "demo123"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['token']}"}

        dashboard = client.get("/api/dashboard", headers=headers)
        assert dashboard.status_code == 200
        assert len(dashboard.json()["progress"]) == 2

        answer = client.post("/api/tutor/respond", headers=headers, json={
            "language": "English", "level": "A0", "message": "Как произносить TH sound?"
        })
        assert answer.status_code == 200
        assert answer.json()["sources"]
        assert answer.json()["attempt_limit"] == 2


def test_invalid_login_and_language_validation():
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"email": "x@y.z", "password": "wrong12"}).status_code == 401
        login = client.post("/api/auth/login", json={"email": "demo@lingua.local", "password": "demo123"})
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        bad = client.post("/api/tutor/respond", headers=headers, json={"language": "French", "level": "A0", "message": "Bonjour"})
        assert bad.status_code == 422

