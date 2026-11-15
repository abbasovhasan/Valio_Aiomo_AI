"""Independent authored expectations for public evidence and honest sort scope."""

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from backend import catalog, procurement, product_facts as facts, upstream
from backend.app import create_app
from backend.config import access_codes
from backend.procurement_contract import ProductDetailsResponse
from backend.store import Store


@pytest.fixture
def rows(monkeypatch):
    data = {}
    for pid, name, brand, category, mass in [
        ("100", "Zulu ingredient", "North", "A", 1),
        ("101", "Alpha ingredient", "South", "B", .25),
        ("102", "Echo ingredient", "North", "B", None),
        ("103", "Bravo ingredient", "South", "A", 2),
    ]:
        data[pid] = {
            "id": pid, "salesUnit": "ST", "baseUnit": "ST", "category": category,
            "allowedLotSize": .01, "deleted": False, "deposits": [],
            "units": [{"unitId": "ST", "sizeInBaseUnits": 1}],
            "synkkaData": {
                "names": [{"language": "en", "value": name}], "brand": brand,
                "countriesOfOrigin": ["246"], "classifications": [],
                "unitConversions": [{"synkkaPackagingType": "BASE_UNIT_OR_EACH", "netWeight": {"value": mass, "unit": "KGM"}}] if mass else [],
                "medias": [{"id": 123, "primary": True}],
            },
        }
    monkeypatch.setattr(catalog, "load_catalog", lambda: data)
    monkeypatch.setattr(catalog, "supplemental", lambda: {})
    return data


@pytest.fixture
def client(rows, monkeypatch, tmp_path):
    def lookup(customer, day, ids):
        evidence = upstream.fixture_lookup(customer, day, ids)
        prices = {"100": 9, "101": 4, "102": 1, "103": 2}
        for price in evidence["price"]["products"]:
            price["catalogPrice"]["valueWithTax"] = prices[price["productId"]]
            if price["productId"] == "103":
                price["catalogPrice"]["currency"] = "USD"
        return evidence
    monkeypatch.setattr(procurement, "fixture_lookup", lookup)
    store = Store(tmp_path / "presentation.sqlite3", postgres=False)
    with TestClient(create_app(store)) as client:
        assert client.post("/api/v1/session", json={"access_code": access_codes()["buyer"]}).status_code == 200
        yield client
    assert store.spent() == 0


def search(client, **params):
    day = (datetime.now(ZoneInfo("Europe/Helsinki")) + timedelta(days=2)).date()
    response = client.get("/api/v1/products", params={"mode": "fixture", "date": str(day), "apply_preferences": False, **params})
    assert response.status_code == 200, response.text
    return response.json()


def test_normalized_nutrition_preserves_basis_precision_zero_and_temperature(rows):
    rows["100"]["synkkaData"].update(
        nutritionalContent=[
            {"id": "SUGAR-", "value": 0, "unit": "GRM", "unitPrecision": "LESS_THAN", "basisQuantity": 100, "basisQuantityUnit": "MLT", "servingSize": 250, "servingSizeUnit": "MLT", "dailyValueIntakePercent": 0},
            {"id": "BAD", "value": "NaN", "unit": "GRM", "basisQuantity": 100, "basisQuantityUnit": "GRM"},
        ], minTemperature=-20, maxTemperature=-18,
    )
    normalized = ProductDetailsResponse.model_validate(facts.normalize("100")).model_dump()
    assert normalized["nutrition"] == [{"id": "SUGAR-", "value": "0", "unit": "GRM", "basis_quantity": "100", "basis_unit": "MLT", "precision": "LESS_THAN", "serving_size": "250", "serving_unit": "MLT", "daily_intake_percent": "0"}]
    assert normalized["min_storage_temperature"] == "-20"
    assert normalized["max_storage_temperature"] == "-18"
    assert normalized["image_url"] is None and normalized["image_status"] == "not_supplied"


