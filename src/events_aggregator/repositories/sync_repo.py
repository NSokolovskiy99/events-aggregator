from datetime import timedelta

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.config import settings
from events_aggregator.enums import SyncStatus
from events_aggregator.models import SyncMetadata
from events_aggregator.services.domain import KEY_SYNC_STATUS
from events_aggregator.timeutils import db_now, parse_iso

# Время захвата lock'а — по нему определяется «протухший» running-статус.
KEY_SYNC_STATUS_ACQUIRED_AT = "sync_status_acquired_at"


class SyncMetadataRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> str | None:
        row = await self._session.get(SyncMetadata, key)
        return row.value if row else None

    async def _upsert(self, key: str, value: str) -> None:
        row = await self._session.get(SyncMetadata, key)
        if row is None:
            self._session.add(SyncMetadata(key=key, value=value))
        else:
            row.value = value

    async def set(self, key: str, value: str) -> None:
        await self._upsert(key, value)
        await self._session.commit()

    async def reset_running(self) -> None:
        """Сбрасывает только «протухший» lock синхронизации при старте пода.

        Lock имеет TTL: если статус 'running', но время захвата старше TTL,
        значит синк завис (под упал в окне синхронизации) — сбрасываем.
        Свежий lock не трогаем, чтобы при нескольких репликах не снять
        чужой живой lock.
        """
        if await self.get(KEY_SYNC_STATUS) != SyncStatus.RUNNING:
            return
        acquired_at = await self.get(KEY_SYNC_STATUS_ACQUIRED_AT)
        if acquired_at is None:
            # Нет отметки времени (старый формат) — считаем lock протухшим.
            await self.set(KEY_SYNC_STATUS, SyncStatus.SUCCESS)
            return
        age = db_now() - parse_iso(acquired_at)
        if age > timedelta(seconds=settings.sync_lock_ttl):
            await self.set(KEY_SYNC_STATUS, SyncStatus.SUCCESS)

    async def try_acquire(self, key: str, value: str) -> bool:
        """Атомарно переводит ключ в value, если он ещё не в этом значении.

        Возвращает True, если захват удался. Защищает от параллельных
        синхронизаций (воркер + ручной запуск) на уровне БД: INSERT ... ON
        CONFLICT DO UPDATE ... WHERE выполняется одной атомарной операцией.
        """
        stmt = (
            insert(SyncMetadata)
            .values(key=key, value=value)
            .on_conflict_do_update(
                index_elements=[SyncMetadata.key],
                set_={"value": value},
                where=SyncMetadata.value != value,
            )
        )
        result = await self._session.execute(stmt)
        acquired = result.rowcount == 1
        if acquired:
            # Фиксируем время захвата для TTL-проверки в reset_running.
            await self._upsert(KEY_SYNC_STATUS_ACQUIRED_AT, db_now().isoformat())
        await self._session.commit()
        return acquired
