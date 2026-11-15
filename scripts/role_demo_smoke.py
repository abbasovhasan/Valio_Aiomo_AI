"""Keyless controlled-demo HTTP QA; fixture quotes and zero orders by default.

Usage: .venv/bin/python scripts/role_demo_smoke.py --url http://127.0.0.1:8012
Only --commit-demo permits one eligible simulated confirmation below EUR100.
No code/password is loaded, printed or sent. Live/model calls are unsupported.
The manager uses a separate browser actor; switching the creator's role must
never authorize its own request. Only this run's personal QA entries are hidden.
Private source-derived UI cases/report are written under ignored .local only.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from http.cookies import SimpleCookie
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import catalog, product_facts as facts
from backend.config import BUYER, CUSTOMER
from scripts.catalog_qa import inventory

D = Decimal
API = "/api/v1"
CARTS = "/procurement/sessions"


def prepare_cases(path=ROOT / ".local/role-demo-cases.json"):
    rows = catalog.load_catalog()
    assert rows, "Install the original private catalog before preparing cases"
    products = (facts.normalize(pid) for pid in sorted(rows))
    usable = [p for p in products if not p["deleted"] and not p["variable_unit"] and not p["deposits"] and not p["conversion_issues"]]
    clt_ids = {pid for pid, raw in rows.items() if raw.get("salesUnit") == raw.get("baseUnit") == "BOT"
               and any(c.get("synkkaPackagingType") == "BASE_UNIT_OR_EACH" and (c.get("volume") or {}).get("unit") == "CLT"
                       and D(str((c.get("volume") or {}).get("value", 0))) == 75
                       for c in raw.get("synkkaData", {}).get("unitConversions", []))}
    syrup = next(p for p in usable if p["id"] in clt_ids and D(p["liters_per_sales_unit"]) == D(".75"))
    kg = next(p for p in usable if p["sales_unit"] == p["base_unit"] == "KG"
              and D(p["base_units_per_sales_unit"]) == 1 and D(p["allowed_lot_size"]) == D(".01"))
    milk_options = [p for p in facts.search("milk", limit=50, dietary=["lactose_free"])
                    if not facts.suitability(p, ["lactose_free"]) and p.get("liters_per_sales_unit")
                    and not p["variable_unit"] and not p["deposits"] and not p.get("purpose_review_required")]
    assert len(milk_options) >= 2, "Find multiple verified real milk alternatives"
    milk = milk_options[0]
    cases = []
    def append(key, p, quantity, unit, **extra):
        cases.append({"key": key, "product_id": p["id"], "name": p["name"], "category": p["category"],
                      "sales_unit": p["sales_unit"], "quantity": quantity, "unit": unit,
                      "liters_per_sales_unit": p["liters_per_sales_unit"], "kg_per_sales_unit": p["kg_per_sales_unit"],
                      "base_units_per_sales_unit": p["base_units_per_sales_unit"], "allowed_lot_size": p["allowed_lot_size"], **extra})
    append("clt_75cl", syrup, "1", "L")
    append("fractional_kg", kg, "1.5", "kg")
    append("milk_alternatives", milk, "20", "L", alternative_ids=[p["id"] for p in milk_options[:8]])
    used = {case["category"] for case in cases}
    remaining = sorted((p for p in usable if p["category"] not in used and p["sales_unit"] != "KG"), key=lambda p: (p["category"], p["id"]))
    for index in range(2):
        eligible = [p for p in remaining if p["category"] not in used]
        p = eligible[len(eligible) * (index + 1) // 3]
        append("additional_category_" + str(index + 1), p, "1", "packages")
        used.add(p["category"])
    assert len(used) == 5
    result = {"created_at": datetime.now(timezone.utc).isoformat(), "catalog_count": len(rows),
              "category_count": len({p["category"] for p in rows.values()}), "source_inventory": inventory(), "cases": cases}
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2)); path.chmod(0o600)
    return result


def run_smoke(client, case_file, *, manager_client=None, commit_demo=False, save=None):
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "mode": "fixture", "model_calls": 0,
              "supplier_calls": 0, "orders_created": 0, "non_demo_mutations": 0, "checks": []}
    started = time.perf_counter()
    owned_carts = set()
    own_manager = manager_client is None
    if manager_client is None:
        if hasattr(client, "app"):
            manager_client = type(client)(client.app, base_url=str(client.base_url))
        else:
            import httpx
            manager_client = httpx.Client(base_url=str(client.base_url), timeout=60)
    manager_identity = {}
    def checked(name, value):
        assert value, name
        report["checks"].append(name)
        report["check_count"] = len(report["checks"])
        report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        if save: save(report)
    def call(method, path, expected=200, manager=False, **kwargs):
        assert not any(part in path for part in ("/runs", "/offers", "/auth/login", "/auth/register")), "Only the quick-demo workflow is mutable in this smoke"
        if path.endswith("/confirm"):
            assert commit_demo and report["orders_created"] == 0, "Confirmation was not authorized"
        if method != "GET" and path != "/auth/demo" and path != "/session":
            assert (manager_identity if manager else identity).get("quick_demo") is True, "Mutation requires server-issued quick-demo scope"
        response = (manager_client if manager else client).request(method, API + path, **kwargs)
        assert response.status_code == expected, f"{method} {path.rsplit('/',1)[-1]} HTTP{response.status_code}, expected{expected}"
        return response
    def data(method, path, **kwargs): return call(method, path, **kwargs).json()
    def cookies(response):
        result = SimpleCookie()
        for header in response.headers.get_list("set-cookie"):
            result.load(header)
        return result
    def enter(role, remember=False, manager=False):
        nonlocal identity, manager_identity
        response = call("POST", "/auth/demo", manager=manager, json={"role": role, "remember_me": remember})
        issued = response.json()
        if manager:
            manager_identity = issued
        else:
            identity = issued
        checked("Server-issued " + role + " is isolated from legacy/private identities", issued["role"] == role and issued["quick_demo"] and issued["buyer_id"] != BUYER and issued["customer_id"] != CUSTOMER and issued["workspace_id"] == issued["buyer_id"])
        return response
    def action(session, name, **fields):
        return data("POST", CARTS + "/" + session["id"] + "/actions", json={"version": session["version"], "action": name, **fields})
    def create(case, quantity=None, unit=None):
        session = data("POST", CARTS + "/from-product", json={"product_id": case["product_id"], "quantity": quantity or case["quantity"], "unit": unit or case["unit"], "date": str(date.today() + timedelta(days=2)), "mode": "fixture", "apply_preferences": False})
        owned_carts.add(session["id"])
        return session
    def exact(session, **fields):
        return {"version": session["version"], "fingerprint": session["offer"]["fingerprint"], **fields}
    def request_approval(session, explanation="QA: review this exact fixture basket"):
        return data("POST", CARTS + "/" + session["id"] + "/request-approval", json=exact(session, explanation=explanation))
    def decide(session, name="approve", **fields):
        return data("POST", CARTS + "/" + session["id"] + "/" + name, manager=True, json=exact(session, **fields))
    identity = {}
    try:
        config = data("GET", "/auth/demo")
        checked("Quick authentication is explicitly enabled and exposes no secret", config == {"enabled": True})
        checked("Protected workspace denies anonymous access", call("GET", "/workspace", expected=401).status_code == 401)
        checked("Forged role is rejected", call("POST", "/auth/demo", expected=422, json={"role": "admin"}).status_code == 422)
        checked("Client-selected workspace cannot escape fixed demo scope", call("POST", "/auth/demo", expected=422, json={"role": "approver", "workspace_id": BUYER}).status_code == 422)
        checked("Cross-origin quick login is blocked", call("POST", "/auth/demo", expected=403, headers={"Origin": "https://qa-invalid.example"}, json={"role": "buyer"}).status_code == 403)
        response = enter("buyer", True)
        cookie = cookies(response); morsel = cookie["aimo_session"]
        checked("Remember Me uses HttpOnly/Strict persistent30-day cookie", bool(morsel["httponly"]) and morsel["samesite"].lower() == "strict" and morsel["max-age"] == str(30*24*3600))
        if str(client.base_url).startswith("https:"):
            checked("Hosted cookie is Secure", bool(morsel["secure"]))
        buyer_scope = (identity["buyer_id"], identity["customer_id"])
        before = data("GET", "/workspace")
        before_spent = D(before["mandate"]["spent"])
        prefs = data("GET", "/preferences")
        checked("Existing mandatory preferences are not silently cleared", not prefs["dietary_restrictions"] and not prefs["excluded_ingredients"])
        checked("Session restoration returns backend buyer role", data("GET", "/session")["role"] == "buyer")
        old_token = client.cookies.get("aimo_session")
        data("DELETE", "/session")
        checked("Buyer logout revokes protected access", call("GET", "/workspace", expected=401).status_code == 401)
        checked("Revoked bearer cannot preserve buyer authority", call("GET", "/workspace", expected=401, headers={"Authorization": "Bearer " + old_token}).status_code == 401)
        response = enter("approver")
        cookie = cookies(response)
        checked("Unchecked Remember Me creates a session cookie", not cookie["aimo_session"]["max-age"])
        checked("Approver deliberately shares only the paired demo workspace", (identity["buyer_id"],identity["customer_id"]) == buyer_scope)
        call("POST", CARTS + "/from-product", expected=403, json={"product_id": case_file["cases"][0]["product_id"], "quantity": "1", "unit": "packages", "mode": "fixture"})
        checked("Approver cannot create a buyer basket", True)
        data("DELETE", "/session")
        checked("Approver logout revokes protected access", call("GET", "/workspace", expected=401).status_code == 401)
        enter("buyer")
        checked("Role re-entry does not reset synthetic spending", D(data("GET", "/workspace")["mandate"]["spent"]) == before_spent)
        checked("Buyer cannot view the approver queue", call("GET", "/approvals", expected=403).status_code == 403)

        cases = case_file["cases"]
        mixed = create(cases[0])
        for case in cases[1:]:
            mixed = action(mixed, "add_product", product_id=case["product_id"], quantity=case["quantity"], unit=case["unit"])
        checked("Five actual source categories form separate selected requirements", len(mixed["lines"]) == 5 and {line["selected_product_id"] for line in mixed["lines"]} == {case["product_id"] for case in cases})
        for case in cases:
            line = next(line for line in mixed["lines"] if line["selected_product_id"] == case["product_id"])
            selected = next(p for p in line["candidates"] if p["id"] == case["product_id"])
            total = (D(selected["unit_price"]) * D(selected["quantity_sales_units"])).quantize(D(".01"), rounding=ROUND_HALF_UP)
            checked("Actual " + case["key"] + " quotation has deterministic subtotal", D(selected["line_total"]) == total and selected["source"] == "authored_fixture")
            if case["key"] == "clt_75cl": checked("75cl metadata yields two packs/1.5L for1L", D(selected["pack_quantity"]) == D(".75") and D(selected["quantity_sales_units"]) == 2 and D(selected["effective_quantity"]) == D("1.5"))
            if case["key"] == "fractional_kg": checked("Measured KG preserves fractional1.5kg native quantity", D(selected["quantity_sales_units"]) == D("1.5"))
        checked("Five-category basket is a draft without model authority", mixed["receipt"] is None and mixed["use_model"] is False)

        # Use a fixed CLT commercial package, deriving quantity from configured
        # authority and its fixture price rather than hardcoding a costly SKU.
        small = create(cases[0], "1", "packages")
        price = D(small["cart"]["items"][0]["unit_price"])
        mandate = before["mandate"]
        autonomous, ceiling = D(mandate["autonomous_limit"]), D(mandate["exception_limit"])
        needed = (autonomous / price).to_integral_value(rounding=ROUND_CEILING) + 2
        checked("Configured policy has a safe approval-only test range", price * (needed+2) <= ceiling and before_spent + price * (needed+2) <= D(mandate["cumulative_limit"]))
        decision = create(cases[0], str(needed), "packages")
        enter("approver", manager=True)
        checked("Manager has an independent browser actor and assigned principal", manager_identity["actor_id"] != identity["actor_id"] and manager_identity["principal_id"] != identity["principal_id"] and manager_identity["buyer_id"] == identity["buyer_id"])
        queue = data("GET", "/approvals", manager=True, params={"limit": 100})
        checked("An unrequested financial exception does not enter the queue", not any(entry["id"] == decision["id"] for entry in queue["items"]))
        old_fingerprint = decision["offer"]["fingerprint"]
        decision = action(decision, "set_quantity", line_id=decision["lines"][0]["id"], quantity=str(needed+1), unit="packages")
        checked("Buyer revision invalidates exact old fingerprint", decision["approval"]["status"] == "required" and decision["offer"]["fingerprint"] != old_fingerprint)
        call("POST", CARTS + "/" + decision["id"] + "/approve", expected=403, json=exact(decision))
        checked("Buyer cannot approve itself", True)
        pending = request_approval(decision)
        checked("Buyer explicitly submits a versioned exact financial request", pending["approval"]["pending"] and pending["submitted_at"] and pending["version"] == decision["version"] + 1 and pending["offer"]["fingerprint"] != decision["offer"]["fingerprint"])
        old_token = client.cookies.get("aimo_session")
        buyer_actor = identity["actor_id"]
        enter("approver")
        checked("Role switch revokes previous buyer token", call("GET", "/workspace", expected=401, headers={"Authorization": "Bearer " + old_token}).status_code == 401)
        checked("Role switching preserves the creator actor lineage", identity["actor_id"] == buyer_actor)
        queue = data("GET", "/approvals", params={"limit": 100})
        own_entry = next(entry for entry in queue["items"] if entry["id"] == pending["id"])
        checked("Same-browser manager review cannot authorize its own request", not own_entry["can_approve"] and not own_entry["can_reject"] and not own_entry["can_request_changes"] and own_entry["decision_blockers"])
        for operation in ["approve", "reject", "request-changes"]:
            call("POST", CARTS + "/" + pending["id"] + "/" + operation, expected=403, json=exact(pending, **({"reason": "QA: self decision must fail"} if operation != "approve" else {})))
        checked("Direct same-actor approval, rejection and changes are forbidden", True)
        enter("buyer")
        queue = data("GET", "/approvals", manager=True, params={"limit": 100})
        checked("Independent manager queue exposes the exact submitted request", any(entry["id"] == pending["id"] and entry["fingerprint"] == pending["offer"]["fingerprint"] and entry["can_approve"] for entry in queue["items"]))
        call("POST", CARTS + "/" + pending["id"] + "/approve", expected=409, manager=True, json={"version": pending["version"], "fingerprint": old_fingerprint})
        checked("Old-fingerprint approval is blocked", True)
        changes = decide(pending, "request-changes", reason="QA: reduce or review quantities")
        checked("Request changes returns the pending basket to buyer control", changes["review_state"] == "CHANGES_REQUESTED" and changes["changes_requested"]["reason"] and not changes["can_confirm"] and not changes["approval"]["pending"])
        fresh = action(changes, "quote")
        checked("A fresh quote invalidates the previous decision version", fresh["version"] > changes["version"] and fresh["approval"]["can_request"] and fresh["offer"]["fingerprint"] != pending["offer"]["fingerprint"])
        pending = request_approval(fresh)
        reason = "QA: revise this exact basket"
        declined = decide(pending, "reject", reason=reason)
        checked("Exact decline records reason and blocks confirmation", declined["rejection"]["reason"] == reason and not declined["can_confirm"])
        refreshed = data("GET", CARTS + "/" + decision["id"])
        checked("Buyer read-only status refresh sees the decline", refreshed["version"] == declined["version"] and refreshed["rejection"]["reason"] == reason and not refreshed["can_confirm"])
        revised = action(refreshed, "set_quantity", line_id=refreshed["lines"][0]["id"], quantity=str(needed+2), unit="packages")
        revised = request_approval(revised)
        approved = decide(revised)
        checked("Independent manager approves only the fresh submitted revision", approved["approval"]["approved"] and approved["offer"]["approved"] and approved["offer"]["fingerprint"] == revised["offer"]["fingerprint"])
        resumed = data("GET", CARTS + "/" + revised["id"])
        checked("Buyer status sees exact approval without spending", resumed["approval"]["approved"] and resumed["can_confirm"] and resumed["receipt"] is None)
        cancelled = data("POST", CARTS + "/" + resumed["id"] + "/cancel", json={"version": resumed["version"], "reason": "QA complete; no order intended"})
        checked("High-value QA basket is cancelled without any confirmation", cancelled["review_state"] == "CANCELLED" and not cancelled["can_confirm"])
        call("POST", CARTS + "/" + cancelled["id"] + "/actions", expected=409, json={"version": cancelled["version"], "action": "quote"})
        checked("A cancelled draft cannot resume using stale editing actions", True)

        budget_units = (D(36) / price).to_integral_value(rounding=ROUND_CEILING) + 1
        budget_cart = create(cases[0], str(budget_units), "packages")
        total = D(budget_cart["cart"]["subtotal"])
        original_budget = format(total - 36, ".2f")
        budget_cart = action(budget_cart, "set_budget", budget=original_budget)
        checked("Requested budget can expose a precise EUR36 exception without authority", budget_cart["approval"]["can_request"] and "requested_budget" in budget_cart["approval"]["reasons"] and budget_cart["budget_exception"]["excess"] == "36.00" and not budget_cart["can_confirm"])
        budget_pending = request_approval(budget_cart, "QA: exact EUR36 budget exception")
        queue = data("GET", "/approvals", manager=True, params={"limit": 100})
        checked("Budget excess and buyer explanation persist in the eligible queue", any(entry["id"] == budget_pending["id"] and entry["requested_budget"] == original_budget and entry["budget_excess"] == "36.00" and entry["explanation"] == "QA: exact EUR36 budget exception" for entry in queue["items"]))
        budget_approved = decide(budget_pending)
        checked("Exact exception approval preserves original budget and future authority", budget_approved["can_confirm"] and budget_approved["budget_exception"]["status"] == "approved" and budget_approved["constraints"]["budget"] == original_budget and budget_approved["approval"]["threshold"] == before["mandate"]["autonomous_limit"] and data("GET", "/workspace")["mandate"] == before["mandate"])
        data("POST", CARTS + "/" + budget_approved["id"] + "/cancel", json={"version": budget_approved["version"], "reason": "QA exception checked; do not order"})

        expected_spent = before_spent
        if commit_demo:
            small = create(cases[0], "1", "packages")
            subtotal = D(small["cart"]["subtotal"])
            checked("Optional confirmation is one eligible basket below EUR100", D(0) < subtotal < 100 and small["can_confirm"] and small["approval"]["status"] == "not_required")
            confirmed = data("POST", CARTS + "/" + small["id"] + "/confirm", headers={"Idempotency-Key": "role-demo-" + uuid.uuid4().hex}, json=exact(small))
            report["orders_created"] = 1
            expected_spent += subtotal
            checked("Optional receipt is explicitly simulated and below EUR100", confirmed["receipt"]["simulated"] and D(confirmed["receipt"]["total"]) == subtotal)
        checked("Only explicitly authorized small simulation can affect demo spend", D(data("GET", "/workspace")["mandate"]["spent"]) == expected_spent)
        checked("Saved preferences were not changed", data("GET", "/preferences") == prefs)
        report.update(status="passed", source_categories=[case["category"] for case in cases], synthetic_spend_before=str(before_spent), synthetic_spend_after=str(expected_spent))
    except Exception as exc:
        report.update(status="failed", failure={"type": type(exc).__name__, "message": str(exc)[:250]})
    finally:
        cleanup_errors = []
        try:
            if owned_carts:
                if identity.get("role") != "buyer": enter("buyer")
                for session_id in owned_carts:
                    current = data("GET", CARTS + "/" + session_id)
                    if not current.get("receipt") and not current.get("cancelled"):
                        data("POST", CARTS + "/" + session_id + "/cancel", json={"version": current["version"], "reason": "QA cleanup: retain purchasing evidence"})
                    data("DELETE", "/history/" + session_id)
                    data("GET", CARTS + "/" + session_id)
                checked("Only this run's personal QA entries are hidden; purchasing records remain", True)
            for use_manager in [False, True]:
                if (manager_identity if use_manager else identity).get("role"):
                    data("DELETE", "/session", manager=use_manager)
                    call("GET", "/workspace", expected=401, manager=use_manager)
            checked("Both independent sessions are logged out and revoked", True)
        except Exception as exc:
            cleanup_errors.append(type(exc).__name__)
        if cleanup_errors:
            report["cleanup_errors"] = cleanup_errors
            report["status"] = "failed"
        if own_manager: manager_client.close()
    report["owned_request_count"] = len(owned_carts)
    report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    if save: save(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--cases", type=Path, default=ROOT / ".local/role-demo-cases.json")
    parser.add_argument("--report", type=Path, default=ROOT / ".local/role-demo-smoke-report.json")
    parser.add_argument("--commit-demo", action="store_true", help="Permit exactly one eligible simulated order below EUR100")
    args = parser.parse_args()
    case_file = json.loads(args.cases.read_text()) if args.cases.exists() else prepare_cases(args.cases)
    def save(report):
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)); args.report.chmod(0o600)
    import httpx
    with httpx.Client(base_url=args.url.rstrip("/"), timeout=60) as client, httpx.Client(base_url=args.url.rstrip("/"), timeout=60) as manager:
        report = run_smoke(client, case_file, manager_client=manager, commit_demo=args.commit_demo, save=save)
    print(json.dumps({key: report.get(key) for key in ["status", "check_count", "elapsed_seconds", "orders_created", "failure", "cleanup_errors"]}, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
