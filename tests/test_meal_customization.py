"""Editable kitchen quantities reuse real quotation boundaries; no provider calls."""

import copy
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend import catalog, planning
from backend.app import create_app
from backend.config import BUYER, access_codes
from backend.store import Store


def ingredient(id="carrot", query="carrot", grams="125", **extra):
    return {"id": id, "label": query, "query": query, "grams_per_serving": grams, "applies_to": "all", **extra}


def recipe(**extra):
    return {"meal_name": "Kitchen vegetable soup", "template": "custom", "recipe_source": "customer",
        "servings": 40, "vegetarian": 0, "gluten_free": 0, "vegetarian_gluten_free": 0,
        "ingredients": [ingredient()], **extra}


@pytest.fixture
def env(tmp_path, monkeypatch):
    rows = {}
    for pid, name, kg, claims in [
        ("carrot", "Carrot", "2", ["VEGAN", "FREE_FROM_GLUTEN", "FREE_FROM_LACTOSE"]),
        ("onion", "Onion", "1", ["VEGAN", "FREE_FROM_GLUTEN", "FREE_FROM_LACTOSE"]),
        ("beef", "Minced beef", "1", []),
    ]:
        rows[pid] = {"id": pid, "salesUnit": "ST", "baseUnit": "ST", "allowedLotSize": 1,
            "units": [{"unitId": "ST", "sizeInBaseUnits": 1}],
            "synkkaData": {"names": [{"language": "en", "value": name}], "brand": "Kitchen Test",
                "countriesOfOrigin": ["246"], "classifications": [{"name": "nutritionalClaim", "values": [{"id": claim} for claim in claims]}],
                "unitConversions": [{"synkkaPackagingType": "BASE_UNIT_OR_EACH", "netWeight": {"unit": "KGM", "value": kg}}]}}
    monkeypatch.setattr(catalog, "load_catalog", lambda: rows)
    store = Store(tmp_path / "meal-customization.sqlite", postgres=False)
    client = TestClient(create_app(store))
    client.post("/api/v1/session", json={"access_code": access_codes()["buyer"]})
    return client, store, rows


def test_custom_recipe_exact_scaling_stable_ids_and_explicit_unverified_source(env):
    data = recipe(ingredients=[ingredient(grams="123.45"), ingredient("onion", "onion", "0.25")], servings=37)
    first = planning.plan(planning.MealInput(**data))
    assert first["dish"] == "Kitchen vegetable soup" and first["verified_recipe"] is False
    assert first["recipe_provenance"] == "customer_entered_unverified"
    assert "recipe" not in first["request"] and "include_carrot" not in first["request"]
    assert [item["query"] for item in first["request"]["ingredients"]] == ["carrot", "onion"]
    assert "not a verified recipe" in first["recipe_note"]
    assert [Decimal(line["required_kg"]) for line in first["lines"]] == [Decimal("4.56765"), Decimal("0.00925")]
    data["servings"] = 74
    second = planning.plan(planning.MealInput(**data))
    assert [line["id"] for line in first["lines"]] == [line["id"] for line in second["lines"]]
    assert [Decimal(line["required_kg"]) for line in second["lines"]] == [Decimal("9.1353"), Decimal("0.0185")]
    assert first["total"] is None and not first["can_commit"]


@pytest.mark.parametrize("changes", [
    {"ingredients": []}, {"ingredients": None},
    {"ingredients": [ingredient(), ingredient()]},
    {"ingredients": [ingredient(grams="NaN")]}, {"ingredients": [ingredient(grams="0")]},
    {"ingredients": [ingredient(query=" ")]},
    {"ingredients": [ingredient(applies_to="vegetarian")]},
    {"servings": 10, "vegetarian": 8, "gluten_free": 8, "vegetarian_gluten_free": 0},
])
def test_invalid_custom_recipe_or_cohorts_fail_without_invented_ingredients(changes):
    with pytest.raises(ValidationError):
        planning.MealInput(**recipe(**changes))


def test_unknown_meal_cannot_silently_use_bolognese_template():
    with pytest.raises(ValidationError, match="bolognese template"):
        planning.MealInput(meal_name="Vegetable soup")


def test_ingredient_add_remove_replace_recalculates_without_legacy_recipe_reappearing(env):
    data = recipe(ingredients=[ingredient(), ingredient("onion", "onion", "30")])
    initial = planning.plan(planning.MealInput(**data))
    data["ingredients"] = [ingredient(grams="150"), ingredient("replacement", "missing kitchen ingredient", "50")]
    changed = planning.plan(planning.MealInput(**data))
    assert len(changed["ingredients"]) == len(changed["lines"]) == 2
    assert changed["lines"][0]["id"] == initial["lines"][0]["id"]
    assert changed["lines"][0]["required_kg"] == "6"
    assert all(line["search_query"] != "onion" for line in changed["lines"])
    assert changed["lines"][1]["candidates"] == []
    assert not any("beef" in line["search_query"] for line in changed["lines"])


