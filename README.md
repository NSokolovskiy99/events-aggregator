# Events Aggregator

Backend-сервис-агрегатор, который синхронизирует мероприятия из **Events Provider API**
в локальную PostgreSQL и предоставляет REST API для работы с событиями и регистрациями.


## Стек

- Python 3.12, FastAPI, Uvicorn
- SQLAlchemy 2 (async) + asyncpg, Alembic (миграции)
- httpx (клиент Events Provider API)
- APScheduler (фоновая синхронизация)
- uv (зависимости), ruff (линтер), pytest (тесты)

## Архитектура

```
src/events_aggregator/
├── clients/        # HTTP-клиент провайдера + EventsPaginator (cursor-based)
├── repositories/   # Repository-паттерн (Protocol + SQLAlchemy-реализации)
├── services/       # бизнес-логика (usecase-классы, не знают про FastAPI/БД)
├── main.py         # FastAPI-приложение и эндпоинты
├── worker.py       # фоновый воркер синхронизации
├── models.py       # ORM-модели
└── config.py       # конфигурация из переменных окружения
```

Бизнес-логика вынесена в usecase-классы (`services/`), которые зависят только от
`typing.Protocol`-интерфейсов репозиториев и клиента.

## Переменные окружения

Скопируйте шаблон и заполните значения:

```bash
cp .env.example .env
```

| Переменная | Описание | По умолчанию |
|---|---|---|
| `DATABASE_URL` | DSN PostgreSQL (asyncpg) | `postgresql+asyncpg://postgres:password@localhost:5432/events_db` |
| `PROVIDER_BASE_URL` | Базовый URL Events Provider API | `http://localhost:9000`; реальный провайдер — `https://events-provider.dev-2.python-labs.ru` |
| `PROVIDER_API_KEY` | API-ключ (`x-api-key`) из LMS | — |
| `PROVIDER_TIMEOUT` | Таймаут запросов к провайдеру, сек | `10` |
| `USE_PROVIDER_MOCK` | Работать на встроенных моках | `true` |
| `SEATS_CACHE_TTL` | TTL кэша свободных мест, сек | `30` |
| `SYNC_DAILY_AT` | Время ежедневной синхронизации `HH:MM` | `03:00` |
| `SYNC_LOCK_TTL` | TTL «замка» синхронизации, сек (протухший lock сбрасывается при старте) | `3600` |
| `RUN_WORKER_IN_API` | Запускать воркер внутри процесса API | `true` |

## Локальный запуск

```bash
uv sync
cp .env.example .env          # заполнить PROVIDER_API_KEY, DATABASE_URL
uv run alembic upgrade head   # применить миграции
uv run uvicorn events_aggregator.main:app --reload
```

Воркер синхронизации запускается либо внутри API (`RUN_WORKER_IN_API=true`),
либо отдельным процессом:

```bash
uv run python -m events_aggregator.worker
```

## Запуск в Docker

`run.sh` применяет миграции и поднимает API и воркер параллельными процессами
в одном контейнере:

```bash
docker compose up --build
```

- API: http://localhost:8000
- PostgreSQL: `localhost:5432`

## Эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/health` | Проверка доступности |
| POST | `/api/sync/trigger` | Ручной запуск синхронизации |
| GET | `/api/events` | Список событий (фильтр `date_from`, пагинация) |
| GET | `/api/events/{event_id}` | Детали события |
| GET | `/api/events/{event_id}/seats` | Свободные места (кэш 30 сек) |
| POST | `/api/tickets` | Регистрация на событие |
| DELETE | `/api/tickets/{ticket_id}` | Отмена регистрации |

## Разработка

```bash
uv run ruff check .    # линтер (PEP 8)
uv run pytest -q       # тесты
uv run alembic revision --autogenerate -m "message"   # новая миграция
```
