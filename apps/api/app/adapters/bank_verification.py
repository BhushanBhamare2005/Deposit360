import json
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings

_BANK_STATUSES = {"pending_external", "confirmed", "failed", "unable_to_verify"}


@dataclass(frozen=True)
class BankVerificationResult:
    status: str
    source: str
    note: str
    checked_at: datetime


def _mock_result(instrument_number: str, bank_name: str) -> BankVerificationResult:
    return BankVerificationResult(
        status="unable_to_verify",
        source="mock-adapter",
        note=(
            "Simulation only: no bank was contacted. "
            f"Instrument {instrument_number} at {bank_name} requires manual confirmation."
        ),
        checked_at=datetime.now(UTC),
    )


def _http_result(instrument_number: str, bank_name: str) -> BankVerificationResult:
    settings = get_settings()
    if not settings.bank_verification_url:
        raise RuntimeError("BANK_VERIFICATION_URL is required for the http adapter")

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if settings.bank_verification_api_key:
        headers["Authorization"] = f"Bearer {settings.bank_verification_api_key}"
    request = Request(
        settings.bank_verification_url,
        data=json.dumps({"instrument_number": instrument_number, "bank_name": bank_name}).encode(
            "utf-8"
        ),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read())
    except HTTPError as exc:
        raise RuntimeError(f"Bank verification provider returned HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Bank verification provider could not be reached") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("Bank verification provider returned invalid JSON") from exc

    if not isinstance(payload, dict) or payload.get("status") not in _BANK_STATUSES:
        raise RuntimeError("Bank verification provider response has an unsupported status")
    note = payload.get("note", "")
    if not isinstance(note, str):
        raise RuntimeError("Bank verification provider response has an invalid note")
    return BankVerificationResult(
        status=payload["status"],
        source="configured-http-provider",
        note=note,
        checked_at=datetime.now(UTC),
    )


def request_verification(instrument_number: str, bank_name: str) -> BankVerificationResult:
    adapter = get_settings().bank_verification_adapter
    if adapter == "mock":
        return _mock_result(instrument_number, bank_name)
    if adapter == "http":
        return _http_result(instrument_number, bank_name)
    raise RuntimeError(f"Unsupported bank verification adapter: {adapter}")
