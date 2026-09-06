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
        assert len(dashboard.json()["skills"]) == 12
        assert dashboard.json()["plan"]["English"]["id"] == "en-a0-01"

        answer = client.post("/api/tutor/respond", headers=headers, json={
            "language": "English", "level": "A0", "message": "Как произносить TH sound?"
        })
        assert answer.status_code == 200
        assert answer.json()["sources"]
        assert answer.json()["attempt_limit"] == 2


def test_balanced_learning_loop_and_idempotency():
    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"email": "demo@lingua.local", "password": "demo123"})
        headers = {"Authorization": f"Bearer {login.json()['token']}"}

        plan = client.get("/api/learning/plan", headers=headers)
        assert plan.status_code == 200
        assert plan.json()["allocation"] == {"English": 70, "Spanish": 30}
        assert len(plan.json()["week"]) == 7

        today = client.get("/api/learning/today?language=English", headers=headers)
        assert today.status_code == 200
        assert len(today.json()["steps"]) == 10

        payload = {
            "lesson_id": "en-a0-01", "language": "English", "minutes": 20,
            "practiced_skills": ["speaking", "listening", "reading", "writing", "vocabulary", "pronunciation"],
        }
        first = client.post("/api/learning/complete", headers=headers, json=payload)
        second = client.post("/api/learning/complete", headers=headers, json=payload)
        assert first.status_code == 200 and first.json()["xp_added"] == 20
        assert second.status_code == 200 and second.json()["already_completed"] is True

        reflection = client.post("/api/reflections", headers=headers, json={
            "language": "English", "lesson_id": "en-a0-01", "confidence": 4,
            "learned": "I can introduce myself", "difficult": "TH sound",
        })
        assert reflection.status_code == 200 and reflection.json()["saved"] is True

        mistake = client.post("/api/exercises/submit", headers=headers, json={
            "language": "English", "answer": "I tink", "attempt": 2,
        })
        assert mistake.status_code == 200 and mistake.json()["review_in_days"] == 2
        reviews = client.get("/api/reviews?language=English", headers=headers)
        assert reviews.status_code == 200 and len(reviews.json()) == 1


def test_invalid_login_and_language_validation():
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"email": "x@y.z", "password": "wrong12"}).status_code == 401
        login = client.post("/api/auth/login", json={"email": "demo@lingua.local", "password": "demo123"})
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        bad = client.post("/api/tutor/respond", headers=headers, json={"language": "French", "level": "A0", "message": "Bonjour"})
        assert bad.status_code == 422
