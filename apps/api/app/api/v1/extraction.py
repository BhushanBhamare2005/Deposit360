import uuid
from pathlib import Path

import pymupdf as fitz
from fastapi import APIRouter, Depends, HTTPException
from pytesseract import TesseractError, TesseractNotFoundError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.permissions import Role, has_role, is_applicant, is_staff
from app.db.session import get_db
from app.models.document import Document
from app.models.extracted_field import ExtractedField
from app.models.instrument import Instrument
from app.models.user import User
from app.schemas.workflows import ExtractedFieldRead, ExtractionRead
from app.services.audit_service import record_event
from app.services.extraction_service import OCRUnavailableError, extract_from_pdf

router = APIRouter(prefix="/documents", tags=["document extraction"])


@router.post("/{document_id}/extract", response_model=ExtractionRead)
def extract_document_fields(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExtractionRead:
    if not (
        is_applicant(user.roles)
        or has_role(user.roles, Role.SCRUTINY_OFFICER, Role.COMPLIANCE_ADMINISTRATOR, Role.ADMIN)
    ):
        raise HTTPException(status_code=403, detail="Document extraction permission required")
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    instrument = db.get(Instrument, document.instrument_id)
    if instrument is None or (
        instrument.institution_id != user.institution_id
        and not is_staff(user.roles)
    ):
        raise HTTPException(status_code=404, detail="Document not found")
    storage_root = Path(get_settings().storage_local_path).resolve()
    file_path = (storage_root / document.storage_key).resolve()
    if file_path.parent != storage_root or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Stored document not found")
    try:
        result = extract_from_pdf(file_path.read_bytes())
    except OCRUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (fitz.FileDataError, TesseractError, TesseractNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=f"PDF extraction failed: {exc}") from exc

    for existing in db.scalars(
        select(ExtractedField).where(ExtractedField.document_id == document.id)
    ):
        db.delete(existing)
    fields = [
        ExtractedField(
            document_id=document.id,
            field_name=value.field_name,
            extracted_value=value.extracted_value,
            page_number=value.page_number,
            confidence=value.confidence,
        )
        for value in result.fields
    ]
    db.add_all(fields)
    record_event(
        db,
        actor_id=user.id,
        action="document.extracted",
        resource_type="document",
        resource_id=document.id,
        details={"field_count": len(fields), "ocr_used": result.ocr_used},
    )
    db.commit()
    for field in fields:
        db.refresh(field)
    return ExtractionRead(
        document_id=document.id,
        text=result.text[:20_000],
        fields=[ExtractedFieldRead.model_validate(field) for field in fields],
        ocr_used=result.ocr_used,
    )
