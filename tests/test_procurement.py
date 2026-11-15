"""End-to-end basket authority and persistent state with authored commercial data."""

import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pytest
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from backend import interpretation, procurement
from backend.config import BUYER, CUSTOMER, MANDATE
from backend.store import Store

REAL_INTERPRET = interpretation.interpret


@pytest.fixture
def env(tmp_path, monkeypatch):
    products = {
        "pasta": {"id": "pasta", "name": "Authored spaghetti", "sales_unit": "BAG", "kg_per_sales_unit": "5", "liters_per_sales_unit": None, "pieces_per_sales_unit": "1", "allowed_lot_size": "1", "claims": ["VEGAN", "FREE_FROM_GLUTEN"], "origin_codes": ["246"], "deleted": False, "variable_unit": False, "deposits": []},
        "milk": {"id": "milk", "name": "Authored milk", "sales_unit": "KI", "kg_per_sales_unit": None, "liters_per_sales_unit": "12", "pieces_per_sales_unit": "12", "allowed_lot_size": "1", "claims": ["FREE_FROM_LACTOSE"], "origin_codes": ["246"], "deleted": False, "variable_unit": False, "deposits": []},
    }
    def search(query, limit=4, dietary=None, origin=None, **criteria):
        return [copy.deepcopy(p) for p in products.values() if query.casefold() in p["name"].casefold() or query in [p["id"], "all"]]
    monkeypatch.setattr(procurement.catalog, "load_catalog", lambda: products)
    monkeypatch.setattr(procurement.product_facts, "search", search)
    monkeypatch.setattr(procurement.product_facts, "normalize", lambda pid: copy.deepcopy(products[pid]))

    tomorrow = str(date.today() + timedelta(days=2))
    request = {"items": [{"query": "pasta", "quantity": "6", "unit": "kg", "dietary": []}], "budget": None, "delivery_date": tomorrow, "preference": "cheapest", "notes": [], "ambiguous_fields": []}
    def interpret(text, prior=None, use_model=False):
        if text == "keep" and prior:
            return copy.deepcopy(prior) | {"notes": [], "ambiguous_fields": []}
        return copy.deepcopy(request)
    monkeypatch.setattr(interpretation, "interpret", interpret)
    store = Store(tmp_path / "cart.sqlite", postgres=False)
    store.migrate_workspace_authority()
    app = FastAPI()
    def identity(x_role: str = Header(default="buyer")):
        if x_role not in ["buyer", "approver"]:
            raise HTTPException(401)
        return {"role": x_role, "name": "Authored " + x_role, "buyer_id": BUYER, "customer_id": CUSTOMER, "actor_id": "authored-actor-" + x_role, "principal_id": "access_code:" + x_role}
    def buyer(s=Depends(identity)):
        if s["role"] != "buyer":
            raise HTTPException(403)
        return s
    def approver(s=Depends(identity)):
        if s["role"] != "approver":
            raise HTTPException(403)
        return s
    procurement.register_routes(app, store, buyer, approver, identity, lambda *args: None)
    return TestClient(app), store, request, products, app


def create(env, **changes):
    c = env[0]
    r = c.post(procurement.PREFIX, json={"message": "start", **changes})
    assert r.status_code == 200, r.text
    result = r.json()
    if result["approval"].get("can_request") and result["approval"]["reasons"] == ["spending_authority"]:
        requested = c.post(procurement.PREFIX + "/" + result["id"] + "/request-approval", json={"version": result["version"], "fingerprint": result["offer"]["fingerprint"]})
        assert requested.status_code == 200, requested.text
        result = requested.json()
    return result


def act(env, session, action, **changes):
    return env[0].post(procurement.PREFIX + "/" + session["id"] + "/actions", json={"version": session["version"], "action": action, **changes})


def confirm(env, session, key="basket-order-key-1"):
    return env[0].post(procurement.PREFIX + "/" + session["id"] + "/confirm", json={"fingerprint": session["offer"]["fingerprint"]}, headers={"Idempotency-Key": key})


