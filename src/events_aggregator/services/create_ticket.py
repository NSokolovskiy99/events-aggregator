from events_aggregator.cache import TTLCache
from events_aggregator.clients.base import EventsProviderClient
from events_aggregator.clients.exceptions import (
    EmailAlreadyRegistered,
    SeatAlreadyTaken,
)
from events_aggregator.repositories.base import EventRepository, TicketRepository
from events_aggregator.services.constants import PUBLISHED
from events_aggregator.services.exceptions import (
    DuplicateRegistration,
    EventNotFound,
    EventUnexpectedStatus,
    RegistrationDeadlinePassed,
    SeatUnavailable,
)
from events_aggregator.services.seats import GetSeatsUsecase
from events_aggregator.timeutils import now_utc


class CreateTicketUsecase:
    def __init__(
        self,
        client: EventsProviderClient,
        events: EventRepository,
        tickets: TicketRepository,
        seats: GetSeatsUsecase,
        cache: TTLCache,
    ) -> None:
        self._client = client
        self._events = events
        self._tickets = tickets
        self._seats = seats
        self._cache = cache

    async def do(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        event = await self._events.get(event_id)
        if event is None:
            raise EventNotFound(f"Мероприятие {event_id} не найдено")
        if event.status != PUBLISHED:
            raise EventUnexpectedStatus(
                f"Мероприятие {event_id} имеет статус '{event.status}', "
                f"ожидался '{PUBLISHED}'"
            )
        if (
            event.registration_deadline is not None
            and now_utc() > event.registration_deadline
        ):
            raise RegistrationDeadlinePassed(
                f"Срок регистрации на мероприятие {event_id} истёк"
            )

        available = set(await self._seats.do(event_id))
        if seat not in available:
            raise SeatUnavailable(f"Место {seat} недоступно для мероприятия {event_id}")

        try:
            ticket_id = await self._client.register(
                event_id, first_name, last_name, email, seat
            )
        except SeatAlreadyTaken as exc:
            # Гонка: место заняли между нашей проверкой и запросом к провайдеру.
            raise SeatUnavailable(
                f"Место {seat} недоступно для мероприятия {event_id}"
            ) from exc
        except EmailAlreadyRegistered as exc:
            raise DuplicateRegistration(str(exc)) from exc
        await self._tickets.create(
            ticket_id, event_id, first_name, last_name, email, seat
        )
        self._cache.invalidate(event_id)
        return ticket_id
