"""SPA entry documents revalidate across releases; fingerprinted assets retain caching."""

import importlib

import pytest
from fastapi.testclient import TestClient

from backend.store import Store


@pytest.fixture
def shell(tmp_path, monkeypatch):
    module = importlib.import_module("backend.app")
    dist = tmp_path / "frontend" / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text('<!doctype html><script src="/assets/index-old.js"></script>')
    (assets / "index-old.js").write_text('console.log("authored static asset");')
    (assets / "index-old.css").write_text('body { color: green; }')
    monkeypatch.setattr(module, "ROOT", tmp_path)
    # Shell delivery must never need catalog or supplier work.
    monkeypatch.setattr(module.catalog, "load_catalog", lambda: pytest.fail("Static shell requested the catalog"))
    store = Store(tmp_path / "static-shell.sqlite", postgres=False)
    return TestClient(module.create_app(store)), dist


@pytest.mark.parametrize("path", ["/", "/index.html", "/products", "/history/request-example?archived=true"])
def test_root_and_fallback_html_require_revalidation(shell, path):
    client, _ = shell
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-cache, max-age=0, must-revalidate"
    assert "/assets/index-old.js" in response.text
    assert response.headers["etag"] and response.headers["last-modified"]


def test_new_release_shell_replaces_previous_bundle_reference(shell):
    client, dist = shell
    previous = client.get("/")
    (dist / "index.html").write_text('<!doctype html><script src="/assets/index-new-release.js"></script>')
    current = client.get("/products", headers={"If-None-Match": previous.headers["etag"]})
    assert current.status_code == 200
    assert "index-new-release.js" in current.text and "index-old.js" not in current.text
    assert current.headers["etag"] != previous.headers["etag"]
    assert current.headers["cache-control"] == "no-cache, max-age=0, must-revalidate"


@pytest.mark.parametrize("path", ["/assets/index-old.js", "/assets/index-old.css"])
def test_fingerprinted_assets_keep_existing_file_caching(shell, path):
    client, _ = shell
    response = client.get(path)
    assert response.status_code == 200
    assert "cache-control" not in response.headers
    assert response.headers["etag"] and response.headers["last-modified"]
    assert "text/html" not in response.headers["content-type"]


def test_unknown_api_still_returns_api_error_instead_of_spa_shell(shell):
    client, _ = shell
    response = client.get("/api/v1/not-a-real-operation")
    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-type"].startswith("application/json")
