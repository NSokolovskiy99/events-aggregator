import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from events_aggregator.clients.provider_client import EventsProviderClientImpl
from events_aggregator.config import settings
from events_aggregator.database import AsyncSessionLocal
from events_aggregator.repositories.event_repo import EventRepositoryImpl
from events_aggregator.repositories.sync_repo import SyncMetadataRepositoryImpl
from events_aggregator.services.sync import SyncEventsUsecase

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def _sync_job():
    async def run() -> None:
        client = EventsProviderClientImpl(use_mock=settings.use_provider_mock)
        try:
            async with AsyncSessionLocal() as session:
                usecase = SyncEventsUsecase(
                    client,
                    EventRepositoryImpl(session),
                    SyncMetadataRepositoryImpl(session),
                )
                await usecase.do()
        finally:
            await client.aclose()

    return run


def start_worker() -> None:
    hour, minute = (int(p) for p in settings.sync_daily_at.split(":"))
    scheduler.add_job(
        _sync_job(),
        trigger="cron",
        hour=hour,
        minute=minute,
        id="daily_events_sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Ежедневная синхронизация запланирована на %02d:%02d", hour, minute)


def stop_worker() -> None:
    if scheduler.running:
        scheduler.shutdown()


async def _run_forever() -> None:
    start_worker()
    try:
        await asyncio.Event().wait()
    finally:
        stop_worker()


def main() -> None:
    """Отдельный процесс воркера: python -m events_aggregator.worker."""
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(_run_forever())
    except KeyboardInterrupt:
        logger.info("Воркер остановлен")


if __name__ == "__main__":
    main()
