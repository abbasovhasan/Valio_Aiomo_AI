"""Actual catalog regression: independent source sets → public API → selected cart.

These tests need the original private challenge files. They never use live services,
call a commit endpoint or embed restricted catalog records in source.
"""

import collections
import csv
import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend import catalog, procurement, upstream
from backend.app import create_app
from backend.config import ROOT, access_codes
from backend.store import Store
from scripts.catalog_qa import (
    DATA_FILES, active_records, all_pages, category_groups, category_representatives, expected_sales_units,
    representative_cart_cases, representative_queries, source_claims,
)


@pytest.fixture(scope="module")
def actual_catalog():
    if not all((ROOT / "data/raw" / name).exists() for name in DATA_FILES):
        pytest.skip("Original private challenge datasets are not installed")
    rows = catalog.load_catalog()
    assert rows, "Installed product dataset must contain records"
    return rows


@pytest.fixture
def client(tmp_path, actual_catalog):
    store = Store(tmp_path / "catalog.sqlite3", postgres=False)
    with TestClient(create_app(store)) as client:
        assert client.post("/api/v1/session", json={"access_code": access_codes()["buyer"]}).status_code == 200
        yield client
    assert store.spent() == 0, "Catalog regression must not commit a simulated order"


def search(client, **params):
    return client.get("/api/v1/products", params={"q": "", "date": str(date.today() + timedelta(days=2)), "mode": "fixture", "apply_preferences": "false", **params})


def post_product(client, case, **changes):
    return client.post(procurement.PREFIX + "/from-product", json={"product_id": case["id"], "quantity": str(case["quantity"]), "unit": case["unit"], "date": str(date.today() + timedelta(days=2)), "mode": "fixture", "apply_preferences": False, **changes})


def action(client, session, name, **fields):
    return client.post(procurement.PREFIX + "/" + session["id"] + "/actions", json={"version": session["version"], "action": name, **fields})


