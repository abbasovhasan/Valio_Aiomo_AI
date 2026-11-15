"""Independent source-unit regressions; no live lookup, model or order calls.

The private schema defines allowedLotSize as an increment in sales units and
does not translate internal sales/base codes. UNECE defines quantitative CLT
as centilitre: https://vocabulary.uncefact.org/UnitMeasureCode#CLT.
"""

from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from fractions import Fraction

import pytest
from fastapi.testclient import TestClient

from backend import catalog, interpretation, procurement, product_facts as facts, upstream
from backend.app import create_app
from backend.config import ROOT, access_codes
from backend.store import Store

D = Decimal


@pytest.fixture(autouse=True)
def no_external_calls(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Unit regression must not invoke a model or supplier")
    monkeypatch.setattr(upstream, "sponsor_lookup", forbidden)
    monkeypatch.setattr(upstream, "rank_with_nvidia", forbidden)
    monkeypatch.setattr(interpretation, "_model", forbidden)


@pytest.fixture(scope="module")
def source_rows():
    if not (ROOT / "data/raw/valio_aimo_junction26_product_data.json").exists():
        pytest.skip("Original private challenge catalog is not installed")
    return catalog.load_catalog()


def declared_sales_ratio(raw):
    values = {D(str(unit["sizeInBaseUnits"])) for unit in raw.get("units", [])
              if unit.get("unitId") == raw.get("salesUnit")}
    return next(iter(values)) if len(values) == 1 else None


def raw_clt_cases(rows):
    result = []
    for pid, raw in sorted(rows.items()):
        volumes = [conversion.get("volume") or {} for conversion in raw.get("synkkaData", {}).get("unitConversions", [])
                   if conversion.get("synkkaPackagingType") == "BASE_UNIT_OR_EACH"]
        clt = {D(str(value["value"])) / 100 for value in volumes
               if value.get("unit") == "CLT" and D(str(value["value"])) > 0}
        if clt:
            assert len(clt) == 1, "Conflicting source CLT content needs a separate unknown case"
            ratio = declared_sales_ratio(raw)
            assert ratio is not None and ratio > 0
            result.append((pid, raw, next(iter(clt)) * ratio))
    return result


def raw_measured_kg_cases(rows):
    return [(pid, raw) for pid, raw in sorted(rows.items())
            if raw.get("salesUnit") == raw.get("baseUnit") == "KG"
            and declared_sales_ratio(raw) == 1
            and not raw.get("synkkaData", {}).get("variableUnit")
            and not raw.get("deleted")]


def quantize_sales(quantity, step):
    return (D(str(quantity)) / D(str(step))).to_integral_value(rounding=ROUND_CEILING) * D(str(step))


def test_every_actual_clt_consumer_content_converts_to_litres(source_rows):
    cases = raw_clt_cases(source_rows)
    assert cases, "Select every actual CLT record, not an authored syrup shortcut"
    for pid, raw, expected in cases:
        product = facts.normalize(pid)
        assert product["liters_per_sales_unit"] is not None, pid
        assert D(product["liters_per_sales_unit"]) == expected, pid
        assert product["conversion_evidence"].get("L"), pid
        # CLT products remain whole commercial packages; a requested litre can
        # require more than one 0.75-L package, independently of internal code.
        lot = D(str(raw["allowedLotSize"]))
        step = D(Fraction(lot).numerator)
        units = (D(1) / expected / step).to_integral_value(rounding=ROUND_CEILING) * step
        assert facts.units_for(product, "1", "L") == units, pid


def test_every_actual_fixed_measured_kg_uses_the_declared_fractional_lot(source_rows):
    cases = raw_measured_kg_cases(source_rows)
    assert any(D(str(raw["allowedLotSize"])) == D(".01") for _, raw in cases)
    assert any(D(str(raw["allowedLotSize"])) == D("1.2") for _, raw in cases)
    for pid, raw in cases:
        product = facts.normalize(pid)
        assert product["kg_per_sales_unit"] is not None and D(product["kg_per_sales_unit"]) == 1, pid
        for quantity in (D("1.5"), D("1.505")):
            expected = quantize_sales(quantity, raw["allowedLotSize"])
            assert facts.units_for(product, quantity, "kg") == expected, pid
            assert facts.units_for(product, quantity * 1000, "g") == expected, pid
            assert procurement.round_sales_units(product, Fraction(quantity)) == expected, pid


@pytest.mark.parametrize("sales", ["ST", "KI"])
@pytest.mark.parametrize("lot,expected", [(".01", "2"), (".4", "2"), ("1.5", "3")])
def test_fixed_commercial_packs_remain_whole_and_lot_compatible(sales, lot, expected):
    product = {"sales_unit": sales, "base_unit": "ST", "base_units_per_sales_unit": "1",
               "kg_per_sales_unit": "2", "liters_per_sales_unit": None,
               "pieces_per_sales_unit": "1", "allowed_lot_size": lot, "variable_unit": False}
    assert facts.units_for(product, "2.1", "kg") == D(expected)
    assert procurement.round_sales_units(product, Fraction(21, 20)) == D(expected)


def authored_raw(*, variable=False, conflicting_ratio=False, volumes=None):
    return {"id": "authored-unit", "salesUnit": "KG", "baseUnit": "KG", "allowedLotSize": .01,
            "units": [{"unitId": "KG", "sizeInBaseUnits": 1}] + ([{"unitId": "KG", "sizeInBaseUnits": 2}] if conflicting_ratio else []),
            "synkkaData": {"names": [{"language": "en", "value": "Authored unit evidence"}],
                           "variableUnit": variable, "unitConversions": volumes or []}}


@pytest.mark.parametrize("variable,conflicting_ratio", [(True, False), (False, True)])
def test_variable_weight_and_conflicting_ratios_remain_unknown(monkeypatch, variable, conflicting_ratio):
    raw = authored_raw(variable=variable, conflicting_ratio=conflicting_ratio)
    monkeypatch.setattr(catalog, "load_catalog", lambda: {raw["id"]: raw})
    product = facts.normalize(raw["id"])
    assert product["kg_per_sales_unit"] is None
    assert facts.units_for(product, "1.5", "kg") is None


def test_conflicting_clt_and_ltr_content_is_not_resolved_by_guessing(monkeypatch):
    raw = authored_raw(volumes=[
        {"synkkaPackagingType": "BASE_UNIT_OR_EACH", "volume": {"unit": "CLT", "value": 75}},
        {"synkkaPackagingType": "BASE_UNIT_OR_EACH", "volume": {"unit": "LTR", "value": 1}},
    ])
    raw.update(salesUnit="BOT", baseUnit="BOT", units=[{"unitId": "BOT", "sizeInBaseUnits": 1}])
    monkeypatch.setattr(catalog, "load_catalog", lambda: {raw["id"]: raw})
    product = facts.normalize(raw["id"])
    assert product["liters_per_sales_unit"] is None
    assert facts.units_for(product, "1", "L") is None


@pytest.fixture
def client(tmp_path, source_rows):
    store = Store(tmp_path / "unit-semantics.sqlite3", postgres=False)
    with TestClient(create_app(store)) as client:
        assert client.post("/api/v1/session", json={"access_code": access_codes()["buyer"]}).status_code == 200
        yield client
    assert store.spent() == 0


def from_product(client, pid, quantity, unit):
    response = client.post(procurement.PREFIX + "/from-product", json={"product_id": pid,
        "quantity": str(quantity), "unit": unit, "date": str(date.today() + timedelta(days=2)),
        "mode": "fixture", "apply_preferences": False})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("lot", [D(".01"), D("1.2")])
def test_measured_kg_api_retains_fractional_sales_quantity_and_price_basis(client, source_rows, lot):
    pid, _ = next((pid, raw) for pid, raw in raw_measured_kg_cases(source_rows)
                  if D(str(raw["allowedLotSize"])) == lot and not raw.get("deposits"))
    session = from_product(client, pid, "1.5", "kg")
    line = session["lines"][0]
    candidate = next(candidate for candidate in line["candidates"] if candidate["id"] == pid)
    expected = quantize_sales("1.5", lot)
    assert D(candidate["pack_quantity"]) == 1
    assert D(candidate["quantity_sales_units"]) == expected
    assert D(candidate["effective_quantity"]) == expected
    assert D(candidate["surplus_quantity"]) == expected - D("1.5")
    assert D(candidate["price_per_requested_unit"]) == D(candidate["unit_price"])
    assert D(candidate["line_total"]) == (D(candidate["unit_price"]) * expected).quantize(D(".01"), rounding=ROUND_HALF_UP)
    assert session.get("receipt") is None and not session["use_model"]


def test_shared_measured_kg_demands_aggregate_before_lot_rounding(client, source_rows):
    pid, _ = next((pid, raw) for pid, raw in raw_measured_kg_cases(source_rows)
                  if D(str(raw["allowedLotSize"])) == D(".01") and not raw.get("deposits"))
    session = from_product(client, pid, ".755", "kg")
    added = client.post(procurement.PREFIX + "/" + session["id"] + "/actions", json={
        "version": session["version"], "action": "add_product", "product_id": pid,
        "quantity": ".745", "unit": "kg"})
    assert added.status_code == 200, added.text
    updated = added.json()
    assert len(updated["cart"]["items"]) == 1
    item = updated["cart"]["items"][0]
    assert D(item["quantity_sales_units"]) == D("1.5")
    assert D(item["line_total"]) == (D(item["unit_price"]) * D("1.5")).quantize(D(".01"), rounding=ROUND_HALF_UP)
    assert updated.get("receipt") is None


def test_measured_kg_stock_boundary_stays_in_decimal_sales_units(client, source_rows, monkeypatch):
    pid, _ = next((pid, raw) for pid, raw in raw_measured_kg_cases(source_rows)
                  if D(str(raw["allowedLotSize"])) == D(".01") and not raw.get("deposits"))
    original = procurement.fixture_lookup
    available = "1.49"
    def fractional_stock(customer, day, ids):
        evidence = original(customer, day, ids)
        for product in evidence["availability"]["products"]:
            if str(product["productId"]) == pid:
                for schedule in product["scheduleLines"]:
                    schedule["availableAmount"] = available
        return evidence
    monkeypatch.setattr(procurement, "fixture_lookup", fractional_stock)
    for available, expected_availability in [("1.49", "insufficient"), ("1.50", "available")]:
        session = from_product(client, pid, "1.5", "kg")
        candidate = next(p for p in session["lines"][0]["candidates"] if p["id"] == pid)
        assert D(candidate["quantity_sales_units"]) == D("1.5")
        assert D(candidate["available_sales_units"]) == D(available)
        assert candidate["availability"] == expected_availability
        assert session["can_confirm"] == (expected_availability == "available")
        assert session.get("receipt") is None


def test_clt_public_quote_has_correct_package_surplus_and_unit_price(client, source_rows):
    pid, _, capacity = raw_clt_cases(source_rows)[0]
    session = from_product(client, pid, "1", "L")
    candidate = next(p for p in session["lines"][0]["candidates"] if p["id"] == pid)
    units = (D(1) / capacity).to_integral_value(rounding=ROUND_CEILING)
    assert D(candidate["pack_quantity"]) == capacity
    assert D(candidate["quantity_sales_units"]) == units
    assert D(candidate["effective_quantity"]) == units * capacity
    assert D(candidate["surplus_quantity"]) == units * capacity - 1
    assert D(candidate["price_per_requested_unit"]) == D(candidate["unit_price"]) / capacity
    assert D(candidate["line_total"]) == (D(candidate["unit_price"]) * units).quantize(D(".01"), rounding=ROUND_HALF_UP)


def test_public_details_preserve_verified_claim_origin_and_organic_evidence(client, source_rows):
    candidates = (facts.normalize(pid) for pid in source_rows)
    product = next(p for p in candidates if p["claims"] and p["origin_codes"] and p["organic"] is True and not p["deleted"])
    response = client.get("/api/v1/products", params={"q": product["id"], "mode": "fixture", "apply_preferences": "false"})
    assert response.status_code == 200, response.text
    details = response.json()["products"][0]["product_details"]
    assert {"claims", "origin_codes", "organic_evidence", "allergens", "conversion_evidence"}.issubset(details)
    assert details["claims"] == product["claims"]
    assert details["origin_codes"] == product["origin_codes"]
    assert details["organic_evidence"] == product["organic_evidence"]
