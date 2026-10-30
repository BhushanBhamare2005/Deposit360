from app.adapters.http_delivery import log_message, send_http_message
from app.core.config import get_settings


def send_email(recipient: str, subject: str, body: str) -> None:
    settings = get_settings()
    if settings.email_delivery_adapter == "log":
        log_message("email", recipient, subject, body)
        return
    if settings.email_delivery_adapter == "http":
        send_http_message(
            channel="email",
            endpoint=settings.email_delivery_url,
            api_key=settings.email_delivery_api_key,
            payload={"to": recipient, "subject": subject, "body": body},
        )
        return
    raise RuntimeError(f"Unsupported email delivery adapter: {settings.email_delivery_adapter}")
