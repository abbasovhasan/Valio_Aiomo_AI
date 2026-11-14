#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! command -v uv >/dev/null 2>&1; then
  echo 'Install uv from https://docs.astral.sh/uv/getting-started/installation/ and rerun ./start.sh.' >&2
  exit 1
fi
if [ ! -x .venv/bin/python ]; then uv venv --python 3.12 .venv; fi
if ! .venv/bin/python -c 'import fastapi, uvicorn, httpx, psycopg, dotenv' >/dev/null 2>&1; then uv pip install --python .venv/bin/python -r requirements.txt; fi
if [ ! -d frontend/node_modules ]; then npm ci --prefix frontend --no-audit --no-fund; fi
npm run build --prefix frontend
printf '%s\n' 'Aimo Order Desk: http://127.0.0.1:8000' 'Access codes are in ignored .local/access.json (buyer and approver). Do not share them publicly.' 'All commitments are simulated; no orders or payments are sent.'
exec .venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port "${AIMO_PORT:-8000}"
