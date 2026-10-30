import uuid

import fitz
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.instrument import Instrument, InstrumentLifecycleState
from app.models.user import User


def test_review_renewal_release_verification_extraction_and_notifications(monkeypatch, tmp_path):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "storage_local_path", str(tmp_path))

    with TestClient(app) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={
                "email": "workflows@example.com",
                "full_name": "Workflow User",
                "password": "a-strong-password-123",
            },
        )
        assert registration.status_code == 201
        token = registration.json()["access_token"]
        owner_headers = {"Authorization": f"Bearer {token}"}
        institution = client.post(
            "/api/v1/institutions",
            headers=owner_headers,
            json={
                "code": "FLOW-001",
                "name": "Workflow Institution",
                "contact_email": "flow@example.com",
            },
        )
        assert institution.status_code == 201

        def create_instrument(number: str, maturity: str) -> str:
            response = client.post(
                "/api/v1/instruments",
                headers=owner_headers,
                json={
                    "instrument_number": number,
                    "bank_name": "Example Bank",
                    "holder_name": "Workflow Institution",
                    "amount": "25000.00",
                    "issue_date": "2025-01-01",
                    "maturity_date": maturity,
                },
            )
            assert response.status_code == 201, response.text
            return response.json()["id"]

        released_id = create_instrument("FLOW-RELEASE", "2030-01-01")
        previous_id = create_instrument("FLOW-OLD", "2031-01-01")
        replacement_id = create_instrument("FLOW-NEW", "2033-01-01")
        review_id = create_instrument("FLOW-REVIEW", "2034-01-01")

        release = client.post(
            f"/api/v1/releases/instruments/{released_id}",
            headers=owner_headers,
            json={"justification": "The original fixed deposit has been closed."},
        )
        assert release.status_code == 201
        request_id = release.json()["id"]
        denied_review = client.patch(
            f"/api/v1/releases/{request_id}",
            headers=owner_headers,
            json={"status": "approved"},
        )
        assert denied_review.status_code == 403

        case = client.post(
            f"/api/v1/cases/instruments/{review_id}",
            headers=owner_headers,
            json={"title": "Review deposit record", "description": "Confirm record details."},
        )
        assert case.status_code == 201
        case_id = case.json()["id"]
        case_details = client.get(f"/api/v1/cases/{case_id}", headers=owner_headers)
        assert case_details.status_code == 200

        reviewer_id = uuid.uuid4()
        with SessionLocal() as db:
            db.add(
                User(
                    id=reviewer_id,
                    email=f"workflow-reviewer-{reviewer_id.hex[:8]}@example.com",
                    full_name="Workflow Admin",
                    hashed_password="not-used-in-this-test",
                    roles=["admin"],
                    is_active=True,
                )
            )
            db.commit()
        reviewer_token = create_access_token(str(reviewer_id), ["admin"])
        reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}

        reviewed_release = client.patch(
            f"/api/v1/releases/{request_id}",
            headers=reviewer_headers,
            json={"status": "approved", "review_note": "Evidence checked."},
        )
        assert reviewed_release.status_code == 200
        assert reviewed_release.json()["status"] == "approved"
        release_details = client.get(f"/api/v1/releases/{request_id}", headers=owner_headers)
        assert release_details.status_code == 200
        with SessionLocal() as db:
            released = db.get(Instrument, uuid.UUID(released_id))
            assert released is not None
            assert released.lifecycle_state == InstrumentLifecycleState.RELEASED

        in_review = client.patch(
            f"/api/v1/cases/{case_id}",
            headers=reviewer_headers,
            json={"status": "in_review"},
        )
        assert in_review.status_code == 200
        approved = client.patch(
            f"/api/v1/cases/{case_id}",
            headers=reviewer_headers,
            json={"status": "approved", "resolution_note": "Records match."},
        )
        assert approved.status_code == 200
        invalid_transition = client.patch(
            f"/api/v1/cases/{case_id}",
            headers=reviewer_headers,
            json={"status": "rejected"},
        )
        assert invalid_transition.status_code == 409

        renewal = client.post(
            "/api/v1/renewals",
            headers=owner_headers,
            json={
                "previous_instrument_id": previous_id,
                "replacement_instrument_id": replacement_id,
            },
        )
        assert renewal.status_code == 201
        assert renewal.json()["status"] == "confirmed"
        renewals = client.get("/api/v1/renewals", headers=owner_headers)
        assert renewals.status_code == 200
        assert len(renewals.json()) == 1

        verification = client.post(
            f"/api/v1/verification/instruments/{review_id}", headers=reviewer_headers
        )
        assert verification.status_code == 201
        check_id = verification.json()["id"]
        assert verification.json()["status"] == "unable_to_verify"
        assert "no bank was contacted" in verification.json()["evidence_note"]
        confirmed = client.patch(
            f"/api/v1/verification/{check_id}",
            headers=reviewer_headers,
            json={"status": "confirmed", "evidence_note": "Confirmation ref: BANK-CASE-77"},
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "confirmed"

        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text(
            (72, 72),
            "FDR Number: FD-12345\nAmount: INR 25,000.00\nMaturity Date: 01-01-2034",
        )
        pdf_bytes = pdf.tobytes()
        pdf.close()
        uploaded = client.post(
            f"/api/v1/instruments/{review_id}/documents",
            headers=owner_headers,
            files={"file": ("evidence.pdf", pdf_bytes, "application/pdf")},
        )
        assert uploaded.status_code == 201
        extracted = client.post(
            f"/api/v1/documents/{uploaded.json()['id']}/extract",
            headers=owner_headers,
        )
        assert extracted.status_code == 200
        assert any(
            field["field_name"] == "instrument_number" for field in extracted.json()["fields"]
        )
        assert extracted.json()["ocr_used"] is False

        notifications = client.get("/api/v1/notifications", headers=owner_headers)
        assert notifications.status_code == 200
        notification = next(
            item for item in notifications.json() if item["subject"] == "Compliance case updated"
        )
        acknowledged = client.patch(
            f"/api/v1/notifications/{notification['id']}/acknowledge",
            headers=owner_headers,
        )
        assert acknowledged.status_code == 200
        assert acknowledged.json()["status"] == "acknowledged"

        audit = client.get("/api/v1/audit?limit=100", headers=reviewer_headers)
        assert audit.status_code == 200
        release_event = next(item for item in audit.json() if item["action"] == "release.reviewed")
        audit_details = client.get(f"/api/v1/audit/{release_event['id']}", headers=reviewer_headers)
        assert audit_details.status_code == 200
