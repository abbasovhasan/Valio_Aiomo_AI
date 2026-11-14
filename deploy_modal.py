"""PREPARED, NOT DEPLOYED. Account-owner prerequisite checks in docs/DEPLOYMENT.md.

No resource is created by importing this module. Do not execute modal deploy
before verifying the current promotional balance, enforced hard budget, expiry,
eligible CPU hosting, CLI access and the restricted Aiven egress path.
"""

import os
import modal

app = modal.App("aimo-order-desk")
# Raw challenge data and CA belong in a PRIVATE mounted volume, never Git or the image.
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir("backend", remote_path="/app/backend")
    .add_local_dir("frontend/dist", remote_path="/app/frontend/dist")
)


# Create this secret only after account/security prerequisites are satisfied.
# Required: VALIO_API_KEY, NVIDIA_API_KEY, DATABASE_URL, PGSSLROOTCERT,
# AIMO_BUYER_CODE, AIMO_APPROVER_CODE, AIMO_SECURE_COOKIES=1.
@app.function(
    image=image,
    secrets=[modal.Secret.from_name("aimo-order-desk-runtime")],
    cpu=0.5,
    memory=1024,
    min_containers=0,
    max_containers=1,
    scaledown_window=60,
    timeout=120,
    # Aiven accepts ONLY explicitly approved static egress, never 0.0.0.0/0.
    # Add proxy=modal.Proxy.from_name(...) only after verifying cost and egress.
)
@modal.concurrent(max_inputs=4)
@modal.asgi_app()
def web():
    os.chdir("/app")
    if not os.path.isfile("/app/data/raw/valio_aimo_junction26_product_data.json"):
        raise RuntimeError("Private catalog volume not mounted; deployment incomplete.")
    if not os.path.isfile(os.environ.get("PGSSLROOTCERT", "")):
        raise RuntimeError(
            "Verified database CA is not mounted; deployment incomplete."
        )
    from backend.app import app as api

    if api.state.store.backend != "postgres":
        raise RuntimeError("Deployment requires verified persistent Aiven connection.")
    return api
