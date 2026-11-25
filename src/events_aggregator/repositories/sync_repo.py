from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.models import SyncMetadata
from events_aggregator.services.sync import KEY_SYNC_STATUS, STATUS_SUCCESS


class SyncMetadataRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> str | None:
        row = await self._session.get(SyncMetadata, key)
        return row.value if row else None

    async def set(self, key: str, value: str) -> None:
        row = await self._session.get(SyncMetadata, key)
        if row is None:
            row = SyncMetadata(key=key, value=value)
            self._session.add(row)
        else:
            row.value = value
        await self._session.commit()

    async def reset_running(self) -> None:
        """Сбрасывает признак идущего синка при старте приложения.

        Под только что поднялся — ни один синк физически не выполняется.
        Статус 'running' в базе на этот момент — артефакт прошлого пода
        (деплой пришёлся на окно синка). Без сброса POST /api/sync/trigger
        вечно отвечает 409.
        """
        await self.set(KEY_SYNC_STATUS, STATUS_SUCCESS)

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
        await self._session.commit()
        return result.rowcount == 1