def test_four_source_datasets_and_joined_evidence_are_used(actual_catalog):
    schema = json.loads((ROOT / "data/raw" / DATA_FILES[1]).read_text())
    assert schema.get("type") == "array" and schema.get("items")
    from backend import product_facts
    for filename, column, output in [
        (DATA_FILES[2], "deliveryReliability", "reliability"),
        (DATA_FILES[3], "AVG kg CO2-eq/kg", "carbon_group_estimate"),
    ]:
        with (ROOT / "data/raw" / filename).open() as f:
            rows = {str(row["productId"]): float(row[column]) for row in csv.DictReader(f) if row.get(column)}
        joined = sorted(set(rows) & set(actual_catalog))
        assert joined, "Supplemental source has no joinable product IDs"
        for pid in (joined[0], joined[len(joined) // 2], joined[-1]):
            assert product_facts.normalize(pid)[output] == rows[pid]


def test_catalog_search_requires_identity(tmp_path, actual_catalog):
    with TestClient(create_app(Store(tmp_path / "anonymous.sqlite", postgres=False))) as client:
        assert client.get("/api/v1/products", params={"q": ""}).status_code == 401


def test_browse_returns_real_products_and_total(client, actual_catalog):
    response = search(client, limit=50)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == len(active_records(actual_catalog))
    assert len(body["products"]) == 50 and body["has_more"]
    assert {p["id"] for p in body["products"]}.issubset(actual_catalog)
    assert all(p.get("name") and p.get("sales_unit") for p in body["products"])
    assert all(key in body["facets"] for key in ("categories", "brands"))
    assert all(set(facet) >= {"value", "label", "count"} for facet in body["facets"]["categories"])


def test_all_products_in_actual_large_category_are_accessible(client, actual_catalog):
    groups = category_groups(actual_catalog)
    category = max(groups, key=lambda value: len(groups[value]))
    assert len(groups[category]) > 50, "Choose a genuinely paginated source category"
    products, _ = all_pages(client, {"q": "", "category": category}, page_size=50)
    assert {p["id"] for p in products} == groups[category]


def test_category_query_discovers_actual_category_products(client, actual_catalog):
    groups = category_groups(actual_catalog)
    category = max(groups, key=lambda value: len(groups[value]))
    products, _ = all_pages(client, {"q": category})
    assert groups[category].issubset({product["id"] for product in products})


def test_every_source_category_count_and_exact_name_are_accessible(client, actual_catalog):
    examples = category_representatives(actual_catalog)
    assert len(examples) == len(category_groups(actual_catalog))
    for example in examples:
        category_response = search(client, category=example["category"], limit=1)
        assert category_response.status_code == 200, f"Category {example['category']}: {category_response.text[:180]}"
        assert category_response.json()["total"] == example["count"], f"Incomplete category {example['category']}"
        named = search(client, category=example["category"], q=example["q"], limit=50)
        assert named.status_code == 200, f"Exact source name/category {example['category']}: {named.text[:180]}"
        assert example["id"] in {product["id"] for product in named.json()["products"]}, f"Missing exact source name in category {example['category']}"


@pytest.mark.parametrize("language", ["en", "fi", "sv"])
def test_actual_localized_name_and_case_are_findable(client, actual_catalog, language):
    case = next(case for case in representative_queries(actual_catalog) if case["kind"] == "localized_" + language)
    products, body = all_pages(client, {"q": case["q"]})
    uppercase, upper_body = all_pages(client, {"q": case["q"].upper()})
    assert case["id"] in {p["id"] for p in products}
    assert {p["id"] for p in products} == {p["id"] for p in uppercase}
    assert body["total"] == upper_body["total"]


def test_partial_and_hyphenated_source_names(client, actual_catalog):
    cases = representative_queries(actual_catalog)
    for case in cases:
        if case["kind"] not in {"partial", "hyphen"}:
            continue
        products, _ = all_pages(client, {"q": case["q"]})
        found = {p["id"] for p in products}
        assert found.issubset(actual_catalog)
        if "expected_subset" in case:
            assert case["expected_subset"].issubset(found)
        else:
            assert case["id"] in found


def test_exact_id_single_result_and_search_alias(client, actual_catalog):
    pid = sorted(active_records(actual_catalog))[len(actual_catalog) // 2]
    response = search(client, q=pid)
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert [product["id"] for product in response.json()["products"]] == [pid]
    alias = client.get("/api/v1/products/search", params={"q": pid, "mode": "fixture", "apply_preferences": "false"})
    assert alias.status_code == 200 and [p["id"] for p in alias.json()["products"]] == [pid]


def test_no_match_is_empty_and_filters_combine(client, actual_catalog):
    none = search(client, q="zzqacatalogunfindable8fc249ad")
    assert none.status_code == 200, none.text
    assert none.json()["products"] == [] and none.json()["total"] == 0 and not none.json()["has_more"]
    groups = collections.defaultdict(set)
    for pid, raw in active_records(actual_catalog).items():
        brand = raw.get("synkkaData", {}).get("brand")
        if isinstance(brand, str) and brand.strip():
            groups[(str(raw.get("category")), brand)].add(pid)
    (category, brand), expected = max(groups.items(), key=lambda pair: len(pair[1]))
    products, body = all_pages(client, {"q": "", "category": category, "brand": brand})
    assert {p["id"] for p in products} == expected
    assert body["applied_filters"]
    empty = search(client, q="", category=category, brand="zzqacatalognonexistentbrand")
    assert empty.status_code == 200 and empty.json()["products"] == [] and empty.json()["total"] == 0


def test_dietary_filter_uses_explicit_source_claims(client, actual_catalog):
    claim = "FREE_FROM_LACTOSE"
    def source_verifies_lactose_free(raw):
        lactose = [value for group in raw.get("synkkaData", {}).get("classifications", [])
                   if group.get("name") in {"allergen", "nonAllergen"}
                   for value in group.get("values", []) if value.get("id") == "ML"]
        absent = claim in source_claims(raw) or any(value.get("unit") == "FREE_FROM" for value in lactose)
        contradictory = any(value.get("unit") in {"CONTAINS", "MAY_CONTAIN"} for value in lactose)
        return absent and not contradictory
    expected_by_category = collections.defaultdict(set)
    for pid, raw in active_records(actual_catalog).items():
        if source_verifies_lactose_free(raw):
            expected_by_category[str(raw.get("category"))].add(pid)
    category, expected = max(expected_by_category.items(), key=lambda pair: len(pair[1]))
    products, _ = all_pages(client, {"q": "", "category": category, "dietary": "lactose_free"})
    assert {p["id"] for p in products} == expected
    assert all(source_verifies_lactose_free(actual_catalog[p["id"]]) for p in products)


def test_required_origin_excludes_unknown_and_conflicting_source_countries(client, actual_catalog):
    expected_by_category = collections.defaultdict(set)
    for pid, raw in active_records(actual_catalog).items():
        codes = {str(code).strip().upper().zfill(3) if str(code).strip().isdigit() else str(code).strip().upper()
                 for code in raw.get("synkkaData", {}).get("countriesOfOrigin", []) if str(code).strip()}
        if raw.get("countryOfOrigin"):
            codes.add(str(raw["countryOfOrigin"]).strip().upper())
        if codes and codes.issubset({"246", "FI"}):
            expected_by_category[str(raw.get("category"))].add(pid)
    category, expected = max(expected_by_category.items(), key=lambda pair: len(pair[1]))
    products, _ = all_pages(client, {"q": "", "category": category, "origin": "finland"})
    assert {product["id"] for product in products} == expected


def test_search_never_returns_a_deleted_record(client, actual_catalog, monkeypatch):
    case = representative_cart_cases(actual_catalog)[0]
    changed = dict(actual_catalog)
    changed[case["id"]] = dict(actual_catalog[case["id"]]) | {"deleted": True}
    monkeypatch.setattr(catalog, "load_catalog", lambda: changed)
    response = search(client, q=case["id"])
    assert response.status_code == 200, response.text
    assert response.json()["products"] == [] and response.json()["total"] == 0


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 51}, {"offset": -1}, {"q": "x" * 501}, {"quantity": "0"}])
def test_search_rejects_invalid_bounds(client, params):
    assert search(client, **params).status_code == 422


