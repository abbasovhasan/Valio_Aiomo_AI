"""Exact financial exceptions use the existing gateway and isolated ledgers."""

import copy
import hashlib
import json
from threading import Barrier
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend import auth, catalog, procurement
from backend.app import create_app
from backend.config import BUYER, MANDATE, access_codes
from backend.store import Store

PASSWORD = "authored-budget-test-password"


@pytest.fixture
def env(tmp_path, monkeypatch):
    row = {"id": "budget-product", "salesUnit": "ST", "baseUnit": "ST", "allowedLotSize": 1,
        "units": [{"unitId": "ST", "sizeInBaseUnits": 1}],
        "synkkaData": {"names": [{"language": "en", "value": "Kitchen milk"}],
            "unitConversions": [{"synkkaPackagingType": "BASE_UNIT_OR_EACH", "netWeight": {"unit": "KGM", "value": 1}}],
            "classifications": [], "countriesOfOrigin": ["246"]}}
    rows = {row["id"]: row}
    monkeypatch.setattr(catalog, "load_catalog", lambda: rows)
    monkeypatch.setattr(catalog, "supplemental", lambda: {})
    prices = {"value": 836}
    original = procurement.fixture_lookup
    def fixture(*args):
        evidence = original(*args)
        for item in evidence["price"]["products"]:
            item["catalogPrice"]["valueWithTax"] = prices["value"]
        return evidence
    monkeypatch.setattr(procurement, "fixture_lookup", fixture)
    store = Store(tmp_path / "budget-exceptions.sqlite", postgres=False)
    app = create_app(store)
    buyer = TestClient(app)
    registered = buyer.post("/api/v1/auth/register", json={"name": "Budget test chef", "username": "budget.chef", "password": PASSWORD, "invite_code": access_codes()["buyer"]})
    assert registered.status_code == 201, registered.text
    identity = registered.json()
    manager = TestClient(app)
    assert manager.post("/api/v1/session", json={"access_code": access_codes()["approver"], "workspace_id": identity["workspace_id"]}).status_code == 200
    return {"buyer": buyer, "manager": manager, "db": store, "app": app, "identity": identity,
        "rows": rows, "prices": prices, "date": str(date.today() + timedelta(days=2))}


def path(session, action=""):
    return procurement.PREFIX + "/" + session["id"] + ("/" + action if action else "")