def test_complete_cart_confirmation_and_retry(env):
    s = create(env)
    assert s["order_status"] == "READY_TO_ORDER" and s["can_confirm"]
    assert s["cart"]["items"][0]["quantity_sales_units"] == "2"
    assert s["cart"]["total"] is None and s["cart"]["unknown_charges"]
    assert "product" not in s["lines"][0]["candidates"][0]
    first = confirm(env, s)
    assert first.status_code == 200, first.text
    receipt = first.json()["receipt"]
    assert receipt["simulated"] and receipt["items"][0]["id"] == "pasta"
    spend = env[1].spent()
    again = confirm(env, s)
    assert again.status_code == 200 and again.json()["receipt"]["id"] == receipt["id"]
    assert again.json()["receipt"]["idempotent_replay"] and env[1].spent() == spend
    verification = env[0].get(procurement.PREFIX + "/" + s["id"] + "/verify")
    assert verification.status_code == 200
    assert verification.json()["integrity_valid"] and verification.json()["scope_valid"]
    assert env[1].spent() == spend


def test_expired_saved_quote_is_not_reported_ready_and_refresh_recovers(env, monkeypatch):
    session = create(env)
    expiry = procurement.policy.parse_time(session["offer"]["expires_at"])
    with monkeypatch.context() as context:
        context.setattr(procurement.policy, "now", lambda: expiry + timedelta(seconds=1))
        response = env[0].get(procurement.PREFIX + "/" + session["id"])
        assert response.status_code == 200
        assert response.json()["order_status"] == "NEEDS_CLARIFICATION"
        assert not response.json()["can_confirm"]
        assert "expired" in response.json()["assistant_message"]
        assert response.json()["version"] == session["version"]
    refreshed = act(env, session, "quote")
    assert refreshed.status_code == 200 and refreshed.json()["can_confirm"]


def test_consolidation_before_pack_rounding_and_stock_allocation(env):
    env[2]["items"] = [{"query": "pasta", "quantity": "3", "unit": "kg", "dietary": []}, {"query": "spaghetti", "quantity": "2", "unit": "kg", "dietary": []}]
    s = create(env)
    assert len(s["lines"]) == 2 and len(s["cart"]["items"]) == 1
    assert s["cart"]["items"][0]["quantity_sales_units"] == "1"
    assert len(s["cart"]["items"][0]["line_ids"]) == 2


def test_requested_budget_blocks_direct_confirmation_and_edit_preserves_selection(env):
    s = create(env, budget="0.01")
    assert not s["can_confirm"] and s["offer"] and s["approval"]["can_request"]
    assert any("requested budget" in q["prompt"] for q in s["clarification_questions"])
    resolution = next(o for q in s["clarification_questions"] for o in q["options"] if o["action"] == "set_budget")
    assert resolution["payload"]["budget"] == s["cart"]["subtotal"]
    fixed = act(env, s, resolution["action"], **resolution["payload"])
    assert fixed.status_code == 200, fixed.text
    fixed = fixed.json()
    assert fixed["can_confirm"]
    assert fixed["lines"][0]["selected_product_id"] == s["lines"][0]["selected_product_id"]


def test_multi_turn_persistence_and_optimistic_conflict(env):
    env[2]["items"].append({"query": "milk", "quantity": "13", "unit": "L", "dietary": ["lactose_free"]})
    s = create(env)
    first_fp = s["offer"]["fingerprint"]
    update = act(env, s, "set_quantity", line_id=s["lines"][0]["id"], quantity="21")
    assert update.status_code == 200, update.text
    new = update.json()
    assert new["lines"][1]["selected_product_id"] == "milk"
    assert new["offer"]["fingerprint"] != first_fp
    assert act(env, s, "remove_line", line_id=s["lines"][0]["id"]).status_code == 409
    got = env[0].get(procurement.PREFIX + "/" + s["id"]).json()
    assert got["version"] == new["version"] and got["lines"][0]["quantity"] == "21"


def test_exact_separate_approval_and_changed_offer_invalidation(env, monkeypatch):
    monkeypatch.setitem(MANDATE, "autonomous_limit", "1.00")
    s = create(env)
    assert s["approval"]["status"] == "required" and not s["can_confirm"]
    path = procurement.PREFIX + "/" + s["id"] + "/approve"
    assert env[0].post(path, json={"fingerprint": s["offer"]["fingerprint"]}).status_code == 403
    assert env[0].post(path, json={"fingerprint": "a" * 64}, headers={"X-Role": "approver"}).status_code == 409
    result = env[0].post(path, json={"fingerprint": s["offer"]["fingerprint"]}, headers={"X-Role": "approver"})
    assert result.status_code == 200, result.text
    approved = result.json()
    assert approved["can_confirm"]
    changed = act(env, approved, "set_quantity", line_id=s["lines"][0]["id"], quantity="30").json()
    assert not changed["can_confirm"] and not changed["offer"]["approved"]
    assert confirm(env, approved).status_code == 409