def test_comparable_prices_do_not_cross_dimensions_or_guess_density(rows):
    p = facts.normalize("101")
    assert facts.comparable_prices(p, "4.00") == {"price_per_kg": "16", "price_per_litre": None}
    assert facts.comparable_prices(facts.normalize("102"), "1") == {"price_per_kg": None, "price_per_litre": None}
    assert facts.comparable_prices(p, "NaN") == {"price_per_kg": None, "price_per_litre": None}
    assert facts.comparable_prices(p, "0") == {"price_per_kg": "0", "price_per_litre": None}


def test_name_order_covers_all_filtered_products_before_paging(client):
    first = search(client, sort="name_asc", limit=2)
    second = search(client, sort="name_asc", limit=2, offset=2)
    assert [p["id"] for p in first["products"] + second["products"]] == ["101", "103", "102", "100"]
    assert first["sort_scope"] == "full_filtered_catalog"
    assert [p["id"] for p in search(client, sort="name_desc", limit=2)["products"]] == ["100", "102"]


@pytest.mark.parametrize("sort,expected", [
    ("price_asc", ["102", "101", "100", "103"]),
    ("price_desc", ["100", "101", "102", "103"]),
    ("price_kg_asc", ["100", "101", "102", "103"]),
    ("price_kg_desc", ["101", "100", "102", "103"]),
])
def test_price_sort_basis_is_explicit_and_unknowns_are_last(client, sort, expected):
    body = search(client, sort=sort)
    assert [p["id"] for p in body["products"]] == expected
    assert body["sort_scope"] == "quoted_page"
    assert body["total"] == 4 and body["applied_filters"]["sort"] == sort
    a = next(p for p in body["products"] if p["id"] == "101")
    assert Decimal(a["price_per_kg"]) == 16
    assert a["price_per_litre"] is None and a["available_sales_units"] == "1000000"


def test_sort_never_fetches_entire_catalog_or_claims_unknown_prices(client):
    body = search(client, sort="price_desc", limit=1)
    assert len(body["products"]) == 1 and body["total"] == 4
    response = client.get("/api/v1/products", params={"sort": "invented_quality"})
    assert response.status_code == 422
    unquoted = client.get("/api/v1/products", params={"sort": "price_asc"}).json()
    assert unquoted["sort_scope"] == "quoted_page"
    assert all(p["unit_price"] is None and p["price_per_kg"] is None for p in unquoted["products"])


def test_facets_respect_other_real_filters_without_fictional_brands(client):
    body = search(client, category="A")
    assert {p["id"] for p in body["products"]} == {"100", "103"}
    assert {p["value"]: p["count"] for p in body["facets"]["brands"]} == {"North": 1, "South": 1}
    body = search(client, brand="North")
    assert {p["value"]: p["count"] for p in body["facets"]["categories"]} == {"A": 1, "B": 1}


def test_smart_order_details_retain_declared_nutrition_origin_claims(client, rows):
    rows["100"]["synkkaData"]["nutritionalContent"] = [{"id": "PRO-", "value": 3.4, "unit": "GRM", "basisQuantity": 100, "basisQuantityUnit": "GRM"}]
    day = (datetime.now(ZoneInfo("Europe/Helsinki")) + timedelta(days=2)).date()
    response = client.post("/api/v1/procurement/sessions/from-product", json={"product_id": "100", "quantity": "2", "unit": "kg", "date": str(day), "mode": "fixture", "apply_preferences": False})
    assert response.status_code == 200, response.text
    candidate = next(c for c in response.json()["lines"][0]["candidates"] if c["id"] == "100")
    assert candidate["product_details"]["nutrition"][0]["value"] == "3.4"
    assert candidate["product_details"]["origin_codes"] == ["246"]
    assert candidate["product_details"]["claims"] == []
    assert candidate["price_per_kg"] == "9"
    assert candidate["price_per_litre"] is None
