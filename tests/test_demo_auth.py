"""Quick identities use normal revocable sessions and an isolated demo ledger."""

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend import auth, catalog, policy
from backend.app import create_app
from backend.config import BUYER, CUSTOMER, MANDATE, access_codes
from backend.store import Store


@pytest.fixture
def demo_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AIMO_DEMO_MODE", "true")
    monkeypatch.setitem(MANDATE, "autonomous_limit", "1.00")
    products = {"demo-milk": {
        "id": "demo-milk", "salesUnit": "ST", "baseUnit": "ST", "allowedLotSize": 1,
        "units": [{"unitId": "ST", "sizeInBaseUnits": 1}],
        "synkkaData": {"names": [{"language": "en", "value": "Milk 1 L"}], "classifications": [],
            "unitConversions": [{"synkkaPackagingType": "BASE_UNIT_OR_EACH", "volume": {"unit": "LTR", "value": 1}}]},
    }}
    monkeypatch.setattr(catalog, "load_catalog", lambda: products)
    store = Store(tmp_path / "quick-demo.sqlite", postgres=False)
    app = create_app(store)
    return store, app


def enter(client, role="buyer", **options):
    response = client.post("/api/v1/auth/demo", json={"role": role, **options})
    assert response.status_code == 200, response.text
    return response


def cart(client):
    day = (date.today() + timedelta(days=2)).isoformat()
    response = client.post("/api/v1/procurement/sessions", json={"message": f"20 litres of milk by {day}, choose cheapest", "mode": "fixture", "use_model": False})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["approval"]["status"] == "required"
    return result


@pytest.mark.parametrize("flag", [None, "", "false", "1", "yes"])
def test_demo_requires_explicit_server_flag(demo_env, monkeypatch, flag):
    _, app = demo_env
    if flag is None:
        monkeypatch.delenv("AIMO_DEMO_MODE", raising=False)
    else:
        monkeypatch.setenv("AIMO_DEMO_MODE", flag)
    client = TestClient(app)
    assert client.get("/api/v1/auth/demo").json() == {"enabled": False}
    response = client.post("/api/v1/auth/demo", json={"role": "approver"})
    assert response.status_code == 404 and "set-cookie" not in response.headers
    # The protected existing code login remains available when quick demo is off.
    ordinary = client.post("/api/v1/session", json={"access_code": access_codes()["buyer"]})
    assert ordinary.status_code == 200 and ordinary.json()["buyer_id"] == BUYER


def test_demo_identity_is_server_bound_and_role_switch_revokes_old_token(demo_env):
    store, app = demo_env
    client = TestClient(app, base_url="https://testserver")
    assert client.get("/api/v1/auth/demo").json() == {"enabled": True}
    first = enter(client).json()
    token = client.cookies.get("aimo_session")
    assert first["buyer_id"] == auth.QUICK_DEMO_BUYER != BUYER
    assert first["customer_id"] == auth.QUICK_DEMO_CUSTOMER != CUSTOMER
    assert first["commercial_customer_id"] == CUSTOMER and first["quick_demo"]
    assert first["auth_method"] == "demo" and first["demo_workspace"] is False
    assert "password" not in first and "access_code" not in first
    assert client.get("/api/v1/workspace").json()["trust_scenarios_available"] is False
    response = enter(client, "approver", remember_me=True)
    assert response.json()["role"] == "approver"
    assert response.json()["buyer_id"] == first["buyer_id"]
    assert "Max-Age=2592000" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"] and "Secure" in response.headers["set-cookie"]
    stale = TestClient(app, base_url="https://testserver")
    stale.cookies.set("aimo_session", token)
    assert stale.get("/api/v1/session").json() == {"role": None}
    assert stale.get("/api/v1/approvals").status_code == 401
    assert store.spent() == store.spent(auth.QUICK_DEMO_BUYER) == 0
    forged = client.post("/api/v1/auth/demo", json={"role": "approver", "workspace_id": BUYER})
    assert forged.status_code == 422 and "set-cookie" not in forged.headers