@pytest.mark.parametrize("unit", ["kg", "L", "pieces", "packages"])
def test_dynamic_product_selection_updates_correct_cart_quantities(client, actual_catalog, unit):
    cases = representative_cart_cases(actual_catalog)
    assert {case["unit"] for case in cases} == {"kg", "L", "pieces", "packages"}
    case = next(case for case in cases if case["unit"] == unit)
    response = post_product(client, case)
    assert response.status_code == 200, response.text
    session = response.json()
    assert len(session["lines"]) == 1 and session.get("receipt") is None
    line = session["lines"][0]
    assert line["selected_product_id"] == case["id"] and line["unit"] == unit
    chosen = next(product for product in line["candidates"] if product["id"] == case["id"])
    expected = expected_sales_units(case["quantity"], case["capacity"], case["lot"])
    assert Decimal(chosen["quantity_sales_units"]) == expected
    assert Decimal(chosen["effective_quantity"]) == expected * case["capacity"]
    assert chosen["unit_price"] is not None and chosen["line_total"] is not None
    assert Decimal(chosen["line_total"]) == (expected * Decimal(chosen["unit_price"])).quantize(Decimal(".01"))
    updated_quantity = (case["capacity"] * Decimal("2.25")).quantize(Decimal(".001"))
    update = action(client, session, "set_quantity", line_id=line["id"], quantity=str(updated_quantity), unit=unit)
    assert update.status_code == 200, update.text
    changed = update.json()
    assert changed["lines"][0]["selected_product_id"] == case["id"]
    selected = next(p for p in changed["lines"][0]["candidates"] if p["id"] == case["id"])
    assert Decimal(selected["quantity_sales_units"]) == expected_sales_units(updated_quantity, case["capacity"], case["lot"])
    assert Decimal(selected["line_total"]) == (Decimal(selected["quantity_sales_units"]) * Decimal(selected["unit_price"])).quantize(Decimal(".01"))
    removed = action(client, changed, "remove_line", line_id=line["id"])
    assert removed.status_code == 200 and removed.json()["lines"] == [] and not removed.json()["can_confirm"]


