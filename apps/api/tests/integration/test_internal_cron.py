from fastapi.testclient import TestClient

from app.api import internal
from app.core.config import get_settings
from app.main import app


def test_lifecycle_cron_requires_configured_secret(monkeypatch):
    monkeypatch.setattr(get_settings(), "cron_secret", "")

    with TestClient(app) as client:
        response = client.post("/internal/lifecycle/refresh")

    assert response.status_code == 503


def test_lifecycle_cron_rejects_invalid_authorization(monkeypatch):
    monkeypatch.setattr(get_settings(), "cron_secret", "test-cron-secret")

    with TestClient(app) as client:
        response = client.post(
            "/internal/lifecycle/refresh",
            headers={"Authorization": "Bearer wrong-secret"},
        )

    assert response.status_code == 401


def test_lifecycle_cron_runs_maturity_refresh(monkeypatch):
    monkeypatch.setattr(get_settings(), "cron_secret", "test-cron-secret")
    monkeypatch.setattr(internal, "run_maturity_alerts", lambda: (2, 1))

    with TestClient(app) as client:
        response = client.post(
            "/internal/lifecycle/refresh",
            headers={"Authorization": "Bearer test-cron-secret"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "changed": 2, "reminders": 1}
