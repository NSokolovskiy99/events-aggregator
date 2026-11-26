from datetime import datetime

from events_aggregator.repositories.event_repo import EventRepositoryImpl


class _FakeResult:
    rowcount = 1


class _FakeSession:
    """Минимальная заглушка AsyncSession для проверки маппинга."""

    def __init__(self) -> None:
        self.added: list = []
        self.executed: list = []
        self.commits = 0

    async def get(self, model, pk):
        return None

    def add(self, obj) -> None:
        self.added.append(obj)

    async def execute(self, stmt):
        self.executed.append(stmt)
        return _FakeResult()

    async def commit(self) -> None:
        self.commits += 1


def _event_payload() -> dict:
    return {
        "id": "evt-1",
        "name": "Мероприятие 1",
        "place": {
            "id": "place-1",
            "name": "Площадка 1",
            "city": "Ставрополь",
            "address": "ул. Ленина, 1",
            "seats_pattern": "A-100,B-50",
        },
        "event_time": "2026-12-01T17:00:00+03:00",
        "registration_deadline": "2026-11-30T17:00:00+03:00",
        "status": "published",
        "number_of_visitors": 5,
        "changed_at": "2026-11-10T12:00:00+00:00",
    }


async def test_upsert_parses_iso_strings_to_datetime():
    repo = EventRepositoryImpl(_FakeSession())

    event = await repo.upsert(_event_payload())

    # asyncpg не принимает строки в DateTime-колонки — должны быть datetime
    assert isinstance(event.event_time, datetime)
    assert isinstance(event.registration_deadline, datetime)
    assert isinstance(event.changed_at, datetime)
    # tz-aware ISO приводится к наивному UTC
    assert event.event_time == datetime(2026, 12, 1, 14, 0, 0)
    assert event.changed_at == datetime(2026, 11, 10, 12, 0, 0)


async def test_upsert_allows_missing_changed_at():
    repo = EventRepositoryImpl(_FakeSession())
    payload = _event_payload()
    payload.pop("changed_at")

    event = await repo.upsert(payload)

    assert event.changed_at is None


async def test_upsert_many_uses_single_commit():
    session = _FakeSession()
    repo = EventRepositoryImpl(session)
    second = {**_event_payload(), "id": "evt-2"}

    count = await repo.upsert_many([_event_payload(), second])

    assert count == 2
    # один bulk-запрос и один коммит на всю страницу
    assert len(session.executed) == 1
    assert session.commits == 1


async def test_upsert_many_empty_is_noop():
    session = _FakeSession()
    repo = EventRepositoryImpl(session)

    assert await repo.upsert_many([]) == 0
    assert session.executed == []
    assert session.commits == 0
