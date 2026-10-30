import secrets

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import get_settings
from app.workers.tasks.maturity_alerts import run_maturity_alerts

router = APIRouter()


@router.post("/internal/lifecycle/refresh", include_in_schema=False)
def refresh_lifecycle(authorization: str | None = Header(default=None)) -> dict[str, int | str]:
    cron_secret = get_settings().cron_secret
    if not cron_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lifecycle cron is not configured",
        )
    expected_authorization = f"Bearer {cron_secret}"
    if not authorization or not secrets.compare_digest(authorization, expected_authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid cron authorization",
        )

    changed, reminders = run_maturity_alerts()
    return {"status": "ok", "changed": changed, "reminders": reminders}