def test_unknown_diet_and_unsupported_pack_remain_blocked(env):
    env[2]["items"][0]["dietary"] = ["lactose_free"]
    s = create(env)
    assert not s["can_confirm"] and s["offer"] is None
    assert any("lactose free" in issue for issue in s["lines"][0]["candidates"][0]["issues"])
    env[2]["items"][0]["dietary"] = []
    env[3]["pasta"]["kg_per_sales_unit"] = None
    s = create(env)
    assert not s["can_confirm"] and s["cart"]["subtotal"] == "0.00"


def test_stock_revalidated_before_confirmation(env, monkeypatch):
    s = create(env)
    real = procurement.fixture_lookup
    def shortage(*args):
        result = real(*args)
        for row in result["availability"]["products"]:
            row["scheduleLines"][0]["availableAmount"] = 0
        return result
    monkeypatch.setattr(procurement, "fixture_lookup", shortage)
    response = confirm(env, s)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "revalidation_failed"
    assert env[1].spent() == 0


def test_total_stock_checked_after_consolidation(env, monkeypatch):
    env[2]["items"] = [{"query": "pasta", "quantity": "4", "unit": "kg", "dietary": []}, {"query": "spaghetti", "quantity": "4", "unit": "kg", "dietary": []}]
    real = procurement.fixture_lookup
    def one_pack(*args):
        result = real(*args)
        result["availability"]["products"][0]["scheduleLines"][0]["availableAmount"] = 1
        return result
    monkeypatch.setattr(procurement, "fixture_lookup", one_pack)
    s = create(env)
    assert not s["can_confirm"] and s["cart"]["items"][0]["quantity_sales_units"] == "2"
    assert s["cart"]["items"][0]["issues"]


def test_recipe_acknowledgement_and_ambiguity_are_required(env):
    env[2]["notes"] = ["Illustrative recipe; chef reviews the quantities."]
    s = create(env)
    assert s["recipe_review_required"] and not s["can_confirm"]
    approved = act(env, s, "acknowledge_recipe").json()
    assert approved["can_confirm"] and not approved["recipe_review_required"]
    env[2]["ambiguous_fields"] = ["Please clarify dietary overlap."]
    s = create(env)
    assert not s["can_confirm"] and any("overlap" in q["prompt"] for q in s["clarification_questions"])


def test_competing_edits_allow_one_version(env):
    s = create(env)
    def edit(qty):
        return act(env, s, "set_quantity", line_id=s["lines"][0]["id"], quantity=qty).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(edit, ["12", "18"]))
    assert sorted(statuses) == [200, 409]


def test_per_requested_unit_limit_and_changed_lot_revalidation(env):
    # A 5kg sales pack may cost more than €3 while its per-kg price stays below €3.
    env[2]["items"][0]["max_unit_price"] = "3"
    s = create(env)
    assert s["can_confirm"]
    env[3]["pasta"]["allowed_lot_size"] = "3"
    response = confirm(env, s)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "catalog_changed"
    assert env[1].spent() == 0


def test_unknown_terminal_quantity_never_confirms(env, monkeypatch):
    real = procurement.fixture_lookup
    def unknown(*args):
        result = real(*args)
        for row in result["availability"]["products"]:
            row["logisticModel"] = "Terminal"
            row["scheduleLines"][0]["availableAmount"] = 999999
        return result
    monkeypatch.setattr(procurement, "fixture_lookup", unknown)
    s = create(env)
    assert not s["can_confirm"] and s["order_status"] == "CANNOT_FULFILL"
    assert s["lines"][0]["candidates"][0]["availability"] == "unknown"


def test_malformed_commercial_records_are_blocked_without_zero_price(env, monkeypatch):
    real = procurement.fixture_lookup
    def malformed(*args):
        result = real(*args)
        result["price"]["products"] = [None, {"productId": "pasta", "catalogPrice": "invalid", "tax": []}]
        result["availability"]["products"][0]["scheduleLines"] = ["invalid", None]
        return result
    monkeypatch.setattr(procurement, "fixture_lookup", malformed)
    s = create(env)
    assert not s["can_confirm"] and s["lines"][0]["candidates"][0]["unit_price"] is None


