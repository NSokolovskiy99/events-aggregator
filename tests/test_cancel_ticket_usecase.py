from types import SimpleNamespace

import pytest

from events_aggregator.services.cancel_ticket import CancelTicketUsecase
from events_aggregator.services.exceptions import TicketNotFound


@pytest.fixture
def usecase(provider_client, tickets_repo, cache):
    return CancelTicketUsecase(provider_client, tickets_repo, cache)


async def test_cancel_calls_provider_and_repo(usecase, provider_client, tickets_repo):
    tickets_repo.get.return_value = SimpleNamespace(
        id="t-1", is_cancelled=False, event_id="evt-1"
    )

    await usecase.do("t-1")

    provider_client.cancel.assert_awaited_once_with("evt-1", "t-1")
    tickets_repo.cancel.assert_awaited_once_with("t-1")


async def test_unknown_ticket_raises(usecase, tickets_repo):
    tickets_repo.get.return_value = None
    with pytest.raises(TicketNotFound):
        await usecase.do("no-such")


async def test_already_cancelled_raises(usecase, tickets_repo):
    tickets_repo.get.return_value = SimpleNamespace(
        id="t-1", is_cancelled=True, event_id="evt-1"
    )
    with pytest.raises(TicketNotFound):
        await usecase.do("t-1")

    provider_cancel = getattr(usecase, "_client", None)
    assert provider_cancel is None or not provider_cancel.cancel.called
