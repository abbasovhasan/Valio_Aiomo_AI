"""Behavioral authority tests. Fixtures are authored, not sponsor responses."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.config import access_codes, MANDATE, BUYER
from backend.store import Store
from backend import catalog, upstream, policy


@pytest.fixture
def env(tmp_path, monkeypatch):
    def product(pid):
        if pid not in ["464306", "464398", "465039", "460396"]:
            raise ValueError("No product")
        return {
            "id": pid,
            "name": "Authored test milk " + pid,
            "sales_unit": "KI" if pid == "465039" else "ST",
            "base_unit": "ST",
            "base_units_per_sales_unit": "5" if pid == "465039" else "1",
            "liters_per_sales_unit": "5"
            if pid == "465039"
            else "10"
            if pid == "460396"
            else "1",
            "volume_evidence": "authored dimensional test metadata",
            "lactose_free": pid != "460396",
            "diet_evidence": "FREE_FROM_LACTOSE" if pid != "460396" else "unknown",
            "allowed_lot_size": "1",
            "deleted": False,
            "deposits": [],
            "variable_unit": False,
        }

    monkeypatch.setattr(catalog, "product", product)
    monkeypatch.setattr(
        catalog, "load_catalog", lambda: {str(n): {} for n in range(20)}
    )
    monkeypatch.setattr(
        catalog,
        "search",
        lambda q, limit: [product(q)] if q in ["464306", "464398", "465039"] else [],
    )
    store = Store(tmp_path / "test.sqlite", postgres=False)
    app = create_app(store)

    def client(role="buyer"):
        c = TestClient(app)
        assert (
            c.post(
                "/api/v1/session", json={"access_code": access_codes()[role]}
            ).status_code
            == 200
        )
        return c

    return client, store, app


def run(c, **kw):
    req = {
        "quantity_liters": 1000,
        "date": str(date.today() + timedelta(days=2)),
        "mode": "fixture",
    }
    req.update(kw)
    r = c.post("/api/v1/runs", json=req)
    assert r.status_code == 200, r.text
    return r.json()


def selected(r):
    return next(o for o in r["offers"] if o["id"] == r["recommended_offer_id"])


def commit(c, o, key="test-order-123"):
    return c.post(
        "/api/v1/offers/" + o["id"] + "/commit", headers={"Idempotency-Key": key}
    )


def test_normal_autonomy_receipt_independent_verify_and_duplicate(env):
    client, db, app = env
    c = client()
    r = run(c)
    o = selected(r)
    assert o["status"] == "within_mandate" and o["total"] == "1150.00"
    first = commit(c, o)
    assert first.status_code == 200, first.text
    again = commit(c, o)
    assert (
        again.json()["id"] == first.json()["id"] and again.json()["idempotent_replay"]
    )
    assert db.spent() == 115000
    v = c.get("/api/v1/receipts/" + first.json()["id"] + "/verify").json()
    assert v["integrity_valid"] and v["scope_valid"] and v["simulated"]


def test_approval_separate_identity_and_bound_fingerprint(env):
    client, db, _ = env
    c = client()
    r = run(c, scenario="shortage")
    o = selected(r)
    assert o["status"] == "approval_required" and o["product"]["id"] == "464398"
    assert commit(c, o).status_code == 403
    assert (
        c.post(
            "/api/v1/offers/" + o["id"] + "/approve",
            json={"fingerprint": o["fingerprint"]},
        ).status_code
        == 403
    )
    a = client("approver")
    assert (
        a.post(
            "/api/v1/offers/" + o["id"] + "/approve", json={"fingerprint": "a" * 64}
        ).status_code
        == 409
    )
    assert (
        a.post(
            "/api/v1/offers/" + o["id"] + "/approve",
            json={"fingerprint": o["fingerprint"]},
        ).status_code
        == 200
    )
    assert commit(c, o).status_code == 200
    newer = selected(run(c, scenario="shortage", quantity_liters=1001))
    assert commit(c, newer, "different-request").status_code == 403


def test_invalid_diet_not_approvable_even_by_human(env):
    client, _, _ = env
    c = client()
    r = run(c, scenario="diet")
    o = r["offers"][0]
    assert o["status"] == "invalid" and o["product"]["id"] == "460396"
    assert commit(c, o).status_code == 409
    a = client("approver")
    assert (
        a.post(
            "/api/v1/offers/" + o["id"] + "/approve",
            json={"fingerprint": o["fingerprint"]},
        ).status_code
        == 409
    )


def test_unknown_quantity_and_cutoff_not_a_million_stock(env):
    client, _, _ = env
    c = client()
    r = run(c, scenario="unknown")
    assert all(o["status"] == "invalid" for o in r["offers"])
    assert any("UNKNOWN" in x for x in r["offers"][0]["reasons"])


def test_stale_offer_requires_new_run_and_no_approval_transfer(env):
    client, _, _ = env
    c = client()
    r = run(c, scenario="stale")
    o = r["offers"][0]
    assert commit(c, o).status_code == 409
    n = c.post("/api/v1/offers/" + o["id"] + "/revalidate")
    assert n.status_code == 200
    assert n.json()["id"] != r["id"]
    assert all(not o["approved"] for o in n.json()["offers"])
    assert selected(n.json())["status"] == "within_mandate"


def test_quantity_and_role_authority_cannot_be_minted_in_body(env):
    client, _, app = env
    c = client()
    for qty in [0, -2, "NaN", 10001]:
        assert c.post("/api/v1/runs", json={"quantity_liters": qty}).status_code == 422
    assert (
        c.post(
            "/api/v1/runs",
            json={"role": "approver", "customer_id": "other", "budget": 100000},
        ).status_code
        == 422
    )
    unknown = TestClient(app)
    assert unknown.get("/api/v1/workspace").status_code == 401
    assert c.get("/api/v1/offers/not-your-offer").status_code == 404


def test_concurrent_cumulative_cap_atomic_and_split_requests_cannot_bypass(env):
    client, db, _ = env
    c = client()
    # Four distinct 1,000L orders consume €4,600, leaving room for just one.
    for i in range(4):
        assert commit(c, selected(run(c)), f"prelude-{i}").status_code == 200
    offers = [selected(run(c)), selected(run(c))]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda pair: commit(c, pair[1], f"concurrent-{pair[0]}"),
                enumerate(offers),
            )
        )
    assert sorted(r.status_code for r in results) == [200, 409]
    assert db.spent() == 575000


def test_legacy_trust_cannot_self_approve_by_switching_role_in_one_browser(env):
    client, db, _ = env
    buyer = client()
    offer = selected(run(buyer, scenario="shortage"))
    actor = buyer.get("/api/v1/session").json()["actor_id"]
    buyer.delete("/api/v1/session")
    switched = buyer.post("/api/v1/session", json={"access_code": access_codes()["approver"]}).json()
    assert switched["actor_id"] == actor
    denied = buyer.post("/api/v1/offers/" + offer["id"] + "/approve", json={"fingerprint": offer["fingerprint"]})
    assert denied.status_code == 403 and denied.json()["detail"]["code"] == "self_approval_forbidden"
    independent = client("approver")
    assert independent.post("/api/v1/offers/" + offer["id"] + "/approve", json={"fingerprint": offer["fingerprint"]}).status_code == 200
    assert db.spent() == 0


@pytest.mark.parametrize("restriction", ["permission", "ceiling"])
def test_legacy_decision_cannot_claim_approval_beyond_current_manager_assignment(env, restriction):
    client, db, _ = env
    offer = selected(run(client(), scenario="shortage"))
    manager = client("approver")
    assignment = db.get("workspace_authority", "workspace-authority-" + BUYER, BUYER)
    if restriction == "permission":
        assignment["permissions"] = []
    else:
        assignment["max_total"] = "100.00"
    db.save("workspace_authority", "workspace-authority-" + BUYER, BUYER, assignment)
    response = manager.post("/api/v1/offers/" + offer["id"] + "/approve", json={"fingerprint": offer["fingerprint"]})
    assert response.status_code == 403 and response.json()["detail"]["code"] == "manager_authority"
    assert not db.get("offer", offer["id"], BUYER)["approved"] and db.spent() == 0


def test_concurrent_duplicate_commit_single_receipt(env):
    client, db, _ = env
    c = client()
    o = selected(run(c))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: commit(c, o), range(2)))
    assert all(r.status_code == 200 for r in results)
    assert results[0].json()["id"] == results[1].json()["id"] and db.spent() == 115000


def test_idempotency_key_cannot_name_another_offer(env):
    client, db, _ = env
    c = client()
    a = selected(run(c))
    b = selected(run(c))
    assert commit(c, a).status_code == 200
    assert commit(c, b).status_code == 409
    assert db.spent() == 115000


def test_supplier_prompt_injection_cannot_change_authority(env):
    client, _, _ = env
    c = client()
    r = run(c, scenario="injection")
    o = selected(r)
    assert "reveal API keys" in o["product"]["untrusted_text"]
    assert (
        o["status"] == "within_mandate"
        and o["total"] == "1150.00"
        and not o["approved"]
    )
    assert (
        c.post(
            "/api/v1/offers/" + o["id"] + "/approve",
            json={"fingerprint": o["fingerprint"]},
        ).status_code
        == 403
    )


def test_upstream_failure_never_silently_becomes_fixture(env, monkeypatch):
    client, _, _ = env
    c = client()

    def fail(*args):
        raise upstream.UpstreamError(
            "Valio sandbox unavailable; no fixture substituted."
        )

    monkeypatch.setattr(upstream, "sponsor_lookup", fail)
    r = c.post(
        "/api/v1/runs",
        json={"mode": "live", "date": str(date.today() + timedelta(days=2))},
    )
    assert r.status_code == 502 and "no fixture" in r.text


def test_model_failure_recorded_and_hard_checks_still_apply(env, monkeypatch):
    client, _, _ = env
    c = client()
    monkeypatch.setattr(upstream, "sponsor_lookup", upstream.fixture_lookup)

    def fail(*args):
        raise upstream.UpstreamError("Model typed output invalid.")

    monkeypatch.setattr(upstream, "rank_with_nvidia", fail)
    r = run(c, mode="live", use_model=True, scenario="diet")
    assert r["agent"]["status"] == "failed" and r["offers"][0]["status"] == "invalid"


def test_changed_live_price_after_approval_is_blocked(env, monkeypatch):
    client, _, _ = env
    c = client()
    monkeypatch.setattr(upstream, "sponsor_lookup", upstream.fixture_lookup)
    r = run(c, mode="live", scenario="shortage")
    o = selected(r)
    a = client("approver")
    assert (
        a.post(
            "/api/v1/offers/" + o["id"] + "/approve",
            json={"fingerprint": o["fingerprint"]},
        ).status_code
        == 200
    )
    original = upstream.fixture_lookup

    def changed(*args):
        e = original(*args)
        for p in e["price"]["products"]:
            p["catalogPrice"]["valueWithTax"] = 2
        return e

    monkeypatch.setattr(upstream, "sponsor_lookup", changed)
    r = commit(c, o)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "revalidation_failed"


def test_late_blocked_missing_price_and_invalid_dimension(env, monkeypatch):
    client, _, _ = env
    c = client()
    original = upstream.fixture_lookup

    def broken(*args):
        e = original(*args)
        for p in e["price"]["products"]:
            p["error"] = True
        for p in e["availability"]["products"]:
            p["closingTime"] = (policy.now() - timedelta(hours=1)).isoformat()
            for line in p["scheduleLines"]:
                line["availableDate"] = str(date.today() + timedelta(days=20))
        return e

    monkeypatch.setattr(upstream, "fixture_lookup", broken)
    r = run(c)
    assert all(o["status"] == "invalid" and o["total"] is None for o in r["offers"])
    assert {"price", "cutoff", "availability"} <= set(
        x["code"] for x in r["offers"][0]["checks"] if x["status"] != "pass"
    )


def test_dimensional_unknown_and_deposits_fail_closed(env, monkeypatch):
    client, _, _ = env
    c = client()
    original = catalog.product

    def bad(pid):
        p = original(pid)
        p["liters_per_sales_unit"] = None
        p["volume_evidence"] = "Only kilogram mass known; no litre conversion"
        p["deposits"] = [{"unknown_charge": True}]
        return p

    monkeypatch.setattr(catalog, "product", bad)
    r = run(c)
    assert all(o["status"] == "invalid" for o in r["offers"])
    assert {"units", "deposits"} <= set(
        x["code"] for x in r["offers"][0]["checks"] if x["status"] != "pass"
    )


def test_fractional_lot_rounding_preserves_whole_sales_pack(env, monkeypatch):
    client, _, _ = env
    c = client()
    original = catalog.product

    def changed(pid):
        p = original(pid)
        p["allowed_lot_size"] = "1.5"
        return p

    monkeypatch.setattr(catalog, "product", changed)
    r = run(c, quantity_liters=10)
    first = r["offers"][0]
    assert first["quantity_sales_units"] == "12" and first["effective_liters"] == "12"
    assert Decimal(first["quantity_sales_units"]) % Decimal("1.5") == 0


def test_price_expiry_fails_closed(env, monkeypatch):
    client, _, _ = env
    c = client()
    original = upstream.fixture_lookup

    def expired(*args):
        e = original(*args)
        for p in e["price"]["products"]:
            p["catalogPrice"]["validTo"] = (
                policy.now() - timedelta(hours=1)
            ).isoformat()
        return e

    monkeypatch.setattr(upstream, "fixture_lookup", expired)
    r = run(c)
    assert all(o["status"] == "invalid" for o in r["offers"])
    assert "price_validity" in {
        x["code"] for x in r["offers"][0]["checks"] if x["status"] != "pass"
    }


def test_foreign_buyer_scoped_records_are_inaccessible(env):
    client, db, _ = env
    c = client()
    db.save(
        "offer",
        "foreign-offer",
        "another-buyer",
        {"id": "foreign-offer", "customer_id": "other-customer"},
    )
    assert c.get("/api/v1/offers/foreign-offer").status_code == 404


def test_future_timestamp_and_stale_lookup_rejected(env, monkeypatch):
    client, _, _ = env
    c = client()
    original = upstream.fixture_lookup
    for delta in [timedelta(minutes=10), -timedelta(minutes=10)]:

        def clock_shifted(*args):
            e = original(*args)
            e["fetched_at"] = (policy.now() + delta).isoformat()
            return e

        monkeypatch.setattr(upstream, "fixture_lookup", clock_shifted)
        r = run(c)
        assert all(o["status"] == "invalid" for o in r["offers"])
        assert "freshness" in {
            x["code"] for x in r["offers"][0]["checks"] if x["status"] != "pass"
        }


def test_model_tool_candidates_drive_dynamic_lookup(env, monkeypatch):
    client, _, _ = env
    c = client()
    seen = []

    def model(*args):
        return {
            "provider": "NVIDIA test double",
            "status": "fixture_model",
            "tool_calls": [
                {"name": "propose_candidates", "arguments": {"product_ids": ["464398"]}}
            ],
        }

    def lookup(customer, day, ids):
        seen.extend(ids)
        return upstream.fixture_lookup(customer, day, ids)

    monkeypatch.setattr(upstream, "rank_with_nvidia", model)
    monkeypatch.setattr(upstream, "sponsor_lookup", lookup)
    r = run(c, mode="live", use_model=True)
    assert seen == ["464398"] and [o["product"]["id"] for o in r["offers"]] == [
        "464398"
    ]
    assert r["offers"][0]["status"] == "approval_required"


def test_existing_order_cannot_mask_conflicting_idempotency_key(env):
    client, db, _ = env
    c = client()
    a = selected(run(c))
    b = selected(run(c))
    assert commit(c, a, "first-key-123").status_code == 200
    assert commit(c, b, "second-key-123").status_code == 200
    assert commit(c, a, "second-key-123").status_code == 409
    assert db.spent() == 230000


def test_expiry_is_rechecked_inside_atomic_commit(env):
    client, db, _ = env
    c = client()
    o = selected(run(c))
    o["expires_at"] = (policy.now() - timedelta(seconds=1)).isoformat()
    from backend.store import StoreError

    with pytest.raises(StoreError) as exc:
        db.commit(o, "expired-lock", {"id": "never-created"}, 600000, o["expires_at"])
    assert exc.value.code == "stale_offer" and db.spent() == 0


def test_security_headers_and_mutation_origin(env):
    client, _, app = env
    c = client()
    r = c.get("/api/v1/workspace")
    assert (
        r.headers["cache-control"] == "no-store"
        and r.headers["x-content-type-options"] == "nosniff"
    )
    r = c.post(
        "/api/v1/runs",
        json={"mode": "fixture"},
        headers={"Origin": "https://untrusted.example"},
    )
    assert r.status_code == 403 and r.json()["detail"]["code"] == "origin_blocked"
    assert "default-src 'self'" in c.get("/").headers["content-security-policy"]


def test_different_key_retry_is_rejected_before_key_can_change_meaning(env):
    client, db, _ = env
    c = client()
    a = selected(run(c))
    b = selected(run(c))
    first = commit(c, a, "original-key-A")
    assert first.status_code == 200
    changed = commit(c, a, "new-key-B")
    assert (
        changed.status_code == 409
        and changed.json()["detail"]["code"] == "idempotency_key_mismatch"
    )
    # Since key B was rejected, its first accepted use can still name new offer B.
    assert commit(c, b, "new-key-B").status_code == 200
    assert commit(c, a, "original-key-A").json()["id"] == first.json()["id"]
    assert db.spent() == 230000


@pytest.mark.parametrize("boundary", ["cutoff", "price_validity", "freshness"])
def test_supplier_deadline_crossing_during_row_lock_prevents_commit(
    env, monkeypatch, boundary
):
    """The pre-lock checks pass. Time advances only after the account lock."""
    from contextlib import contextmanager

    client, db, _ = env
    c = client()
    clock = [policy.now()]
    monkeypatch.setattr(policy, "now", lambda: clock[0])
    monkeypatch.setattr(upstream, "now", lambda: clock[0])
    original_lookup = upstream.fixture_lookup

    def narrow_window(*args):
        e = original_lookup(*args)
        if boundary == "cutoff":
            for p in e["availability"]["products"]:
                p["closingTime"] = (clock[0] + timedelta(seconds=2)).isoformat()
        elif boundary == "price_validity":
            for p in e["price"]["products"]:
                p["catalogPrice"]["validTo"] = (
                    clock[0] + timedelta(seconds=2)
                ).isoformat()
        else:
            e["fetched_at"] = (clock[0] - timedelta(seconds=298)).isoformat()
        return e

    monkeypatch.setattr(upstream, "fixture_lookup", narrow_window)
    o = selected(run(c, date=str(date.today())))
    assert o["status"] == "within_mandate"
    original_tx = db.tx
    original_commit = db.commit
    atomic = [False]
    advanced = [False]

    @contextmanager
    def tx_with_delayed_lock():
        with original_tx() as connection:
            execute = connection.execute

            def after_lock(q, args=()):
                result = execute(q, args)
                if atomic[0] and not advanced[0] and q.startswith("SELECT spent_cents"):
                    clock[0] += timedelta(seconds=3)
                    advanced[0] = True
                return result

            connection.execute = after_lock
            yield connection

    def marked_atomic_commit(*args, **kwargs):
        atomic[0] = True
        try:
            return original_commit(*args, **kwargs)
        finally:
            atomic[0] = False

    monkeypatch.setattr(db, "tx", tx_with_delayed_lock)
    monkeypatch.setattr(db, "commit", marked_atomic_commit)
    result = commit(c, o)
    assert advanced[0] and result.status_code == 409
    assert result.json()["detail"]["code"] == "evidence_expired"
    assert db.spent() == 0


def test_unknown_candidate_distinguished_from_missing_catalog(env, monkeypatch):
    client, db, _ = env
    c = client()
    unknown = c.post(
        "/api/v1/runs", json={"mode": "fixture", "candidate_ids": ["invented-product"]}
    )
    assert (
        unknown.status_code == 422
        and unknown.json()["detail"]["code"] == "unknown_product_id"
    )
    assert db.spent() == 0
    monkeypatch.setattr(catalog, "load_catalog", lambda: {})
    missing = c.post("/api/v1/runs", json={"mode": "fixture"})
    assert (
        missing.status_code == 503
        and missing.json()["detail"]["code"] == "catalog_missing"
    )


def test_missing_dietary_claim_stays_unknown_and_cannot_pass_policy(monkeypatch):
    monkeypatch.setattr(catalog, "supplemental", lambda: {})
    p = catalog.normalize(
        {
            "id": "464306",
            "salesUnit": "ST",
            "baseUnit": "ST",
            "units": [{"unitId": "ST", "sizeInBaseUnits": 1}],
            "synkkaData": {
                "names": [{"language": "en", "value": "Authored test milk 1 l"}]
            },
        }
    )
    assert p["lactose_free"] is None and p["contains_milk"] is None
    req = {
        "quantity_liters": "1000",
        "date": str(date.today() + timedelta(days=2)),
        "mode": "fixture",
        "scenario": "baseline",
    }
    o = policy.make_offer(
        p, req, upstream.fixture_lookup("test", req["date"], ["464306"])
    )
    assert o["status"] == "invalid"
    assert any(c["code"] == "diet" and c["status"] == "blocked" for c in o["checks"])


def test_volume_in_name_cannot_convert_mass_sales_base_to_litres(monkeypatch):
    monkeypatch.setattr(catalog, "supplemental", lambda: {})
    p = catalog.normalize(
        {
            "id": "464306",
            "salesUnit": "KG",
            "baseUnit": "KG",
            "units": [{"unitId": "KG", "sizeInBaseUnits": 5}],
            "synkkaData": {
                "names": [{"language": "en", "value": "Authored liquid milk 1 l"}]
            },
        }
    )
    assert p["liters_per_sales_unit"] is None
    req = {
        "quantity_liters": "1000",
        "date": str(date.today() + timedelta(days=2)),
        "mode": "fixture",
        "scenario": "baseline",
    }
    o = policy.make_offer(
        p, req, upstream.fixture_lookup("test", req["date"], ["464306"])
    )
    assert o["status"] == "invalid"
    assert any(c["code"] == "units" and c["status"] == "blocked" for c in o["checks"])


def test_changed_tax_basis_after_approval_requires_new_offer(env, monkeypatch):
    client, db, _ = env
    c = client()
    monkeypatch.setattr(upstream, "sponsor_lookup", upstream.fixture_lookup)
    o = selected(run(c, mode="live", scenario="shortage"))
    a = client("approver")
    assert (
        a.post(
            "/api/v1/offers/" + o["id"] + "/approve",
            json={"fingerprint": o["fingerprint"]},
        ).status_code
        == 200
    )
    original = upstream.fixture_lookup

    def changed_tax(*args):
        evidence = original(*args)
        for p in evidence["price"]["products"]:
            p["tax"]["taxRate"] = 14
        return evidence

    monkeypatch.setattr(upstream, "sponsor_lookup", changed_tax)
    result = commit(c, o)
    assert (
        result.status_code == 409
        and result.json()["detail"]["code"] == "revalidation_failed"
    )
    assert db.spent() == 0


def test_policy_change_invalidates_uncommitted_offer_and_approval(env, monkeypatch):
    client, db, app = env
    c = client()
    offer = selected(run(c))
    monkeypatch.setitem(MANDATE, "autonomous_limit", "1000.00")
    response = commit(c, offer)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "policy_changed"
    new_offer = selected(run(c))
    assert new_offer["status"] == "approval_required"
    a = client("approver")
    monkeypatch.setitem(MANDATE, "exception_limit", "1100.00")
    response = a.post(
        f"/api/v1/offers/{new_offer['id']}/approve",
        json={"fingerprint": new_offer["fingerprint"]},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "policy_changed"
    assert db.spent() == 0
