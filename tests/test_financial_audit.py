"""Independent screenshot arithmetic and budget-versus-authority regressions.

The screenshot used authored fixture pricing, not a current supplier contract.
No provider, model, confirmation or shared-ledger mutation is permitted here.
"""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import pytest
from fastapi.testclient import TestClient

from backend import catalog, interpretation, procurement, upstream
from backend.app import create_app
from backend.config import MANDATE, ROOT
from backend.store import Store

D = Decimal
PREFIX = procurement.PREFIX


@pytest.fixture
def audit(tmp_path, monkeypatch):
    if not (ROOT / "data/raw/valio_aimo_junction26_product_data.json").exists():
        pytest.skip("Original private challenge catalog is not installed")
    def forbidden(*args, **kwargs):
        raise AssertionError("Financial regression must not call supplier/model services")
    monkeypatch.setattr(upstream, "sponsor_lookup", forbidden)
    monkeypatch.setattr(upstream, "rank_with_nvidia", forbidden)
    monkeypatch.setattr(interpretation, "_model", forbidden)
    monkeypatch.setenv("AIMO_DEMO_MODE", "true")
    store = Store(tmp_path / "financial-audit.sqlite3", postgres=False)
    limits = deepcopy(MANDATE)
    with TestClient(create_app(store)) as client:
        login = client.post("/api/v1/auth/demo", json={"role": "buyer"})
        assert login.status_code == 200
        scope = login.json()
        yield client, store, scope
    assert store.spent(scope["buyer_id"]) == 0
    assert MANDATE == limits, "Customer budget must not rewrite purchasing authority"


def raw_product(name):
    matches = [(pid, raw) for pid, raw in catalog.load_catalog().items()
               if any(n.get("language") == "en" and n.get("value") == name
                      for n in raw.get("synkkaData", {}).get("names", []))]
    assert len(matches) == 1
    return matches[0]


def physical_capacity(raw, field, unit, scale):
    ratios = {D(str(row["sizeInBaseUnits"])) for row in raw["units"]
              if row["unitId"] == raw["salesUnit"]}
    amounts = {D(str(row[field]["value"])) * scale
               for row in raw["synkkaData"]["unitConversions"]
               if row["synkkaPackagingType"] == "BASE_UNIT_OR_EACH"
               and row.get(field, {}).get("unit") == unit}
    assert len(ratios) == len(amounts) == 1
    return ratios.pop() * amounts.pop()


def create(client, pid, quantity, unit, budget="101000.00"):
    response = client.post(PREFIX + "/from-product", json={
        "product_id": pid, "quantity": quantity, "unit": unit,
        "date": str(date.today() + timedelta(days=2)), "budget": budget,
        "mode": "fixture", "apply_preferences": False})
    assert response.status_code == 200, response.text
    return response.json()


def prompts(session):
    return [q["prompt"] for q in session["clarification_questions"]]


def test_screenshot_two_products_use_verified_sales_capacity_and_fixture_totals(audit):
    client, _, _ = audit
    butter, raw_butter = raw_product("Valio butter 500 g unsalted")
    milk, raw_milk = raw_product("Valio whole milk 1 l lactose free UHT")
    # The oracle reads consumer net mass/volume and the actual sales/base ratio,
    # independently of the application's normalization and quantity helpers.
    assert physical_capacity(raw_butter, "netWeight", "GRM", D(".001")) == D(".5")
    assert physical_capacity(raw_milk, "volume", "LTR", D(1)) == 1
    assert raw_butter["salesUnit"] == raw_milk["salesUnit"] == "ST"
    session = create(client, butter, "200", "kg")
    response = client.post(PREFIX + "/" + session["id"] + "/actions", json={
        "version": session["version"], "action": "add_product",
        "product_id": milk, "quantity": "300", "unit": "L"})
    assert response.status_code == 200, response.text
    session = response.json()
    items = {row["id"]: row for row in session["cart"]["items"]}
    for pid, units, price, total in [(butter, "400", "8.91", "3564.00"),
                                     (milk, "300", "3.87", "1161.00")]:
        assert D(items[pid]["quantity_sales_units"]) == D(units)
        assert D(items[pid]["unit_price"]) == D(price)
        assert D(items[pid]["line_total"]) == (D(units) * D(price)).quantize(D(".01"), rounding=ROUND_HALF_UP) == D(total)
    assert session["cart"]["subtotal"] == "4725.00"
    assert session["cart"]["budget_remaining"] == "96275.00"
    assert session["constraints"]["budget"] == "101000.00"
    assert any("per-order limit" in p for p in prompts(session))
    assert not any("remaining simulated purchasing allowance" in p or "exceeds your hard budget" in p for p in prompts(session))
    assert not any(option.get("id") == "raise-item-budget"
                   for question in session["clarification_questions"] for option in question["options"])
    assert not session["can_confirm"] and session["offer"] is None and session["receipt"] is None


