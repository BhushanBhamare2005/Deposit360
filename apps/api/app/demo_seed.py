"""Seed a local-only, synthetic Deposit360 role-play dataset."""

import hashlib
import logging
from datetime import date, timedelta
from decimal import Decimal

import pymupdf as fitz
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.init_db import upgrade_database
from app.db.session import SessionLocal
from app.models import (
    AuditEvent,
    CaseStatus,
    ComplianceCase,
    Document,
    ExtractedField,
    Institution,
    Instrument,
    InstrumentLifecycleState,
    PolicyRule,
    ReleaseRequest,
    ReleaseStatus,
    User,
    VerificationCheck,
    VerificationStatus,
)
from app.services.storage_service import save_pdf

logger = logging.getLogger(__name__)

LOCAL_DEMO_PASSWORD = "Demo360-SIH-2026!"
DEMO_USERS = (
    ("applicant.deposit360@example.com", "Institution Applicant", "institution_applicant"),
    ("scrutiny.deposit360@example.com", "Scrutiny Officer", "scrutiny_officer"),
    ("compliance.deposit360@example.com", "Compliance Administrator", "compliance_administrator"),
    ("finance.deposit360@example.com", "Finance Officer", "finance_officer"),
    ("approver.deposit360@example.com", "Approving Authority", "approving_authority"),
)


def _synthetic_pdf(instrument: Instrument) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_textbox(
        fitz.Rect(54, 54, 558, 738),
        (
            "DEPOSIT360 SYNTHETIC DEMO RECORD\n"
            "NOT A BANK-ISSUED DOCUMENT — NOT VALID FOR FINANCIAL USE\n\n"
            f"Bank name: {instrument.bank_name}\n"
            f"FDR number: {instrument.instrument_number}\n"
            f"Holder: {instrument.holder_name}\n"
            f"Principal: INR {instrument.amount:,.2f}\n"
            f"Issue date: {instrument.issue_date:%d-%m-%Y}\n"
            f"Maturity date: {instrument.maturity_date:%d-%m-%Y}\n\n"
            "All names, identifiers, amounts, and dates in this document are fabricated "
            "for software demonstration. Text extraction does not establish authenticity "
            "or confirm the deposit with the named bank."
        ),
        fontsize=14,
    )
    content = document.tobytes()
    document.close()
    return content


