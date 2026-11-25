from types import SimpleNamespace

from events_aggregator.repositories.ticket_repo import TicketRepositoryImpl


class _FakeSession:
    """Минимальная заглушка AsyncSession для проверки upsert-логики."""

    def __init__(self, existing=None) -> None:
        self._existing = existing
        self.added: list = []

    async def get(self, model, pk):
        return self._existing

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        pass


async def test_create_inserts_new_ticket():
    session = _FakeSession(existing=None)
    repo = TicketRepositoryImpl(session)

    ticket = await repo.create("t1", "evt-1", "Иван", "Иванов", "a@b.c", "A1")

    assert ticket.id == "t1"
    assert ticket.is_cancelled is False
    assert session.added == [ticket]


async def test_create_reuses_cancelled_ticket_row():
    """Контракт: провайдер переиспользует ticket_id для того же места.

    Повторная регистрация на отменённое место не должна падать на
    нарушении первичного ключа — строка переиспользуется.
    """
    existing = SimpleNamespace(
        id="t1",
        event_id="evt-1",
        first_name="Пётр",
        last_name="Петров",
        email="old@b.c",
        seat="A1",
        created_at=None,
        is_cancelled=True,
    )
    session = _FakeSession(existing=existing)
    repo = TicketRepositoryImpl(session)

    ticket = await repo.create("t1", "evt-1", "Иван", "Иванов", "new@b.c", "A1")

    assert ticket is existing
    assert ticket.is_cancelled is False
    assert ticket.first_name == "Иван"
    assert ticket.email == "new@b.c"
    # повторной вставки не было — иначе нарушение первичного ключа
    assert session.added == []
