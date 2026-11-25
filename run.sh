#!/usr/bin/env bash
set -euo pipefail  # -e(выход при первой же ошибке), u - защита от опечаток 

# Воркер синхронизации запускается отдельным процессом (см. ниже),
# поэтому внутри процесса API его стартовать не нужно.
export RUN_WORKER_IN_API=false

# Применяем миграции БД до старта приложения.
uv run --no-sync alembic upgrade head

# API и воркер — параллельные процессы в одном контейнере.
uv run --no-sync uvicorn events_aggregator.main:app --host 0.0.0.0 --port 8000 &
uv run --no-sync python -m events_aggregator.worker &

wait