import json
from types import SimpleNamespace

from app.adapters import bank_verification, email_sender, sms_sender


class FakeResponse:
    status = 202

    def __init__(self, body: bytes = b"{}"):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.body


def test_bank_verification_defaults_to_mock_without_contacting_provider(monkeypatch):
    monkeypatch.setattr(
        bank_verification,
        "get_settings",
        lambda: SimpleNamespace(bank_verification_adapter="mock"),
    )

    result = bank_verification.request_verification("FD-123", "Example Bank")

    assert result.status == "unable_to_verify"
    assert result.source == "mock-adapter"
    assert "no bank was contacted" in result.note


def test_bank_http_adapter_uses_explicit_endpoint_and_provider_contract(monkeypatch):
    request_data = {}

    def fake_urlopen(request, timeout):
        request_data["url"] = request.full_url
        request_data["headers"] = request.headers
        request_data["body"] = json.loads(request.data)
        request_data["timeout"] = timeout
        return FakeResponse(b'{"status":"confirmed","note":"Provider confirmed."}')

    monkeypatch.setattr(
        bank_verification,
        "get_settings",
        lambda: SimpleNamespace(
            bank_verification_adapter="http",
            bank_verification_url="https://provider.invalid/check",
            bank_verification_api_key="test-key",
        ),
    )
    monkeypatch.setattr(bank_verification, "urlopen", fake_urlopen)

    result = bank_verification.request_verification("FD-123", "Example Bank")

    assert request_data["url"] == "https://provider.invalid/check"
    assert request_data["headers"]["Authorization"] == "Bearer test-key"
    assert request_data["body"] == {
        "instrument_number": "FD-123",
        "bank_name": "Example Bank",
    }
    assert result.status == "confirmed"
    assert result.source == "configured-http-provider"
    assert result.note == "Provider confirmed."


def test_email_and_sms_http_adapters_send_provider_contract(monkeypatch):
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(
        email_sender,
        "get_settings",
        lambda: SimpleNamespace(
            email_delivery_adapter="http",
            email_delivery_url="https://email.invalid/send",
            email_delivery_api_key="email-key",
        ),
    )
    monkeypatch.setattr(
        sms_sender,
        "get_settings",
        lambda: SimpleNamespace(
            sms_delivery_adapter="http",
            sms_delivery_url="https://sms.invalid/send",
            sms_delivery_api_key="sms-key",
        ),
    )
    monkeypatch.setattr("app.adapters.http_delivery.urlopen", fake_urlopen)

    email_sender.send_email("user@example.com", "Subject", "Email body")
    sms_sender.send_sms("+15551234567", "SMS body")

    assert json.loads(requests[0][0].data) == {
        "to": "user@example.com",
        "subject": "Subject",
        "body": "Email body",
    }
    assert requests[0][0].headers["Authorization"] == "Bearer email-key"
    assert json.loads(requests[1][0].data) == {"to": "+15551234567", "body": "SMS body"}
    assert requests[1][0].headers["Authorization"] == "Bearer sms-key"


def test_email_and_sms_default_to_local_development_sink(monkeypatch):
    accepted = []
    monkeypatch.setattr(
        email_sender,
        "get_settings",
        lambda: SimpleNamespace(email_delivery_adapter="log"),
    )
    monkeypatch.setattr(
        sms_sender,
        "get_settings",
        lambda: SimpleNamespace(sms_delivery_adapter="log"),
    )
    monkeypatch.setattr(email_sender, "log_message", lambda *args: accepted.append(args))
    monkeypatch.setattr(sms_sender, "log_message", lambda *args: accepted.append(args))

    email_sender.send_email("user@example.com", "Subject", "Email body")
    sms_sender.send_sms("+15551234567", "SMS body")

    assert accepted == [
        ("email", "user@example.com", "Subject", "Email body"),
        ("sms", "+15551234567", "SMS notification", "SMS body"),
    ]
