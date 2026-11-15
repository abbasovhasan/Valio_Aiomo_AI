"""Response diagnostics report bounded handler timing without request contents."""

import re

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.store import Store


def test_server_timing_for_health_and_protected_error(tmp_path):
    client = TestClient(create_app(Store(tmp_path / "timing.sqlite", postgres=False)))
    for path, status in [("/health", 200), ("/api/v1/workspace", 401)]:
        response = client.get(path)
        assert response.status_code == status
        timing = response.headers["server-timing"]
        assert re.fullmatch(r"app;dur=\d+\.\d{3}", timing)
        assert float(timing.split("=")[1]) >= 0
        assert response.headers["cache-control"] == "no-store"


def test_diagnostic_does_not_echo_untrusted_request_data(tmp_path):
    client = TestClient(create_app(Store(tmp_path / "timing.sqlite", postgres=False)))
    response = client.post("/api/v1/auth/login", json={"username": "authored-sensitive-marker", "password": "authored-password-marker"})
    assert response.status_code == 401
    assert re.fullmatch(r"app;dur=\d+\.\d{3}", response.headers["server-timing"])
    assert "authored" not in response.headers["server-timing"]
