FROM python:3.12-slim


COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/


ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app


COPY pyproject.toml uv.lock ./
 
RUN uv sync --locked --no-install-project --no-dev


COPY . .
RUN uv sync --locked --no-dev


ENV PATH="/app/.venv/bin:$PATH"


RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --ingroup appuser appuser

ENV UV_CACHE_DIR=/tmp/uv-cache
    
USER appuser


EXPOSE 8000


CMD ["bash", "./run.sh"]