def test_rational_cohort_aggregation_cannot_add_an_unneeded_pack(env):
    env[3]["pasta"]["kg_per_sales_unit"] = "7"
    env[2]["items"] = [{"query": "pasta", "quantity": "1", "unit": "kg", "dietary": []} for _ in range(7)]
    s = create(env)
    assert s["cart"]["items"][0]["quantity_sales_units"] == "1"
    assert s["cart"]["items"][0]["quantity_breakdown"][0]["surplus_quantity"] == "0"


def test_cheaper_followup_replaces_only_focused_choice_and_budget_keeps_it(env, monkeypatch):
    env[3]["milk2"] = copy.deepcopy(env[3]["milk"]) | {"id": "milk2", "name": "Authored milk alternative"}
    env[2]["items"].append({"query": "milk", "quantity": "20", "unit": "L", "dietary": ["lactose_free"]})
    s = create(env)
    milk = s["lines"][1]
    assert len(milk["candidates"]) == 2
    cheapest = min(milk["candidates"], key=lambda c: float(c["line_total"]))
    expensive = max(milk["candidates"], key=lambda c: float(c["line_total"]))
    assert cheapest["id"] != expensive["id"]
    s = act(env, s, "select_product", line_id=milk["id"], product_id=expensive["id"]).json()
    pasta_selection = s["lines"][0]["selected_product_id"]
    def followup(text, prior=None, use_model=False):
        return copy.deepcopy(prior) | {"preference": "cheapest", "budget": "1000" if "budget" in text else prior["budget"]}
    monkeypatch.setattr(interpretation, "interpret", followup)
    cheaper = act(env, s, "message", message="Choose cheaper milk").json()
    assert cheaper["lines"][1]["selected_product_id"] == cheapest["id"]
    assert cheaper["lines"][0]["selected_product_id"] == pasta_selection
    costly = act(env, cheaper, "select_product", line_id=milk["id"], product_id=expensive["id"]).json()
    budget_only = act(env, costly, "message", message="My budget is €1000").json()
    assert budget_only["lines"][1]["selected_product_id"] == expensive["id"]
    focused = act(env, budget_only, "message", message="The cheaper one").json()
    assert focused["lines"][1]["selected_product_id"] == cheapest["id"]
    assert focused["lines"][0]["selected_product_id"] == pasta_selection


def saved_meal_plan(env):
    env[3]["beef"] = copy.deepcopy(env[3]["pasta"]) | {"id": "beef", "name": "Authored minced beef", "claims": ["FREE_FROM_GLUTEN"], "origin_codes": ["246"]}
    plan = {
        "id": "meal-saved-kitchen", "buyer_id": BUYER, "customer_id": CUSTOMER,
        "dish": "Spaghetti bolognese / lentil bolognese",
        "request": {"servings": 20, "vegetarian": 5, "gluten_free": 10, "vegetarian_gluten_free": 2, "recipe_source": "customer", "recipe": {"pasta_g": "250"}, "priority": "balanced"},
        "cohorts": {"meat_standard": 7, "meat_gluten_free": 8, "vegetarian_standard": 3, "vegetarian_gluten_free": 2},
        "recipe_note": "Customer-entered recipe quantities; chef validates separate preparation.",
        "lines": [
            {"ingredient": "Dry spaghetti · standard", "search_query": "pasta", "required_kg": "3", "servings": 12, "grams_per_serving": "250", "gluten_free_required": False, "meat_origin": "any", "candidates": [{"product_id": "pasta"}]},
            {"ingredient": "Dry spaghetti · gluten-free", "search_query": "pasta", "required_kg": "2", "servings": 8, "grams_per_serving": "250", "gluten_free_required": True, "meat_origin": "any", "candidates": [{"product_id": "pasta"}]},
            {"ingredient": "Raw minced beef · gluten-free", "search_query": "beef", "required_kg": "2", "servings": 8, "grams_per_serving": "250", "gluten_free_required": True, "meat_origin": "finland", "candidates": [{"product_id": "beef"}]},
        ],
    }
    env[1].save("meal_plan", plan["id"], BUYER, plan)
    return plan