def test_demo_remember_restart_expiry_logout_and_disable(demo_env, monkeypatch):
    store, app = demo_env
    client = TestClient(app, base_url="https://testserver")
    session_cookie = enter(client)
    assert "Max-Age" not in session_cookie.headers["set-cookie"]
    digest = hashlib.sha256(client.cookies.get("aimo_session").encode()).hexdigest()
    session = store.get("session", digest, BUYER)
    assert 8 * 3600 - 10 < session["expires"] - time.time() <= 8 * 3600
    remembered = enter(client, remember_me=True)
    token = client.cookies.get("aimo_session")
    digest = hashlib.sha256(token.encode()).hexdigest()
    session = store.get("session", digest, BUYER)
    assert 30 * 86400 - 10 < session["expires"] - time.time() <= 30 * 86400
    assert token not in json.dumps(session)
    restarted = TestClient(create_app(store), base_url="https://testserver")
    restarted.cookies.set("aimo_session", token, domain="testserver.local")
    assert restarted.get("/api/v1/session").json() == remembered.json()
    session["expires"] = time.time() - 1
    store.save("session", digest, BUYER, session)
    assert restarted.get("/api/v1/workspace").status_code == 401
    enter(restarted)
    revoked = restarted.cookies.get("aimo_session")
    assert restarted.delete("/api/v1/session").json()["signed_out"]
    old = TestClient(app, base_url="https://testserver")
    old.cookies.set("aimo_session", revoked)
    assert old.get("/api/v1/workspace").status_code == 401
    enter(client)
    monkeypatch.setenv("AIMO_DEMO_MODE", "false")
    assert client.get("/api/v1/session").json() == {"role": None}
    assert client.get("/api/v1/workspace").status_code == 401


def test_demo_login_csrf_and_rate_limit_survive_restart(demo_env):
    store, app = demo_env
    client = TestClient(app)
    assert client.post("/api/v1/auth/demo", json={"role": "buyer"}, headers={"Origin": "https://unrelated.example"}).status_code == 403
    for _ in range(30):
        enter(client)
    assert client.post("/api/v1/auth/demo", json={"role": "buyer"}).status_code == 429
    assert TestClient(create_app(store)).post("/api/v1/auth/demo", json={"role": "buyer"}).status_code == 429


def test_pending_queue_and_legacy_trust_are_tenant_and_role_scoped(demo_env):
    store, app = demo_env
    shared = TestClient(app)
    shared.post("/api/v1/session", json={"access_code": access_codes()["buyer"]})
    shared_cart = cart(shared)
    # Existing Trust records remain unreachable even with a known identifier.
    store.save("run", "aurora-known-run", BUYER, {"id": "aurora-known-run", "offers": []})
    store.save("offer", "aurora-known-offer", BUYER, {"customer_id": CUSTOMER})
    private = TestClient(app)
    account = private.post("/api/v1/auth/register", json={"name": "Private test", "username": "private.demo.test", "password": "authored-test-password-123", "invite_code": access_codes()["buyer"]}).json()
    private_cart = cart(private)
    buyer = TestClient(app)
    enter(buyer)
    demo_cart = cart(buyer)
    assert buyer.get("/api/v1/approvals").status_code == 403
    assert buyer.post("/api/v1/runs", json={}).status_code == 403
    manager = TestClient(create_app(store))
    enter(manager, "approver")
    queue = manager.get("/api/v1/approvals").json()
    assert queue["total"] == 1 and queue["items"][0]["id"] == demo_cart["id"]
    assert queue["items"][0]["status"] == "pending" and queue["items"][0]["can_approve"]
    assert manager.get("/api/v1/approvals?limit=1&offset=1").json()["items"] == []
    assert manager.get("/api/v1/approvals?limit=101").status_code == 422
    for existing in [shared_cart, private_cart]:
        path = "/api/v1/procurement/sessions/" + existing["id"]
        assert manager.get(path).status_code == 404
        assert manager.post(path + "/approve", json={"fingerprint": existing["offer"]["fingerprint"]}).status_code == 404
        assert manager.post(path + "/reject", json={"fingerprint": existing["offer"]["fingerprint"]}).status_code == 404
    assert manager.get("/api/v1/runs/aurora-known-run").status_code == 404
    assert manager.get("/api/v1/offers/aurora-known-offer").status_code == 404
    assert manager.post("/api/v1/offers/aurora-known-offer/approve", json={"fingerprint": "a" * 64}).status_code == 404
    assert manager.post("/api/v1/runs", json={}).status_code == 403
    assert manager.post("/api/v1/procurement/sessions", json={"message": "20 litres milk"}).status_code == 403
    assert manager.put("/api/v1/preferences", json={}).status_code == 403
    # Original managers keep their explicit customer scope; quick entry does not
    # grant them private-account or Aurora authority.
    ordinary_manager = TestClient(app)
    ordinary_manager.post("/api/v1/session", json={"access_code": access_codes()["approver"], "workspace_id": account["workspace_id"]})
    assert [r["id"] for r in ordinary_manager.get("/api/v1/approvals").json()["items"]] == [private_cart["id"]]
    assert ordinary_manager.get("/api/v1/procurement/sessions/" + demo_cart["id"]).status_code == 404
    assert store.spent() == store.spent(account["buyer_id"]) == store.spent(auth.QUICK_DEMO_BUYER) == 0