def test_add_product_preserves_other_line_and_selection(client, actual_catalog):
    first, second = representative_cart_cases(actual_catalog)[:2]
    created = post_product(client, first)
    assert created.status_code == 200, created.text
    session = created.json()
    first_line = session["lines"][0]
    added = action(client, session, "add_product", product_id=second["id"], quantity=str(second["quantity"]), unit=second["unit"])
    assert added.status_code == 200, added.text
    session = added.json()
    assert len(session["lines"]) == 2
    preserved = next(line for line in session["lines"] if line["id"] == first_line["id"])
    assert preserved["selected_product_id"] == first["id"] and preserved["quantity"] == first_line["quantity"]
    assert next(line for line in session["lines"] if line["id"] != first_line["id"])["selected_product_id"] == second["id"]
    assert session["cart"]["subtotal"] is not None


def test_explicit_replacement_can_use_actual_catalog_outside_candidate_window(client, actual_catalog):
    case = next(case for case in representative_cart_cases(actual_catalog) if case["unit"] == "packages")
    created = post_product(client, case)
    assert created.status_code == 200, created.text
    session = created.json()
    line = session["lines"][0]
    shown = {product["id"] for product in line["candidates"]}
    alternatives = [pid for pid in sorted(category_groups(actual_catalog)[case["category"]]) if pid not in shown]
    assert alternatives, "Representative category must contain a product outside the quote window"
    replacement = alternatives[-1]
    changed = action(client, session, "select_product", line_id=line["id"], product_id=replacement)
    assert changed.status_code == 200, changed.text
    updated = changed.json()["lines"][0]
    assert updated["selected_product_id"] == replacement
    assert updated["quantity"] == line["quantity"] and updated["unit"] == "packages"
    assert any(product["id"] == replacement for product in updated["candidates"])


def test_requested_mozzarella_and_cheddar_keep_separate_quantities_and_quoted_choices(client):
    response = client.post(procurement.PREFIX, json={"message": "I need 8 kg of mozzarella and 12 kg of cheddar", "date": str(date.today() + timedelta(days=2)), "mode": "fixture", "use_model": False, "apply_preferences": False})
    assert response.status_code == 200, response.text
    session = response.json()
    assert len(session["lines"]) == 2
    assert [(line["requested_label"].casefold(), Decimal(line["quantity"]), line["unit"]) for line in session["lines"]] == [("mozzarella", Decimal(8), "kg"), ("cheddar", Decimal(12), "kg")]
    for original in list(session["lines"]):
        current = next(line for line in session["lines"] if line["id"] == original["id"])
        viable = [product for product in current["candidates"] if not product["issues"]]
        assert viable, "Actual mozzarella/cheddar source has valid fixed-weight fixture-quoted alternatives"
        chosen = viable[0]
        assert chosen["unit_price"] is not None and chosen["line_total"] is not None
        selected = action(client, session, "select_product", line_id=current["id"], product_id=chosen["id"])
        assert selected.status_code == 200, selected.text
        session = selected.json()
    assert len(session["cart"]["items"]) == 2 and session["cart"]["subtotal"] is not None
    assert [Decimal(line["quantity"]) for line in session["lines"]] == [Decimal(8), Decimal(12)]
    assert session.get("receipt") is None


def test_early_budget_and_delivery_apply_to_catalog_selected_cart(client, actual_catalog):
    case = representative_cart_cases(actual_catalog)[0]
    delivery = str(date.today() + timedelta(days=4))
    created = post_product(client, case, date=delivery, budget="0.01")
    assert created.status_code == 200, created.text
    session = created.json()
    assert session["constraints"]["delivery_date"] == delivery
    assert Decimal(session["constraints"]["budget"]) == Decimal(".01")
    assert not session["can_confirm"]
    chosen = next(product for product in session["lines"][0]["candidates"] if product["id"] == case["id"])
    assert chosen["delivery_date"] == delivery
    assert Decimal(chosen["line_total"]) > Decimal(".01")
    corrected = action(client, session, "set_budget", budget=str(Decimal(chosen["line_total"]) * 2))
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["constraints"]["delivery_date"] == delivery
    assert corrected.json()["cart"]["subtotal"] == session["cart"]["subtotal"]


