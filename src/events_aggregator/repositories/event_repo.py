from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.models import Event
from events_aggregator.timeutils import db_now, parse_iso


class EventRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, event_id: str) -> Event | None:
        return await self._session.get(Event, event_id)

    def _values(self, data: dict) -> dict:
        """Приводит payload провайдера к значениям колонок Event.

        Провайдер отдаёт даты строками ISO-8601, а колонки — DateTime.
        asyncpg не приводит строки к datetime сам, поэтому парсим здесь.
        """
        raw_changed = data.get("changed_at")
        return {
            "id": data["id"],
            "name": data["name"],
            "place_id": data["place"]["id"],
            "place_name": data["place"]["name"],
            "place_city": data["place"]["city"],
            "place_address": data["place"]["address"],
            "seats_pattern": data["place"].get("seats_pattern"),
            "event_time": parse_iso(data["event_time"]),
            "registration_deadline": parse_iso(data["registration_deadline"]),
            "status": data["status"],
            "number_of_visitors": data.get("number_of_visitors") or 0,
            "changed_at": parse_iso(raw_changed) if raw_changed else None,
            "synced_at": db_now(),
        }

    async def upsert(self, data: dict) -> Event:
        event = await self.get(data["id"])
        if event is None:
            event = Event(id=data["id"])
            self._session.add(event)
        for field, value in self._values(data).items():
            setattr(event, field, value)
        await self._session.commit()
        return event

    async def upsert_many(self, events: list[dict]) -> int:
        """Bulk upsert страницы событий одним коммитом.

        Один INSERT ... ON CONFLICT DO UPDATE на всю страницу вместо
        коммита на каждое событие — меньше round-trip'ов к БД.
        """
        if not events:
            return 0
        rows = [self._values(data) for data in events]
        stmt = insert(Event).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Event.id],
            set_={col: getattr(stmt.excluded, col) for col in rows[0] if col != "id"},
        )
        await self._session.execute(stmt)
        await self._session.commit()
        return len(rows)

    async def list(
        self, date_from: datetime | None, page: int, page_size: int
    ) -> tuple[int, list[Event]]:
        stmt = select(Event)
        if date_from is not None:
            stmt = stmt.where(Event.event_time >= date_from)
        total = await self._session.scalar(
            select(func.count()).select_from(stmt.subquery())
        )
        rows = (
            await self._session.scalars(
                stmt.order_by(Event.event_time)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return total or 0, list(rows)
