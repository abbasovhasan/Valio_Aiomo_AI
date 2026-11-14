"""Account, session and tenant boundaries using isolated simulated ledgers."""

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend import auth, catalog, policy
from backend.app import create_app
from backend.config import BUYER, CUSTOMER, access_codes, MANDATE
from backend.store import Store

TEST_PASSWORD = "authored-test-password-123"


@pytest.fixture
def env(tmp_path):
    store = Store(tmp_path / "auth.sqlite", postgres=False)
    app = create_app(store)
    return store, app


def register(client, username="chef.one", **options):
    result = client.post("/api/v1/auth/register", json={"name": "Test Chef", "username": username, "password": TEST_PASSWORD, "invite_code": access_codes()["buyer"], **options})
    assert result.status_code == 201, result.text
    return result


def test_registration_hashes_secrets_and_creates_private_workspace(env):
    store, app = env
    client = TestClient(app)
    response = register(client, username="Chef.One")
    session = response.json()
    assert session["username"] == "chef.one" and session["role"] == "buyer"
    assert session["workspace_id"] == session["buyer_id"] != BUYER
    assert session["customer_id"] != CUSTOMER and session["commercial_customer_id"] == CUSTOMER
    assert "not a supplier customer contract" in session["commercial_account_note"]
    user = store.user("chef.one")
    assert user["password_hash"].startswith("scrypt$")
    assert TEST_PASSWORD not in user["password_hash"]
    assert "password_hash" not in response.text and TEST_PASSWORD not in response.text and "invite_code" not in response.text
    assert auth.verify_password(TEST_PASSWORD, user["password_hash"])
    assert not auth.verify_password("wrong", user["password_hash"])
    token = client.cookies.get("aimo_session")
    stored_session = store.get("session", hashlib.sha256(token.encode()).hexdigest(), BUYER)
    assert token not in json.dumps(stored_session)
    assert stored_session["buyer_id"] == user["buyer_id"]
    workspace = client.get("/api/v1/workspace").json()
    assert workspace["mandate"]["buyer_id"] == session["buyer_id"]
    assert workspace["mandate"]["spent"] == "0.00" and not workspace["trust_scenarios_available"]
    assert store.spent(user["buyer_id"]) == 0


def test_session_cookie_vs_remember_cookie_and_restart_persistence(env):
    store, app = env
    client = TestClient(app, base_url="https://testserver")
    first = register(client)
    cookie = first.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Secure" in cookie
    assert "Max-Age" not in cookie and "expires=" not in cookie.lower()
    expiry = datetime.fromisoformat(first.json()["session_expires_at"]).timestamp()
    assert 8 * 3600 - 10 < expiry - time.time() <= 8 * 3600
    old_token = client.cookies.get("aimo_session")
    result = client.post("/api/v1/auth/login", json={"username": "CHEF.ONE", "password": TEST_PASSWORD, "remember_me": True})
    assert result.status_code == 200
    assert "Max-Age=2592000" in result.headers["set-cookie"]
    assert result.json()["remember_me"]
    persistent_token = client.cookies.get("aimo_session")
    restarted = TestClient(create_app(store), base_url="https://testserver")
    restarted.cookies.set("aimo_session", persistent_token)
    assert restarted.get("/api/v1/session").json()["username"] == "chef.one"
    old = TestClient(create_app(store))
    old.cookies.set("aimo_session", old_token)
    assert old.get("/api/v1/session").json()["role"] is None
    assert restarted.delete("/api/v1/session").status_code == 200
    revoked = TestClient(create_app(store))
    revoked.cookies.set("aimo_session", persistent_token)
    assert revoked.get("/api/v1/session").json()["role"] is None


def test_expired_session_and_bearer_logout_are_enforced(env):
    store, app = env
    client = TestClient(app)
    register(client)
    token = client.cookies.get("aimo_session")
    bearer = TestClient(app)
    assert bearer.delete("/api/v1/session", headers={"Authorization": "Bearer " + token}).status_code == 200
    assert client.get("/api/v1/session").json()["role"] is None
    result = client.post("/api/v1/auth/login", json={"username": "chef.one", "password": TEST_PASSWORD})
    assert result.status_code == 200
    token = client.cookies.get("aimo_session")
    digest = hashlib.sha256(token.encode()).hexdigest()
    record = store.get("session", digest, BUYER)
    record["expires"] = time.time() - 1
    store.save("session", digest, BUYER, record)
    assert client.get("/api/v1/workspace").status_code == 401