def test_saved_meal_plan_bridge_preserves_exact_recipe_choices_and_constraints(env):
    plan = saved_meal_plan(env)
    body = {"plan_id": plan["id"], "selections": {"0": "pasta", "1": "pasta", "2": "beef"}, "mode": "fixture", "date": str(date.today() + timedelta(days=2))}
    result = env[0].post(procurement.PREFIX + "/from-meal-plan", json=body)
    assert result.status_code == 200, result.text
    s = result.json()
    assert s["recipe_review_required"] and not s["can_confirm"] and s["offer"] is None
    assert s["source_meal_plan"]["cohorts"] == plan["cohorts"]
    assert s["source_meal_plan"]["request"]["recipe"] == {"pasta_g": "250"}
    assert [line["selected_product_id"] for line in s["lines"]] == ["pasta", "pasta", "beef"]
    assert [line["quantity"] for line in s["lines"]] == ["3", "2", "2"]
    assert s["lines"][1]["dietary"] == ["gluten_free", "vegetarian"]
    assert s["lines"][2]["dietary"] == ["gluten_free"] and s["lines"][2]["origin"] == "finland"
    pasta = next(item for item in s["cart"]["items"] if item["id"] == "pasta")
    assert pasta["quantity_sales_units"] == "1"  # shared SKU is rounded once
    reviewed = act(env, s, "acknowledge_recipe").json()
    assert reviewed["can_confirm"]
    assert env[1].spent() == 0


def test_meal_bridge_selection_and_scope_cannot_be_forged(env):
    plan = saved_meal_plan(env)
    path = procurement.PREFIX + "/from-meal-plan"
    for selections in [{"0": "milk"}, {"99": "pasta"}, {"-1": "pasta"}]:
        result = env[0].post(path, json={"plan_id": plan["id"], "selections": selections})
        assert result.status_code == 422, result.text
    assert env[0].post(path, json={"plan_id": "not-owned"}).status_code == 404
    assert env[0].post(path, json={"plan_id": plan["id"]}, headers={"X-Role": "approver"}).status_code == 403
    assert env[1].spent() == 0


def test_change_search_preserves_hard_requirements_and_unaffected_cart(env):
    env[2]["items"] = [{"query": "pasta", "quantity": "6", "unit": "kg", "dietary": ["gluten_free"], "origin": "finland"}, {"query": "milk", "quantity": "20", "unit": "L", "dietary": []}]
    s = create(env)
    original = s["lines"][0]
    other_selection = s["lines"][1]["selected_product_id"]
    changed = act(env, s, "set_query", line_id=original["id"], query="milk")
    assert changed.status_code == 200, changed.text
    new = changed.json()
    assert new["lines"][0]["requested_label"] == "milk"
    assert new["lines"][0]["dietary"] == ["gluten_free"] and new["lines"][0]["origin"] == "finland"
    assert new["lines"][0]["quantity"] == original["quantity"] and new["lines"][0]["unit"] == "kg"
    assert new["lines"][0]["selected_product_id"] is None
    assert new["lines"][1]["selected_product_id"] == other_selection
    assert not new["can_confirm"]
    assert act(env, new, "set_query", line_id=original["id"], query=" ").status_code == 422


def test_actual_meal_planner_api_bridges_saved_custom_grams(tmp_path, monkeypatch):
    from backend.app import create_app
    from backend.config import access_codes
    raw = {"pasta-api": {"id": "pasta-api", "baseUnit": "ST", "salesUnit": "BAG", "allowedLotSize": 1, "units": [{"unitId": "BAG", "sizeInBaseUnits": 1}], "synkkaData": {"names": [{"language": "en", "value": "Spaghetti"}], "classifications": [{"name": "nutritionalClaim", "values": [{"id": "FREE_FROM_GLUTEN"}, {"id": "VEGETARIAN"}]}], "unitConversions": [{"synkkaPackagingType": "BASE_UNIT_OR_EACH", "netWeight": {"unit": "KGM", "value": 3}}]}}}
    monkeypatch.setattr(procurement.catalog, "load_catalog", lambda: raw)
    store = Store(tmp_path / "planner-bridge.sqlite", postgres=False)
    c = TestClient(create_app(store))
    assert c.post("/api/v1/session", json={"access_code": access_codes()["buyer"]}).status_code == 200
    plan = c.post("/api/v1/meal-plans", json={"recipe_source": "customer", "recipe": {"pasta_g": "125"}})
    assert plan.status_code == 200, plan.text
    plan = plan.json()
    assert plan["lines"][0]["required_kg"] == "56.25"
    bridge = c.post(procurement.PREFIX + "/from-meal-plan", json={"plan_id": plan["id"], "selections": {"0": "pasta-api"}, "date": str(date.today() + timedelta(days=2))})
    assert bridge.status_code == 200, bridge.text
    result = bridge.json()
    assert result["lines"][0]["quantity"] == "56.25"
    assert result["lines"][0]["meal_plan_line"]["grams_per_serving"] == "125"
    assert result["lines"][0]["selected_product_id"] == "pasta-api"
    assert result["source_meal_plan"]["cohorts"] == plan["cohorts"]
    assert result["recipe_review_required"] and not result["can_confirm"]
    assert store.spent() == 0


