"""Behavioral tests for traceable dimensions, suitability and candidate recall."""

from decimal import Decimal

import pytest

from backend import catalog, product_facts as facts


@pytest.fixture
def products(monkeypatch):
    def row(pid, name="Spaghetti", claims=None, base="ST", sales="KI", size=4,
            net=500, net_unit="GRM", volume=None, variable=False, origin="246"):
        conversion = {"synkkaPackagingType": "BASE_UNIT_OR_EACH"}
        if net is not None:
            conversion["netWeight"] = {"value": net, "unit": net_unit}
        if volume is not None:
            conversion["volume"] = {"value": volume, "unit": "LTR"}
        return {
            "id": pid, "baseUnit": base, "salesUnit": sales,
            "allowedLotSize": .01, "deleted": False, "deposits": [],
            "units": [{"unitId": sales, "sizeInBaseUnits": size}],
            "synkkaData": {"names": [{"language": "en", "value": name}],
                           "countriesOfOrigin": [origin] if origin else [],
                           "variableUnit": variable, "unitConversions": [conversion],
                           "classifications": [{"name": "nutritionalClaim", "values": [{"id": c} for c in claims or []]}]},
        }
    rows = {
        "100": row("100", claims=["VEGAN"]),
        "200": row("200", "Spaghetti gluten free", ["FREE_FROM_GLUTEN", "VEGAN"]),
        "300": row("300", "Milk drink 1 l", ["FREE_FROM_LACTOSE"], size=5, volume=1),
        "400": row("400", "Mushrooms", base="KG", size=2, net=None),
        "500": row("500", "Variable beef", variable=True),
        "600": row("600", "Mushrooms 2kg case", net=None),
    }
    monkeypatch.setattr(catalog, "load_catalog", lambda: rows)
    monkeypatch.setattr(catalog, "supplemental", lambda: {})
    return rows, row


def test_net_mass_conversion_and_whole_pack_rounding(products):
    p = facts.normalize("100")
    assert p["kg_per_sales_unit"] == "2.0"
    assert facts.units_for(p, Decimal("2.01"), "kg") == 2
    assert facts.units_for(p, Decimal(2001), "g") == 2
    assert facts.units_for(p, Decimal(5), "pieces") == 2
    assert facts.units_for(p, Decimal("1.1"), "packages") == 2
    assert p["conversion_evidence"]["kg"].startswith("BASE_UNIT_OR_EACH.netWeight")
    p["allowed_lot_size"] = "1.5"
    assert facts.units_for(p, Decimal("2.01"), "kg") == 3
    p["allowed_lot_size"] = "0.4"
    assert facts.units_for(p, Decimal("0.1"), "kg") == 2


def test_volume_uses_explicit_volume_and_never_density(products):
    p = facts.normalize("300")
    assert p["liters_per_sales_unit"] == "5"
    assert p["kg_per_sales_unit"] == "2.5"
    assert facts.units_for(p, 5001, "ml") == 2
    p = facts.normalize("100")
    assert facts.units_for(p, 1, "L") is None


def test_base_kg_case_is_mass_not_piece_count(products):
    p = facts.normalize("400")
    assert p["kg_per_sales_unit"] == "2"
    assert p["pieces_per_sales_unit"] is None
    assert facts.units_for(p, 3, "kg") == 2
    assert facts.units_for(p, 3, "pieces") is None


def test_variable_unknown_and_gross_weight_cannot_establish_mass(products):
    rows, _ = products
    rows["600"]["synkkaData"]["unitConversions"][0]["grossWeight"] = {"unit": "KGM", "value": 2}
    assert facts.normalize("600")["kg_per_sales_unit"] is None
    assert facts.units_for(facts.normalize("600"), 1, "kg") is None
    assert facts.units_for(facts.normalize("500"), 1, "packages") is None
    for amount in [0, -1, "NaN", "Infinity", None]:
        assert facts.units_for(facts.normalize("100"), amount, "kg") is None
    assert facts.units_for(facts.normalize("100"), 1, "unknown") is None


def test_diet_claims_are_explicit_and_origin_preserves_conflicts(products):
    rows, _ = products
    p = facts.normalize("100")
    assert facts.suitability(p, ["vegan", "vegetarian"], "finland") == []
    assert facts.suitability(p, ["gluten_free"])
    assert facts.suitability(p, ["nut_free"])
    rows["100"]["countryOfOrigin"] = "CN"
    assert facts.suitability(facts.normalize("100"), [], "finland")
    rows["100"]["synkkaData"]["countriesOfOrigin"] = []
    rows["100"]["countryOfOrigin"] = "fi"
    assert facts.suitability(facts.normalize("100"), [], "EU") == []
    rows["100"]["countryOfOrigin"] = ""
    assert facts.suitability(facts.normalize("100"), [], "EU")