def test_unknown_product_never_creates_a_cart(client, actual_catalog):
    response = post_product(client, representative_cart_cases(actual_catalog)[0], product_id="zzqanonexistentproduct")
    assert response.status_code in {404, 422}


def test_missing_quote_does_not_hide_or_deselect_a_real_product(client, actual_catalog, monkeypatch):
    case = representative_cart_cases(actual_catalog)[0]
    original = procurement.fixture_lookup
    def without_price(customer, day, ids):
        result = original(customer, day, ids)
        result["price"]["products"] = [row for row in result["price"]["products"] if str(row["productId"]) != case["id"]]
        return result
    monkeypatch.setattr(procurement, "fixture_lookup", without_price)
    response = search(client, q=case["id"], quantity=str(case["quantity"]), unit=case["unit"])
    assert response.status_code == 200, response.text
    product = response.json()["products"][0]
    assert product["id"] == case["id"] and product["selectable"]
    assert product["unit_price"] is None and product["line_total"] is None
    assert product["quote_issues"], "Missing price must be explained, never silently zero"
    created = post_product(client, case)
    assert created.status_code == 200, created.text
    session = created.json()
    assert session["lines"][0]["selected_product_id"] == case["id"]
    assert session["cart"]["subtotal"] is None and not session["can_confirm"]
    assert session.get("receipt") is None


def test_quote_provider_failure_preserves_discovery_without_fake_price(client, actual_catalog, monkeypatch):
    case = representative_cart_cases(actual_catalog)[0]
    def unavailable(*args):
        raise upstream.UpstreamError("Authored QA quotation failure")
    monkeypatch.setattr(procurement, "fixture_lookup", unavailable)
    response = search(client, q=case["id"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1 and body["quote_error"]
    product = body["products"][0]
    assert product["id"] == case["id"] and product["selectable"]
    assert product["unit_price"] is None and product["line_total"] is None
    assert product["availability"] == "not_queried" and product["quote_issues"]


@pytest.mark.parametrize("restriction,allergen,known", [
    ("milk_free", "AM", True),
    ("peanut_free", "AP", True),
    ("peanut_free", "AP", False),
])
def test_saved_hard_allergy_applies_to_search_and_cart_even_with_soft_preferences_off(client, actual_catalog, restriction, allergen, known):
    choices = []
    for raw in active_records(actual_catalog).values():
        entries = [value for group in raw.get("synkkaData", {}).get("classifications", [])
                   if group.get("name") == "allergen" for value in group.get("values", [])
                   if value.get("id") == allergen]
        explicit_absence = any(value.get("id") == allergen and value.get("unit") == "FREE_FROM"
                               for group in raw.get("synkkaData", {}).get("classifications", [])
                               if group.get("name") == "nonAllergen" for value in group.get("values", []))
        known_contains = any(value.get("unit") == "CONTAINS" for value in entries)
        unknown = not entries and not explicit_absence and not source_claims(raw).intersection({"FREE_FROM_PEANUTS", "FREE_FROM_PEANUT"})
        if (known and known_contains) or (not known and unknown):
            choices.append(raw)
    raw = min(choices, key=lambda row: str(row["id"]))
    saved = client.put("/api/v1/preferences", json={"dietary_restrictions": [restriction]})
    assert saved.status_code == 200, saved.text
    found = search(client, q=str(raw["id"]), apply_preferences="false")
    assert found.status_code == 200, found.text
    for product in found.json()["products"]:
        assert not product["selectable"] and product["eligibility_issues"], "Known allergen/unknown safety cannot become compliant"
    created = post_product(client, {"id": str(raw["id"]), "quantity": "1", "unit": "packages"}, apply_preferences=False)
    assert created.status_code in {200, 422}, created.text
    if created.status_code == 200:
        session = created.json()
        assert not session["can_confirm"]
        assert restriction in session["lines"][0]["dietary"]
        assert session.get("receipt") is None
