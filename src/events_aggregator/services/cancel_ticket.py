from events_aggregator.cache import TTLCache
from events_aggregator.clients.base import EventsProviderClient
from events_aggregator.repositories.base import TicketRepository
from events_aggregator.services.exceptions import TicketNotFound


class CancelTicketUsecase:
    def __init__(
        self, client: EventsProviderClient, tickets: TicketRepository, cache: TTLCache
    ) -> None:
        self._client = client
        self._tickets = tickets
        self._cache = cache

    async def do(self, ticket_id: str) -> None:
        ticket = await self._tickets.get(ticket_id)
        if ticket is None or ticket.is_cancelled:
            raise TicketNotFound(f"Билет {ticket_id} не найден")

        await self._client.cancel(ticket.event_id, ticket_id)
        await self._tickets.cancel(ticket_id)
        self._cache.invalidate(ticket.event_id)