def test_quote_checks_available_fifth_product_before_claiming_cannot_fulfill(env, monkeypatch):
    for i in range(5):
        env[3][f"milk{i}"] = copy.deepcopy(env[3]["milk"]) | {"id": f"milk{i}", "name": f"Authored milk {i}"}
    env[2]["items"] = [{"query": "milk", "quantity": "20", "unit": "L", "dietary": ["lactose_free"]}]
    looked_up = []
    real = procurement.fixture_lookup
    def stock(*args):
        looked_up.extend(args[2])
        evidence = real(*args)
        for row in evidence["availability"]["products"]:
            row["scheduleLines"][0]["availableAmount"] = 100 if row["productId"] == "milk4" else 0
        return evidence
    monkeypatch.setattr(procurement, "fixture_lookup", stock)
    s = create(env)
    assert "milk4" in looked_up and s["order_status"] == "READY_TO_ORDER"
    assert s["lines"][0]["selected_product_id"] == "milk4"
    assert len(s["lines"][0]["candidates"]) == 6


def test_semantic_replacement_requires_explicit_selection_even_when_cheapest(env):
    env[2]["items"] = [{"query": "milk alternative", "retrieval_queries": ["milk"], "quantity": "20", "unit": "L", "dietary": ["lactose_free"]}]
    s = create(env)
    assert s["lines"][0]["selected_product_id"] is None and not s["can_confirm"]
    c = s["lines"][0]["candidates"][0]
    assert c["match_method"] == "semantic_expansion" and c["requires_explicit_choice"]
    chosen = act(env, s, "select_product", line_id=s["lines"][0]["id"], product_id=c["id"]).json()
    assert chosen["can_confirm"] and not chosen["lines"][0]["candidates"][0]["requires_explicit_choice"]


def test_brand_organic_hard_rules_and_soft_preference_ranking(env):
    env[3]["milk"]["brand"] = "Arla"
    env[3]["milk"]["origin_codes"] = ["752"]
    env[3]["milk2"] = copy.deepcopy(env[3]["milk"]) | {"id": "milk2", "name": "Authored milk alternative", "brand": "Valio", "origin_codes": ["246"], "organic": True, "organic_evidence": ["EU_ORGANIC_FARMING"]}
    env[2].update(preference="balanced", items=[{"query": "milk", "quantity": "20", "unit": "L", "dietary": ["lactose_free"], "preferred_brand": "Valio", "preferred_origin": "finland", "preferred_organic": True}])
    s = create(env)
    assert s["lines"][0]["selected_product_id"] == "milk2"
    assert s["lines"][0]["preferred_brand"] == "Valio" and s["can_confirm"]
    env[2]["items"][0].update(required_brand="Valio", require_organic=True)
    hard = create(env)
    assert hard["lines"][0]["selected_product_id"] == "milk2"
    rejected = next(c for c in hard["lines"][0]["candidates"] if c["id"] == "milk")
    assert "BRAND_CONFLICT" in rejected["issue_codes"] and "ORGANIC_EVIDENCE_UNKNOWN" in rejected["issue_codes"]
    env[3]["milk2"]["brand"] = "Changed brand"
    assert confirm(env, hard).status_code == 409
    assert env[1].spent() == 0


