import hashlib
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.permissions import is_applicant, is_staff
from app.db.session import get_db
from app.models.document import Document
from app.models.instrument import Instrument
from app.models.user import User
from app.schemas.document import DocumentRead
from app.services.audit_service import record_event
from app.services.storage_service import delete_file, read_file, save_pdf

router = APIRouter(prefix="/instruments", tags=["documents"])
_settings = get_settings()


@router.post(
    "/{instrument_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    instrument_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Document:
    if not is_applicant(user.roles):
        raise HTTPException(
            status_code=403, detail="Only institution applicants can upload documents"
        )
    instrument = db.get(Instrument, instrument_id)
    if instrument is None or (
        instrument.institution_id != user.institution_id and not is_staff(user.roles)
    ):
        raise HTTPException(status_code=404, detail="Instrument not found")
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Only PDF documents are accepted")
    content = await file.read(_settings.max_upload_size_bytes + 1)
    if len(content) > _settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail="Document exceeds the configured size limit")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="The uploaded file is not a valid PDF")

    original_filename = (file.filename or "document.pdf").replace("\\", "/").rsplit("/", 1)[-1]
    original_filename = original_filename[:255] or "document.pdf"
    storage_key = await run_in_threadpool(save_pdf, content)
    document = Document(
        instrument_id=instrument.id,
        original_filename=original_filename,
        storage_key=storage_key,
        mime_type="application/pdf",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        uploaded_by=user.id,
    )
    db.add(document)
    try:
        db.flush()
        record_event(
            db,
            actor_id=user.id,
            action="document.uploaded",
            resource_type="document",
            resource_id=document.id,
            details={"instrument_id": str(instrument.id), "size_bytes": len(content)},
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        await run_in_threadpool(delete_file, storage_key)
        raise
    db.refresh(document)
    return document


@router.get("/{instrument_id}/documents", response_model=list[DocumentRead])
def list_documents(
    instrument_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Document]:
    instrument = db.get(Instrument, instrument_id)
    if instrument is None or (
        instrument.institution_id != user.institution_id and not is_staff(user.roles)
    ):
        raise HTTPException(status_code=404, detail="Instrument not found")
    statement = select(Document).where(Document.instrument_id == instrument_id)
    return list(db.scalars(statement.order_by(Document.created_at.desc())).all())


@router.get("/{instrument_id}/documents/{document_id}/download")
def download_document(
    instrument_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    instrument = db.get(Instrument, instrument_id)
    if instrument is None or (
        instrument.institution_id != user.institution_id and not is_staff(user.roles)
    ):
        raise HTTPException(status_code=404, detail="Instrument not found")
    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.instrument_id == instrument_id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        content = read_file(document.storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Stored document not found") from exc
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{quote(document.original_filename)}"
            )
        },
    )
