"""Planning arithmetic and authority boundaries; no sponsor requests."""

import copy
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend import catalog, planning
from backend.app import create_app
from backend.config import access_codes, spend_limits
from backend.store import Store


@pytest.fixture
def products(monkeypatch):
    rows = {}
    for pid, name, gf, origin in [
        ("pasta", "Spaghetti", False, "380"),
        ("gf", "Spaghetti gluten free", True, "380"),
        ("beef", "Minced beef", False, "246"),
        ("foreign", "Minced beef", False, "840"),
        ("lentil", "Red lentils", False, "124"),
    ]:
        rows[pid] = {
            "id": pid,
            "baseUnit": "ST",
            "salesUnit": "KI",
            "allowedLotSize": 1,
            "units": [{"unitId": "KI", "sizeInBaseUnits": 5}],
            "synkkaData": {
                "names": [{"language": "en", "value": name}],
                "countriesOfOrigin": [origin],
                "unitConversions": [
                    {
                        "synkkaPackagingType": "BASE_UNIT_OR_EACH",
                        "netWeight": {"unit": "GRM", "value": 250},
                    }
                ],
                "classifications": [
                    {
                        "name": "nutritionalClaim",
                        "values": [{"id": "FREE_FROM_GLUTEN"}] if gf else [],
                    }
                ],
            },
        }
    monkeypatch.setattr(catalog, "load_catalog", lambda: rows)
    return rows


def test_cohorts_scale_once_and_account_for_overlap(products):
    p = planning.plan(planning.MealInput())
    assert p["cohorts"] == {
        "meat_standard": 370,
        "meat_gluten_free": 30,
        "vegetarian_standard": 80,
        "vegetarian_gluten_free": 20,
    }
    assert sum(p["cohorts"].values()) == 500
    totals = {line["ingredient"]: Decimal(line["required_kg"]) for line in p["lines"]}
    assert totals["Dry spaghetti · standard"] == 45
    assert totals["Dry spaghetti · gluten-free"] == 5
    assert totals["Dry lentils · vegetarian & gluten-free"] == Decimal("1.4")
    assert totals["Crushed tomatoes"] == 75
    assert p["total"] is None and p["can_commit"] is False


@pytest.mark.parametrize(
    "values",
    [
        {"vegetarian_gluten_free": 101},
        {"servings": 100},
        {"servings": 0},
        {"vegetarian": -1},
        {"servings": 1.5},
        {"recipe": {"pasta_g": "NaN"}},
        {"autonomous_limit": 99999},
    ],
)
def test_impossible_or_untrusted_inputs_rejected(values):
    with pytest.raises(ValidationError):
        planning.MealInput(**values)


def test_pack_rounding_and_unknown_evidence(products):
    assert planning.pack_kg(products["gf"]) == Decimal("1.25")
    results = planning.candidates("spaghetti", Decimal("5.01"), True, "any")
    good = next(c for c in results if c["product_id"] == "gf")
    assert good["quantity_sales_units"] == "5" and good["effective_kg"] == "6.25"
    assert good["status"] == "needs_chef_review"  # claim is not chef authorization
    bad = next(c for c in results if c["product_id"] == "pasta")
    assert bad["issues"] and bad["historical_reliability"] is None
    beef = planning.candidates("minced beef", Decimal(1), False, "finland")
    assert next(c for c in beef if c["product_id"] == "foreign")["issues"]
    unknown = copy.deepcopy(products["gf"])
    unknown["synkkaData"]["unitConversions"][0]["netWeight"]["unit"] = "LTR"
    assert planning.pack_kg(unknown) is None
    unknown["synkkaData"]["variableUnit"] = True
    assert planning.pack_kg(unknown) is None


def test_all_vegetarian_zero_groups_and_optional_addition(products):
    p = planning.plan(
        planning.MealInput(
            servings=50,
            vegetarian=50,
            gluten_free=50,
            vegetarian_gluten_free=50,
            include_carrot=True,
        )
    )
    assert not any("beef" in line["ingredient"] for line in p["lines"])
    assert not any(line["servings"] == 0 for line in p["lines"])
    assert all(line["gluten_free_required"] for line in p["lines"])
    assert p["lines"][-1]["required_kg"] == "1.5"