def test_search_ranks_suitable_products_before_truncation_and_supports_sku(products):
    rows, row = products
    for n in range(30):
        rows[str(n)] = row(str(n))
    result = facts.search("spaghetti", limit=1, dietary=["gluten_free"])
    assert result[0]["id"] == "200"
    assert facts.search("300")[0]["id"] == "300"
    assert facts.search("nonexistent product") == []
    rows["200"]["deleted"] = True
    assert all(p["id"] != "200" for p in facts.search("spaghetti"))


def test_supplier_name_litres_are_traceable_but_multipacks_not_guessed(products):
    rows, row = products
    rows["700"] = row("700", "Milk drink 1 l", size=5, net=None)
    assert facts.normalize("700")["liters_per_sales_unit"] == "5"
    rows["700"]["synkkaData"]["names"][0]["value"] = "Milk 6 x 1 l"
    assert facts.normalize("700")["liters_per_sales_unit"] is None


def test_inconsistent_dimensions_remain_unknown(products):
    rows, _ = products
    rows["100"]["units"].append({"unitId": "KI", "sizeInBaseUnits": 5})
    assert facts.normalize("100")["kg_per_sales_unit"] is None


def test_ingredient_relevance_is_not_overridden_by_ready_food_diet_claims(products):
    rows, row = products
    rows["010"] = row("010", "Spaghetti Sauce", ["FREE_FROM_GLUTEN"])
    rows["020"] = row("020", "Salt Potato Chips")
    rows["030"] = row("030", "Sea Salt")
    assert all("Sauce" not in p["name"] for p in facts.search("spaghetti", dietary=["gluten_free"]))
    assert [p["id"] for p in facts.search("salt")] == ["030"]
    rows["040"] = row("040", "Milk free spread", ["FREE_FROM_LACTOSE"])
    assert all(p["id"] != "040" for p in facts.search("milk", dietary=["lactose_free"]))


def test_inconsistent_named_multipack_mass_blocks_instead_of_guessing(products):
    rows, row = products
    # Exact real-catalog contradiction observed on Valio butter SKU 464205.
    rows["464205"] = row("464205", "Valio butter 4x5kg unsalted", size=4, net=20000)
    p = facts.normalize("464205")
    assert p["kg_per_sales_unit"] is None
    assert "Conflicting package mass" in p["conversion_issues"][0]
    assert facts.units_for(p, 30, "kg") is None
    # A consistent multiplier remains usable, and names cannot create mass.
    rows["800"] = row("800", "Butter 4 x 5 kg", size=4, net=5000)
    assert facts.normalize("800")["kg_per_sales_unit"] == "20"
    rows["801"] = row("801", "Butter 5kg x4", size=4, net=20000)
    assert facts.normalize("801")["kg_per_sales_unit"] is None
    rows["802"] = row("802", "Butter 4x5kg", size=4, net=None)
    assert facts.normalize("802")["kg_per_sales_unit"] is None


def test_raw_ingredients_are_not_replaced_by_prepared_food_with_diet_claims(products):
    rows, row = products
    for pid, name in [("010", "Raw Onion"), ("020", "Sea Salt"), ("030", "Minced Beef")]:
        rows[pid] = row(pid, name)
    for pid, name in [("011", "Onion Salad"), ("012", "Onion Sausage Coldcut"),
                      ("021", "Salt Pepper Garlic Spice Mix"), ("022", "Salt licorice dates"),
                      ("023", "Chicken Strips with Sea Salt"), ("024", "Less Salt Ketchup"),
                      ("031", "Cooked Minced Beef"), ("032", "Minced Beef Meatballs"),
                      ("033", "Minced Beef Bolognese")]:
        rows[pid] = row(pid, name, ["FREE_FROM_GLUTEN"])
    for query, wanted in [("onion", "010"), ("salt", "020"), ("minced beef", "030")]:
        results = facts.search(query, dietary=["gluten_free"])
        assert [p["id"] for p in results] == [wanted]
        assert facts.suitability(results[0], ["gluten_free"])
    # Explicitly requested prepared foods remain discoverable.
    assert facts.search("onion salad")[0]["id"] == "011"