def test_quality_keeps_product_choice_manual_and_stock_has_precise_codes(env, monkeypatch):
    env[2]["preference"] = "quality"
    s = create(env)
    assert s["lines"][0]["selected_product_id"] is None and not s["can_confirm"]
    assert s["lines"][0]["candidates"][0]["comparison_delta"] is None
    real = procurement.fixture_lookup
    def zero(*args):
        evidence = real(*args)
        for row in evidence["availability"]["products"]:
            row["scheduleLines"][0]["availableAmount"] = 0
        return evidence
    monkeypatch.setattr(procurement, "fixture_lookup", zero)
    s = create(env)
    assert s["lines"][0]["status"] == "OUT_OF_STOCK"
    assert "INSUFFICIENT_STOCK" in s["lines"][0]["issue_codes"]
    assert "CONSTRAINT_CONFLICT" in s["lines"][0]["classifications"]


def test_comparison_delta_recomputes_shared_sku_pack_cost_not_naive_line_difference(env, monkeypatch):
    env[3]["pasta2"] = copy.deepcopy(env[3]["pasta"]) | {"id": "pasta2", "name": "Authored spaghetti pasta alternative"}
    env[2]["items"] = [{"query": "pasta", "quantity": "3", "unit": "kg", "dietary": []}, {"query": "spaghetti", "quantity": "2", "unit": "kg", "dietary": []}]
    real = procurement.fixture_lookup
    def prices(*args):
        evidence = real(*args)
        for row in evidence["price"]["products"]:
            row["catalogPrice"]["valueWithTax"] = 10 if row["productId"] == "pasta" else 6
        return evidence
    monkeypatch.setattr(procurement, "fixture_lookup", prices)
    s = create(env)
    for line in s["lines"]:
        s = act(env, s, "select_product", line_id=line["id"], product_id="pasta").json()
    assert s["cart"]["subtotal"] == "10.00"
    alternative = next(c for c in s["lines"][0]["candidates"] if c["id"] == "pasta2")
    assert alternative["line_total"] == "6.00" and alternative["comparison_delta"] == "6.00"
    assert alternative["price_per_requested_unit"] == "1.2"
    assert alternative["product_details"]["name"] == "Authored spaghetti pasta alternative"
    assert "commercial" not in alternative and "product" not in alternative


def test_real_parser_cheaper_product_followup_preserves_other_line(env, monkeypatch):
    monkeypatch.setattr(interpretation, "interpret", REAL_INTERPRET)
    env[3]["milk2"] = copy.deepcopy(env[3]["milk"]) | {"id": "milk2", "name": "Authored milk alternative"}
    result = env[0].post(procurement.PREFIX, json={"message": "6 kg of pasta and 20 litres of lactose-free milk by Monday", "mode": "fixture", "use_model": False})
    assert result.status_code == 200, result.text
    s = result.json()
    milk = next(line for line in s["lines"] if line["requested_label"] == "milk")
    pasta = next(line for line in s["lines"] if line["requested_label"] == "pasta")
    costly = max(milk["candidates"], key=lambda c: float(c["line_total"]))
    cheaper = min(milk["candidates"], key=lambda c: float(c["line_total"]))
    s = act(env, s, "select_product", line_id=milk["id"], product_id=costly["id"]).json()
    changed = act(env, s, "message", message="Choose cheaper milk")
    assert changed.status_code == 200, changed.text
    changed = changed.json()
    assert next(line for line in changed["lines"] if line["id"] == milk["id"])["selected_product_id"] == cheaper["id"]
    assert next(line for line in changed["lines"] if line["id"] == pasta["id"])["selected_product_id"] == pasta["selected_product_id"]


def test_delivery_conflict_offers_explicit_date_action_then_revalidates(env, monkeypatch):
    later = str(date.today() + timedelta(days=3))
    real = procurement.fixture_lookup
    def delayed(*args):
        evidence = real(*args)
        for row in evidence["availability"]["products"]:
            row["scheduleLines"][0]["availableDate"] = later
        return evidence
    monkeypatch.setattr(procurement, "fixture_lookup", delayed)
    s = create(env)
    assert s["lines"][0]["status"] == "CONSTRAINT_CONFLICT"
    assert "DELIVERY_CONFLICT" in s["lines"][0]["issue_codes"]
    assert s["constraints"]["delivery_date"] != later
    option = next(o for q in s["clarification_questions"] for o in q["options"] if o["action"] == "set_date")
    assert option["payload"] == {"date": later}
    resolved = act(env, s, option["action"], **option["payload"])
    assert resolved.status_code == 200, resolved.text
    resolved = resolved.json()
    assert resolved["constraints"]["delivery_date"] == later and resolved["can_confirm"]
    assert env[1].spent() == 0
