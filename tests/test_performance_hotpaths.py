"""Reusable connections never cache commercial facts, credentials or decisions."""
import json
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from backend import catalog, http_clients, interpretation, model_providers, upstream


@pytest.fixture(autouse=True)
def isolated_pools():
    http_clients.close_clients()
    yield
    http_clients.close_clients()


def transport(monkeypatch, handler):
    real_client = httpx.Client
    made = []
    def factory(**kwargs):
        client = real_client(transport=httpx.MockTransport(handler), **kwargs)
        made.append(client)
        return client
    monkeypatch.setattr(http_clients.httpx, "Client", factory)
    return made


def tool_response(request):
    body = json.loads(request.content)
    name = body["tools"][0]["function"]["name"]
    return httpx.Response(200, json={"choices": [{"message": {"tool_calls": [{"function": {
        "name": name, "arguments": json.dumps({"items": []})}}]}}]},
        headers={"set-cookie": "provider_session=must-not-cross-requests; Path=/"})


def test_connections_are_reused_without_closing_each_request_scope(monkeypatch):
    made = transport(monkeypatch, lambda request: httpx.Response(200))
    with http_clients.provider_client("nvidia") as first:
        first.get("https://example.invalid")
    assert not first.is_closed
    with http_clients.provider_client("nvidia") as second:
        assert second is first
    assert len(made) == 1
    http_clients.close_clients()
    assert first.is_closed


def test_suppliers_and_models_use_distinct_pools(monkeypatch):
    made = transport(monkeypatch, lambda request: httpx.Response(200))
    with http_clients.provider_client("valio") as supplier, http_clients.provider_client("nvidia") as model:
        assert supplier is not model
    assert len(made) == 2
    with pytest.raises(ValueError):
        with http_clients.provider_client("user-selected-pool"):
            pass


def test_all_leases_share_one_thread_safe_client(monkeypatch):
    made = transport(monkeypatch, lambda request: httpx.Response(200))
    def obtain(_):
        with http_clients.provider_client("nvidia") as client:
            return id(client)
    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(obtain, range(16)))
    assert len(set(ids)) == len(made) == 1


def test_cookies_are_not_retained_or_forwarded_to_other_requests(monkeypatch):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, headers={"set-cookie": "supplier_auth=private; Path=/"})
    transport(monkeypatch, handler)
    with http_clients.provider_client("valio") as client:
        client.get("https://example.invalid", headers={"Cookie": "caller=also-disallowed"})
        assert not client.cookies
        client.get("https://example.invalid")
        assert not client.cookies
    assert all("cookie" not in request.headers for request in requests)


def test_each_supplier_call_fetches_fresh_customer_payload_and_current_key(monkeypatch, tmp_path):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"products": []})
    made = transport(monkeypatch, handler)
    monkeypatch.setattr(upstream, "LOCAL", tmp_path)
    monkeypatch.setenv("VALIO_API_KEY", "test-only-key-a")
    first = upstream.sponsor_lookup("customer-a", "2026-11-18", ["sku-a"])
    monkeypatch.setenv("VALIO_API_KEY", "test-only-key-b")
    second = upstream.sponsor_lookup("customer-b", "2026-11-19", ["sku-b"])
    assert len(made) == 1 and len(requests) == 4
    assert first["customer_id"] == "customer-a" and second["customer_id"] == "customer-b"
    assert [json.loads(request.content)["customer"] for request in requests] == ["customer-a"] * 2 + ["customer-b"] * 2
    assert [request.headers["x-api-key"] for request in requests] == ["test-only-key-a"] * 2 + ["test-only-key-b"] * 2
    assert all(request.extensions["timeout"]["read"] == 15 and request.extensions["timeout"]["connect"] == 5 for request in requests)
    assert "x-api-key" not in made[0].headers


