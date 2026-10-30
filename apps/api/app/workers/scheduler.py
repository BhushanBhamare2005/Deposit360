import asyncio
import logging

from app.workers.tasks.maturity_alerts import run_maturity_alerts

logger = logging.getLogger(__name__)


async def run_lifecycle_scheduler(interval_seconds: int) -> None:
    while True:
        try:
            changed, reminders = await asyncio.to_thread(run_maturity_alerts)
            logger.info(
                "Lifecycle scheduler refreshed %d states and queued %d reminders",
                changed,
                reminders,
            )
        except Exception:
            logger.exception("Lifecycle scheduler run failed")
        await asyncio.sleep(interval_seconds)
