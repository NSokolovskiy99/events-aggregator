from datetime import datetime

import pytest

from events_aggregator.clients.exceptions import (
    EmailAlreadyRegistered,
    SeatAlreadyTaken,
)
from events_aggregator.services.create_ticket import CreateTicketUsecase
from events_aggregator.services.exceptions import (
    DuplicateRegistration,
    EventNotFound,
    EventUnexpectedStatus,
    RegistrationDeadlinePassed,
    SeatUnavailable,
)
from events_aggregator.services.seats import GetSeatsUsecase


@pytest.fixture
def seats_usecase(provider_client, events_repo, tickets_repo, cache):
    return GetSeatsUsecase(provider_client, events_repo, tickets_repo, cache)


@pytest.fixture
def usecase(provider_client, events_repo, tickets_repo, seats_usecase, cache):
    return CreateTicketUsecase(
        provider_client, events_repo, tickets_repo, seats_usecase, cache
    )


def _event(status="published", deadline=datetime(2099, 1, 1)):
    from types import SimpleNamespace

    return SimpleNamespace(id="evt-1", status=status, registration_deadline=deadline)


async def test_successful_registration(
    usecase, provider_client, events_repo, tickets_repo, cache, fake_event
):
    events_repo.get.return_value = fake_event
    provider_client.seats.return_value = ["A1", "A2"]
    tickets_repo.taken_seats.return_value = set()
    provider_client.register.return_value = "ticket-42"

    ticket_id = await usecase.do("evt-1", "Иван", "Иванов", "i@example.com", "A1")

    assert ticket_id == "ticket-42"
    provider_client.register.assert_awaited_once_with(
        "evt-1", "Иван", "Иванов", "i@example.com", "A1"
    )
    tickets_repo.create.assert_awaited_once_with(
        "ticket-42", "evt-1", "Иван", "Иванов", "i@example.com", "A1"
    )


async def test_event_not_found(usecase, events_repo):
    events_repo.get.return_value = None
    with pytest.raises(EventNotFound):
        await usecase.do("no-such", "Иван", "Иванов", "i@example.com", "A1")


async def test_unexpected_status(usecase, events_repo):
    events_repo.get.return_value = _event(status="cancelled")
    with pytest.raises(EventUnexpectedStatus):
        await usecase.do("evt-1", "Иван", "Иванов", "i@example.com", "A1")


async def test_registration_deadline_passed(usecase, events_repo):
    events_repo.get.return_value = _event(deadline=datetime(2020, 1, 1))
    with pytest.raises(RegistrationDeadlinePassed):
        await usecase.do("evt-1", "Иван", "Иванов", "i@example.com", "A1")


async def test_seat_taken(
    usecase, events_repo, provider_client, tickets_repo, fake_event
):
    events_repo.get.return_value = fake_event
    provider_client.seats.return_value = ["A1", "A2"]
    tickets_repo.taken_seats.return_value = {"A1"}

    with pytest.raises(SeatUnavailable):
        await usecase.do("evt-1", "Иван", "Иванов", "i@example.com", "A1")

    # при недоступном месте до внешнего API не доходим
    provider_client.register.assert_not_called()


async def test_provider_failure_does_not_save_ticket(
    usecase, provider_client, tickets_repo, events_repo, fake_event
):
    events_repo.get.return_value = fake_event
    provider_client.seats.return_value = ["A1"]
    tickets_repo.taken_seats.return_value = set()
    provider_client.register.side_effect = RuntimeError("provider down")

    with pytest.raises(RuntimeError):
        await usecase.do("evt-1", "Иван", "Иванов", "i@example.com", "A1")

    tickets_repo.create.assert_not_called()


async def test_provider_seat_taken_maps_to_seat_unavailable(
    usecase, provider_client, tickets_repo, events_repo, fake_event
):
    # Гонка: место заняли между проверкой и запросом к провайдеру.
    events_repo.get.return_value = fake_event
    provider_client.seats.return_value = ["A1"]
    tickets_repo.taken_seats.return_value = set()
    provider_client.register.side_effect = SeatAlreadyTaken("already sold")

    with pytest.raises(SeatUnavailable):
        await usecase.do("evt-1", "Иван", "Иванов", "i@example.com", "A1")

    tickets_repo.create.assert_not_called()


async def test_provider_email_duplicate_maps_to_duplicate_registration(
    usecase, provider_client, tickets_repo, events_repo, fake_event
):
    events_repo.get.return_value = fake_event
    provider_client.seats.return_value = ["A1"]
    tickets_repo.taken_seats.return_value = set()
    provider_client.register.side_effect = EmailAlreadyRegistered("already registered")

    with pytest.raises(DuplicateRegistration):
        await usecase.do("evt-1", "Иван", "Иванов", "i@example.com", "A1")

    tickets_repo.create.assert_not_called()
