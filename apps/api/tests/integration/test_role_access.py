import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


def _role_headers(role: str) -> dict[str, str]:
    user_id = uuid.uuid4()
    with SessionLocal() as db:
        db.add(
            User(
                id=user_id,
                email=f"{role}-{user_id.hex[:10]}@example.test",
                full_name=role.replace("_", " ").title(),
                hashed_password=hash_password("role-test-password"),
                roles=[role],
                is_active=True,
            )
        )
        db.commit()
    token = create_access_token(str(user_id), [role])
    return {"Authorization": f"Bearer {token}"}


def test_five_role_workflow_enforces_separation_and_staged_release_approval():
    with TestClient(app) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"applicant-{uuid.uuid4().hex[:8]}@example.com",
                "full_name": "Demo Applicant",
                "password": "a-strong-password-123",
            },
        )
        assert registration.status_code == 201
        applicant = {"Authorization": f"Bearer {registration.json()['access_token']}"}
        assert registration.json()["user"]["roles"] == ["institution_applicant"]

        institution = client.post(
            "/api/v1/institutions",
            headers=applicant,
            json={
                "code": f"ROLE-{uuid.uuid4().hex[:8]}",
                "name": "Synthetic Role Test Office",
                "contact_email": "role-test@example.com",
            },
        )
        assert institution.status_code == 201
        instrument = client.post(
            "/api/v1/instruments",
            headers=applicant,
            json={
                "instrument_number": "SYN-ROLE-001",
                "bank_name": "Synthetic Test Bank",
                "holder_name": "Synthetic Role Test Office",
                "amount": "100000.00",
                "issue_date": "2026-01-01",
                "maturity_date": "2027-01-01",
            },
        )
        assert instrument.status_code == 201
        instrument_id = instrument.json()["id"]

        scrutiny = _role_headers("scrutiny_officer")
        compliance = _role_headers("compliance_administrator")
        finance = _role_headers("finance_officer")
        authority = _role_headers("approving_authority")

        assert (
            client.post(
                "/api/v1/institutions",
                headers=finance,
                json={
                    "code": "STAFF-001",
                    "name": "Staff Test Office",
                    "contact_email": "staff@example.com",
                },
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v1/instruments",
                headers=authority,
                json={
                    "instrument_number": "DENIED-001",
                    "bank_name": "Synthetic Test Bank",
                    "holder_name": "Denied",
                    "amount": "1000",
                    "issue_date": "2026-01-01",
                    "maturity_date": "2027-01-01",
                },
            ).status_code
            == 403
        )
        assert client.get("/api/v1/policy-rules", headers=finance).status_code == 403
        assert (
            client.post(
                f"/api/v1/verification/instruments/{instrument_id}", headers=applicant
            ).status_code
            == 403
        )
        assert client.get("/api/v1/cases", headers=finance).status_code == 403
        assert client.get("/api/v1/releases", headers=scrutiny).status_code == 403
        assert client.get("/api/v1/audit", headers=finance).status_code == 403

        case = client.post(
            f"/api/v1/cases/instruments/{instrument_id}",
            headers=applicant,
            json={"title": "Synthetic evidence review", "description": "Check sample evidence."},
        )
        assert case.status_code == 201
        case_id = case.json()["id"]
        assert client.get("/api/v1/dashboard/summary", headers=applicant).json()["open_cases"] == 1
        assert client.get("/api/v1/dashboard/summary", headers=finance).json()["open_cases"] == 0
        assert client.get("/api/v1/dashboard/summary", headers=compliance).json()["open_cases"] >= 1
        correction = client.patch(
            f"/api/v1/cases/{case_id}",
            headers=scrutiny,
            json={
                "status": "changes_requested",
                "resolution_note": "Upload corrected synthetic evidence.",
            },
        )
        assert correction.status_code == 200
        assert correction.json()["status"] == "changes_requested"
        assert (
            client.patch(
                f"/api/v1/cases/{case_id}",
                headers=finance,
                json={"status": "approved"},
            ).status_code
            == 403
        )
        resubmitted = client.post(f"/api/v1/cases/{case_id}/resubmit", headers=applicant)
        assert resubmitted.status_code == 200
        assert resubmitted.json()["status"] == "open"

        verification = client.post(
            f"/api/v1/verification/instruments/{instrument_id}", headers=compliance
        )
        assert verification.status_code == 201
        assert (
            client.patch(
                f"/api/v1/verification/{verification.json()['id']}",
                headers=scrutiny,
                json={"status": "confirmed", "evidence_note": "Synthetic source check"},
            ).status_code
            == 403
        )

        policy = client.post(
            "/api/v1/policy-rules",
            headers=compliance,
            json={
                "key": "demo.minimum_evidence",
                "description": "Require an evidence PDF before review.",
                "config": {"minimum_document_count": 1},
                "effective_from": date.today().isoformat(),
            },
        )
        assert policy.status_code == 201
        assert policy.json()["version"] == 1
        assert client.get("/api/v1/policy-rules", headers=authority).status_code == 403
        next_policy = client.post(
            "/api/v1/policy-rules",
            headers=compliance,
            json={
                "key": "demo.minimum_evidence",
                "description": "Require evidence documents before scrutiny.",
                "config": {"minimum_document_count": 2},
                "effective_from": (date.today() + timedelta(days=1)).isoformat(),
            },
        )
        assert next_policy.status_code == 201
        assert next_policy.json()["version"] == 2

        release = client.post(
            f"/api/v1/releases/instruments/{instrument_id}",
            headers=applicant,
            json={"justification": "Synthetic request for staged approval demonstration."},
        )
        assert release.status_code == 201
        release_id = release.json()["id"]
        assert (
            client.patch(
                f"/api/v1/releases/{release_id}",
                headers=finance,
                json={"status": "approved"},
            ).status_code
            == 409
        )

        finance_cleared = client.patch(
            f"/api/v1/releases/{release_id}",
            headers=finance,
            json={"status": "under_review", "review_note": "Synthetic finance review complete."},
        )
        assert finance_cleared.status_code == 200
        assert finance_cleared.json()["status"] == "under_review"
        assert (
            client.patch(
                f"/api/v1/releases/{release_id}",
                headers=finance,
                json={"status": "rejected"},
            ).status_code
            == 409
        )
        approved = client.patch(
            f"/api/v1/releases/{release_id}",
            headers=authority,
            json={"status": "approved", "review_note": "Final synthetic demo approval."},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"
        assert client.get("/api/v1/audit", headers=finance).status_code == 403