def test_nvidia_text_and_vision_share_connections_but_keep_auth_and_timeouts_scoped(monkeypatch):
    requests = []
    def handler(request):
        requests.append(request)
        return tool_response(request)
    made = transport(monkeypatch, handler)
    monkeypatch.setenv("NVIDIA_API_KEY", "test-only-token-a")
    assert interpretation._model("20 litres of milk", None) == {"items": []}
    monkeypatch.setenv("NVIDIA_API_KEY", "test-only-token-b")
    result = model_providers.nvidia_tool("Extract only", "synthetic content", {"type": "object"}, "extract")
    assert result.data == {"items": []}
    assert len(made) == 1 and len(requests) == 2
    assert [request.extensions["timeout"]["read"] for request in requests] == [55, 45]
    assert [request.headers["authorization"] for request in requests] == ["Bearer test-only-token-a", "Bearer test-only-token-b"]
    assert "authorization" not in made[0].headers and not made[0].cookies
    assert all("cookie" not in request.headers for request in requests)


def test_legacy_nvidia_shortlist_retains_its_own_timeout(monkeypatch):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"tool_calls": [{"function": {
            "name": "propose_candidates", "arguments": json.dumps({"product_ids": ["sku-a"], "summary": "Compare supplied data."})}}]}}]})
    transport(monkeypatch, handler)
    monkeypatch.setenv("NVIDIA_API_KEY", "test-only-token")
    result = upstream.rank_with_nvidia([{"id": "sku-a", "name": "Synthetic item"}], {})
    assert result["status"] == "live_tool_call"
    assert requests[0].extensions["timeout"]["read"] == 50


def test_supplier_redirects_do_not_forward_authentication(monkeypatch, tmp_path):
    seen = []
    def handler(request):
        seen.append(request.url.host)
        return httpx.Response(302, headers={"location": "https://unrelated.invalid/collect"})
    transport(monkeypatch, handler)
    monkeypatch.setattr(upstream, "LOCAL", tmp_path)
    monkeypatch.setenv("VALIO_API_KEY", "test-only-key")
    with pytest.raises(upstream.UpstreamError, match="HTTP 302"):
        upstream.sponsor_lookup("customer", "2026-11-18", ["sku"])
    assert len(seen) == 1 and "unrelated.invalid" not in seen


def test_supplier_retry_remains_bounded_and_never_uses_cached_or_fixture_data(monkeypatch, tmp_path):
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(503)
    transport(monkeypatch, handler)
    monkeypatch.setattr(upstream, "LOCAL", tmp_path)
    monkeypatch.setenv("VALIO_API_KEY", "test-only-key")
    monkeypatch.setattr(upstream.time, "sleep", lambda _: None)
    with pytest.raises(upstream.UpstreamError, match="HTTP 503"):
        upstream.sponsor_lookup("customer", "2026-11-18", ["sku"])
    assert len(seen) == 2 and not list(tmp_path.iterdir())


def test_missing_credentials_fail_before_a_connection_is_created(monkeypatch):
    made = transport(monkeypatch, lambda request: pytest.fail("Network must not be reached"))
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("VALIO_API_KEY", raising=False)
    with pytest.raises(upstream.UpstreamError):
        interpretation._model("milk", None)
    with pytest.raises(upstream.UpstreamError):
        model_providers.nvidia_tool("system", "text", {}, "extract")
    with pytest.raises(upstream.UpstreamError):
        upstream.sponsor_lookup("customer", "2026-11-18", ["sku"])
    assert not made


def test_brand_index_reuses_only_static_names_and_rebuilds_when_source_reloads(monkeypatch):
    class Rows(dict):
        reads = 0
        def values(self):
            self.reads += 1
            return super().values()
    rows = Rows({"a": {"synkkaData": {"brand": "Valio"}}, "b": {"synkkaData": {"brand": "Arla"}}})
    monkeypatch.setattr(catalog, "load_catalog", lambda: rows)
    assert interpretation._brands("Valio and Arla") == ["Valio", "Arla"]
    assert interpretation._brands("Valio butter") == ["Valio"]
    assert interpretation._brands("NotValioElsewhere") == []
    assert rows.reads == 1
    replacement = Rows({"c": {"synkkaData": {"brand": "Different Brand"}}})
    monkeypatch.setattr(catalog, "load_catalog", lambda: replacement)
    assert interpretation._brands("Different Brand") == ["Different Brand"]
    assert interpretation._brands("Valio") == [] and replacement.reads == 1