def test_used_allowance_blocks_below_per_order_and_customer_budget_without_mutating_ledger(audit):
    client, store, scope = audit
    butter, _ = raw_product("Valio butter 500 g unsalted")
    created = create(client, butter, "1", "packages")
    assert D(created["cart"]["subtotal"]) < D(MANDATE["exception_limit"])
    assert created["cart"]["budget_remaining"] == "100991.09"
    # Inject prior usage only as quote input. Never spend, reset or enlarge a
    # real/demo ledger, and never request confirmation to create this boundary.
    saved = store.get("procurement", created["id"], scope["buyer_id"])
    used_cents = int(D(MANDATE["cumulative_limit"]) * 100) - 100
    quoted = procurement.quote(deepcopy(saved), used_cents)
    assert D(quoted["cart"]["subtotal"]) == D("8.91")
    assert quoted["cart"]["budget_remaining"] == "100991.09"
    assert any("remaining simulated purchasing allowance" in p for p in prompts(quoted))
    assert not any("per-order limit" in p or "exceeds your hard budget" in p for p in prompts(quoted))
    assert not any(option.get("id") == "raise-item-budget"
                   for question in quoted["clarification_questions"] for option in question["options"])
    assert not quoted["can_confirm"] and quoted["offer"] is None and quoted["receipt"] is None
    assert store.spent(scope["buyer_id"]) == 0


def test_customer_budget_shortfall_has_its_own_explicit_correction(audit):
    client, _, _ = audit
    butter, _ = raw_product("Valio butter 500 g unsalted")
    session = create(client, butter, "1", "packages", budget="1.00")
    assert session["cart"]["budget_remaining"] == "-7.91"
    assert any("exceeds your requested budget by €7.91" in p for p in prompts(session))
    assert not any("Purchasing policy:" in p for p in prompts(session))
    correction = [o for q in session["clarification_questions"] for o in q["options"]
                  if o["id"] == "raise-item-budget"]
    assert len(correction) == 1 and correction[0]["payload"]["budget"] == "8.91"
    assert not session["can_confirm"] and session["receipt"] is None


@pytest.mark.parametrize("tax_rate", ["0", "10", "13.5", "24"])
def test_authored_gross_price_and_net_evidence_reconcile_using_declared_tax(audit, monkeypatch, tax_rate):
    butter, _ = raw_product("Valio butter 500 g unsalted")
    day = str(date.today() + timedelta(days=2))
    source = upstream.fixture_lookup("isolated-fixture-test", day, [butter])
    source["price"]["products"][0]["tax"]["taxRate"] = float(tax_rate)
    monkeypatch.setattr(upstream, "fixture_lookup", lambda *args: deepcopy(source))
    evidence = procurement.fixture_lookup("isolated-fixture-test", day, [butter])
    price = evidence["price"]["products"][0]
    gross = D(str(price["catalogPrice"]["valueWithTax"]))
    net = D(str(price["catalogPrice"]["value"]))
    assert gross == D("8.91")  # Existing deterministic screenshot gross remains stable.
    expected_gross = (net * (1 + D(tax_rate) / 100)).quantize(D(".01"), rounding=ROUND_HALF_UP)
    assert expected_gross == gross
    assert abs(net - gross / (1 + D(tax_rate) / 100)) < D(".000000000001")


def test_legacy_fixture_prices_and_tax_evidence_remain_unchanged(audit, monkeypatch):
    pid = sorted(catalog.DEFAULT_IDS)[0]
    day = str(date.today() + timedelta(days=2))
    source = upstream.fixture_lookup("isolated-fixture-test", day, [pid])
    monkeypatch.setattr(upstream, "fixture_lookup", lambda *args: deepcopy(source))
    evidence = procurement.fixture_lookup("isolated-fixture-test", day, [pid])
    assert evidence["price"] == source["price"]
