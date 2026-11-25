from typing import Any


class MockProviderData:
    """Фейковые страницы провайдера, чтобы работать без реального API."""

    def _event(self, idx: int) -> dict[str, Any]:
        return {
            "id": f"evt-{idx}",
            "name": f"Мероприятие {idx}",
            "place": {
                "id": f"place-{idx}",
                "name": f"Площадка {idx}",
                "city": "Ставрополь",
                "address": f"ул. Светлая, д. 196, {idx}",
                "seats_pattern": "A-100,B-50",
            },
            "event_time": "2026-12-01T17:00:00+03:00",
            "registration_deadline": "2026-11-30T17:00:00+03:00",
            "status": "published",
            "number_of_visitors": idx,
            "changed_at": f"2026-11-{10 + idx}T12:00:00+00:00",
        }

    def events(
        self, changed_at: str | None = None, next_url: str | None = None
    ) -> dict[str, Any]:
        if next_url is None:
            return {
                "count": 4,
                "next": "http://fake/api/events/?changed_at=2000-01-01&cursor=2",
                "previous": None,
                "results": [self._event(i) for i in (1, 2)],
            }
        return {
            "count": 4,
            "next": None,
            "previous": None,
            "results": [self._event(i) for i in (3, 4)],
        }

    def seats(self, event_id: str) -> list[str]:
        return [f"A{i}" for i in range(1, 11)]
