import pytest

from events_aggregator.services.exceptions import SyncAlreadyRunning
from events_aggregator.services.sync import (
    KEY_LAST_CHANGED_AT,
    KEY_SYNC_STATUS,
    STATUS_ERROR,
    STATUS_RUNNING,
    STATUS_SUCCESS,
    SyncEventsUsecase,
)

CHANGED_AT_1 = "2026-11-10"
CHANGED_AT_2 = "2026-11-15"

STORED_CHANGED_AT_1 = "2026-11-10"
STORED_CHANGED_AT_2 = "2026-11-15"


def _page(changed_at: str) -> dict:
    return {
        "results": [{"id": "evt-1", "changed_at": changed_at}],
        "next": None,
    }


async def test_first_sync_uses_initial_changed_at(
    provider_client, events_repo, sync_repo
):
    sync_repo.get.return_value = None
    provider_client.events.return_value = _page(CHANGED_AT_1)

    usecase = SyncEventsUsecase(provider_client, events_repo, sync_repo)
    processed = await usecase.do()

    assert processed == 1
    events_repo.upsert.assert_awaited_once_with(
        {"id": "evt-1", "changed_at": CHANGED_AT_1}
    )
    # первый запрос — с точкой отсчёта из ТЗ (формат даты YYYY-MM-DD)
    provider_client.events.assert_awaited_once_with(
        changed_at="2000-01-01", next_url=None
    )
    sync_repo.set.assert_any_await(KEY_SYNC_STATUS, STATUS_SUCCESS)


async def test_incremental_sync_uses_last_changed_at(
    provider_client, events_repo, sync_repo
):
    sync_repo.get.return_value = CHANGED_AT_1
    provider_client.events.return_value = _page(CHANGED_AT_2)

    usecase = SyncEventsUsecase(provider_client, events_repo, sync_repo)
    await usecase.do()

    provider_client.events.assert_awaited_once_with(
        changed_at=CHANGED_AT_1, next_url=None
    )

    sync_repo.set.assert_any_await(KEY_LAST_CHANGED_AT, STORED_CHANGED_AT_2)


async def test_failed_sync_sets_error_status(provider_client, events_repo, sync_repo):
    sync_repo.get.return_value = None
    provider_client.events.side_effect = RuntimeError("provider down")

    usecase = SyncEventsUsecase(provider_client, events_repo, sync_repo)
    try:
        await usecase.do()
    except RuntimeError:
        pass  # ошибка пробрасывается наверх — так и задумано

    sync_repo.set.assert_any_await(KEY_SYNC_STATUS, STATUS_ERROR)
    # «замок» running был захвачен до запроса
    sync_repo.try_acquire.assert_any_await(KEY_SYNC_STATUS, STATUS_RUNNING)
    events_repo.upsert.assert_not_called()


async def test_error_status_not_reset_to_success(
    provider_client, events_repo, sync_repo
):
    sync_repo.get.return_value = None
    provider_client.events.side_effect = RuntimeError("provider down")

    usecase = SyncEventsUsecase(provider_client, events_repo, sync_repo)
    try:
        await usecase.do()
    except RuntimeError:
        pass

    statuses = [
        c.args[1] for c in sync_repo.set.await_args_list if c.args[0] == KEY_SYNC_STATUS
    ]
    assert STATUS_SUCCESS not in statuses


async def test_skips_when_sync_already_running(provider_client, events_repo, sync_repo):
    # Захват не удался — значит синхронизация уже идёт в другом процессе.
    sync_repo.try_acquire.return_value = False

    usecase = SyncEventsUsecase(provider_client, events_repo, sync_repo)
    with pytest.raises(SyncAlreadyRunning):
        await usecase.do()

    provider_client.events.assert_not_called()
    events_repo.upsert.assert_not_called()
