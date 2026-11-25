from unittest.mock import AsyncMock

from events_aggregator.clients.paginator import EventsPaginator

NEXT_URL = "http://fake/api/events/?changed_at=2000-01-01&cursor=abc"


def _page(results: list[dict], next_url: str | None) -> dict:
    return {"results": results, "next": next_url}


async def test_iterates_all_pages_via_next_url():
    client = AsyncMock()
    client.events.side_effect = [
        _page([{"id": "1"}, {"id": "2"}], NEXT_URL),
        _page([{"id": "3"}], None),
    ]

    events = [event async for event in EventsPaginator(client, "2000-01-01")]

    assert [event["id"] for event in events] == ["1", "2", "3"]
    assert client.events.await_count == 2
    client.events.assert_any_await(changed_at="2000-01-01", next_url=None)
    client.events.assert_any_await(changed_at="2000-01-01", next_url=NEXT_URL)


async def test_single_page_stops_immediately():
    client = AsyncMock()
    client.events.return_value = _page([{"id": "1"}], None)

    events = [event async for event in EventsPaginator(client)]

    assert [event["id"] for event in events] == ["1"]
    client.events.assert_awaited_once_with(changed_at=None, next_url=None)


async def test_empty_results_yield_nothing():
    client = AsyncMock()
    client.events.return_value = _page([], None)

    events = [event async for event in EventsPaginator(client)]

    assert events == []
