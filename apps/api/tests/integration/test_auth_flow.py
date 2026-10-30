from fastapi.testclient import TestClient

from app.main import app


def test_registration_institution_deposit_case_and_dashboard(monkeypatch, tmp_path):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "storage_local_path", str(tmp_path))

    with TestClient(app) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={
                "email": "owner@example.com",
                "full_name": "Institution Owner",
                "password": "a-strong-password-123",
            },
        )
        assert registration.status_code == 201
        assert registration.json()["user"]["roles"] == ["institution_applicant"]
        token = registration.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        institution = client.post(
            "/api/v1/institutions",
            headers=headers,
            json={
                "code": "TEST-001",
                "name": "Example Institution",
                "contact_email": "office@example.com",
            },
        )
        assert institution.status_code == 201

        instrument = client.post(
            "/api/v1/instruments",
            headers=headers,
            json={
                "instrument_number": "FDR-001",
                "bank_name": "Example Bank",
                "holder_name": "Example Institution",
                "amount": "12500.75",
                "issue_date": "2025-01-01",
                "maturity_date": "2030-01-01",
            },
        )
        assert instrument.status_code == 201
        instrument_id = instrument.json()["id"]

        case = client.post(
            f"/api/v1/cases/instruments/{instrument_id}",
            headers=headers,
            json={
                "title": "Check instrument details",
                "description": "Review the uploaded record.",
            },
        )
        assert case.status_code == 201
        assert case.json()["status"] == "open"

        dashboard = client.get("/api/v1/dashboard/summary", headers=headers)
        assert dashboard.status_code == 200
        assert dashboard.json()["total_instruments"] == 1
        assert dashboard.json()["open_cases"] == 1

        records = client.get("/api/v1/instruments", headers=headers)
        assert records.status_code == 200
        assert records.json()["total"] == 1

        document = client.post(
            f"/api/v1/instruments/{instrument_id}/documents",
            headers=headers,
            files={"file": ("proof.pdf", b"%PDF-1.4\nproof", "application/pdf")},
        )
        assert document.status_code == 201
        document_id = document.json()["id"]
        download = client.get(
            f"/api/v1/instruments/{instrument_id}/documents/{document_id}/download",
            headers=headers,
        )
        assert download.status_code == 200
        assert download.content.startswith(b"%PDF-")

        denied = client.get("/api/v1/instruments")
        assert denied.status_code == 401

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "a-strong-password-123"},
        )
        assert login.status_code == 200
