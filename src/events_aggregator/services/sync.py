import logging

from events_aggregator.clients.base import EventsProviderClient
from events_aggregator.clients.paginator import EventsPaginator
from events_aggregator.config import INITIAL_CHANGED_AT
from events_aggregator.repositories.base import EventRepository, SyncMetadataRepository
from events_aggregator.services.exceptions import SyncAlreadyRunning
from events_aggregator.timeutils import now_utc, parse_iso

logger = logging.getLogger(__name__)

STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"

KEY_LAST_CHANGED_AT = "last_changed_at"
KEY_LAST_SYNC_TIME = "last_sync_time"
KEY_SYNC_STATUS = "sync_status"


class SyncEventsUsecase:
    def __init__(
        self,
        client: EventsProviderClient,
        events: EventRepository,
        sync_meta: SyncMetadataRepository,
    ) -> None:
        self._client = client
        self._events = events
        self._sync_meta = sync_meta

    async def do(self) -> int:
        # Захватываем «замок» на уровне БД, чтобы воркер и ручной запуск
        # не выполняли синхронизацию одновременно.
        acquired = await self._sync_meta.try_acquire(KEY_SYNC_STATUS, STATUS_RUNNING)
        if not acquired:
            raise SyncAlreadyRunning("Синхронизация уже выполняется")

        last_changed_at = await self._sync_meta.get(KEY_LAST_CHANGED_AT)
        if last_changed_at is None:
            # Первая синхронизация — берём все события с 2000-01-01
            last_changed_at = INITIAL_CHANGED_AT

        max_changed = parse_iso(last_changed_at)
        processed = 0
        try:
            async for event_data in EventsPaginator(self._client, last_changed_at):
                await self._events.upsert(event_data)
                processed += 1
                raw_changed = event_data.get("changed_at")
                if raw_changed:
                    changed = parse_iso(raw_changed)
                    max_changed = max(max_changed, changed)
        except Exception:
            logger.exception("Синхронизация не удалась")
            await self._sync_meta.set(KEY_SYNC_STATUS, STATUS_ERROR)
            raise

        # Контракт: changed_at передаётся в формате YYYY-MM-DD,
        # поэтому храним максимум из пачки как дату.
        await self._sync_meta.set(KEY_LAST_CHANGED_AT, max_changed.date().isoformat())
        await self._sync_meta.set(KEY_LAST_SYNC_TIME, now_utc().isoformat())
        await self._sync_meta.set(KEY_SYNC_STATUS, STATUS_SUCCESS)
        logger.info("Синхронизация завершена: обработано событий — %d", processed)
        return processed
