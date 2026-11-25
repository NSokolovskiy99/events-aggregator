from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from events_aggregator.cache import TTLCache


@pytest.fixture
def fake_event():
    return SimpleNamespace(
        id="evt-1",
        name="Мероприятие 1",
        place_id="place-1",
        place_name="Площадка 1",
        place_city="Ставрополь",
        place_address="ул. Ленина, 1",
        seats_pattern="A-100,B-50",
        event_time=datetime(2026, 12, 1, 17, 0, 0),
        registration_deadline=datetime(2099, 1, 1),
        status="published",
        number_of_visitors=1,
        changed_at=datetime(2026, 11, 10, 12, 0, 0),
        synced_at=datetime(2026, 11, 20),
    )


@pytest.fixture
def events_repo():
    return AsyncMock()


@pytest.fixture
def tickets_repo():
    return AsyncMock()


@pytest.fixture
def sync_repo():
    return AsyncMock()


@pytest.fixture
def provider_client():
    return AsyncMock()


@pytest.fixture
def cache():
    return TTLCache(ttl_seconds=30)
