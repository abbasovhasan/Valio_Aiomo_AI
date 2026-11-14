"""Scoped, explicitly saved soft preferences; never a source of authority."""

import re
from typing import Literal

from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import policy


class PreferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preferred_brand: str | None = Field(default=None, max_length=80)
    preferred_origin: Literal["finland", "eu"] | None = None
    preferred_organic: bool = False
    priority: Literal["balanced", "cheapest", "quality", "origin", "delivery"] = "balanced"

    @field_validator("preferred_brand")
    @classmethod
    def clean_brand(cls, value):
        return value.strip() or None if value is not None else None


class PreferenceResponse(PreferenceInput):
    updated_at: str | None = None


def read(db, scope):
    stored = db.get("preferences", scope["buyer_id"], scope["buyer_id"])
    return PreferenceResponse.model_validate(stored or {}).model_dump()


def apply_saved(session, db, scope, message="", *, apply_priority=True):
    saved = read(db, scope)
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
