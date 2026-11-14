"""Scoped food restrictions and soft purchasing preferences; never authority."""

import re
from typing import Annotated, Literal

from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import policy


DietaryRestriction = Literal[
    "lactose_free", "milk_free", "gluten_free", "peanut_free", "nut_free",
    "egg_free", "soy_free", "fish_free", "crustacean_free", "mollusc_free",
    "celery_free", "mustard_free", "sesame_free", "sulphite_free", "lupin_free",
    "vegetarian", "vegan", "no_pork", "halal", "kosher",
]


def dietary_from_text(text):
    """Extract expressed restrictions, never infer suitability from a food name."""
    restrictions = []
    explicit = {
        "lactose_free": r"\blactose[- ]free\b|\b(?:no|without|avoid) lactose\b",
        "gluten_free": r"\bgluten[- ]free\b|\b(?:no|without|avoid) gluten\b|\bcoeliac\b|\bceliac\b",
        "milk_free": r"\b(?:milk|dairy)[- ]free\b|\b(?:no|without|avoid) (?:milk|dairy)\b",
        "vegetarian": r"\bvegetarian\b",
        "vegan": r"\bvegan\b",
        "no_pork": r"\b(?:no|without|avoid|exclude) pork\b|\bpork[- ]free\b",
        "halal": r"\bhalal\b",
        "kosher": r"\bkosher\b",
    }
    allergens = {
        "milk_free": r"milk|dairy", "peanut_free": r"peanuts?",
        "nut_free": r"(?:tree[- ]?)?nuts?", "egg_free": r"eggs?",
        "soy_free": r"soy|soya|soybeans?", "fish_free": r"fish",
        "crustacean_free": r"crustaceans?|shellfish|shrimp|prawns?",
        "mollusc_free": r"molluscs?|mollusks?|shellfish", "celery_free": r"celery",
        "mustard_free": r"mustard", "sesame_free": r"sesame(?: seeds?)?",
        "sulphite_free": r"sulphites?|sulfites?|sulphur dioxide|sulfur dioxide",
        "lupin_free": r"lupins?", "gluten_free": r"gluten",
    }
    for name, allergen in allergens.items():
        patterns = [
            r"\b(?:" + allergen + r")[- ]free\b",
            r"\b(?:no|without|avoid|exclude|free from) (?:" + allergen + r")\b",
            r"\b(?:" + allergen + r")\s+allerg(?:y|ies|ic)\b",
            r"\ballerg(?:y|ies|ic)\s+(?:to\s+)?(?:" + allergen + r")\b",
        ]
        if any(re.search(pattern, text, re.I) for pattern in patterns):
            restrictions.append(name)
    # Coordinated allergy lists such as "nut and peanut allergies" need both.
    allergen_names = "|".join("(?:" + pattern + ")" for pattern in allergens.values())
    allergen_list = r"(?:" + allergen_names + r")(?:\s*(?:,|and|&)\s*(?:" + allergen_names + r"))*"
    for match in re.finditer(r"\b(?:allergic to|allergies? to)\s+(" + allergen_list + r")\b|\b(" + allergen_list + r")\s+allerg(?:y|ies)\b", text, re.I):
        clause = match[1] or match[2]
        for name, allergen in allergens.items():
            if re.search(r"\b(?:" + allergen + r")\b", clause, re.I):
                restrictions.append(name)
    for name, pattern in explicit.items():
        if re.search(pattern, text, re.I):
            restrictions.append(name)
    return list(dict.fromkeys(restrictions))


class PreferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preferred_brand: str | None = Field(default=None, max_length=80)
    preferred_origin: Literal["finland", "eu"] | None = None
    preferred_organic: bool = False
    priority: Literal["balanced", "cheapest", "quality", "origin", "delivery"] = "balanced"
    dietary_restrictions: list[DietaryRestriction] = Field(default_factory=list, max_length=20)
    excluded_ingredients: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(default_factory=list, max_length=8)
    custom_preferences: str = Field(default="", max_length=500)

    @field_validator("preferred_brand")
    @classmethod
    def clean_brand(cls, value):
        return value.strip() or None if value is not None else None

    @field_validator("dietary_restrictions")
    @classmethod
    def unique_diets(cls, value):
        return list(dict.fromkeys(value))

    @field_validator("excluded_ingredients")
    @classmethod
    def clean_exclusions(cls, value):
        return list(dict.fromkeys(item.strip().casefold() for item in value if item.strip()))

    @field_validator("custom_preferences")
    @classmethod
    def clean_custom(cls, value):
        return value.strip()


class PreferenceResponse(PreferenceInput):
    updated_at: str | None = None


def read(db, scope):
    stored = db.get("preferences", scope["buyer_id"], scope["buyer_id"])
    return PreferenceResponse.model_validate(stored or {}).model_dump()


def enforce_hard(session, db, scope):
    """Rebuild effective restrictions from explicit intent and current defaults.

    Explicit and saved requirements need separate provenance: disabling a saved
    default can remove only that default, never a customer's requested allergy.
    Legacy lines without provenance retain their restrictions conservatively.
    """
    saved = read(db, scope)
    for line in session["lines"]:
        for requested, effective, defaults in [
            ("requested_dietary", "dietary", "dietary_restrictions"),
            ("requested_excluded_ingredients", "excluded_ingredients", "excluded_ingredients"),
        ]:
            if requested not in line:
                line[requested] = list(dict.fromkeys(line.get(effective, [])))
            line[effective] = list(dict.fromkeys(line[requested] + saved[defaults]))
    session["saved_restrictions_applied"] = {key: saved[key] for key in ["dietary_restrictions", "excluded_ingredients"]}
    return saved


def apply_saved(session, db, scope, message="", *, apply_priority=True, hard_only=False):
    saved = enforce_hard(session, db, scope)
    if hard_only:
        return
    for line in session["lines"]:
        if not line.get("preferred_brand") and not line.get("required_brand"):
            line["preferred_brand"] = saved["preferred_brand"]
        if not line.get("preferred_origin") and not line.get("origin"):
            line["preferred_origin"] = saved["preferred_origin"]
        if not line.get("preferred_organic") and not line.get("require_organic"):
            line["preferred_organic"] = saved["preferred_organic"]
    explicit_priority = re.search(r"cheap|affordable|economical|lowest|quality|origin first|delivery first|earliest|fastest|balanced", message, re.I)
    if apply_priority and not explicit_priority and session["constraints"]["preferences"] == "balanced":
        session["constraints"]["preferences"] = saved["priority"]
    session["saved_preferences_applied"] = saved


def register_routes(app, db, buyer, limit):
    @app.get("/api/v1/preferences", response_model=PreferenceResponse)
    def get_preferences(scope=Depends(buyer)):
        return read(db, scope)

    @app.put("/api/v1/preferences", response_model=PreferenceResponse)
    def save_preferences(data: PreferenceInput, scope=Depends(buyer)):
        limit("preferences-" + scope["buyer_id"], 30)
        value = data.model_dump() | {"updated_at": policy.now().isoformat()}
        db.save("preferences", scope["buyer_id"], scope["buyer_id"], value)
        db.audit(policy.uid("audit"), scope["buyer_id"], "preferences_saved", value)
        return value
