import httpx
import pytest

from events_aggregator.clients.exceptions import (
    EmailAlreadyRegistered,
    SeatAlreadyTaken,
)
from events_aggregator.clients.provider_client import EventsProviderClientImpl


@pytest.fixture
def transport():
    def handler(request: httpx.Request) -> httpx.Response:
        # все пути — с префиксом /api и обязательным trailing slash
        path = request.url.path
        if path == "/api/events/":
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [{"id": "evt-1", "name": "Мероприятие 1"}],
                },
            )
        if path == "/api/events/evt-1/seats/":
            return httpx.Response(200, json={"seats": ["A1", "A2"]})
        if path == "/api/events/evt-1/register/" and request.method == "POST":
            return httpx.Response(201, json={"ticket_id": "abc-123"})
        if path == "/api/events/evt-1/unregister/" and request.method == "DELETE":
            return httpx.Response(200, json={"success": True})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.fixture
def client(transport):
    impl = EventsProviderClientImpl(use_mock=False)
    impl._http = httpx.AsyncClient(
        transport=transport, base_url="https://fake", follow_redirects=True
    )
    impl._base_scheme = "https"
    return impl


async def test_events_returns_provider_json(client):
    data = await client.events(changed_at="2000-01-01T00:00:00+00:00")
    assert data["count"] == 1
    assert data["results"][0]["id"] == "evt-1"


async def test_events_follows_next_url(client):
    data = await client.events(
        next_url="http://fake/api/events/?changed_at=2000-01-01&cursor=abc"
    )
    assert data["results"][0]["id"] == "evt-1"


async def test_events_upgrades_next_url_scheme_to_https():
    """Провайдер отдаёт next по http — клиент обязан поднять схему до https."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"count": 0, "next": None, "results": []})

    impl = EventsProviderClientImpl(use_mock=False)
    impl._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://fake"
    )
    impl._base_scheme = "https"

    await impl.events(next_url="http://fake/api/events/?cursor=abc")

    assert seen == ["https://fake/api/events/?cursor=abc"]


async def test_events_follows_redirect():
    """Контракт: URL без trailing slash отдаёт 301 — клиент должен его пройти."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/events":
            return httpx.Response(301, headers={"Location": "/api/events/"})
        return httpx.Response(
            200, json={"count": 1, "next": None, "results": [{"id": "evt-1"}]}
        )

    impl = EventsProviderClientImpl(use_mock=False)
    impl._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://fake",
        follow_redirects=True,
    )
    impl._base_scheme = "https"

    data = await impl.events(next_url="https://fake/api/events")

    assert data["results"][0]["id"] == "evt-1"


async def test_seats_returns_seats(client):
    assert await client.seats("evt-1") == ["A1", "A2"]


async def test_register_returns_ticket_id(client):
    ticket_id = await client.register("evt-1", "Иван", "Иванов", "i@example.com", "A1")
    assert ticket_id == "abc-123"


async def test_cancel_does_not_raise(client):
    await client.cancel("evt-1", "abc-123")


async def test_http_error_raises(client):
    with pytest.raises(httpx.HTTPStatusError):
        await client.seats("unknown-event")


async def test_register_maps_400_to_seat_already_taken():
    """Контракт: 400 при регистрации = место уже занято."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400, json=["This ticket is not available (already sold)."]
        )

    impl = EventsProviderClientImpl(use_mock=False)
    impl._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://fake"
    )
    impl._base_scheme = "https"

    with pytest.raises(SeatAlreadyTaken):
        await impl.register("evt-1", "Иван", "Иванов", "i@example.com", "A1")


async def test_register_maps_400_email_to_email_already_registered():
    """Провайдер использует 400 и для дубликата email — различаем по тексту."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json=["Visitor with this email is already registered for this event."],
        )

    impl = EventsProviderClientImpl(use_mock=False)
    impl._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://fake"
    )
    impl._base_scheme = "https"

    with pytest.raises(EmailAlreadyRegistered):
        await impl.register("evt-1", "Иван", "Иванов", "i@example.com", "A1")
