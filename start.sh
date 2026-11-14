#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! command -v uv >/dev/null 2>&1; then
  echo 'Install uv from https://docs.astral.sh/uv/getting-started/installation/ and rerun ./start.sh.' >&2
  exit 1
fi
if [ ! -x .venv/bin/python ]; then uv venv --python 3.12 .venv; fi
uv pip install --python .venv/bin/python -r requirements.txt
aimo_setup_args=()
if [ -f .local/model-bundle/whisper-base/model.bin ] && [ -f .local/model-bundle/whisper-base/tokenizer.json ] && [ -f .local/model-bundle/whisper-base/config.json ] && [ -f .local/model-bundle/whisper-base/vocabulary.txt ] && [ -f .local/model-bundle/whisper-base/LICENSE ] && [ -f .local/model-bundle/whisper-base/MODEL_PROVENANCE.json ]; then
  aimo_setup_args+=(--skip-model)
fi
if ! command -v tesseract >/dev/null 2>&1 && [ ! -x .local/tesseract/usr/bin/tesseract ]; then
  aimo_setup_args+=(--local-ocr)
fi
if [ "${#aimo_setup_args[@]}" -ne 1 ] || [ "${aimo_setup_args[0]}" != --skip-model ]; then
  .venv/bin/python scripts/prepare_multimodal.py "${aimo_setup_args[@]}"
fi
if [ ! -d frontend/node_modules ]; then npm ci --prefix frontend --no-audit --no-fund; fi
npm run build --prefix frontend
printf '%s\n' "A4TB Valio Aimo: http://127.0.0.1:${AIMO_PORT:-8000}" 'Access codes are in ignored .local/access.json (buyer and approver). Do not share them publicly.' 'All commitments are simulated; no orders or payments are sent.'
exec .venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port "${AIMO_PORT:-8000}"
