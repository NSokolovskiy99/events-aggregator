"""Перечисляемые доменные значения (статусы событий и синхронизации)."""

from enum import StrEnum


class EventStatus(StrEnum):
    """Статус мероприятия в Events Provider API."""

    NEW = "new"
    PUBLISHED = "published"
    REGISTRATION_CLOSED = "registration_closed"
    FINISHED = "finished"
    CANCELLED = "cancelled"

    @classmethod
    def _missing_(cls, value: object) -> "EventStatus | None":
        """Не роняем API, если провайдер добавит новый статус.

        Вместо ошибки валидации создаём псевдо-член с исходным значением,
        чтобы неизвестный статус просто прошёл насквозь.
        """
        if isinstance(value, str):
            member = str.__new__(cls, value)
            member._name_ = value
            member._value_ = value
            return member
        return None


class SyncStatus(StrEnum):
    """Статус фоновой синхронизации (хранится в sync_metadata)."""

    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
