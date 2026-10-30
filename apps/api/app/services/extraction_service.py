import io
import re
import shutil
from dataclasses import dataclass
from decimal import Decimal

import pymupdf as fitz
import pytesseract
from PIL import Image
from pytesseract import Output, image_to_data, image_to_string

from app.core.config import get_settings

_PATTERNS = {
    "instrument_number": re.compile(
        r"(?:FDR|FD|Receipt)\s*(?:No\.?|Number)?\s*[:#]?\s*([A-Z0-9][A-Z0-9/-]{2,})",
        re.IGNORECASE,
    ),
    "amount": re.compile(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE),
    "issue_date": re.compile(
        r"(?:Issue(?:d)?\s*(?:Date)?)[:\s]*"
        r"([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})",
        re.IGNORECASE,
    ),
    "maturity_date": re.compile(
        r"(?:Maturity\s*(?:Date)?)[:\s]*"
        r"([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})",
        re.IGNORECASE,
    ),
    "holder_name": re.compile(r"(?:Holder|Name)[:\s]*([A-Z][A-Za-z\s.]{2,80})"),
}


@dataclass(frozen=True)
class ExtractedValue:
    field_name: str
    extracted_value: str
    page_number: int
    confidence: Decimal | None


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    fields: list[ExtractedValue]
    ocr_used: bool


class OCRUnavailableError(RuntimeError):
    pass


def _average_confidence(confidences: list[object], words: list[str]) -> Decimal | None:
    values: list[Decimal] = []
    for confidence, word in zip(confidences, words, strict=True):
        if not word.strip():
            continue
        try:
            value = Decimal(str(confidence)) / Decimal(100)
        except (ArithmeticError, TypeError, ValueError):
            continue
        if value.is_finite() and value >= 0:
            values.append(value)
    if not values:
        return None
    return sum(values) / len(values)


def extract_from_pdf(pdf_bytes: bytes) -> ExtractionResult:
    settings = get_settings()
    configured_tesseract = settings.tesseract_cmd.strip()
    if configured_tesseract:
        pytesseract.pytesseract.tesseract_cmd = configured_tesseract
    tesseract_available = bool(configured_tesseract or shutil.which("tesseract"))

    text_parts: list[str] = []
    field_by_name: dict[str, ExtractedValue] = {}
    ocr_used = False
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        for page_index, page in enumerate(document):
            page_number = page_index + 1
            page_text = page.get_text("text").strip()
            page_confidence: Decimal | None = None
            if not page_text and not tesseract_available:
                raise OCRUnavailableError(
                    "This PDF page has no selectable text and Tesseract OCR is not installed."
                )
            if not page_text:
                pixmap = page.get_pixmap(dpi=200, alpha=False)
                image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                data = image_to_data(image, output_type=Output.DICT)
                page_text = image_to_string(image).strip()
                page_confidence = _average_confidence(data["conf"], data["text"])
                ocr_used = True
            text_parts.append(page_text)
            for name, pattern in _PATTERNS.items():
                match = pattern.search(page_text)
                if match and name not in field_by_name:
                    field_by_name[name] = ExtractedValue(
                        field_name=name,
                        extracted_value=match.group(1).strip(),
                        page_number=page_number,
                        confidence=page_confidence,
                    )

    return ExtractionResult(
        text="\n".join(part for part in text_parts if part),
        fields=list(field_by_name.values()),
        ocr_used=ocr_used,
    )