def test_bad_credentials_invites_validation_and_origin_do_not_leak_secrets(env):
    _, app = env
    client = TestClient(app)
    bad = client.post("/api/v1/auth/register", json={"name": "Chef", "username": "chef.one", "password": TEST_PASSWORD, "invite_code": "invalid"})
    assert bad.status_code == 401
    short = client.post("/api/v1/auth/register", json={"name": "Chef", "username": "chef.one", "password": "shortkey", "invite_code": access_codes()["buyer"]})
    assert short.status_code == 422 and "shortkey" not in short.text and access_codes()["buyer"] not in short.text
    register(client)
    duplicate = client.post("/api/v1/auth/register", json={"name": "Other Chef", "username": "CHEF.ONE", "password": TEST_PASSWORD, "invite_code": access_codes()["buyer"]})
    assert duplicate.status_code == 409
    wrong = client.post("/api/v1/auth/login", json={"username": "chef.one", "password": "wrong"})
    missing = client.post("/api/v1/auth/login", json={"username": "not-a-user", "password": "wrong"})
    assert wrong.status_code == missing.status_code == 401 and wrong.json() == missing.json()
    forged = client.post("/api/v1/auth/register", json={"name": "Forged", "username": "forged", "password": TEST_PASSWORD, "invite_code": access_codes()["buyer"], "role": "approver", "buyer_id": BUYER})
    assert forged.status_code == 422
    for path, body in [("/api/v1/session", {"access_code": access_codes()["buyer"]}), ("/api/v1/auth/login", {"username": "chef.one", "password": TEST_PASSWORD})]:
        assert client.post(path, json=body, headers={"Origin": "https://unrelated.example"}).status_code == 403
    assert client.post("/api/v1/session", json={"access_code": "not-ascii-😀"}).status_code == 401
    malformed = client.post("/api/v1/auth/login", content=json.dumps({"username": "chef.one", "password": "\ud800hidden-secret"}), headers={"Content-Type": "application/json"})
    assert malformed.status_code == 422 and "hidden-secret" not in malformed.text


