from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.models import Event
from events_aggregator.timeutils import now_utc, parse_iso


class EventRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, event_id: str) -> Event | None:
        return await self._session.get(Event, event_id)

    async def upsert(self, data: dict) -> Event:
        event = await self.get(data["id"])
        if event is None:
            event = Event(id=data["id"])
            self._session.add(event)
        event.name = data["name"]
        event.place_id = data["place"]["id"]
        event.place_name = data["place"]["name"]
        event.place_city = data["place"]["city"]
        event.place_address = data["place"]["address"]
        event.seats_pattern = data["place"].get("seats_pattern")
        # Провайдер отдаёт даты строками ISO-8601, а колонки — DateTime.
        # asyncpg не приводит строки к datetime сам, поэтому парсим здесь.
        event.event_time = parse_iso(data["event_time"])
        event.registration_deadline = parse_iso(data["registration_deadline"])
        event.status = data["status"]
        event.number_of_visitors = data.get("number_of_visitors") or 0
        raw_changed = data.get("changed_at")
        event.changed_at = parse_iso(raw_changed) if raw_changed else None
        event.synced_at = now_utc()
        await self._session.commit()
        return event

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
