import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


def send_http_message(
    *,
    channel: str,
    endpoint: str,
    api_key: str,
    payload: dict[str, str],
) -> None:
    if not endpoint:
        raise RuntimeError(f"{channel.upper()}_DELIVERY_URL is required for the http adapter")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(f"{channel} provider returned HTTP {response.status}")
    except HTTPError as exc:
        raise RuntimeError(f"{channel} provider returned HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"{channel} provider could not be reached") from exc


def log_message(channel: str, recipient: str, subject: str, body: str) -> None:
    logger.info(
        "Local %s notification sink accepted message to %s: %s (%d characters)",
        channel,
        recipient,
        subject,
        len(body),
    )