def create(env, budget="800.00"):
    body = {"product_id": "budget-product", "quantity": "1", "unit": "kg", "mode": "fixture", "date": env["date"]}
    if budget is not None:
        body["budget"] = budget
    response = env["buyer"].post(procurement.PREFIX + "/from-product", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def request(env, session, explanation="Avoid a service shortage"):
    response = env["buyer"].post(path(session, "request-approval"), json={"version": session["version"], "fingerprint": session["offer"]["fingerprint"], "explanation": explanation})
    assert response.status_code == 200, response.text
    return response.json()


def decide(env, session, action="approve", **fields):
    return env["manager"].post(path(session, action), json={"version": session["version"], "fingerprint": session["offer"]["fingerprint"], **fields})


def submit(env, session, key="budget-simulation-key"):
    return env["buyer"].post(path(session, "confirm"), json={"version": session["version"], "fingerprint": session["offer"]["fingerprint"]}, headers={"Idempotency-Key": key})


def test_exact_36_euro_exception_persists_without_raising_original_budget_or_authority(env):
    draft = create(env)
    assert draft["cart"]["subtotal"] == "836.00" and draft["constraints"]["budget"] == "800.00"
    assert draft["approval"]["reasons"] == ["requested_budget"]
    assert draft["workspace_name"] == env["identity"]["workspace_name"]
    assert draft["approval"]["can_request"] and not draft["approval"]["pending"]
    assert not draft["can_confirm"] and env["manager"].get("/api/v1/approvals").json()["total"] == 0
    assert submit(env, draft).status_code == 409
    pending = request(env, draft)
    snapshot = env["db"].get("approval_snapshot", pending["offer"]["id"], env["identity"]["buyer_id"])
    assert snapshot["fingerprint"] == pending["offer"]["fingerprint"] and snapshot["approval_request"]["budget_excess"] == "36.00"
    assert snapshot["requested_requirements"]["budget"] == "800.00"
    assert pending["version"] == draft["version"] + 1
    assert pending["offer"]["fingerprint"] != draft["offer"]["fingerprint"]
    assert pending["budget_exception"]["excess"] == "36.00"
    assert pending["budget_exception"]["original_budget"] == pending["constraints"]["budget"] == "800.00"
    assert pending["budget_exception"]["explanation"] == "Avoid a service shortage"
    assert pending["submitted_at"] and pending["approval"]["pending"]
    queue = env["manager"].get("/api/v1/approvals").json()["items"]
    assert len(queue) == 1 and queue[0]["reasons"] == ["requested_budget"] and queue[0]["budget_excess"] == "36.00"
    assert queue[0]["requested_budget"] == "800.00" and queue[0]["buyer_name"] == "Budget test chef"
    assert queue[0]["can_approve"] and queue[0]["submitted_at"] == pending["submitted_at"]
    replay = request(env, draft)
    assert replay["version"] == pending["version"] and len(replay["decision_history"]) == 1
    approved = decide(env, pending)
    assert approved.status_code == 200, approved.text
    approved = approved.json()
    assert approved["can_confirm"] and approved["review_state"] == "APPROVED"
    assert approved["budget_exception"]["status"] == "approved" and approved["constraints"]["budget"] == "800.00"
    assert env["db"].spent(env["identity"]["buyer_id"]) == 0
    receipt = submit(env, approved)
    assert receipt.status_code == 200, receipt.text
    receipt = receipt.json()["receipt"]
    assert receipt["simulated"] and receipt["total"] == "836.00" and receipt["budget_exception"]["excess"] == "36.00"
    replay = submit(env, approved)
    assert replay.status_code == 200 and replay.json()["receipt"]["id"] == receipt["id"] and replay.json()["receipt"]["idempotent_replay"]
    assert env["db"].spent(env["identity"]["buyer_id"]) == 83600 and env["db"].spent(BUYER) == 0
    next_draft = create(env)
    assert not next_draft["can_confirm"] and next_draft["approval"]["threshold"] == draft["approval"]["threshold"]


@pytest.mark.parametrize("budget,reasons", [("1000.00", ["spending_authority"]), ("800.00", ["requested_budget", "spending_authority"])])
def test_budget_cannot_increase_authority_and_both_exceptions_are_exact(env, monkeypatch, budget, reasons):
    monkeypatch.setitem(MANDATE, "autonomous_limit", "150.00")
    draft = create(env, budget)
    assert draft["approval"]["threshold"] == "150.00" and draft["approval"]["reasons"] == reasons
    pending = request(env, draft, explanation=None)
    assert pending["approval"]["explanation"] is None
    approved = decide(env, pending).json()
    stored = env["db"].get("procurement", draft["id"], env["identity"]["buyer_id"])
    assert stored["offer"]["approval"]["covered_reasons"] == reasons
    assert approved["approval"]["threshold"] == "150.00" and approved["constraints"]["budget"] == budget
    assert env["db"].spent(env["identity"]["buyer_id"]) == 0


def test_same_browser_cannot_approve_reject_or_request_changes_after_role_switch_and_logout(env):
    pending = request(env, create(env))
    buyer = env["buyer"]
    before = buyer.get("/api/v1/session").json()
    buyer.delete("/api/v1/session")
    switched = buyer.post("/api/v1/session", json={"access_code": access_codes()["approver"], "workspace_id": env["identity"]["workspace_id"]}).json()
    assert switched["actor_id"] == before["actor_id"] and switched["principal_id"] != before["principal_id"]
    queue = buyer.get("/api/v1/approvals").json()["items"][0]
    assert not queue["can_approve"] and not queue["can_reject"] and not queue["can_request_changes"] and queue["decision_blockers"]
    for action in ["approve", "reject", "request-changes"]:
        response = buyer.post(path(pending, action), json={"version": pending["version"], "fingerprint": pending["offer"]["fingerprint"], **({"reason": "Change recipe"} if action != "approve" else {})})
        assert response.status_code == 403, response.text
    assert decide(env, pending).status_code == 200


@pytest.mark.parametrize("decision", ["reject", "request-changes"])
def test_closed_decision_requires_fresh_version_and_keeps_history(env, decision):
    pending = request(env, create(env))
    response = decide(env, pending, decision, reason="Reduce the quantities")
    assert response.status_code == 200, response.text
    closed = response.json()
    assert not closed["can_confirm"] and not closed["approval"]["pending"]
    assert closed["review_state"] == ("REJECTED" if decision == "reject" else "CHANGES_REQUESTED")
    assert submit(env, closed).status_code == 409
    assert env["manager"].get("/api/v1/approvals").json()["total"] == 0
    edited = env["buyer"].post(path(closed, "actions"), json={"version": closed["version"], "action": "quote"})
    assert edited.status_code == 200, edited.text
    fresh = edited.json()
    assert fresh["offer"]["fingerprint"] != closed["offer"]["fingerprint"] and fresh["approval"]["can_request"]
    assert len(fresh["decision_history"]) == 2
    assert decide(env, pending).status_code == 409
    assert request(env, fresh)["approval"]["pending"]


def test_cancel_cannot_be_submitted_or_mutated_and_history_can_reuse(env):
    pending = request(env, create(env))
    result = env["buyer"].post(path(pending, "cancel"), json={"version": pending["version"], "reason": "Service cancelled"})
    assert result.status_code == 200, result.text
    cancelled = result.json()
    assert cancelled["review_state"] == "CANCELLED" and not cancelled["can_confirm"]
    assert submit(env, cancelled).status_code == 409
    assert env["buyer"].post(path(cancelled, "actions"), json={"version": cancelled["version"], "action": "quote"}).status_code == 409
    reused = env["buyer"].post("/api/v1/history/" + cancelled["id"] + "/reuse", json={"date": env["date"]})
    assert reused.status_code == 200 and reused.json()["id"] != cancelled["id"] and not reused.json().get("cancelled")
    assert env["db"].spent(env["identity"]["buyer_id"]) == 0


def test_hard_dietary_blocker_cannot_be_sent_for_financial_exception(env):
    draft = create(env)
    assert env["buyer"].put("/api/v1/preferences", json={"dietary_restrictions": ["gluten_free"]}).status_code == 200
    refreshed = env["buyer"].post(path(draft, "actions"), json={"version": draft["version"], "action": "quote"}).json()
    assert not refreshed["approval"]["can_request"] and refreshed["approval"]["blockers"] and refreshed["offer"] is None
    denied = env["buyer"].post(path(refreshed, "request-approval"), json={"version": refreshed["version"], "fingerprint": draft["offer"]["fingerprint"]})
    assert denied.status_code == 409 and env["manager"].get("/api/v1/approvals").json()["total"] == 0
    assert env["db"].spent(env["identity"]["buyer_id"]) == 0


def test_current_price_change_blocks_approval_without_mutating_pending_request(env):
    pending = request(env, create(env))
    env["prices"]["value"] = 837
    response = decide(env, pending)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "revalidation_failed"
    assert env["buyer"].get(path(pending)).json()["version"] == pending["version"]


@pytest.mark.parametrize("key,value", [("autonomous_limit", None), ("autonomous_limit", "NaN"), ("exception_limit", "1.00"), ("expires_at", "invalid")])
def test_missing_or_invalid_trusted_policy_never_grants_authority(env, monkeypatch, key, value):
    draft = create(env, None)
    if value is None:
        monkeypatch.delitem(MANDATE, key)
    else:
        monkeypatch.setitem(MANDATE, key, value)
    response = env["buyer"].get(path(draft))
    assert response.status_code == 200 and not response.json()["can_confirm"]
    assert env["buyer"].post(path(draft, "actions"), json={"version": draft["version"], "action": "quote"}).status_code == 503
    assert submit(env, draft).status_code != 200
    assert env["db"].spent(env["identity"]["buyer_id"]) == 0


@pytest.mark.parametrize("change", ["policy", "dietary"])
def test_final_transaction_rechecks_policy_and_saved_hard_restrictions(env, monkeypatch, change):
    draft = create(env, None)
    original = env["db"].commit
    def commit(*args):
        if change == "policy":
            monkeypatch.setitem(MANDATE, "autonomous_limit", "150.00")
        else:
            env["db"].save("preferences", env["identity"]["buyer_id"], env["identity"]["buyer_id"], {"dietary_restrictions": ["gluten_free"]})
        return original(*args)
    monkeypatch.setattr(env["db"], "commit", commit)
    result = submit(env, draft)
    assert result.status_code == 409, result.text
    assert result.json()["detail"]["code"] == ("policy_changed" if change == "policy" else "preferences_changed")
    assert env["db"].spent(env["identity"]["buyer_id"]) == 0


def test_concurrent_baskets_cannot_split_past_lifetime_committed_allowance(env, monkeypatch):
    monkeypatch.setitem(MANDATE, "autonomous_limit", "1000.00")
    monkeypatch.setitem(MANDATE, "exception_limit", "1000.00")
    monkeypatch.setitem(MANDATE, "cumulative_limit", "1200.00")
    first, second = create(env, None), create(env, None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [future.result() for future in [pool.submit(submit, env, first, "split-allowance-first"), pool.submit(submit, env, second, "split-allowance-second")]]
    assert sorted(result.status_code for result in results) == [200, 409]
    assert env["db"].spent(env["identity"]["buyer_id"]) == 83600 and env["db"].spent(BUYER) == 0


def test_other_workspace_cannot_see_or_decide_private_financial_request(env):
    pending = request(env, create(env))
    outsider = TestClient(env["app"])
    outsider.post("/api/v1/session", json={"access_code": access_codes()["approver"]})
    assert outsider.get("/api/v1/approvals").json()["total"] == 0
    assert outsider.get(path(pending)).status_code == 404
    assert outsider.post(path(pending, "approve"), json={"version": pending["version"], "fingerprint": pending["offer"]["fingerprint"]}).status_code == 404


@pytest.mark.parametrize("change", ["revoked", "permission", "ceiling", "principal"])
def test_assignment_reduction_inside_final_transaction_invalidates_old_approval(env, monkeypatch, change):
    approved = decide(env, request(env, create(env))).json()
    buyer_id = env["identity"]["buyer_id"]
    original = env["db"].commit
    def commit(*args):
        assignment = env["db"].workspace_authority(buyer_id, env["identity"]["customer_id"])
        if change == "revoked":
            assignment["active"] = False
        elif change == "permission":
            assignment["permissions"] = ["spending_authority"]
        elif change == "ceiling":
            assignment["max_total"] = "835.00"
        else:
            assignment["approver_principals"] = ["another-configured-manager"]
        env["db"].save("workspace_authority", "workspace-authority-" + buyer_id, buyer_id, assignment)
        return original(*args)
    monkeypatch.setattr(env["db"], "commit", commit)
    result = submit(env, approved)
    assert result.status_code == 409 and result.json()["detail"]["code"] == "manager_authority_changed"
    assert env["db"].spent(buyer_id) == 0


def test_no_eligible_manager_is_not_a_misleading_financial_approval_route(env):
    buyer_id = env["identity"]["buyer_id"]
    assignment = env["db"].workspace_authority(buyer_id, env["identity"]["customer_id"])
    assignment["permissions"] = []
    env["db"].save("workspace_authority", "workspace-authority-" + buyer_id, buyer_id, assignment)
    draft = create(env)
    assert not draft["approval"]["can_request"]
    assert any("manager" in blocker for blocker in draft["approval"]["blockers"])
    response = env["buyer"].post(path(draft, "request-approval"), json={"version": draft["version"], "fingerprint": draft["offer"]["fingerprint"]})
    assert response.status_code == 409
    assert env["manager"].get("/api/v1/approvals").json()["total"] == 0


def test_revoked_or_missing_assignment_is_not_regranted_by_login_or_restart(env):
    buyer_id = env["identity"]["buyer_id"]
    with env["db"].tx() as connection:
        connection.execute("DELETE FROM aimo_documents WHERE kind=? AND id=? AND buyer_id=?", ("workspace_authority", "workspace-authority-" + buyer_id, buyer_id))
    assert env["manager"].get("/api/v1/approvals").status_code == 403
    restarted = TestClient(create_app(env["db"]))
    login = restarted.post("/api/v1/session", json={"access_code": access_codes()["approver"], "workspace_id": buyer_id})
    assert login.status_code == 403 and not env["db"].workspace_authority(buyer_id, env["identity"]["customer_id"])
    assert env["buyer"].get("/api/v1/session").json()["role"] == "buyer"


def test_authenticated_legacy_migration_is_flagged_and_preserves_credential_and_spend(env):
    buyer_id = env["identity"]["buyer_id"]
    before = env["db"].user("budget.chef")
    with env["db"].tx() as connection:
        for kind, identifier, owner in [("auth_migration", "workspace-authority-migration-v1", BUYER), ("workspace_registration", "workspace-registration-" + buyer_id, buyer_id), ("workspace_authority", "workspace-authority-" + buyer_id, buyer_id)]:
            connection.execute("DELETE FROM aimo_documents WHERE kind=? AND id=? AND buyer_id=?", (kind, identifier, owner))
    response = env["buyer"].get("/api/v1/session")
    assert response.status_code == 200 and response.headers["x-aimo-state-changed"] == "1"
    assert env["db"].workspace_authority(buyer_id, env["identity"]["customer_id"])["active"]
    assert env["db"].user("budget.chef") == before and env["db"].spent(buyer_id) == 0
    assert "x-aimo-state-changed" not in env["buyer"].get("/api/v1/session", headers={"X-Aimo-State-Changed": "1"}).headers


def test_old_remembered_session_get_binds_lineage_and_marks_server_write(env):
    token = env["buyer"].cookies.get("aimo_session")
    digest = hashlib.sha256(token.encode()).hexdigest()
    record = env["db"].get("session", digest, BUYER)
    expiry = record["expires"]
    record.pop("actor_id")
    record.pop("principal_id")
    env["db"].save("session", digest, BUYER, record)
    env["buyer"].cookies.delete("aimo_actor")
    response = env["buyer"].get("/api/v1/session")
    assert response.status_code == 200 and response.headers["x-aimo-state-changed"] == "1"
    restored = env["db"].get("session", digest, BUYER)
    assert restored["actor_id"] == response.json()["actor_id"] and restored["principal_id"] == "account:budget.chef"
    assert restored["expires"] == expiry
    actor_cookie = next(value for value in response.headers.get_list("set-cookie") if value.startswith("aimo_actor="))
    assert "HttpOnly" in actor_cookie and "SameSite=strict" in actor_cookie


def test_policy_can_forbid_budget_exception_without_changing_buyer_budget(env, monkeypatch):
    monkeypatch.setitem(MANDATE, "allow_budget_exceptions", False)
    draft = create(env)
    assert draft["constraints"]["budget"] == "800.00" and not draft["approval"]["can_request"] and not draft["offer"]
    assert any("prohibited" in blocker for blocker in draft["approval"]["blockers"])


def test_issued_manager_session_ignores_workspace_query_and_rejects_scope_payload(env):
    own = request(env, create(env))
    other = TestClient(env["app"])
    account = other.post("/api/v1/auth/register", json={"name": "Another chef", "username": "other.chef", "password": PASSWORD, "invite_code": access_codes()["buyer"]}).json()
    foreign = other.post(procurement.PREFIX + "/from-product", json={"product_id": "budget-product", "quantity": "1", "unit": "kg", "budget": "800.00", "mode": "fixture", "date": env["date"]}).json()
    queue = env["manager"].get("/api/v1/approvals?workspace_id=" + account["buyer_id"]).json()
    assert [row["id"] for row in queue["items"]] == [own["id"]]
    assert env["manager"].get(path(foreign)).status_code == 404
    forged = env["manager"].post(path(own, "approve"), json={"version": own["version"], "fingerprint": own["offer"]["fingerprint"], "workspace_id": account["buyer_id"], "authority_limit": "1000000"})
    assert forged.status_code == 422


@pytest.mark.parametrize("evidence,expected", [("missing", "evidence_missing"), ("conflict", "verified_incompatible"), ("compatible", "verified_compatible")])
def test_meal_planner_dietary_status_and_conflicting_selection_cannot_bypass_bridge(env, evidence, expected):
    source = env["rows"]["budget-product"]["synkkaData"]
    source["classifications"] = [] if evidence == "missing" else [{"name": "nutritionalClaim", "values": [{"id": "FREE_FROM_GLUTEN"}]}]
    if evidence == "conflict":
        source["classifications"].append({"name": "allergen", "values": [{"id": "AW", "unit": "CONTAINS"}]})
    plan = env["buyer"].post("/api/v1/meal-plans", json={"meal_name": "Kitchen soup", "template": "custom", "recipe_source": "customer", "servings": 10, "vegetarian": 0, "gluten_free": 0, "vegetarian_gluten_free": 0,
        "dietary_restrictions": ["gluten_free"], "ingredients": [{"id": "milk", "label": "Milk", "query": "milk", "grams_per_serving": "100"}]})
    assert plan.status_code == 200, plan.text
    plan = plan.json()
    candidate = plan["lines"][0]["candidates"][0]
    assert candidate["dietary_status"] == expected
    assert candidate["selectable"] is (evidence == "compatible")
    result = env["buyer"].post(procurement.PREFIX + "/from-meal-plan", json={"plan_id": plan["id"], "selections": {"0": "budget-product"}, "date": env["date"]})
    if evidence != "compatible":
        assert result.status_code == 422 and result.json()["detail"]["code"] == "meal_selection_ineligible"
    else:
        assert result.status_code == 200 and result.json()["lines"][0]["selected_product_id"] == "budget-product"
        assert result.json()["recipe_review_required"] and not result.json()["can_confirm"]
        assert result.json()["request_title"] == "Kitchen soup" and "10 servings" in result.json()["original_request"]
    assert env["db"].spent(env["identity"]["buyer_id"]) == 0


def test_concurrent_manager_decision_and_buyer_cancel_cannot_both_win(env):
    pending = request(env, create(env))
    with ThreadPoolExecutor(max_workers=2) as pool:
        approve = pool.submit(decide, env, pending)
        cancel = pool.submit(env["buyer"].post, path(pending, "cancel"), json={"version": pending["version"]})
        results = [approve.result(), cancel.result()]
    assert sorted(result.status_code for result in results) == [200, 409]
    current = env["buyer"].get(path(pending)).json()
    assert current["version"] == pending["version"] + 1
    assert current["review_state"] in ["APPROVED", "CANCELLED"]
    assert env["db"].spent(env["identity"]["buyer_id"]) == 0


def test_all_required_exception_reasons_must_be_covered_at_final_commit(env, monkeypatch):
    monkeypatch.setitem(MANDATE, "autonomous_limit", "150.00")
    approved = decide(env, request(env, create(env))).json()
    record = env["db"].get("procurement", approved["id"], env["identity"]["buyer_id"])
    record["offer"]["approval"]["covered_reasons"] = ["spending_authority"]
    env["db"].save("procurement", record["id"], record["buyer_id"], record)
    result = submit(env, approved)
    assert result.status_code == 409 and result.json()["detail"]["code"] == "approval_required"
    assert env["db"].spent(env["identity"]["buyer_id"]) == 0


def test_malformed_explanation_is_rejected_without_saving_request(env):
    draft = create(env)
    response = env["buyer"].post(path(draft, "request-approval"), content=json.dumps({"version": draft["version"], "fingerprint": draft["offer"]["fingerprint"], "explanation": "\ud800"}), headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert env["buyer"].get(path(draft)).json()["version"] == draft["version"]


def test_legacy_session_migration_does_not_revive_concurrently_revoked_token(env, monkeypatch):
    token = env["buyer"].cookies.get("aimo_session")
    digest = hashlib.sha256(token.encode()).hexdigest()
    record = env["db"].get("session", digest, BUYER)
    record.pop("actor_id"); record.pop("principal_id")
    env["db"].save("session", digest, BUYER, record)
    original = auth.Auth.bind_actor
    def revoke_during_migration(self, request, expected=None):
        actor = original(self, request, expected)
        latest = env["db"].get("session", digest, BUYER)
        latest["expires"] = 0
        env["db"].save("session", digest, BUYER, latest)
        return actor
    monkeypatch.setattr(auth.Auth, "bind_actor", revoke_during_migration)
    response = env["buyer"].get("/api/v1/session")
    assert response.json() == {"role": None}
    assert env["db"].get("session", digest, BUYER)["expires"] == 0


def test_concurrent_legacy_session_migrations_converge_on_one_browser_actor(env, monkeypatch):
    token = env["buyer"].cookies.get("aimo_session")
    digest = hashlib.sha256(token.encode()).hexdigest()
    record = env["db"].get("session", digest, BUYER)
    record.pop("actor_id"); record.pop("principal_id")
    env["db"].save("session", digest, BUYER, record)
    barrier = Barrier(2)
    original = auth.Auth.bind_actor
    def simultaneous(self, request, expected=None):
        if expected is None:
            barrier.wait(timeout=5)
        return original(self, request, expected)
    monkeypatch.setattr(auth.Auth, "bind_actor", simultaneous)
    clients = [TestClient(env["app"]), TestClient(env["app"])]
    for client in clients:
        client.cookies.set("aimo_session", token)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = [future.result() for future in [pool.submit(client.get, "/api/v1/session") for client in clients]]
    assert all(response.status_code == 200 for response in responses)
    assert responses[0].json()["actor_id"] == responses[1].json()["actor_id"]
    assert env["db"].get("session", digest, BUYER)["actor_id"] == responses[0].json()["actor_id"]


def test_current_review_and_queue_show_consumed_allowance_without_requoting_or_writes(env, monkeypatch):
    monkeypatch.setitem(MANDATE, "autonomous_limit", "1000.00")
    monkeypatch.setitem(MANDATE, "exception_limit", "1000.00")
    monkeypatch.setitem(MANDATE, "cumulative_limit", "1200.00")
    pending = request(env, create(env))
    second = create(env, None)
    receipt = submit(env, second, "current-review-other-order")
    assert receipt.status_code == 200, receipt.text
    buyer_id = env["identity"]["buyer_id"]
    saved = env["db"].get("procurement", pending["id"], buyer_id)
    snapshot = env["db"].get("approval_snapshot", pending["offer"]["id"], buyer_id)
    with monkeypatch.context() as context:
        context.setattr(procurement, "lookup", lambda *args: pytest.fail("GET review must not query a provider or reprice"))
        reviewed = env["manager"].get(path(pending))
        assert reviewed.status_code == 200, reviewed.text
        reviewed = reviewed.json()
        assert reviewed["approval"]["cumulative_spent"] == "836.00" and reviewed["approval"]["cumulative_remaining"] == "364.00"
        assert reviewed["review_state"] == "BLOCKED" and reviewed["approval"]["can_decide"]
        assert not reviewed["approval"]["can_request"] and not reviewed["can_confirm"]
        assert any("cumulative" in blocker for blocker in reviewed["approval"]["blockers"])
        queue = env["manager"].get("/api/v1/approvals").json()["items"][0]
        assert queue["cumulative_remaining"] == "364.00" and queue["cumulative_spent"] == "836.00"
        assert not queue["can_approve"] and queue["can_reject"] and queue["can_request_changes"]
        assert queue["review_state"] == "BLOCKED" and queue["blockers"]
        assert env["buyer"].get(path(second)).json()["receipt"] == receipt.json()["receipt"]
    assert env["db"].get("procurement", pending["id"], buyer_id) == saved
    assert env["db"].get("approval_snapshot", pending["offer"]["id"], buyer_id) == snapshot
    assert decide(env, pending).status_code == 409
    changes = decide(env, pending, "request-changes", reason="Reduce quantities to fit the remaining allowance")
    assert changes.status_code == 200 and changes.json()["review_state"] == "CHANGES_REQUESTED"


def test_current_review_and_queue_detect_saved_diet_change_without_mutating_snapshot(env, monkeypatch):
    pending = request(env, create(env))
    buyer_id = env["identity"]["buyer_id"]
    assert env["buyer"].put("/api/v1/preferences", json={"dietary_restrictions": ["gluten_free"]}).status_code == 200
    saved = env["db"].get("procurement", pending["id"], buyer_id)
    with monkeypatch.context() as context:
        context.setattr(procurement, "lookup", lambda *args: pytest.fail("Read-only review called a provider"))
        reviewed = env["manager"].get(path(pending)).json()
        assert reviewed["lines"][0]["dietary"] == []  # the original review snapshot stays intact
        assert reviewed["review_state"] == "BLOCKED" and reviewed["approval"]["can_decide"]
        assert any("dietary" in blocker for blocker in reviewed["approval"]["blockers"])
        assert not reviewed["can_confirm"] and not reviewed["approval"]["can_request"]
        queue = env["manager"].get("/api/v1/approvals").json()["items"][0]
        assert not queue["can_approve"] and queue["can_reject"] and queue["can_request_changes"]
        assert any("dietary" in blocker for blocker in queue["blockers"])
    assert env["db"].get("procurement", pending["id"], buyer_id) == saved
    declined = decide(env, pending, "reject", reason="Refresh the dietary requirements")
    assert declined.status_code == 200 and declined.json()["review_state"] == "REJECTED"


def test_policy_changed_pending_request_stays_visible_for_nonspending_recovery(env, monkeypatch):
    pending = request(env, create(env))
    monkeypatch.setitem(MANDATE, "autonomous_limit", "1300.00")
    reviewed = env["manager"].get(path(pending)).json()
    assert reviewed["review_state"] == "BLOCKED" and reviewed["approval"]["can_decide"]
    assert any("policy changed" in blocker for blocker in reviewed["approval"]["blockers"])
    queue = env["manager"].get("/api/v1/approvals").json()["items"][0]
    assert not queue["can_approve"] and queue["can_request_changes"] and queue["can_reject"]
    result = decide(env, pending, "request-changes", reason="Review the current policy")
    assert result.status_code == 200 and not result.json()["can_confirm"]