def test_password_login_rate_limit_survives_restart(env):
    store, app = env
    client = TestClient(app)
    for _ in range(10):
        assert client.post("/api/v1/auth/login", json={"username": "target", "password": "incorrect"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": "target", "password": "incorrect"}).status_code == 429
    restarted = TestClient(create_app(store))
    assert restarted.post("/api/v1/auth/login", json={"username": "target", "password": "incorrect"}).status_code == 429


def test_tenants_cannot_read_or_edit_carts_preferences_or_receipts(env, monkeypatch):
    store, app = env
    first, second = TestClient(app), TestClient(app)
    a, b = register(first, "tenant.a").json(), register(second, "tenant.b").json()
    assert a["buyer_id"] != b["buyer_id"] and a["customer_id"] != b["customer_id"]
    store.save("procurement", "private-cart", a["buyer_id"], {"customer_id": a["customer_id"]})
    store.save("meal_plan", "private-plan", a["buyer_id"], {"customer_id": a["customer_id"]})
    assert second.get("/api/v1/procurement/sessions/private-cart").status_code == 404
    assert second.post("/api/v1/procurement/sessions/private-cart/actions", json={"version": 1, "action": "quote"}).status_code == 404
    assert second.get("/api/v1/meal-plans/private-plan").status_code == 404
    assert second.get("/api/v1/receipts/does-not-belong").status_code == 404
    assert first.put("/api/v1/preferences", json={"preferred_brand": "Valio"}).status_code == 200
    assert second.get("/api/v1/preferences").json()["preferred_brand"] is None
    assert first.post("/api/v1/runs", json={}).status_code == 403
    assert store.spent(a["buyer_id"]) == store.spent(b["buyer_id"]) == store.spent() == 0


def test_manager_code_targets_only_explicit_workspace_and_buyer_cannot_self_approve(env, monkeypatch):
    store, app = env
    owner = TestClient(app)
    account = register(owner).json()
    outsider = TestClient(app)
    assert outsider.post("/api/v1/session", json={"access_code": access_codes()["buyer"], "workspace_id": account["workspace_id"]}).status_code == 403
    manager = TestClient(app)
    manager_session = manager.post("/api/v1/session", json={"access_code": access_codes()["approver"], "workspace_id": account["workspace_id"]})
    assert manager_session.status_code == 200
    assert manager_session.json()["role"] == "approver" and manager_session.json()["buyer_id"] == account["buyer_id"]
    assert manager_session.json()["customer_id"] == account["customer_id"]
    assert manager.post("/api/v1/meal-plans", json={}).status_code == 403
    unknown = manager.post("/api/v1/session", json={"access_code": access_codes()["approver"], "workspace_id": "unknown"})
    assert unknown.status_code == 404
    default_manager = TestClient(app)
    assert default_manager.post("/api/v1/session", json={"access_code": access_codes()["approver"]}).json()["buyer_id"] == BUYER
    assert default_manager.get("/api/v1/meal-plans/private-plan").status_code == 404


def test_registered_workspace_exact_approval_and_receipt_stay_tenant_scoped(env, monkeypatch):
    store, app = env
    monkeypatch.setitem(MANDATE, "autonomous_limit", "1.00")
    raw = {"tenant-milk": {"id": "tenant-milk", "salesUnit": "ST", "baseUnit": "ST", "allowedLotSize": 1, "units": [{"unitId": "ST", "sizeInBaseUnits": 1}], "synkkaData": {"names": [{"language": "en", "value": "Milk 1 L"}], "classifications": [{"name": "nutritionalClaim", "values": [{"id": "FREE_FROM_LACTOSE"}]}], "unitConversions": [{"synkkaPackagingType": "BASE_UNIT_OR_EACH", "volume": {"unit": "LTR", "value": 1}}]}}}
    monkeypatch.setattr(catalog, "load_catalog", lambda: raw)
    owner = TestClient(app)
    account = register(owner).json()
    result = owner.post("/api/v1/procurement/sessions", json={"message": "20 litres of lactose-free milk by Monday", "mode": "fixture", "use_model": False})
    assert result.status_code == 200, result.text
    cart = result.json()
    assert cart["approval"]["status"] == "required" and not cart["can_confirm"]
    path = "/api/v1/procurement/sessions/" + cart["id"]
    exact = {"fingerprint": cart["offer"]["fingerprint"]}
    assert owner.post(path + "/approve", json=exact).status_code == 403
    wrong_manager = TestClient(app)
    wrong_manager.post("/api/v1/session", json={"access_code": access_codes()["approver"]})
    assert wrong_manager.post(path + "/approve", json=exact).status_code == 404
    manager = TestClient(app)
    manager.post("/api/v1/session", json={"access_code": access_codes()["approver"], "workspace_id": account["workspace_id"]})
    approved = manager.post(path + "/approve", json=exact)
    assert approved.status_code == 200, approved.text
    receipt = owner.post(path + "/confirm", json=exact, headers={"Idempotency-Key": "private-auth-order-1"})
    assert receipt.status_code == 200, receipt.text
    receipt = receipt.json()["receipt"]
    assert receipt["buyer_id"] == account["buyer_id"] and receipt["customer_id"] == account["customer_id"]
    assert store.spent(account["buyer_id"]) > 0 and store.spent() == 0
    assert wrong_manager.get(path + "/verify").status_code == 404
    assert manager.get(path + "/verify").json()["scope_valid"]


def test_duplicate_account_creation_is_atomic_and_password_salts_are_distinct(env):
    store, app = env
    def signup(_):
        return TestClient(app).post("/api/v1/auth/register", json={"name": "Chef", "username": "same-chef", "password": TEST_PASSWORD, "invite_code": access_codes()["buyer"]}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(signup, range(2))) == [201, 409]
    register(TestClient(app), "other-chef")
    assert store.user("same-chef")["password_hash"] != store.user("other-chef")["password_hash"]
