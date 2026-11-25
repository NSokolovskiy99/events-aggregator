FROM python:3.12-slim

# uv — менеджер зависимостей проекта
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 1. Быстрый лог или print() в реальном времени, без буфера от Python
# 2. Не создавать .pyc при импорте
# 3. Компиляция 1 раз на этапе сборки образа(быстрее старт контейнера)
# 4. Копирует файлы пакетов, а не ссылки(чуть больше места в контейнера)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Слой зависимостей кэшируется отдельно от кода проекта
COPY pyproject.toml uv.lock ./
# 1. pytest, Ruff в прод-образе не нужны. Ставить только зависимости 
RUN uv sync --locked --no-install-project --no-dev

# Код проекта: тут уже копируется полностью код
COPY . .
RUN uv sync --locked --no-dev

# uv sync создаёт виртуальное окружение в /app/.venv c активацией окружения
ENV PATH="/app/.venv/bin:$PATH"

# Не открывает порт наружу. проброска портов в compose(если нужно)
EXPOSE 8000

# run.sh запускает миграции, API и воркер синхронизации
CMD ["bash", "./run.sh"]
