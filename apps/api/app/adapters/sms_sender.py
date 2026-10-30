from app.adapters.http_delivery import log_message, send_http_message
from app.core.config import get_settings


def send_sms(recipient: str, body: str) -> None:
    settings = get_settings()
    if settings.sms_delivery_adapter == "log":
        log_message("sms", recipient, "SMS notification", body)
        return
    if settings.sms_delivery_adapter == "http":
        send_http_message(
            channel="sms",
            endpoint=settings.sms_delivery_url,
            api_key=settings.sms_delivery_api_key,
            payload={"to": recipient, "body": body},
        )
        return
    raise RuntimeError(f"Unsupported SMS delivery adapter: {settings.sms_delivery_adapter}")
