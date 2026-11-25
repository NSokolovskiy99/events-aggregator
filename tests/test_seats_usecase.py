from types import SimpleNamespace

import pytest

from events_aggregator.services.exceptions import EventNotFound, EventUnexpectedStatus
from events_aggregator.services.seats import GetSeatsUsecase


async def test_returns_difference_between_provider_and_taken(
    provider_client, events_repo, tickets_repo, cache, fake_event
):
    events_repo.get.return_value = fake_event
    provider_client.seats.return_value = ["A1", "A2", "A3"]
    tickets_repo.taken_seats.return_value = {"A2"}

    usecase = GetSeatsUsecase(provider_client, events_repo, tickets_repo, cache)
    seats = await usecase.do("evt-1")

    assert seats == ["A1", "A3"]


async def test_uses_cache_within_ttl(
    provider_client, events_repo, tickets_repo, cache, fake_event
):
    events_repo.get.return_value = fake_event
    provider_client.seats.return_value = ["A1", "A2"]
    tickets_repo.taken_seats.return_value = set()

    usecase = GetSeatsUsecase(provider_client, events_repo, tickets_repo, cache)
    await usecase.do("evt-1")
    await usecase.do("evt-1")

    # второй вызов из кэша — провайдер дёрнут один раз
    assert provider_client.seats.await_count == 1


async def test_unknown_event_raises(provider_client, events_repo, tickets_repo, cache):
    events_repo.get.return_value = None

    usecase = GetSeatsUsecase(provider_client, events_repo, tickets_repo, cache)
    with pytest.raises(EventNotFound):
        await usecase.do("no-such-event")


async def test_non_published_event_raises_without_provider_call(
    provider_client, events_repo, tickets_repo, cache
):
    # Провайдер отдаёт 500 с HTML для неопубликованных событий —
    # до внешнего API доходить не должны.
    events_repo.get.return_value = SimpleNamespace(id="evt-1", status="new")

    usecase = GetSeatsUsecase(provider_client, events_repo, tickets_repo, cache)
    with pytest.raises(EventUnexpectedStatus):
        await usecase.do("evt-1")

    provider_client.seats.assert_not_called()
