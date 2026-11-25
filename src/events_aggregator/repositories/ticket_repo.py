from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from events_aggregator.models import Ticket
from events_aggregator.timeutils import db_now


class TicketRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ticket_id: str) -> Ticket | None:
        return await self._session.get(Ticket, ticket_id)

    async def create(
        self,
        ticket_id: str,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> Ticket:
        # Контракт: ticket_id привязан к месту, поэтому после отмены повторная
        # регистрация на то же место вернёт тот же id. Делаем upsert, чтобы не
        # ловить нарушение первичного ключа.
        ticket = await self.get(ticket_id)
        if ticket is None:
            ticket = Ticket(id=ticket_id)
            self._session.add(ticket)
        ticket.event_id = event_id
        ticket.first_name = first_name
        ticket.last_name = last_name
        ticket.email = email
        ticket.seat = seat
        ticket.created_at = db_now()
        ticket.is_cancelled = False
        await self._session.commit()
        return ticket

    async def cancel(self, ticket_id: str) -> None:
        ticket = await self.get(ticket_id)
        if ticket is None:
            return
        ticket.is_cancelled = True
        await self._session.commit()

    async def taken_seats(self, event_id: str) -> set[str]:
        rows = await self._session.scalars(
            select(Ticket.seat).where(
                Ticket.event_id == event_id, Ticket.is_cancelled.is_(False)
            )
        )
        return set(rows)
