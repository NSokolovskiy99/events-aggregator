from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from events_aggregator.cache import TTLCache
from events_aggregator.clients.provider_client import EventsProviderClientImpl
from events_aggregator.config import settings
from events_aggregator.database import AsyncSessionLocal, SessionDep, ping
from events_aggregator.repositories.event_repo import EventRepositoryImpl
from events_aggregator.repositories.sync_repo import SyncMetadataRepositoryImpl
from events_aggregator.repositories.ticket_repo import TicketRepositoryImpl
from events_aggregator.schemas import (
    CancelResponse,
    EventDetailResponse,
    EventListItem,
    EventListResponse,
    HealthResponse,
    PlaceResponse,
    SeatsResponse,
    SyncTriggerResponse,
    TicketCreateRequest,
    TicketResponse,
)
from events_aggregator.services.cancel_ticket import CancelTicketUsecase
from events_aggregator.services.create_ticket import CreateTicketUsecase
from events_aggregator.services.exceptions import (
    DomainError,
    DuplicateRegistration,
    EventNotFound,
    EventUnexpectedStatus,
    RegistrationDeadlinePassed,
    SeatUnavailable,
    SyncAlreadyRunning,
    TicketNotFound,
)
from events_aggregator.services.seats import GetSeatsUsecase
from events_aggregator.services.sync import SyncEventsUsecase
from events_aggregator.worker import start_worker, stop_worker

seats_cache = TTLCache(ttl_seconds=settings.seats_cache_ttl)
_client = EventsProviderClientImpl(use_mock=settings.use_provider_mock)


def get_client() -> EventsProviderClientImpl:
    return _client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Схема БД создаётся миграциями Alembic (см. run.sh), не приложением.
    # В Docker воркер идёт отдельным процессом, поэтому внутри API он
    # стартует только при RUN_WORKER_IN_API=true.
    async with AsyncSessionLocal() as session:
        await SyncMetadataRepositoryImpl(session).reset_running()

    if settings.run_worker_in_api:
        start_worker()
    yield
    if settings.run_worker_in_api:
        stop_worker()
    # Закрываем общий httpx-клиент, иначе соединения утекают при остановке.
    await _client.aclose()


app = FastAPI(title="Events Aggregator", lifespan=lifespan)

ClientDep = Annotated[EventsProviderClientImpl, Depends(get_client)]


@app.get("/api/health", response_model=HealthResponse)
async def health(db: SessionDep) -> HealthResponse:
    await ping(db)
    return HealthResponse(status="ok")


@app.post("/api/sync/trigger", response_model=SyncTriggerResponse)
async def trigger_sync(db: SessionDep, client: ClientDep) -> SyncTriggerResponse:
    usecase = SyncEventsUsecase(
        client, EventRepositoryImpl(db), SyncMetadataRepositoryImpl(db)
    )
    processed = await usecase.do()
    return SyncTriggerResponse(status="ok", processed=processed)


@app.get("/api/events", response_model=EventListResponse)
async def list_events(
    request: Request,
    db: SessionDep,
    date_from: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> EventListResponse:
    date_filter = datetime.strptime(date_from, "%Y-%m-%d") if date_from else None
    repo = EventRepositoryImpl(db)
    total, rows = await repo.list(date_filter, page, page_size)

    def _url(p: int) -> str:
        params = {"page": p, "page_size": page_size}
        if date_from:
            params["date_from"] = date_from
        # Абсолютный URL следующей/предыдущей страницы (как в ТЗ).
        return str(request.url.replace(query=urlencode(params)))

    return EventListResponse(
        count=total,
        next=_url(page + 1) if page * page_size < total else None,
        previous=_url(page - 1) if page > 1 else None,
        results=[
            EventListItem(
                id=e.id,
                name=e.name,
                place=PlaceResponse(
                    id=e.place_id or "",
                    name=e.place_name or "",
                    city=e.place_city or "",
                    address=e.place_address or "",
                    seats_pattern=e.seats_pattern,
                ),
                event_time=e.event_time,
                registration_deadline=e.registration_deadline,
                status=e.status,
                number_of_visitors=e.number_of_visitors or 0,
            )
            for e in rows
        ],
    )


@app.get("/api/events/{event_id}", response_model=EventDetailResponse)
async def event_details(event_id: str, db: SessionDep) -> EventDetailResponse:
    repo = EventRepositoryImpl(db)
    event = await repo.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")
    return EventDetailResponse(
        id=event.id,
        name=event.name,
        place=PlaceResponse(
            id=event.place_id,
            name=event.place_name,
            city=event.place_city,
            address=event.place_address,
            seats_pattern=event.seats_pattern,
        ),
        event_time=event.event_time,
        registration_deadline=event.registration_deadline,
        status=event.status,
        number_of_visitors=event.number_of_visitors,
    )


@app.get("/api/events/{event_id}/seats", response_model=SeatsResponse)
async def get_seats(event_id: str, db: SessionDep, client: ClientDep) -> SeatsResponse:
    usecase = GetSeatsUsecase(
        client, EventRepositoryImpl(db), TicketRepositoryImpl(db), seats_cache
    )
    seats = await usecase.do(event_id)
    return SeatsResponse(event_id=event_id, available_seats=seats)


@app.post("/api/tickets", status_code=201, response_model=TicketResponse)
async def create_ticket(
    payload: TicketCreateRequest, db: SessionDep, client: ClientDep
) -> TicketResponse:
    seats_usecase = GetSeatsUsecase(
        client, EventRepositoryImpl(db), TicketRepositoryImpl(db), seats_cache
    )
    usecase = CreateTicketUsecase(
        client,
        EventRepositoryImpl(db),
        TicketRepositoryImpl(db),
        seats_usecase,
        seats_cache,
    )
    ticket_id = await usecase.do(
        payload.event_id,
        payload.first_name,
        payload.last_name,
        payload.email,
        payload.seat,
    )
    return TicketResponse(ticket_id=ticket_id)


@app.delete("/api/tickets/{ticket_id}", response_model=CancelResponse)
async def cancel_ticket(
    ticket_id: str, db: SessionDep, client: ClientDep
) -> CancelResponse:
    usecase = CancelTicketUsecase(client, TicketRepositoryImpl(db), seats_cache)
    await usecase.do(ticket_id)
    return CancelResponse(success=True)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    if isinstance(exc, EventNotFound | TicketNotFound):
        status = 404
    elif isinstance(exc, SeatUnavailable | SyncAlreadyRunning | DuplicateRegistration):
        status = 409
    elif isinstance(exc, EventUnexpectedStatus | RegistrationDeadlinePassed):
        status = 400
    else:
        status = 500
    return JSONResponse(status_code=status, content={"detail": str(exc)})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": exc.errors()})