def test_cohorts_overlap_and_all_serving_diets_remain_conservative(env):
    data = recipe(vegetarian=8, gluten_free=4, vegetarian_gluten_free=2,
        ingredients=[ingredient(split_gluten_free=True), ingredient("beef", "minced beef", "120", applies_to="meat", split_gluten_free=True), ingredient("onion", "onion", "30", applies_to="vegetarian", split_gluten_free=True)])
    plan = planning.plan(planning.MealInput(**data))
    assert plan["cohorts"] == {"meat_standard": 30, "meat_gluten_free": 2, "vegetarian_standard": 6, "vegetarian_gluten_free": 2}
    assert sum(plan["cohorts"].values()) == 40
    for line in plan["lines"]:
        assert ("gluten_free" in line["dietary"]) is line["gluten_free_required"]
        if line["applies_to"] != "meat":
            assert "vegetarian" in line["dietary"]
    vegan = planning.plan(planning.MealInput(**recipe(dietary_restrictions=["vegan", "gluten_free", "lactose_free"],
        ingredients=[ingredient(), ingredient("beef", "minced beef", "120", applies_to="meat")])))
    assert vegan["cohorts"] == {"meat_standard": 0, "meat_gluten_free": 0, "vegetarian_standard": 0, "vegetarian_gluten_free": 40}
    assert len(vegan["lines"]) == 1 and set(vegan["lines"][0]["dietary"]) >= {"vegan", "gluten_free", "lactose_free"}


def test_saved_diets_validate_candidates_without_becoming_recipe_requested_constraints(env):
    plan = planning.plan(planning.MealInput(**recipe()), dietary=["milk_free"])
    line = plan["lines"][0]
    assert line["dietary"] == []
    assert line["candidates"][0]["issues"]  # no verified milk-allergen absence
    assert "milk_free" in plan["dietary_restrictions"]


def test_custom_plan_bridge_preserves_exact_choices_prefs_and_hard_budget(env):
    client, store, _ = env
    original = client.post("/api/v1/meal-plans", json=recipe(ingredients=[ingredient(grams="125"), ingredient("shared-carrot", "carrot", "25")], dietary_restrictions=["vegan"], preferred_brand="Kitchen Test", preferred_origin="finland"))
    assert original.status_code == 200, original.text
    plan = original.json()
    day = (date.today() + timedelta(days=2)).isoformat()
    bridged = client.post("/api/v1/procurement/sessions/from-meal-plan", json={"plan_id": plan["id"], "selections": {"0": "carrot", "1": "carrot"}, "mode": "fixture", "date": day, "budget": "0.01"})
    assert bridged.status_code == 200, bridged.text
    cart = bridged.json()
    assert cart["recipe_review_required"] and not cart["can_confirm"]
    assert cart["constraints"]["delivery_date"] == day and cart["constraints"]["budget"] == "0.01"
    assert [Decimal(line["quantity"]) for line in cart["lines"]] == [Decimal("5"), Decimal("1")]
    assert all(line["selected_product_id"] == "carrot" and "vegan" in line["dietary"] and line["preferred_brand"] == "Kitchen Test" and line["preferred_origin"] == "finland" for line in cart["lines"])
    assert len(cart["cart"]["items"]) == 1 and cart["cart"]["items"][0]["quantity_sales_units"] == "3"
    assert any("requested budget" in question["prompt"] for question in cart["clarification_questions"])
    assert client.get("/api/v1/meal-plans/" + plan["id"]).json() == plan
    assert store.spent() == 0


def test_custom_plan_origin_not_inferred_from_beef_name_and_missing_date_is_draft(env):
    client, store, _ = env
    data = recipe(ingredients=[ingredient(origin="finland")], dietary_restrictions=["gluten_free"])
    response = client.post("/api/v1/meal-plans", json=data)
    assert response.status_code == 200, response.text
    plan = response.json()
    result = client.post("/api/v1/procurement/sessions/from-meal-plan", json={"plan_id": plan["id"], "selections": {"0": "carrot"}})
    assert result.status_code == 200, result.text
    cart = result.json()
    assert cart["lines"][0]["origin"] == "finland" and "gluten_free" in cart["lines"][0]["dietary"]
    assert cart["constraints"]["delivery_date"] is None and not cart["can_confirm"] and cart["offer"] is None
    assert store.spent(BUYER) == 0
