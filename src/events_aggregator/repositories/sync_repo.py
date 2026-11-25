from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.models import SyncMetadata


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
