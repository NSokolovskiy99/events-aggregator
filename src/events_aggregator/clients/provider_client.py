import uuid
from typing import Any

import httpx

from events_aggregator.clients.exceptions import (
    EmailAlreadyRegistered,
    ProviderError,
    SeatAlreadyTaken,
)
from events_aggregator.clients.mock import MockProviderData
from events_aggregator.config import settings


def _error_message(resp: httpx.Response) -> str:
    """Достаёт текст ошибки из ответа провайдера.

    Провайдер отдаёт бизнес-ошибки как JSON-массив строк, а инфраструктурные —
    как объект с полем detail.
    """
    try:
        data = resp.json()
    except ValueError:
        return resp.text
    if isinstance(data, list) and data:
        return str(data[0])
    if isinstance(data, dict):
        return str(data.get("detail", data))
    return str(data)


class EventsProviderClientImpl:
    def __init__(self, use_mock: bool = False) -> None:
        self._use_mock = use_mock
        self._mock = MockProviderData()
        # Схема из настроек: провайдер отдаёт next по http, а работаем мы по https.
        self._base_scheme = httpx.URL(settings.provider_base_url).scheme
        self._http = httpx.AsyncClient(
            base_url=settings.provider_base_url,
            timeout=settings.provider_timeout,
            headers={"x-api-key": settings.provider_api_key.get_secret_value()},
            follow_redirects=True,
        )

    async def events(
        self, changed_at: str | None = None, next_url: str | None = None
    ) -> dict[str, Any]:
        if self._use_mock:
            return self._mock.events(changed_at=changed_at, next_url=next_url)

        if next_url is not None:
            # Контракт: следующая страница берётся по полному URL из поля next.
            # Провайдер отдаёт next по http, хотя сам работает по https —
            # поднимаем схему, чтобы не слать x-api-key по открытому каналу.
            url = httpx.URL(next_url).copy_with(scheme=self._base_scheme)
            resp = await self._http.get(url)
        else:
            params = {"changed_at": changed_at} if changed_at else None
            resp = await self._http.get("/api/events/", params=params)
        resp.raise_for_status()
        return resp.json()

    async def seats(self, event_id: str) -> list[str]:
        if self._use_mock:
            return self._mock.seats(event_id)

        resp = await self._http.get(f"/api/events/{event_id}/seats/")
        resp.raise_for_status()
        return resp.json()["seats"]

    async def register(
        self, event_id: str, first_name: str, last_name: str, email: str, seat: str
    ) -> str:
        if self._use_mock:
            return str(uuid.uuid4())

        resp = await self._http.post(
            f"/api/events/{event_id}/register/",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "seat": seat,
                "email": email,
            },
        )
        if resp.status_code == 400:
            # Контракт: 400 при регистрации — бизнес-ошибка. Провайдер использует
            # один код для разных причин, поэтому различаем их по тексту ответа.
            message = _error_message(resp)
            lowered = message.lower()
            if "already sold" in lowered or "not available" in lowered:
                raise SeatAlreadyTaken(message)
            if "already registered" in lowered:
                raise EmailAlreadyRegistered(message)
            raise ProviderError(message)
        resp.raise_for_status()
        return resp.json()["ticket_id"]

    async def cancel(self, event_id: str, ticket_id: str) -> None:
        if self._use_mock:
            return
        resp = await self._http.request(
            "DELETE",
            f"/api/events/{event_id}/unregister/",
            json={"ticket_id": ticket_id},
        )
        resp.raise_for_status()

    async def aclose(self) -> None:
        await self._http.aclose()
