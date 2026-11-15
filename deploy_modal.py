"""Single-writer sponsored demo host. Never sends supplier orders or payments.

Run scripts/deploy_sponsored.py after account credit/cap verification. The private
catalog and state are volumes, not Git or public assets. Stop a previous running
release before redeployment so two revisions never write the same SQLite file.
"""

import os
import sys
import time
import modal

app = modal.App("aimo-order-desk")
catalog_volume = modal.Volume.from_name("aimo-private-catalog-v1", create_if_missing=True, version=2)
state_volume = modal.Volume.from_name("aimo-demo-state-v1", create_if_missing=True, version=2)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("tesseract-ocr", "tesseract-ocr-eng", "tesseract-ocr-fin", "libgomp1")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir(".local/model-bundle/whisper-base", remote_path="/opt/aimo-whisper-base", copy=True)
    .env({"AIMO_WHISPER_MODEL_PATH": "/opt/aimo-whisper-base", "AIMO_DEMO_MODE": "true"})
    .add_local_dir("backend", remote_path="/app/backend", ignore=["**/__pycache__/**", "**/*.pyc"])
    .add_local_dir("frontend/dist", remote_path="/app/frontend/dist")
)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("aimo-order-desk-runtime")],
    volumes={"/app/data": catalog_volume, "/app/.local": state_volume},
    cpu=1,
    memory=1536,
    min_containers=0,
    max_containers=1,
    # A bounded five-minute idle window avoids measured ~6.6s cold reloads
    # during short review/approval handoffs; still scales to zero afterwards.
    scaledown_window=300,
    timeout=180,
)
@modal.concurrent(max_inputs=1)
@modal.asgi_app()
def web():
    os.chdir("/app")
    sys.path.insert(0, "/app")
    if not os.path.isfile("/app/data/raw/valio_aimo_junction26_product_data.json"):
        raise RuntimeError("Authorized private catalog volume is required.")
    if os.environ.get("AIMO_STORAGE") != "sqlite":
        raise RuntimeError("This deployment is explicitly single-writer persistent SQLite.")
    from backend.app import app as api
    if api.state.store.backend != "sqlite":
        raise RuntimeError("Unexpected storage backend.")
    state_volume.commit()

    class DurableResponses:
        async def __call__(self, scope, receive, send):
            async def durable_send(message):
                # Persist all finished SQL transactions before acknowledging a
                # mutation. The single input/container prevents competing files.
                headers = list(message.get("headers", [])) if message["type"] == "http.response.start" else []
                auth_changed = any(name.lower() == b"x-aimo-state-changed" and value == b"1" for name, value in headers)
                if message["type"] == "http.response.start":
                    # Internal auth migration signal is emitted by the app,
                    # never trusted from request headers or exposed publicly.
                    headers = [(name, value) for name, value in headers if name.lower() != b"x-aimo-state-changed"]
                    message = {**message, "headers": headers}
                if message["type"] == "http.response.start" and (scope.get("method") in {"POST", "PUT", "PATCH", "DELETE"} or auth_changed):
                    started = time.perf_counter()
                    await state_volume.commit.aio()
                    elapsed_ms = (time.perf_counter() - started) * 1000
                    timing = [value.decode("ascii") for name, value in headers if name.lower() == b"server-timing"]
                    timing.append(f"persist;dur={elapsed_ms:.3f}")
                    message = {**message, "headers": [(name, value) for name, value in headers if name.lower() != b"server-timing"] + [(b"server-timing", ", ".join(timing).encode("ascii"))]}
                await send(message)
            await api(scope, receive, durable_send)
    return DurableResponses()
