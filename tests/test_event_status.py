from datetime import datetime

from events_aggregator.enums import EventStatus
from events_aggregator.schemas import EventListItem, PlaceResponse


def _item(status: str) -> EventListItem:
    return EventListItem(
        id="evt-1",
        name="Мероприятие 1",
        place=PlaceResponse(
            id="place-1", name="Площадка 1", city="Ставрополь", address="ул. Полевая, 1"
        ),
        event_time=datetime(2026, 12, 1, 17, 0, 0),
        registration_deadline=datetime(2026, 11, 30, 17, 0, 0),
        status=status,
        number_of_visitors=1,
    )


def test_known_statuses_are_enum_members():
    assert EventStatus("published") is EventStatus.PUBLISHED
    assert EventStatus("registration_closed") is EventStatus.REGISTRATION_CLOSED
    assert EventStatus("finished") is EventStatus.FINISHED


def test_unknown_status_does_not_break_schema():
    # Провайдер может добавить новый статус — API не должен падать с 500.
    item = _item("brand_new_status")

    assert item.status == "brand_new_status"
    assert item.model_dump()["status"] == "brand_new_status"


def test_known_status_serializes_to_value():
    assert _item("registration_closed").model_dump()["status"] == "registration_closed"
