from typing import Any, Protocol


class EventsProviderClient(Protocol):
    async def events(
        self, changed_at: str | None = None, next_url: str | None = None
    ) -> dict[str, Any]: ...

    async def seats(self, event_id: str) -> list[str]: ...

    async def register(
        self, event_id: str, first_name: str, last_name: str, email: str, seat: str
    ) -> str: ...

    async def cancel(self, event_id: str, ticket_id: str) -> None: ...
