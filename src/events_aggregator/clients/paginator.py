from collections.abc import AsyncIterator
from typing import Any

from events_aggregator.clients.base import EventsProviderClient


class EventsPaginator:
    """Обходит постранично выдачу EventsProviderClient как асинхронный итератор."""

    def __init__(self, client: EventsProviderClient, changed_at: str | None = None):
        self._client = client
        self._changed_at = changed_at

    def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[dict[str, Any]]:
        async for page in self.pages():
            for event in page:
                yield event

    async def pages(self) -> AsyncIterator[list[dict[str, Any]]]:
        """Отдаёт выдачу страницами — удобно для bulk-обработки и коммита на страницу."""
        next_url: str | None = None
        while True:
            page = await self._client.events(
                changed_at=self._changed_at, next_url=next_url
            )
            yield page.get("results", [])
            # Контракт: следующая страница — полный URL из поля next
            next_url = page.get("next")
            if not next_url:
                return