def seed_demo_data() -> None:
    settings = get_settings()
    demo_password = settings.demo_password
    if not demo_password:
        if settings.app_env.lower() not in {"development", "dev", "test"}:
            raise RuntimeError(
                "Set DEMO_PASSWORD to a private password before seeding demo accounts "
                "outside development."
            )
        demo_password = LOCAL_DEMO_PASSWORD
    upgrade_database()
    with SessionLocal() as db:
        existing = db.scalar(select(Institution).where(Institution.code == "DEMO-SIH-001"))
        if existing:
            demo_users = db.scalars(select(User)).all()
            users_by_role = {
                role: next(
                    (
                        user
                        for user in demo_users
                        if role in user.roles
                        and user.full_name == full_name
                        and user.institution_id
                        == (existing.id if role == "institution_applicant" else None)
                    ),
                    None,
                )
                for _email, full_name, role in DEMO_USERS
            }
            if any(user is None for user in users_by_role.values()):
                raise RuntimeError(
                    "The synthetic demo institution exists but a demo role is missing."
                )
            for email, _name, role in DEMO_USERS:
                user = users_by_role[role]
                assert user is not None
                collision = db.scalar(select(User).where(User.email == email))
                if collision is not None and collision.id != user.id:
                    raise RuntimeError(
                        f"Cannot update demo account email; {email} is already in use."
                    )
                user.email = email
            existing.contact_email = DEMO_USERS[0][0]
            db.commit()
            print("Synthetic demo records already exist; role account emails are synchronized.")
            for email, _full_name, _role in DEMO_USERS:
                print(f"  {email}")
            return

        institution = Institution(
            code="DEMO-SIH-001",
            name="Synthetic Infrastructure Demo Office",
            approval_reference="DEMO-ONLY",
            contact_email="applicant.deposit360@example.com",
        )
        db.add(institution)
        db.flush()

        users: dict[str, User] = {}
        for email, full_name, role in DEMO_USERS:
            user = User(
                email=email,
                full_name=full_name,
                hashed_password=hash_password(demo_password),
                roles=[role],
                is_active=True,
                institution_id=institution.id if role == "institution_applicant" else None,
            )
            db.add(user)
            users[role] = user
        db.flush()

        today = date.today()
        synthetic_records = (
            {
                "number": "SYN-FDR-2026-001",
                "bank": "State Bank of India",
                "branch": "Mumbai Fort (synthetic)",
                "holder": "Synthetic Infrastructure Demo Office",
                "amount": Decimal("1000000.00"),
                "issue": today - timedelta(days=330),
                "maturity": today + timedelta(days=24),
                "state": InstrumentLifecycleState.ACTIVE,
            },
            {
                "number": "SYN-FDR-2026-002",
                "bank": "HDFC Bank",
                "branch": "Pune Camp (synthetic)",
                "holder": "Synthetic Infrastructure Demo Office",
                "amount": Decimal("500000.00"),
                "issue": today - timedelta(days=170),
                "maturity": today + timedelta(days=180),
                "state": InstrumentLifecycleState.ACTIVE,
            },
            {
                "number": "SYN-FDR-2026-003",
                "bank": "ICICI Bank",
                "branch": "Bengaluru MG Road (synthetic)",
                "holder": "Synthetic Infrastructure Demo Office",
                "amount": Decimal("2500000.00"),
                "issue": today - timedelta(days=340),
                "maturity": today + timedelta(days=12),
                "state": InstrumentLifecycleState.ACTIVE,
            },
            {
                "number": "SYN-FDR-2026-004",
                "bank": "Punjab National Bank",
                "branch": "New Delhi Connaught Place (synthetic)",
                "holder": "Synthetic Infrastructure Demo Office",
                "amount": Decimal("750000.00"),
                "issue": today - timedelta(days=730),
                "maturity": today - timedelta(days=5),
                "state": InstrumentLifecycleState.MATURED,
            },
            {
                "number": "SYN-FDR-2026-005",
                "bank": "Axis Bank",
                "branch": "Hyderabad Banjara Hills (synthetic)",
                "holder": "Synthetic Infrastructure Demo Office",
                "amount": Decimal("1250000.00"),
                "issue": today - timedelta(days=120),
                "maturity": today + timedelta(days=245),
                "state": InstrumentLifecycleState.ACTIVE,
            },
        )
        instruments: dict[str, Instrument] = {}
        for record in synthetic_records:
            instrument = Instrument(
                institution_id=institution.id,
                instrument_number=record["number"],
                bank_name=record["bank"],
                branch_name=record["branch"],
                holder_name=record["holder"],
                amount=record["amount"],
                issue_date=record["issue"],
                maturity_date=record["maturity"],
                lifecycle_state=record["state"],
            )
            db.add(instrument)
            instruments[record["number"]] = instrument
        db.flush()

        applicant = users["institution_applicant"]
        scrutiny = users["scrutiny_officer"]
        compliance = users["compliance_administrator"]
        finance = users["finance_officer"]

        case_return = ComplianceCase(
            instrument_id=instruments["SYN-FDR-2026-001"].id,
            title="Correct holder name on supporting evidence",
            description=(
                "The synthetic uploaded record shows a holder-name variation. "
                "Submit corrected supporting evidence before scrutiny can be completed."
            ),
            status=CaseStatus.CHANGES_REQUESTED,
            resolution_note="Please upload a corrected synthetic evidence document.",
            created_by=applicant.id,
            reviewed_by=scrutiny.id,
        )
        case_open = ComplianceCase(
            instrument_id=instruments["SYN-FDR-2026-003"].id,
            title="Maturity evidence review",
            description=(
                "Review the maturity date and supporting evidence before release processing."
            ),
            status=CaseStatus.OPEN,
            created_by=applicant.id,
        )
        db.add_all([case_return, case_open])

        for status, note in (
            (
                ReleaseStatus.SUBMITTED,
                None,
            ),
            (
                ReleaseStatus.UNDER_REVIEW,
                "Synthetic finance review completed; awaiting final authority.",
            ),
        ):
            request = ReleaseRequest(
                instrument_id=instruments["SYN-FDR-2026-002"].id
                if status == ReleaseStatus.SUBMITTED
                else instruments["SYN-FDR-2026-003"].id,
                requested_by=applicant.id,
                reviewed_by=finance.id if status == ReleaseStatus.UNDER_REVIEW else None,
                status=status,
                justification=(
                    "Synthetic demo release request for demonstrating "
                    "the staged finance and approval workflow."
                ),
                review_note=note,
            )
            db.add(request)

        check_instrument = instruments["SYN-FDR-2026-001"]
        db.add(
            VerificationCheck(
                instrument_id=check_instrument.id,
                check_type="bank_confirmation",
                source="mock-adapter",
                status=VerificationStatus.UNABLE_TO_VERIFY,
                evidence_note=(
                    "Synthetic demo only. No bank was contacted and no authenticity claim is made."
                ),
                requested_by=compliance.id,
            )
        )

        rule_definitions = (
            (
                "fdr.document.minimum_set",
                "Require a deposit evidence PDF and institution declaration for scrutiny.",
                {"required_documents": ["deposit_evidence", "institution_declaration"]},
            ),
            (
                "fdr.maturity.review_window",
                "Flag deposits maturing within 30 days for finance review.",
                {"maturity_review_days": 30},
            ),
            (
                "release.dual_review",
                "Require finance review followed by an approving-authority decision.",
                {"stages": ["finance_review", "approving_authority"]},
            ),
        )
        for key, description, config in rule_definitions:
            db.add(
                PolicyRule(
                    key=key,
                    version=1,
                    description=description,
                    config=config,
                    effective_from=today,
                )
            )

        pdf_instrument = instruments["SYN-FDR-2026-001"]
        pdf_bytes = _synthetic_pdf(pdf_instrument)
        storage_key = save_pdf(pdf_bytes)
        demo_document = Document(
            instrument_id=pdf_instrument.id,
            original_filename="SYNTHETIC-DEMO-NOT-A-BANK-FDR.pdf",
            storage_key=storage_key,
            mime_type="application/pdf",
            size_bytes=len(pdf_bytes),
            sha256=hashlib.sha256(pdf_bytes).hexdigest(),
            uploaded_by=applicant.id,
        )
        db.add(demo_document)
        db.flush()
        db.add_all(
            [
                ExtractedField(
                    document_id=demo_document.id,
                    field_name="instrument_number",
                    extracted_value=pdf_instrument.instrument_number,
                    page_number=1,
                    confidence=Decimal("0.990"),
                ),
                ExtractedField(
                    document_id=demo_document.id,
                    field_name="amount",
                    extracted_value=str(pdf_instrument.amount),
                    page_number=1,
                    confidence=Decimal("0.990"),
                ),
                ExtractedField(
                    document_id=demo_document.id,
                    field_name="maturity_date",
                    extracted_value=pdf_instrument.maturity_date.isoformat(),
                    page_number=1,
                    confidence=Decimal("0.990"),
                ),
            ]
        )
        db.add(
            AuditEvent(
                actor_id=None,
                action="demo.synthetic_data_seeded",
                resource_type="institution",
                resource_id=str(institution.id),
                details={
                    "synthetic": True,
                    "record_count": len(instruments),
                    "note": "All data is fabricated; no bank was contacted.",
                },
            )
        )
        db.commit()
    print("Synthetic Deposit360 demo dataset created.")
    for email, _full_name, _role in DEMO_USERS:
        print(f"  {email}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_demo_data()