def test_exact_rejection_persists_and_buyer_can_revise_then_obtain_approval(demo_env):
    store, app = demo_env
    buyer, manager = TestClient(app), TestClient(app)
    enter(buyer)
    enter(manager, "approver")
    draft = cart(buyer)
    path = "/api/v1/procurement/sessions/" + draft["id"]
    exact = {"fingerprint": draft["offer"]["fingerprint"]}
    assert buyer.post(path + "/reject", json=exact).status_code == 403
    assert manager.post(path + "/reject", json={"fingerprint": "a" * 64}).status_code == 409
    assert manager.post(path + "/reject", json=exact, headers={"Origin": "https://unrelated.example"}).status_code == 403
    response = manager.post(path + "/reject", json={**exact, "reason": "  Revise the quantities.  "})
    assert response.status_code == 200, response.text
    rejected = response.json()
    assert rejected["approval"]["status"] == "rejected" and not rejected["can_confirm"]
    assert rejected["rejection"]["reason"] == "Revise the quantities."
    assert rejected["rejection"]["fingerprint"] == exact["fingerprint"]
    assert manager.get("/api/v1/approvals").json()["total"] == 0
    retry = manager.post(path + "/reject", json={**exact, "reason": "A retry cannot replace the recorded reason."})
    assert retry.json()["version"] == rejected["version"] and retry.json()["rejection"] == rejected["rejection"]
    assert manager.post(path + "/approve", json=exact).status_code == 409
    assert buyer.post(path + "/confirm", json=exact, headers={"Idempotency-Key": "rejected-demo-cart"}).status_code == 409
    assert buyer.get(path).json()["rejection"] == rejected["rejection"]
    with store.tx() as connection:
        decisions = connection.execute("SELECT body FROM aimo_audit WHERE buyer_id=? AND kind=?", (auth.QUICK_DEMO_BUYER, "basket_rejected")).fetchall()
    assert len(decisions) == 1 and json.loads(decisions[0][0])["fingerprint"] == exact["fingerprint"]
    updated = buyer.post(path + "/actions", json={"version": rejected["version"], "action": "set_quantity", "line_id": rejected["lines"][0]["id"], "quantity": "21"}).json()
    assert updated["rejection"] is None and updated["approval"]["status"] == "required"
    assert updated["offer"]["fingerprint"] != exact["fingerprint"]
    assert manager.post(path + "/approve", json=exact).status_code == 409
    current = {"fingerprint": updated["offer"]["fingerprint"]}
    assert manager.post(path + "/approve", json=current, headers={"Origin": "https://unrelated.example"}).status_code == 403
    approved = manager.post(path + "/approve", json=current)
    assert approved.status_code == 200 and approved.json()["can_confirm"]
    assert manager.post(path + "/reject", json=current).status_code == 409
    assert manager.post(path + "/confirm", json=current, headers={"Idempotency-Key": "manager-forbidden"}).status_code == 403
    receipt = buyer.post(path + "/confirm", json=current, headers={"Idempotency-Key": "isolated-demo-order"})
    assert receipt.status_code == 200, receipt.text
    assert receipt.json()["receipt"]["simulated"]
    spent = store.spent(auth.QUICK_DEMO_BUYER)
    assert spent > 0 and store.spent() == 0
    repeated = buyer.post(path + "/confirm", json=current, headers={"Idempotency-Key": "isolated-demo-order"})
    assert repeated.json()["receipt"]["id"] == receipt.json()["receipt"]["id"]
    assert store.spent(auth.QUICK_DEMO_BUYER) == spent
    assert buyer.get(path + "/verify").json()["integrity_valid"]
    restarted = TestClient(create_app(store))
    enter(restarted)
    assert restarted.get(path).json()["receipt"]["id"] == receipt.json()["receipt"]["id"]
    assert store.spent(auth.QUICK_DEMO_BUYER) == spent  # demo entry never resets it


