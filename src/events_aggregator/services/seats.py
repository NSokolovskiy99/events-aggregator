from events_aggregator.cache import TTLCache
from events_aggregator.clients.base import EventsProviderClient
from events_aggregator.enums import EventStatus
from events_aggregator.repositories.base import EventRepository, TicketRepository
from events_aggregator.services.exceptions import EventNotFound, EventUnexpectedStatus


class GetSeatsUsecase:
    def __init__(
        self,
        client: EventsProviderClient,
        events: EventRepository,
        tickets: TicketRepository,
        cache: TTLCache,
    ) -> None:
        self._client = client
        self._events = events
        self._tickets = tickets
        self._cache = cache

    async def do(self, event_id: str) -> list[str]:
        event = await self._events.get(event_id)
        if event is None:
            raise EventNotFound(f"Мероприятие {event_id} не найдено")
        # Провайдер отдаёт 500 с HTML для неопубликованных событий,
        # поэтому валидируем статус на своей стороне.
        if event.status != EventStatus.PUBLISHED:
            raise EventUnexpectedStatus(
                f"Мероприятие {event_id} имеет статус '{event.status}', "
                f"ожидался '{EventStatus.PUBLISHED}'"
            )

        cached = self._cache.get(event_id)
        if cached is not None:
            return cached

        provider_seats = set(await self._client.seats(event_id))
        taken = await self._tickets.taken_seats(event_id)
        available = sorted(provider_seats - taken)

        self._cache.set(event_id, available)
        return available
