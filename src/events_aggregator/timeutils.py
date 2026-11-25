from datetime import UTC, datetime


def parse_iso(value: str) -> datetime:
    """Парсит ISO-8601 строку в наивное UTC-время (для колонок DateTime)."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC)
    return dt.replace(tzinfo=None)


def now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def db_now() -> datetime:
    """Наивное UTC-время для дефолтов колонок."""
    return datetime.now(UTC).replace(tzinfo=None)