def test_expired_queue_disables_approval_but_allows_exact_rejection(demo_env, monkeypatch):
    _, app = demo_env
    buyer, manager = TestClient(app), TestClient(app)
    enter(buyer)
    enter(manager, "approver")
    draft = cart(buyer)
    expiry = policy.parse_time(draft["offer"]["expires_at"])
    monkeypatch.setattr(policy, "now", lambda: expiry + timedelta(seconds=1))
    pending = manager.get("/api/v1/approvals").json()["items"][0]
    assert pending["status"] == "expired" and not pending["can_approve"] and pending["can_reject"]
    path = "/api/v1/procurement/sessions/" + draft["id"]
    exact = {"fingerprint": draft["offer"]["fingerprint"]}
    assert manager.post(path + "/approve", json=exact).status_code == 409
    assert manager.post(path + "/reject", json=exact).status_code == 200


def test_concurrent_approval_and_rejection_record_only_one_exact_decision(demo_env):
    store, app = demo_env
    buyer, first, second = TestClient(app), TestClient(app), TestClient(app)
    enter(buyer)
    enter(first, "approver")
    enter(second, "approver")
    draft = cart(buyer)
    path = "/api/v1/procurement/sessions/" + draft["id"]
    exact = {"fingerprint": draft["offer"]["fingerprint"]}
    with ThreadPoolExecutor(max_workers=2) as pool:
        requests = [pool.submit(first.post, path + "/approve", json=exact), pool.submit(second.post, path + "/reject", json=exact)]
        responses = [result.result() for result in requests]
    assert sorted(result.status_code for result in responses) == [200, 409]
    persisted = buyer.get(path).json()
    assert persisted["version"] == draft["version"] + 1
    assert persisted["approval"]["status"] in ["approved", "rejected"]
    assert persisted["can_confirm"] is (persisted["approval"]["status"] == "approved")
    with store.tx() as connection:
        audit = connection.execute("SELECT kind FROM aimo_audit WHERE buyer_id=? AND kind IN (?,?)", (auth.QUICK_DEMO_BUYER, "basket_approved", "basket_rejected")).fetchall()
    assert len(audit) == 1
    assert store.spent(auth.QUICK_DEMO_BUYER) == store.spent() == 0


def test_quick_demo_and_decision_endpoints_publish_typed_contracts(demo_env):
    _, app = demo_env
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    for path, method, model in [
        ("/api/v1/auth/demo", "get", "DemoConfiguration"),
        ("/api/v1/auth/demo", "post", "SessionIdentity"),
        ("/api/v1/approvals", "get", "ApprovalQueue"),
        ("/api/v1/procurement/sessions/{id}/reject", "post", "ProcurementSessionResponse"),
    ]:
        response = paths[path][method]["responses"]["200"]["content"]["application/json"]["schema"]
        assert response["$ref"].endswith("/" + model)