def test_plan_api_authenticated_persisted_and_review_only(products, tmp_path):
    store = Store(tmp_path / "planning.sqlite", postgres=False)
    app = create_app(store)
    c = TestClient(app)
    assert c.post("/api/v1/meal-plans", json={}).status_code == 401
    c.post("/api/v1/session", json={"access_code": access_codes()["buyer"]})
    p = c.post("/api/v1/meal-plans", json={})
    assert p.status_code == 200, p.text
    result = p.json()
    assert result == c.get("/api/v1/meal-plans/" + result["id"]).json()
    assert store.spent() == 0
    assert (
        c.post(
            "/api/v1/offers/" + result["id"] + "/commit",
            headers={"Idempotency-Key": "no-plan-commit"},
        ).status_code
        == 404
    )
    c.post("/api/v1/session", json={"access_code": access_codes()["approver"]})
    assert c.post("/api/v1/meal-plans", json={}).status_code == 403
    assert c.get("/api/v1/meal-plans/" + result["id"]).status_code == 200


def test_configurable_spend_thresholds_validate():
    assert (
        spend_limits({"AIMO_AUTONOMOUS_LIMIT": "1000"})["autonomous_limit"] == "1000.00"
    )
    for value in ["NaN", "Infinity", "-1", "1000.001", "1000001", "1e999999"]:
        with pytest.raises(ValueError):
            spend_limits({"AIMO_AUTONOMOUS_LIMIT": value})
    with pytest.raises(ValueError):
        spend_limits({"AIMO_EXCEPTION_LIMIT": "100"})


def test_ingredient_purpose_beats_prepared_food_with_better_claims(products):
    def row(pid, name, gf):
        p = copy.deepcopy(products["beef"])
        p["id"] = pid
        p["synkkaData"]["names"] = [{"language": "en", "value": name}]
        p["synkkaData"]["classifications"][0]["values"] = [{"id": "FREE_FROM_GLUTEN"}] if gf else []
        products[pid] = p
    row("salt", "Table salt", False)
    row("chips", "Potato chips with sea salt", True)
    row("onion", "Yellow onion", False)
    row("salad", "Onion salad", True)
    row("meatballs", "Minced beef meatballs", True)
    for query, expected, excluded in [("salt", "salt", "chips"), ("onion", "onion", "salad"), ("minced beef", "beef", "meatballs")]:
        candidates = planning.candidates(query, Decimal(1), True, "any")
        assert expected in [c["product_id"] for c in candidates]
        assert excluded not in [c["product_id"] for c in candidates]
        assert all(c["price"] is None and c["availability"] == "not_queried" for c in candidates)
    # Explicitly requesting a prepared product remains a valid catalog search.
    assert planning.candidates("minced beef meatballs", Decimal(1), True, "any")[0]["product_id"] == "meatballs"
    # Required claims remain unknown on raw ingredients; no chef authorization
    # or dietary safety is manufactured just to provide a complete plan.
    raw_salt = planning.candidates("salt", Decimal(1), True, "any")[0]
    assert raw_salt["status"] == "evidence_gap" and not raw_salt["gluten_free_claim"]


def test_planner_uses_quotation_mass_conflict_guard_and_finds_late_gf(products):
    late_gf = products.pop("gf")
    for i in range(25):
        p = copy.deepcopy(products["pasta"])
        p["id"] = f"pasta-{i}"
        products[p["id"]] = p
    products["gf"] = late_gf
    assert planning.candidates("spaghetti", Decimal(2), True, "any")[0]["product_id"] == "gf"
    butter = copy.deepcopy(products["beef"])
    butter["id"] = "butter-conflict"
    butter["units"][0]["sizeInBaseUnits"] = 4
    butter["synkkaData"]["names"] = [{"language": "en", "value": "Butter 4x5 kg unsalted"}]
    butter["synkkaData"]["unitConversions"][0]["netWeight"] = {"unit": "GRM", "value": 20000}
    products[butter["id"]] = butter
    assert planning.pack_kg(butter) is None
    candidate = planning.candidates("butter", Decimal(10), False, "any")[0]
    assert candidate["kg_per_sales_unit"] is None
    assert candidate["quantity_sales_units"] is None and candidate["effective_kg"] is None
    assert candidate["status"] == "evidence_gap" and any("conflict" in issue.lower() for issue in candidate["issues"])
