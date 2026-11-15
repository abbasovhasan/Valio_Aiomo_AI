"""Review-only meal planning. Recipe text and supplier records carry no authority."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import catalog, product_facts
from .preferences import DietaryRestriction

D = Decimal


class RecipeAmounts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pasta_g: Decimal = Field(default=D(100), gt=0, le=500, decimal_places=2)
    beef_g: Decimal = Field(default=D(120), gt=0, le=500, decimal_places=2)
    dry_lentils_g: Decimal = Field(default=D(70), gt=0, le=500, decimal_places=2)
    tomatoes_g: Decimal = Field(default=D(150), gt=0, le=500, decimal_places=2)
    onion_g: Decimal = Field(default=D(30), gt=0, le=500, decimal_places=2)
    oil_g: Decimal = Field(default=D(10), gt=0, le=100, decimal_places=2)
    salt_g: Decimal = Field(default=D(1), gt=0, le=10, decimal_places=2)
    oregano_g: Decimal = Field(default=D("0.5"), gt=0, le=10, decimal_places=2)


class IngredientInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    label: str = Field(min_length=1, max_length=200)
    query: str = Field(min_length=1, max_length=200)
    grams_per_serving: Decimal = Field(gt=0, le=5000, decimal_places=2)
    applies_to: Literal["all", "meat", "vegetarian"] = "all"
    split_gluten_free: bool = False
    dietary: list[DietaryRestriction] = Field(default_factory=list, max_length=16)
    origin: Literal["any", "finland", "eu"] | None = None

    @field_validator("label", "query")
    @classmethod
    def meaningful_text(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError("Enter an ingredient name without control characters.")
        value.encode("utf-8")
        return value


class MealInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meal_name: str = Field(default="Spaghetti bolognese", min_length=1, max_length=120)
    template: Literal["bolognese", "custom"] = "bolognese"
    servings: int = Field(default=500, ge=1, le=10000, strict=True)
    vegetarian: int = Field(default=100, ge=0, le=10000, strict=True)
    gluten_free: int = Field(default=50, ge=0, le=10000, strict=True)
    vegetarian_gluten_free: int = Field(default=20, ge=0, le=10000, strict=True)
    meat_origin: Literal["any", "finland", "eu"] = "finland"
    priority: Literal["price", "quality", "balanced"] = "balanced"
    recipe_source: Literal["proposed", "customer"] = "proposed"
    recipe: RecipeAmounts = Field(default_factory=RecipeAmounts)
    include_carrot: bool = False
    dietary_restrictions: list[DietaryRestriction] = Field(default_factory=list, max_length=16)
    ingredients: list[IngredientInput] | None = Field(default=None, min_length=1, max_length=12)
    preferred_brand: str | None = Field(default=None, min_length=1, max_length=80)
    preferred_origin: Literal["finland", "eu"] | None = None

    @field_validator("meal_name", "preferred_brand")
    @classmethod
    def meaningful_text(cls, value):
        if value is not None:
            value = value.strip()
            if not value or any(ord(c) < 32 for c in value):
                raise ValueError("Enter a name without control characters.")
            value.encode("utf-8")
        return value

    @model_validator(mode="after")
    def consistent_cohorts(self):
        if any(value in self.dietary_restrictions for value in ["vegetarian", "vegan"]):
            self.vegetarian = self.servings
            self.vegetarian_gluten_free = self.gluten_free
        if "gluten_free" in self.dietary_restrictions:
            self.gluten_free = self.servings
            self.vegetarian_gluten_free = self.vegetarian
        if self.ingredients and len({item.id for item in self.ingredients}) != len(self.ingredients):
            raise ValueError("Each ingredient needs its own stable identifier.")
        if self.template == "custom" and not self.ingredients:
            raise ValueError("Add your ingredients and grams per serving for this meal; no verified recipe is supplied.")
        if self.ingredients is None and not any(word in self.meal_name.casefold() for word in ["bolognese", "bolognaise"]):
            raise ValueError("Only an illustrative bolognese template is available. Add your own ingredients for another meal.")
        if self.vegetarian_gluten_free > min(self.vegetarian, self.gluten_free):
            raise ValueError(
                "The overlapping group cannot exceed either dietary group."
            )
        if (
            self.vegetarian + self.gluten_free - self.vegetarian_gluten_free
            > self.servings
        ):
            raise ValueError("Dietary groups exceed the total number of diners.")
        if self.ingredients and not any(item.applies_to == "all" or item.applies_to == "meat" and self.vegetarian < self.servings or item.applies_to == "vegetarian" and self.vegetarian > 0 for item in self.ingredients):
            raise ValueError("No ingredient serves the selected groups. Change an ingredient’s serving group or the dietary counts.")
        return self


def pack_kg(p):
    """Use the same conservative conversion as quotation for a current record."""
    pid = str(p.get("id"))
    if catalog.load_catalog().get(pid) != p:
        return None
    mass = product_facts.normalize(pid).get("kg_per_sales_unit")
    return D(mass) if mass else None


def candidates(query, kg, gf, origin, dietary=None, excluded_ingredients=None, preferred_brand=None, preferred_origin=None):
    out = []
    # Preserve shared ingredient-purpose ranking before checking dietary evidence.
    # Names propose candidates; the chef still reviews every recipe choice.
    restrictions = list(dict.fromkeys((["gluten_free"] if gf else []) + list(dietary or [])))
    for p in product_facts.search(query, 20, restrictions, origin, preferred_brand=preferred_brand, preferred_origin=preferred_origin):
        if p.get("purpose_review_required"):
            # A raw recipe ingredient is an explicit purpose constraint. The
            # complete catalog search still exposes these prepared products.
            continue
        cs = set(p.get("claims", []))
        countries = p.get("origin_codes", [])
        gf_ok = "FREE_FROM_GLUTEN" in cs
        mass = D(p["kg_per_sales_unit"]) if p.get("kg_per_sales_unit") else None
        units = product_facts.units_for(p, kg, "kg")
        issues = product_facts.suitability(p, restrictions, origin, excluded_ingredients=excluded_ingredients)
        dietary_issues = product_facts.suitability(p, restrictions, excluded_ingredients=excluded_ingredients)
        dietary_status = "not_requested" if not restrictions and not excluded_ingredients else "verified_compatible" if not dietary_issues else "verified_incompatible" if any(issue.startswith(("Supplier declares contains", "Identified pork", "Identified excluded")) for issue in dietary_issues) else "evidence_missing"
        if units is None:
            issues.append("Fixed net mass / lot conversion unavailable.")
            issues.extend(p.get("conversion_issues", []))
        if p.get("deposits"):
            issues.append("Deposit charges need separate validation.")
        out.append(
            {
                "product_id": p["id"],
                "name": p["name"],
                "sales_unit": p.get("sales_unit"),
                "kg_per_sales_unit": str(mass) if mass else None,
                "quantity_sales_units": str(units) if units is not None else None,
                "effective_kg": str(units * mass) if units is not None else None,
                "origin_codes": countries,
                "gluten_free_claim": gf_ok,
                "claims": sorted(x for x in cs if x),
                "historical_reliability": p.get("reliability"),
                "issues": issues,
                "selectable": not issues,
                "dietary_status": dietary_status,
                "status": "needs_chef_review" if not issues else "evidence_gap",
                "price": None,
                "availability": "not_queried",
            }
        )
    # Stable sorting retains lexical purpose ranking within each evidence tier.
    out.sort(key=lambda x: bool(x["issues"]))
    return out[:3]


def recipe_ingredients(data: MealInput):
    """Only the named illustrative template supplies quantities automatically."""
    if data.ingredients is not None:
        return data.ingredients
    r = data.recipe
    ingredients = [
        IngredientInput(id="pasta", label="Dry spaghetti", query="spaghetti", grams_per_serving=r.pasta_g, split_gluten_free=True),
        IngredientInput(id="beef", label="Raw minced beef", query="minced beef", grams_per_serving=r.beef_g, applies_to="meat", split_gluten_free=True),
        IngredientInput(id="lentils", label="Dry lentils", query="red lentils", grams_per_serving=r.dry_lentils_g, applies_to="vegetarian", split_gluten_free=True),
        IngredientInput(id="tomatoes", label="Crushed tomatoes", query="crushed tomatoes", grams_per_serving=r.tomatoes_g),
        IngredientInput(id="onion", label="Onions", query="onion", grams_per_serving=r.onion_g),
        IngredientInput(id="oil", label="Oil", query="olive oil", grams_per_serving=r.oil_g),
        IngredientInput(id="salt", label="Salt", query="salt", grams_per_serving=r.salt_g),
        IngredientInput(id="oregano", label="Oregano", query="oregano", grams_per_serving=r.oregano_g),
    ]
    if data.include_carrot:
        ingredients.append(IngredientInput(id="carrot", label="Carrot · chosen addition", query="carrot", grams_per_serving=D(30)))
    return ingredients


def plan(data: MealInput, dietary=None, excluded_ingredients=None):
    n = data.servings
    recipe_dietary = list(dict.fromkeys(data.dietary_restrictions))
    restrictions = list(dict.fromkeys(recipe_dietary + list(dietary or [])))
    # Whole-meal choices define the recipe. Saved hard preferences validate
    # candidates separately, preserving their removable preference provenance.
    veg = n if any(value in recipe_dietary for value in ["vegetarian", "vegan"]) else data.vegetarian
    gf = n if "gluten_free" in recipe_dietary else data.gluten_free
    overlap = gf if veg == n else veg if gf == n else data.vegetarian_gluten_free
    cohorts = {"meat_standard": n - veg - gf + overlap, "meat_gluten_free": gf - overlap,
        "vegetarian_standard": veg - overlap, "vegetarian_gluten_free": overlap}
    ingredients = recipe_ingredients(data)
    lines = []
    for ingredient in ingredients:
        group = ingredient.applies_to
        count = n if group == "all" else n - veg if group == "meat" else veg
        gf_count = gf if group == "all" else gf - overlap if group == "meat" else overlap
        line_restrictions = list(dict.fromkeys(recipe_dietary + ingredient.dietary))
        if group != "meat" and veg > 0:
            line_restrictions = list(dict.fromkeys(line_restrictions + ["vegetarian"]))
        origin = ingredient.origin or (data.meat_origin if group == "meat" else "any")
        portions = [("standard", count - gf_count, False), ("gluten-free", gf_count, True)] if ingredient.split_gluten_free else [("shared", count, gf_count > 0)]
        for cohort, servings, needs_gf in portions:
            if servings <= 0:
                continue
            dietary_for_line = list(dict.fromkeys(line_restrictions + (["gluten_free"] if needs_gf else [])))
            suffix = ""
            if ingredient.split_gluten_free:
                suffix = " · " + ("vegetarian & gluten-free" if group == "vegetarian" and needs_gf else "vegetarian" if group == "vegetarian" else cohort)
            kg = D(servings) * ingredient.grams_per_serving / 1000
            lines.append({
                "id": f"{ingredient.id}-{cohort}", "ingredient_id": ingredient.id,
                "ingredient": ingredient.label + suffix, "search_query": ingredient.query,
                "servings": servings, "grams_per_serving": str(ingredient.grams_per_serving),
                "required_kg": str(kg), "gluten_free_required": needs_gf,
                "dietary": dietary_for_line, "origin": origin if origin != "any" else None,
                "meat_origin": origin, "applies_to": group,
                "preferred_brand": data.preferred_brand, "preferred_origin": data.preferred_origin,
                "candidates": candidates(ingredient.query, kg, needs_gf, origin, list(dict.fromkeys(dietary_for_line + list(dietary or []))),
                    excluded_ingredients, data.preferred_brand, data.preferred_origin),
            })
    request = data.model_dump(mode="json")
    if data.ingredients is not None:
        # These legacy template fields did not participate in this calculation.
        # Retaining their default beef/pasta grams would misstate a custom plan.
        request.pop("recipe", None)
        request.pop("include_carrot", None)
    return {
        "dish": data.meal_name,
        "status": "draft_needs_review",
        "request": request,
        "cohorts": cohorts,
        "ingredients": [ingredient.model_dump(mode="json") for ingredient in ingredients],
        "recipe_provenance": "customer_entered_unverified" if data.recipe_source == "customer" or data.template == "custom" else "illustrative_bolognese_template",
        "verified_recipe": False,
        "dietary_restrictions": restrictions,
        "lines": lines,
        "total": None,
        "can_commit": False,
        "recipe_note": "Customer-entered raw/dry quantities; not a verified recipe. Chef must validate recipe, yield, seasoning and separate preparation." if data.recipe_source == "customer" or data.template == "custom" else "Illustrative bolognese quantities, not an official or verified recipe. Chef must validate recipe, yield, seasoning and separate preparation.",
        "preference_note": {
            "price": "Compare tax-inclusive whole-pack prices after live quotation; no cheapest claim before prices exist.",
            "quality": "Review product specifications with the chef; the catalog supplies no verified quality score.",
            "balanced": "Compare price and chef-reviewed specifications together after quotation.",
        }[data.priority],
        "next_steps": [
            "Chef checks product purpose, ingredient lists and dietary suitability for every line; missing claims remain unknown.",
            "Consolidate selected SKUs across cohorts, round whole packs, and obtain date-specific prices and availability.",
            "Authorize the whole basket under a customer mandate before a simulated commitment.",
        ],
        "reliability_note": "Historical delivered-quantity ratio from challenge data; missing means unknown. It is not an on-time delivery probability.",
        "boundaries": "Local catalog planning only. No price/stock lookup, cart write, order, invoice or payment is made.",
    }
