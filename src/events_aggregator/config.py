from typing import Annotated

from pydantic import BeforeValidator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _validate_hhmm(value: str) -> str:
    """Проверяет, что значение задано в формате HH:MM."""
    try:
        hour, minute = (int(part) for part in value.split(":"))
    except ValueError as exc:
        raise ValueError(f"должно быть в формате HH:MM, получено {value!r}") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"часы должны быть 0-23, минуты 0-59, получено {value!r}")
    return value


SyncDailyAt = Annotated[str, BeforeValidator(_validate_hhmm)]


class Settings(BaseSettings):
    """Конфигурация сервиса: переменные окружения + файл .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+asyncpg://postgres:password@localhost:5432/events_db"
    )
    provider_base_url: str = "http://localhost:9000"
    # Все запросы к Events Provider API требуют заголовок x-api-key.
    provider_api_key: SecretStr = SecretStr("")
    provider_timeout: float = 10.0
    use_provider_mock: bool = True

    seats_cache_ttl: int = 30
    sync_daily_at: SyncDailyAt = "03:00"

    # Запускать ли воркер синхронизации внутри процесса API (lifespan).
    # В Docker воркер идёт отдельным процессом (см. run.sh), поэтому там false.
    run_worker_in_api: bool = True


settings = Settings()

# Точка отсчёта первой синхронизации из ТЗ.
# Контракт провайдера требует формат даты YYYY-MM-DD для параметра changed_at.
INITIAL_CHANGED_AT = "2000-01-01"
