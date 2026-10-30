from decimal import Decimal

import pymupdf as fitz
import pytest

from app.core.config import get_settings
from app.services.extraction_service import OCRUnavailableError, extract_from_pdf


def test_scanned_pdf_requires_tesseract_when_ocr_is_unavailable(monkeypatch):
    document = fitz.open()
    document.new_page()
    pdf_bytes = document.tobytes()
    document.close()
    monkeypatch.setattr(get_settings(), "tesseract_cmd", "")
    monkeypatch.setattr("app.services.extraction_service.shutil.which", lambda _binary: None)

    with pytest.raises(OCRUnavailableError, match="Tesseract OCR is not installed"):
        extract_from_pdf(pdf_bytes)


def test_scanned_pdf_accepts_numeric_ocr_confidence_values(monkeypatch):
    source = fitz.open()
    source.new_page()
    pixmap = source[0].get_pixmap()
    document = fitz.open()
    page = document.new_page()
    page.insert_image(page.rect, stream=pixmap.tobytes("png"))

    monkeypatch.setattr(get_settings(), "tesseract_cmd", "tesseract")
    monkeypatch.setattr(
        "app.services.extraction_service.image_to_data",
        lambda *_args, **_kwargs: {
            "conf": [95, 80, -1],
            "text": ["FDR", "TEST12345", ""],
        },
    )
    monkeypatch.setattr(
        "app.services.extraction_service.image_to_string",
        lambda *_args, **_kwargs: "FDR Number: TEST12345",
    )

    result = extract_from_pdf(document.tobytes())

    assert result.ocr_used is True
    assert result.text == "FDR Number: TEST12345"
    assert result.fields[0].extracted_value == "TEST12345"
    assert result.fields[0].confidence == Decimal("0.875")
