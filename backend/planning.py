"""Review-only meal planning. Recipe text and supplier records carry no authority."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import catalog, product_facts

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


class MealInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    servings: int = Field(default=500, ge=1, le=10000, strict=True)
    vegetarian: int = Field(default=100, ge=0, le=10000, strict=True)
    gluten_free: int = Field(default=50, ge=0, le=10000, strict=True)
    vegetarian_gluten_free: int = Field(default=20, ge=0, le=10000, strict=True)
    meat_origin: Literal["any", "finland", "eu"] = "finland"
    priority: Literal["price", "quality", "balanced"] = "balanced"
    recipe_source: Literal["proposed", "customer"] = "proposed"
    recipe: RecipeAmounts = Field(default_factory=RecipeAmounts)
    include_carrot: bool = False

    @model_validator(mode="after")
    def consistent_cohorts(self):
        if self.vegetarian_gluten_free > min(self.vegetarian, self.gluten_free):
            raise ValueError(
                "The overlapping group cannot exceed either dietary group."
            )
        if (
            self.vegetarian + self.gluten_free - self.vegetarian_gluten_free
            > self.servings
        ):
            raise ValueError("Dietary groups exceed the total number of diners.")
        return self


def pack_kg(p):
    """Use the same conservative conversion as quotation for a current record."""
    pid = str(p.get("id"))
    if catalog.load_catalog().get(pid) != p:
        return None
    mass = product_facts.normalize(pid).get("kg_per_sales_unit")
    return D(mass) if mass else None


def candidates(query, kg, gf, origin):
    out = []
    # Preserve shared ingredient-purpose ranking before checking dietary evidence.
    # Names propose candidates; the chef still reviews every recipe choice.
    for p in product_facts.search(query, 20, ["gluten_free"] if gf else [], origin):
        cs = set(p.get("claims", []))
        countries = p.get("origin_codes", [])
        gf_ok = "FREE_FROM_GLUTEN" in cs
        mass = D(p["kg_per_sales_unit"]) if p.get("kg_per_sales_unit") else None
        units = product_facts.units_for(p, kg, "kg")
        issues = product_facts.suitability(p, ["gluten_free"] if gf else [], origin)
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
                "status": "needs_chef_review" if not issues else "evidence_gap",
                "price": None,
                "availability": "not_queried",
            }
        )
    # Stable sorting retains lexical purpose ranking within each evidence tier.
    out.sort(key=lambda x: bool(x["issues"]))
    return out[:3]


def plan(data: MealInput):
    r = data.recipe
    n = data.servings
    veg = data.vegetarian
    lines = []

    def add(label, query, servings, grams, gf=False, origin="any"):
        if servings <= 0:
            return
        kg = D(servings) * grams / 1000
        lines.append(
            {
                "ingredient": label,
                "search_query": query,
                "servings": servings,
                "grams_per_serving": str(grams),
                "required_kg": str(kg),
                "gluten_free_required": gf,
                "meat_origin": origin,
                "candidates": candidates(query, kg, gf, origin),
            }
        )

    add("Dry spaghetti · standard", "spaghetti", n - data.gluten_free, r.pasta_g)
    add("Dry spaghetti · gluten-free", "spaghetti", data.gluten_free, r.pasta_g, True)
    add(
        "Raw minced beef · standard",
        "minced beef",
        n - veg - data.gluten_free + data.vegetarian_gluten_free,
        r.beef_g,
        origin=data.meat_origin,
    )
    add(
        "Raw minced beef · gluten-free",
        "minced beef",
        data.gluten_free - data.vegetarian_gluten_free,
        r.beef_g,
        True,
        data.meat_origin,
    )
    add(
        "Dry lentils · vegetarian",
        "red lentils",
        veg - data.vegetarian_gluten_free,
        r.dry_lentils_g,
    )
    add(
        "Dry lentils · vegetarian & gluten-free",
        "red lentils",
        data.vegetarian_gluten_free,
        r.dry_lentils_g,
        True,
    )
    # Shared sauce must satisfy the most restrictive group using it.
    for label, query, grams in [
        ("Crushed tomatoes", "crushed tomatoes", r.tomatoes_g),
        ("Onions", "onion", r.onion_g),
        ("Oil", "olive oil", r.oil_g),
        ("Salt", "salt", r.salt_g),
        ("Oregano", "oregano", r.oregano_g),
    ]:
        add(label, query, n, grams, data.gluten_free > 0)
    if data.include_carrot:
        add("Carrot · chosen addition", "carrot", n, D(30), data.gluten_free > 0)
    return {
        "dish": "Spaghetti bolognese / lentil bolognese",
        "status": "draft_needs_review",
        "request": data.model_dump(mode="json"),
        "cohorts": {
            "meat_standard": n - veg - data.gluten_free + data.vegetarian_gluten_free,
            "meat_gluten_free": data.gluten_free - data.vegetarian_gluten_free,
            "vegetarian_standard": veg - data.vegetarian_gluten_free,
            "vegetarian_gluten_free": data.vegetarian_gluten_free,
        },
        "lines": lines,
        "total": None,
        "can_commit": False,
        "recipe_note": "Illustrative raw/dry ingredient quantities; chef must validate recipe, yield, seasoning, and separate preparation. Customer source means customer-entered quantities, not a verified recipe.",
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
