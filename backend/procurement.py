"""Persistent customer purchasing sessions; every commitment is item-price simulation.

This is a separate authored, customer-confirmed basket policy. It does not widen
the breakfast milk agent's approved assortment or let buyer prose grant authority.
"""

import copy
import hashlib
import hmac
import json
import re
from datetime import date as Date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from fractions import Fraction
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import catalog, policy, upstream, product_facts
from .config import MANDATE
from .procurement_contract import ProcurementSessionResponse, ReceiptVerificationResponse

D = Decimal
PREFIX = "/api/v1/procurement/sessions"
ITEM_OPTIONS = {"required_brand": None, "preferred_brand": None, "preferred_origin": None, "require_organic": False, "preferred_organic": False, "retrieval_queries": [], "excluded_ingredients": []}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="after")
    @classmethod
    def valid_text_encoding(cls, value):
        if isinstance(value, str):
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                raise ValueError("Enter valid Unicode text.") from None
        return value


class CreateSession(Strict):
    message: str = Field(min_length=1, max_length=3000)
    mode: Literal["fixture", "live"] = "fixture"
    use_model: bool = False
    apply_preferences: bool = True
    date: Date | None = None
    budget: Decimal | None = Field(default=None, ge=0, le=1000000, decimal_places=2)


class Action(Strict):
    version: int = Field(ge=1)
    action: Literal[
        "message", "select_product", "set_quantity", "remove_line", "set_budget",
        "set_date", "set_query", "quote", "acknowledge_recipe", "add_product",
    ]
    message: str | None = Field(default=None, min_length=1, max_length=3000)
    line_id: str | None = Field(default=None, max_length=80)
    product_id: str | None = Field(default=None, max_length=80)
    query: str | None = Field(default=None, min_length=1, max_length=500)
    quantity: Decimal | None = Field(default=None, gt=0, le=1000000, decimal_places=3)
    unit: Literal["L", "kg", "pieces", "packages"] | None = None
    budget: Decimal | None = Field(default=None, ge=0, le=1000000, decimal_places=2)
    date: Date | None = None


class FromMealPlan(Strict):
    plan_id: str = Field(min_length=1, max_length=80)
    selections: dict[int, str] = Field(default_factory=dict, max_length=24)
    mode: Literal["fixture", "live"] = "fixture"
    apply_preferences: bool = True
    date: Date | None = None
    budget: Decimal | None = Field(default=None, ge=0, le=1000000, decimal_places=2)


class FromProduct(Strict):
    product_id: str = Field(min_length=1, max_length=80)
    quantity: Decimal = Field(default=Decimal(1), gt=0, le=1000000, decimal_places=3)
    unit: Literal["L", "kg", "pieces", "packages"] = "packages"
    mode: Literal["fixture", "live"] = "live"
    apply_preferences: bool = True
    date: Date | None = None
    budget: Decimal | None = Field(default=None, ge=0, le=1000000, decimal_places=2)


class Fingerprint(Strict):
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    version: int | None = Field(default=None, ge=1)


class Rejection(Fingerprint):
    reason: str | None = Field(default=None, max_length=500)


class ApprovalRequest(Fingerprint):
    version: int = Field(ge=1)
    explanation: str | None = Field(default=None, max_length=500)


class ChangesRequest(Fingerprint):
    version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)


class Cancellation(Strict):
    version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=500)


def fail(code, message, status=409):
    raise HTTPException(status, detail={"code": code, "message": message})


def decimal(value):
    try:
        n = D(str(value))
        return n if n.is_finite() else None
    except (ValueError, TypeError, InvalidOperation):
        return None


def money(value):
    return format(value.quantize(D(".01"), rounding=ROUND_HALF_UP), ".2f")


def authority():
    keys = ["autonomous_limit", "exception_limit", "cumulative_limit", "expires_at", "allow_budget_exceptions"]
    if any(key not in MANDATE for key in keys):
        fail("policy_unavailable", "Trusted purchasing policy is incomplete. Ask the operator to restore it; no purchasing authority is granted.", 503)
    amounts = [decimal(MANDATE[key]) for key in keys[:3]]
    if any(value is None or value < 0 or value > 1000000 or value != value.quantize(D(".01")) for value in amounts) or not amounts[0] <= amounts[1] <= amounts[2] or not policy.parse_time(MANDATE["expires_at"]) or not isinstance(MANDATE["allow_budget_exceptions"], bool):
        fail("policy_unavailable", "Trusted purchasing policy is invalid. No purchasing authority is granted.", 503)
    return {
        "id": "customer-confirmed-demo-basket-v1",
        "assortment": "Customer explicitly reviews selected real catalog products; hard dietary evidence remains mandatory.",
        "autonomous_limit": MANDATE["autonomous_limit"],
        "exception_limit": MANDATE["exception_limit"],
        "cumulative_limit": MANDATE["cumulative_limit"],
        "expires_at": MANDATE["expires_at"],
        "confirmation_required": True,
        "orders": "simulated_only",
        "budget_exceptions": MANDATE["allow_budget_exceptions"],
        "approver_permissions": ["requested_budget", "spending_authority"],
        "cumulative_scope": "Lifetime committed simulated spend for this buyer workspace; no calendar reset or verified bank/credit balance.",
        "pending_reservations": False,
    }


def decision_blockers(session, scope, assignment=None):
    reasons = []
    if not assignment or not assignment.get("active") or assignment.get("customer_id") != session["customer_id"] or scope.get("principal_id") not in assignment.get("approver_principals", []):
        reasons.append("This manager is not currently assigned to the request’s workspace.")
    else:
        required = set(session.get("approval", {}).get("reasons", []))
        maximum = decimal(assignment.get("max_total"))
        total = decimal((session.get("offer") or {}).get("total"))
        if not required.issubset(set(assignment.get("permissions", []))) or maximum is None or total is None or total > maximum:
            reasons.append("The assigned manager lacks permission or financial authority for all requested exceptions.")
    if not session.get("requester_actor") or not session.get("requester_principal"):
        return reasons + ["The buyer must refresh this older draft before it can receive an independent decision."]
    if not scope.get("actor_id") or not scope.get("principal_id"):
        return reasons + ["A server-authenticated manager identity is required."]
    if scope["actor_id"] == session["requester_actor"] or scope["principal_id"] == session["requester_principal"]:
        reasons.append("You cannot decide your own request by switching roles. Use a separate authorized manager browser/session.")
    return reasons


def assignment_blockers(session, assignment):
    if not assignment or not assignment.get("active") or assignment.get("customer_id") != session["customer_id"] or not assignment.get("approver_principals"):
        return ["No eligible manager is currently assigned to this workspace. Keep editing or ask the operator to restore the assignment."]
    reasons = set(session.get("approval", {}).get("reasons", []))
    maximum = decimal(assignment.get("max_total"))
    total = decimal((session.get("cart") or {}).get("subtotal"))
    if not reasons.issubset(set(assignment.get("permissions", []))) or maximum is None or total is None or total > maximum:
        return ["No assigned manager has sufficient permission and financial authority for every requested exception."]
    return []


def current_review_context(db, scope):
    """Request-local hard facts only; no supplier lookup or purchasing writes."""
    from .preferences import read
    context = {"spent": db.spent(scope["buyer_id"]), "assignment": db.workspace_authority(scope["buyer_id"], scope["customer_id"])}
    try:
        context["policy"] = authority()
    except HTTPException:
        context["policy"] = None
    try:
        context["preferences"] = read(db, scope)
    except (ValueError, TypeError):
        context["preferences"] = None
    return context


def current_review(session, db, *, context=None):
    """Overlay current hard gates without modifying the reviewed snapshot."""
    from .preferences import enforce_hard
    context = context if context is not None else current_review_context(db, session)
    trusted = context["policy"]
    spent = D(context["spent"]) / 100
    remaining = max(D(0), D(trusted["cumulative_limit"]) - spent) if trusted else None
    blockers = []
    offer = session.get("offer")
    if trusted is None:
        blockers.append("Current trusted purchasing policy is unavailable. No approval or submission can proceed.")
    elif not policy.parse_time(trusted["expires_at"]) or policy.parse_time(trusted["expires_at"]) <= policy.now():
        blockers.append("Current purchasing policy has expired. The operator must restore valid authority.")
    if offer:
        if not session.get("requester_actor") or not session.get("requester_principal"):
            blockers.append("Requester identity needs a fresh buyer review. Refresh this older draft.")
        if offer.get("authority") != trusted:
            blockers.append("Purchasing policy changed since this quotation. Refresh and review the basket again.")
        expiry = policy.parse_time(offer.get("expires_at"))
        if not expiry or expiry <= policy.now():
            blockers.append("This quotation expired. Refresh prices and availability before approving or submitting.")
        if fingerprint(offer) != offer.get("fingerprint") or offer.get("requested_requirements") != requirements(session):
            blockers.append("The basket no longer matches its exact reviewed requirements. Refresh it before continuing.")
        total = decimal(offer.get("total"))
        if total is None:
            blockers.append("The reviewed basket total is not valid.")
        elif trusted:
            if total > D(trusted["exception_limit"]):
                blockers.append("This basket exceeds the current hard per-order purchasing limit.")
            if total > remaining:
                blockers.append("Current remaining workspace purchasing allowance is insufficient. Financial approval cannot override this hard cumulative limit.")
    if context["preferences"] is None:
        blockers.append("Current mandatory dietary preferences cannot be validated. Ask the operator to restore them.")
    else:
        constrained = copy.deepcopy(session)
        enforce_hard(constrained, db, session, saved=context["preferences"])
        if requirements(constrained)["items"] != requirements(session)["items"]:
            blockers.append("Mandatory dietary restrictions or exclusions changed since this quotation. The buyer must refresh and review suitable products.")
    if session.get("approval", {}).get("reasons"):
        blockers.extend(assignment_blockers(session, context["assignment"]))
    return {"blockers": list(dict.fromkeys(blockers)), "cumulative_spent": money(spent), "cumulative_remaining": money(remaining) if remaining is not None else None}


def fingerprint(offer):
    fields = {k: v for k, v in offer.items() if k not in {"fingerprint", "approved", "approval"}}
    return hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def fixture_lookup(customer, day, ids):
    """Authored fixture only. Units match catalog; numbers are never live claims."""
    result = upstream.fixture_lookup(customer, day, ids)
    for row in result["price"]["products"]:
        pid = str(row["productId"])
        if pid not in catalog.DEFAULT_IDS:
            # Stable differences support a repeatable comparison without a fake
            # claim of observed commercial prices.
            cents = 200 + int(hashlib.sha256(pid.encode()).hexdigest()[:4], 16) % 800
            row["catalogPrice"]["valueWithTax"] = cents / 100
            if (tax_rate := decimal(row.get("tax", {}).get("taxRate"))) is not None and tax_rate >= 0:
                row["catalogPrice"]["value"] = float(D(cents) / (D(100) + tax_rate))
    for row in result["availability"]["products"]:
        p = product_facts.normalize(str(row["productId"]))
        for schedule in row.get("scheduleLines", []):
            schedule["salesUnit"] = p["sales_unit"]
    return result


def lookup(session, ids):
    return (upstream.sponsor_lookup if session["mode"] == "live" else fixture_lookup)(
        session.get("commercial_customer_id", session["customer_id"]), session["constraints"]["delivery_date"], ids
    )


def item_facts(product, quantity, unit):
    units = product_facts.units_for(product, D(quantity), unit)
    key = {"L": "liters_per_sales_unit", "kg": "kg_per_sales_unit", "pieces": "pieces_per_sales_unit"}.get(unit)
    pack = D(1) if unit == "packages" else decimal(product.get(key)) if key else None
    return units, pack


def round_sales_units(product, exact):
    """Round aggregated rational requirements without recurring-decimal drift."""
    step = product_facts.order_step(product)
    if step is None or exact <= 0:
        return None
    steps = exact / Fraction(step)
    return D(-(-steps.numerator // steps.denominator)) * step


def base_session(scope, mode, use_model=False):
    return {"id": policy.uid("procurement"), "version": 1, "schema_version": 2, "buyer_id": scope["buyer_id"], "customer_id": scope["customer_id"], "buyer_name": scope.get("name", "Buyer"), "workspace_name": scope.get("workspace_name"), "requester_actor": scope.get("actor_id"), "requester_principal": scope.get("principal_id"), "commercial_customer_id": scope.get("commercial_customer_id", scope["customer_id"]), "commercial_context": "Reference pricing uses the authorized example supplier customer. Your separate demonstration workspace is not a Valio Aimo customer contract.", "mode": mode, "use_model": use_model, "created_at": policy.now().isoformat(), "messages": [], "lines": [], "constraints": {"budget": None, "currency": "EUR", "delivery_date": None, "preferences": "balanced"}, "receipt": None, "checkout_pending": False, "budget_exception": None, "decision_history": [], "submitted_at": None, "cancelled": None, "changes_requested": None}


def commercial(product, units, evidence, day):
    issues = []
    codes = []
    def records(kind):
        payload = evidence.get(kind)
        rows = payload.get("products") if isinstance(payload, dict) else None
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    prices = [r for r in records("price") if str(r.get("productId")) == product["id"]]
    stocks = [r for r in records("availability") if str(r.get("productId")) == product["id"]]
    price = prices[0] if len(prices) == 1 else {}
    stock = stocks[0] if len(stocks) == 1 else {}
    cp = price.get("catalogPrice") if isinstance(price.get("catalogPrice"), dict) else {}
    unit_price = decimal(cp.get("valueWithTax"))
    now = policy.now()
    if not price or price.get("error", True) or cp.get("currency") != "EUR" or unit_price is None or unit_price < 0:
        unit_price = None
        issues.append("A valid EUR tax-inclusive sales-unit price is unavailable.")
        codes.append("PRICE_UNKNOWN")
    start, end = policy.parse_time(cp.get("validFrom")), policy.parse_time(cp.get("validTo"))
    if not start or not end or not start <= now <= end or not start.date().isoformat() <= day <= end.date().isoformat():
        issues.append("Price validity does not cover now and the requested delivery date.")
        codes.append("PRICE_VALIDITY_CONFLICT")
    tax = price.get("tax") if isinstance(price.get("tax"), dict) else {}
    if decimal(tax.get("taxRate")) is None:
        issues.append("Tax information is missing.")
        codes.append("TAX_UNKNOWN")
    cutoff = policy.parse_time(stock.get("closingTime"))
    if not cutoff or cutoff <= now:
        issues.append("Ordering cutoff is unavailable or passed.")
        codes.append("CUTOFF_CONFLICT")
    if not stock or stock.get("salesBlock", True):
        issues.append("Supplier sales permission is missing or blocked.")
        codes.append("SALES_PERMISSION_CONFLICT")
    available = D(0)
    possible_dates = []
    unknown = False
    known_schedule = False
    future_dates = []
    schedules = stock.get("scheduleLines")
    for line in schedules if isinstance(schedules, list) else []:
        if not isinstance(line, dict):
            continue
        amount = decimal(line.get("availableAmount"))
        when = line.get("availableDate")
        if line.get("salesBlock", True) or amount is None or amount < 0 or line.get("salesUnit") != product["sales_unit"]:
            continue
        try:
            Date.fromisoformat(when)
        except (ValueError, TypeError):
            continue
        if stock.get("logisticModel") == "Terminal" and amount == 999999:
            unknown = True
            continue
        known_schedule = True
        if units is not None and amount >= units and when > day:
            future_dates.append(when)
        if when <= day:
            # Schedule lines are alternatives/snapshots, never assumed additive.
            available = max(available, amount)
            if units is not None and amount >= units:
                possible_dates.append(when)
    if units is None:
        issues.append("No verified dimensional conversion into sellable packs.")
        codes.append("QUANTITY_CONVERSION_UNKNOWN")
    elif available < units:
        issues.append("Available quantity is unknown." if unknown or not known_schedule else f"Only {available} {product['sales_unit']} confirmed by {day}; {units} needed.")
        codes.append("STOCK_UNKNOWN" if unknown or not known_schedule else "INSUFFICIENT_STOCK")
        if future_dates:
            issues.append(f"Confirmed quantity is available on {min(future_dates)}, after the requested date.")
            codes.append("DELIVERY_CONFLICT")
    fetched = policy.parse_time(evidence.get("fetched_at"))
    if not fetched or not -30 <= (now - fetched).total_seconds() <= 300:
        issues.append("Supplier evidence is stale or has no valid timestamp.")
        codes.append("STALE_EVIDENCE")
    total = unit_price * units if unit_price is not None and units is not None else None
    deadlines = [v for v in [end, cutoff, fetched + timedelta(minutes=5) if fetched else None] if v]
    return {
        "unit_price": money(unit_price) if unit_price is not None else None,
        "price_decimal": str(unit_price) if unit_price is not None else None,
        "line_total": money(total) if total is not None else None,
        "availability": "available" if units is not None and available >= units else "unknown" if unknown or not known_schedule else "insufficient",
        "available_sales_units": str(available),
        "delivery_date": min(possible_dates) if possible_dates else None,
        "next_available_date": min(future_dates) if future_dates else None,
        "issues": issues,
        "issue_codes": codes,
        "valid_until": min(deadlines).isoformat() if len(deadlines) == 3 else None,
        "evidence": {"source": evidence["source"], "fetched_at": evidence["fetched_at"], "price": price, "availability": stock},
    }


def requirements(session, *, requested_only=False):
    return {
        "items": [{"id": line["id"], "query": line["requested_label"], "quantity": line["quantity"], "unit": line["unit"], "dietary": line.get("requested_dietary", line["dietary"]) if requested_only else line["dietary"], "origin": line.get("origin"), "max_unit_price": line.get("max_unit_price"), **{key: line.get("requested_excluded_ingredients", line.get(key, default)) if requested_only and key == "excluded_ingredients" else line.get(key, default) for key, default in ITEM_OPTIONS.items()}} for line in session["lines"]],
        "budget": session["constraints"]["budget"],
        "delivery_date": session["constraints"]["delivery_date"],
        "preference": session["constraints"]["preferences"],
        "notes": session.get("interpretation_notes", []),
        "ambiguous_fields": session.get("ambiguities", []),
        "recipe_request": session.get("recipe_request"),
        "pending_request": session["messages"][-1]["text"] if not session["lines"] and session.get("messages") else None,
    }


def interpret_into(session, message):
    from .interpretation import interpret
    previous_recipe = session.get("recipe_request")
    previous_recipe_notes = session.get("recipe_notes", [])
    previous_review_required = session.get("recipe_review_required", False)
    result = interpret(message, prior=requirements(session, requested_only=True) if session["lines"] or session.get("messages") else None, use_model=session["use_model"])
    if len(result.get("items", [])) > 24:
        result.setdefault("ambiguous_fields", []).append("This request exceeds the 24-line cart limit. Split it into smaller explicit requests.")
    previous = session["lines"]
    lines = []
    for item in result.get("items", [])[:24]:
        quantity = decimal(item.get("quantity"))
        if quantity is None or quantity <= 0 or quantity > 1000000 or item.get("unit") not in ["L", "kg", "pieces", "packages"] or not str(item.get("query", "")).strip():
            result.setdefault("ambiguous_fields", []).append("Please provide a positive quantity, supported unit and product for every line.")
            continue
        used_ids = {line["id"] for line in lines}
        old = next((p for p in previous if p["id"] == item.get("id") and p["id"] not in used_ids), None)
        if old is None:
            old = next((p for p in previous if p["requested_label"].casefold() == str(item["query"]).casefold() and p["dietary"] == item.get("dietary", []) and p.get("origin") == item.get("origin") and p["id"] not in {line["id"] for line in lines}), None)
        line = {
            "id": old["id"] if old else policy.uid("line"),
            "requested_label": str(item["query"])[:200],
            "quantity": str(quantity), "unit": item["unit"],
            "dietary": item.get("dietary", []), "requested_dietary": copy.deepcopy(item.get("dietary", [])), "requested_excluded_ingredients": copy.deepcopy(item.get("excluded_ingredients", [])), "origin": item.get("origin"),
            "max_unit_price": item.get("max_unit_price"),
            "selected_product_id": old.get("selected_product_id") if old else None,
            **{key: copy.deepcopy(item.get(key, old.get(key, default) if old else default)) for key, default in ITEM_OPTIONS.items()},
        }
        if old and old.get("meal_plan_line"):
            line["meal_plan_line"] = copy.deepcopy(old["meal_plan_line"])
        lines.append(line)
    session["lines"] = lines
    session["constraints"].update(budget=result.get("budget"), delivery_date=result.get("delivery_date"), preferences=result.get("preference", "balanced"))
    session["interpretation_notes"] = result.get("notes", [])
    session["interpretation_source"] = result.get("interpretation_source", "Structured interpretation")
    session["ambiguities"] = result.get("ambiguous_fields", [])
    session["recipe_notes"] = [str(n) for n in result.get("notes", []) if "recipe" in str(n).lower() or "illustrative" in str(n).lower()] or previous_recipe_notes
    session["recipe_request"] = result.get("recipe_request", previous_recipe)
    recipe_changed = session["recipe_request"] != previous_recipe or session["recipe_notes"] != previous_recipe_notes
    session["recipe_review_required"] = previous_review_required or (bool(session["recipe_notes"]) and (recipe_changed or not session.get("recipe_acknowledged_at")))
    if previous and re.search(r"\b(?:cheap(?:er|est)?|lowest[- ]price|most affordable)\b", message, re.I):
        # Selection intent is scoped to the mentioned product or the last
        # clarification choice. A budget-only turn must preserve every choice.
        low = message.casefold()
        targets = []
        for line in lines:
            words = re.findall(r"[a-z]+", line["requested_label"].casefold())
            words = [word for word in words if word not in {"free", "lactose", "gluten", "vegetarian", "vegan", "of", "the", "for"}]
            if words and all(re.search(r"\b" + re.escape(word) + r"\b", low) for word in words):
                targets.append(line["id"])
        if not targets and re.search(r"\b(?:all|everything|every|options|products|items|ones)\b", low):
            targets = [line["id"] for line in lines]
        if not targets:
            unresolved = [line["id"] for line in previous if line.get("status") != "EXACT_MATCH"]
            if len(unresolved) == 1:
                targets = unresolved
            elif session.get("last_selected_line_id"):
                targets = [session["last_selected_line_id"]]
            elif len(lines) == 1:
                targets = [lines[0]["id"]]
            elif not re.search(r"\bone\b", low):
                targets = [line["id"] for line in lines]
            else:
                session["ambiguities"].append("Which product should I compare cheaper options for? Name the product or use its comparison cards.")
        for line in lines:
            if line["id"] in targets:
                line["selected_product_id"] = None
    session["messages"].append({"role": "user", "text": message})


def suitability(product, line):
    return product_facts.suitability(product, line["dietary"], line.get("origin"), line.get("required_brand"), line.get("require_organic", False), line.get("excluded_ingredients", []))


def soft_matches(product, line):
    matches = []
    if line.get("preferred_brand") and product_facts.brand_matches(product.get("brand"), line["preferred_brand"]):
        matches.append("preferred declared brand")
    if line.get("preferred_origin") and not product_facts.suitability(product, [], line["preferred_origin"]):
        matches.append("preferred declared origin")
    if line.get("preferred_organic") and product.get("organic") is True:
        matches.append("preferred explicit organic label")
    return matches


def current_selection_subtotal(lines, replacement=None):
    """Hypothetical complete basket cost, aggregating shared SKUs exactly first."""
    groups = {}
    for line in lines:
        selected = replacement[1] if replacement and line["id"] == replacement[0] else line.get("selected_product_id")
        candidate = next((c for c in line["candidates"] if c["id"] == selected), None)
        if not candidate or candidate["issues"]:
            return None
        pack = decimal(candidate.get("pack_quantity"))
        unit_price = decimal(candidate.get("commercial", {}).get("price_decimal"))
        if pack is None or pack <= 0 or unit_price is None:
            return None
        group = groups.setdefault(selected, {"quantity": Fraction(0), "price": unit_price, "product": candidate["product"]})
        if group["price"] != unit_price:
            return None
        group["quantity"] += Fraction(D(line["quantity"])) / Fraction(pack)
    total = D(0)
    for group in groups.values():
        units = round_sales_units(group["product"], group["quantity"])
        if units is None:
            return None
        total += D(money(units * group["price"]))
    return total


def quote(session, spent):
    session["offer"] = None
    session["receipt"] = None
    session["rejection"] = None
    session["changes_requested"] = None
    session["budget_exception"] = None
    session["submitted_at"] = None
    session["can_confirm"] = False
    questions = []
    blockers = list(session.get("ambiguities", []))
    day = session["constraints"].get("delivery_date")
    try:
        requested = Date.fromisoformat(day)
        today = datetime.now(ZoneInfo("Europe/Helsinki")).date()
        valid_day = today <= requested <= today + timedelta(days=30)
    except (ValueError, TypeError):
        valid_day = False
    if not valid_day:
        blockers.append("Choose a delivery date from today through the next 30 days.")
    if not session["lines"]:
        blockers.append("Describe products with quantities and units to begin your cart.")
    if session.get("recipe_review_required"):
        blockers.append("Review and acknowledge the illustrative recipe before confirming its shopping basket.")
    ids = []
    product_map = {}
    for line in session["lines"]:
        products = product_facts.discover(line["requested_label"], 16, line["dietary"], line.get("origin"), line.get("retrieval_queries", []), line.get("selected_product_id"), line.get("required_brand"), line.get("require_organic", False), line.get("preferred_brand"), line.get("preferred_origin"), line.get("preferred_organic", False))
        products.sort(key=lambda p: (bool(suitability(p, line)), product_facts.units_for(p, D(line["quantity"]), line["unit"]) is None, -len(soft_matches(p, line))))
        if line.get("selected_product_id") and line["selected_product_id"] not in [p["id"] for p in products]:
            try:
                selected_product = product_facts.normalize(line["selected_product_id"])
                products = products[:15] + [dict(selected_product, match_method="lexical", match_reason="Previously customer-reviewed product; retained for fresh checks.")]
            except ValueError:
                line["selected_product_id"] = None
        product_map[line["id"]] = products
        ids.extend(p["id"] for p in products)
    ids = list(dict.fromkeys(ids))
    evidence = None
    session["quotation_error"] = None
    if ids and valid_day:
        try:
            evidence = lookup(session, ids)
        except upstream.UpstreamError as exc:
            session["quotation_error"] = str(exc)
    for line in session["lines"]:
        line["candidates"] = []
        for p in product_map[line["id"]]:
            units, pack = item_facts(p, line["quantity"], line["unit"])
            issues = suitability(p, line)
            eligibility_issues = list(issues)
            issue_codes = []
            if line["dietary"] and product_facts.suitability(dict(p, deleted=False), line["dietary"]):
                issue_codes.append("DIETARY_EVIDENCE_CONFLICT")
            if line.get("origin") and product_facts.suitability(dict(p, deleted=False), [], line["origin"]):
                issue_codes.append("ORIGIN_CONFLICT")
            if line.get("required_brand") and not product_facts.brand_matches(p.get("brand"), line["required_brand"]):
                issue_codes.append("BRAND_CONFLICT")
            if line.get("require_organic") and p.get("organic") is not True:
                issue_codes.append("ORGANIC_EVIDENCE_UNKNOWN")
            if units is None:
                issues.extend(p.get("conversion_issues", []))
            if p.get("deleted"):
                issues.append("Product is deleted.")
                issue_codes.append("PRODUCT_DELETED")
            if p.get("variable_unit"):
                issues.append("Variable-weight commercial charges are unsupported.")
                issue_codes.append("VARIABLE_WEIGHT_UNSUPPORTED")
            if p.get("deposits"):
                issues.append("Deposit charges need a supported charge calculation.")
                issue_codes.append("DEPOSIT_CHARGES_UNKNOWN")
            commercial_facts = commercial(p, units, evidence, day) if evidence else {"issues": [session.get("quotation_error") or "Set a valid delivery date to obtain a quotation."], "unit_price": None, "line_total": None, "availability": "not_queried", "delivery_date": None}
            issues.extend(commercial_facts["issues"])
            issue_codes.extend(commercial_facts.get("issue_codes", ["QUOTATION_NOT_REQUESTED"] if evidence is None else []))
            limit = decimal(line.get("max_unit_price"))
            price = decimal(commercial_facts.get("price_decimal"))
            if limit is not None and (price is None or pack is None or pack <= 0 or price / pack > limit):
                issues.append(f"Price per requested {line['unit']} exceeds the €{limit} limit or is unknown.")
                issue_codes.append("UNIT_PRICE_LIMIT_CONFLICT")
            line["candidates"].append({
                "id": p["id"], "name": p["name"], "sales_unit": p["sales_unit"],
                "pack_quantity": str(pack) if pack is not None else None, "pack_unit": line["unit"],
                "quantity_sales_units": str(units) if units is not None else None,
                "effective_quantity": str(units * pack) if units is not None and pack is not None else None,
                "requested_quantity": line["quantity"],
                "surplus_quantity": str(units * pack - D(line["quantity"])) if units is not None and pack is not None else None,
                "unit_price": commercial_facts["unit_price"], "line_total": commercial_facts["line_total"],
                "availability": commercial_facts["availability"], "delivery_date": commercial_facts["delivery_date"],
                "attributes": {"brand": p.get("brand"), "claims": p.get("claims", []), "origin_codes": p.get("origin_codes", []), "organic": p.get("organic")},
                "match_method": p.get("match_method", "lexical"), "match_reason": p.get("match_reason", "Catalog name match."),
                "requires_explicit_choice": (p.get("purpose_review_required", False) or p.get("match_method") in ["semantic_expansion", "supplier_substitution"]) and p["id"] != line.get("selected_product_id"),
                "eligibility_issues": eligibility_issues, "quote_issues": [issue for issue in issues if issue not in eligibility_issues], "selectable": not eligibility_issues,
                "preference_matches": soft_matches(p, line),
                "price_per_requested_unit": format(price / pack, "f") if price is not None and pack is not None and pack > 0 else None,
                **product_facts.comparable_prices(p, price),
                "comparison_delta": None, "comparison_note": None,
                "available_sales_units": commercial_facts.get("available_sales_units"),
                "next_available_date": commercial_facts.get("next_available_date"),
                "issue_codes": list(dict.fromkeys(issue_codes)),
                "issues": issues, "source": evidence["source"] if evidence else "local_challenge_catalog", "product": p,
                "commercial": commercial_facts,
            })
        viable = [c for c in line["candidates"] if not c["issues"]]
        automatic = [c for c in viable if not c["requires_explicit_choice"]]
        if not line.get("selected_product_id"):
            if len(automatic) == 1 and session["constraints"]["preferences"] != "quality":
                line["selected_product_id"] = automatic[0]["id"]
                line["selection_reason"] = "Only direct catalog candidate satisfies all verified constraints; related replacements require explicit review." if len(viable) > 1 else "Only quoted candidate satisfies all verified constraints."
            elif automatic and session["constraints"]["preferences"] == "cheapest":
                chosen = min(automatic, key=lambda c: (D(c["line_total"]), -len(c["preference_matches"])))
                line["selected_product_id"] = chosen["id"]
                line["selection_reason"] = "Lowest rounded item subtotal among the quoted compliant candidates."
            elif automatic and session["constraints"]["preferences"] == "delivery":
                dated = [c for c in automatic if c.get("delivery_date")]
                earliest = min((c["delivery_date"] for c in dated), default=None)
                preferred = [c for c in dated if c["delivery_date"] == earliest]
                if len(preferred) == 1:
                    line["selected_product_id"] = preferred[0]["id"]
                    line["selection_reason"] = "Earliest observed suitable delivery estimate among the quoted direct candidates; not a delivery guarantee."
            elif automatic and session["constraints"]["preferences"] in {"balanced", "origin"}:
                def preference_score(candidate):
                    matches = candidate["preference_matches"]
                    return len(matches) + (2 if session["constraints"]["preferences"] == "origin" and "preferred declared origin" in matches else 0)
                best = max(preference_score(c) for c in automatic)
                preferred = [c for c in automatic if preference_score(c) == best]
                if best and len(preferred) == 1:
                    line["selected_product_id"] = preferred[0]["id"]
                    line["selection_reason"] = "Best declared match for your soft preferences among the quoted compliant candidates."
        selected = next((c for c in line["candidates"] if c["id"] == line.get("selected_product_id")), None)
        line["issues"] = selected["issues"] if selected else ["Choose a suitable product."] if viable else ["No quoted candidate satisfies every requirement."]
        line["issue_codes"] = list(dict.fromkeys(code for c in ([selected] if selected else line["candidates"]) for code in c["issue_codes"]))
        out_of_stock = bool(line["candidates"]) and all("INSUFFICIENT_STOCK" in c["issue_codes"] and "DELIVERY_CONFLICT" not in c["issue_codes"] for c in line["candidates"])
        line["status"] = "EXACT_MATCH" if selected and not selected["issues"] else "NOT_FOUND" if not line["candidates"] else "OUT_OF_STOCK" if out_of_stock else "CONSTRAINT_CONFLICT" if selected else "AMBIGUOUS_MATCH" if viable else "CONSTRAINT_CONFLICT"
        line["classifications"] = [line["status"]]
        if len(line["candidates"]) > 1 and line["status"] not in ["EXACT_MATCH", "AMBIGUOUS_MATCH"]:
            line["classifications"].append("AMBIGUOUS_MATCH")
        if line["issue_codes"] and line["status"] not in ["CONSTRAINT_CONFLICT", "NOT_FOUND"]:
            line["classifications"].append("CONSTRAINT_CONFLICT")
        if line["issues"]:
            options = [{"id": c["id"], "label": c["name"], "action": "select_product", "payload": {"line_id": line["id"], "product_id": c["id"]}} for c in viable]
            later = [c["next_available_date"] for c in line["candidates"] if c.get("next_available_date") and set(c["issue_codes"]).issubset({"DELIVERY_CONFLICT", "INSUFFICIENT_STOCK"})]
            if later and Date.fromisoformat(min(later)) <= today + timedelta(days=30):
                options.append({"id": "date-" + line["id"], "label": f"Change the deadline to {min(later)} and recheck the whole basket", "action": "set_date", "payload": {"date": min(later)}})
            options.append({"id": "remove-" + line["id"], "label": f"Remove {line['requested_label']} from this request", "action": "remove_line", "payload": {"line_id": line["id"]}})
            questions.append({"id": "choose-" + line["id"], "line_id": line["id"], "prompt": f"Review {line['requested_label']}: " + " ".join(line["issues"]), "options": options})
    baseline = current_selection_subtotal(session["lines"])
    for line in session["lines"]:
        for candidate in line["candidates"]:
            changed = current_selection_subtotal(session["lines"], (line["id"], candidate["id"])) if baseline is not None else None
            if changed is not None:
                candidate["comparison_delta"] = money(changed - baseline)
                candidate["comparison_note"] = "Change to the complete current item subtotal if this line uses this product; shared SKUs are consolidated before pack rounding. Delivery/service charges excluded."
    # Aggregate requirements by SKU and dimension BEFORE pack rounding. Different
    # dimensions on one SKU are converted to fractions of the same sellable unit.
    grouped = {}
    for line in session["lines"]:
        selected = next((c for c in line["candidates"] if c["id"] == line.get("selected_product_id")), None)
        if not selected:
            continue
        p = selected["product"]
        _, pack = item_facts(p, line["quantity"], line["unit"])
        group = grouped.setdefault(p["id"], {"product": p, "units_exact": Fraction(0), "line_ids": [], "issues": [], "dimensions": {}})
        group["line_ids"].append(line["id"])
        group["issues"].extend(selected["issues"])
        if pack is None or pack <= 0:
            group["issues"].append("Dimensional conversion unavailable.")
        else:
            group["units_exact"] += Fraction(D(line["quantity"])) / Fraction(pack)
            group["dimensions"][line["unit"]] = group["dimensions"].get(line["unit"], D(0)) + D(line["quantity"])
    cart_items = []
    subtotal = D(0)
    all_priced = True
    all_valid = bool(session["lines"]) and not questions and not blockers
    deadlines = []
    for pid, group in grouped.items():
        p = group["product"]
        units = round_sales_units(p, group["units_exact"])
        facts = commercial(p, units, evidence, day) if evidence else {"issues": ["Quotation unavailable."], "line_total": None, "unit_price": None, "availability": "not_queried", "delivery_date": None}
        issues = list(dict.fromkeys(group["issues"] + facts["issues"]))
        if issues:
            all_valid = False
        if facts["line_total"] is None:
            all_priced = False
        else:
            subtotal += D(facts["line_total"])
        if facts.get("valid_until"):
            deadlines.append(facts["valid_until"])
        breakdown = []
        for dimension, requested_quantity in group["dimensions"].items():
            _, pack = item_facts(p, requested_quantity, dimension)
            if units is not None and pack is not None:
                effective = units * pack
                equivalent_fraction = group["units_exact"] * Fraction(pack)
                equivalent = D(equivalent_fraction.numerator) / D(equivalent_fraction.denominator)
                breakdown.append({"unit": dimension, "requested_quantity": str(equivalent), "effective_quantity": str(effective), "surplus_quantity": str(effective - equivalent), "includes_converted_requirements": len(group["dimensions"]) > 1})
        cart_items.append({"id": pid, "name": p["name"], "sales_unit": p["sales_unit"], "quantity_sales_units": str(units) if units is not None else None, "effective_quantity": str(units) if units is not None else None, "unit": "packages", "quantity_breakdown": breakdown, "unit_price": facts["unit_price"], "line_total": facts["line_total"], "availability": facts["availability"], "delivery_date": facts["delivery_date"], "line_ids": group["line_ids"], "issues": issues, "evidence": facts.get("evidence")})
    budget = decimal(session["constraints"].get("budget"))
    remaining = budget - subtotal if budget is not None and all_priced else None
    excess = -remaining if remaining is not None and remaining < 0 else D(0)
    snapshot = authority()
    if subtotal > D(snapshot["exception_limit"]):
        blockers.append("Purchasing policy: this basket exceeds the permitted per-order limit. Reduce quantities or ask your workspace manager to review the configured policy. Increasing your budget does not change this limit.")
        all_valid = False
    if spent + int(subtotal * 100) > int(D(snapshot["cumulative_limit"]) * 100):
        blockers.append("Purchasing policy: this workspace has insufficient remaining simulated purchasing allowance. Reduce the basket or ask your workspace manager to review the allowance. Increasing your budget does not replenish it.")
        all_valid = False
    expiry = policy.parse_time(snapshot["expires_at"])
    if not expiry or expiry <= policy.now():
        blockers.append("The demonstration purchasing policy has expired.")
        all_valid = False
    if excess and not snapshot["budget_exceptions"]:
        blockers.append("Requested-budget exceptions are prohibited by the trusted policy. Edit the basket or explicitly edit your requested budget.")
        all_valid = False
    hard_blockers = list(dict.fromkeys(blockers + [question["prompt"] for question in questions]))
    if excess:
        blockers.append(f"Item subtotal exceeds your requested budget by €{money(excess)}. Edit your basket or budget, or request an exact budget exception when all hard checks pass.")
    for i, text in enumerate(blockers):
        options = []
        if text.startswith("Item subtotal exceeds your requested budget") and baseline is not None:
            options.append({"id": "raise-item-budget", "label": f"Raise the item budget to €{money(subtotal)}", "action": "set_budget", "payload": {"budget": money(subtotal)}})
        questions.append({"id": f"constraint-{i}", "line_id": None, "prompt": text, "options": options})
    reasons = (["requested_budget"] if excess else []) + (["spending_authority"] if subtotal > D(snapshot["autonomous_limit"]) else [])
    requires_approval = bool(reasons)
    session["approval"] = {"status": "required" if all_valid and requires_approval else "not_required" if all_valid else "blocked", "threshold": snapshot["autonomous_limit"], "approved": False, "policy": snapshot,
        "reasons": reasons, "requested_budget": money(budget) if budget is not None else None,
        "budget_excess": money(excess) if all_priced else None, "explanation": None,
        "pending": False, "can_request": all_valid and requires_approval, "blockers": hard_blockers,
        "cumulative_spent": money(D(spent) / 100), "cumulative_remaining": money(max(D(0), D(snapshot["cumulative_limit"]) - D(spent) / 100)),
        "scope_note": snapshot["cumulative_scope"] + " Pending approvals do not reserve funds; the final transaction rechecks remaining allowance.",
        "can_decide": False, "decision_blockers": []}
    session["cart"] = {"items": cart_items, "subtotal": money(subtotal) if all_priced else None, "total": None, "unknown_charges": ["Delivery and service charges are outside this item-price simulation; no final commercial charge is quoted."], "budget_remaining": money(remaining) if remaining is not None else None, "currency": "EUR", "price_scope": "tax-inclusive item subtotal"}
    session["clarification_questions"] = questions
    impossible = valid_day and any(not line["candidates"] or all(c["issues"] for c in line["candidates"]) for line in session["lines"])
    session["order_status"] = "READY_TO_ORDER" if all_valid and not excess else "CANNOT_FULFILL" if impossible else "NEEDS_CLARIFICATION"
    session["review_state"] = "DRAFT" if not session["lines"] else "READY" if all_valid and not requires_approval else "BLOCKED"
    session["assistant_message"] = "Your complete item-price basket is ready for review." if all_valid else "Review the highlighted choices and requirements to complete your basket."
    if all_valid:
        offer = {"id": policy.uid("basket"), "schema_version": 2, "buyer_id": session["buyer_id"], "customer_id": session["customer_id"], "requester_actor": session.get("requester_actor"), "requester_principal": session.get("requester_principal"), "session_id": session["id"], "session_version": session["version"], "lines": cart_items, "requested_requirements": requirements(session), "requested_date": day, "total": money(subtotal), "total_cents": int(subtotal * 100), "currency": "EUR", "mode": session["mode"], "status": "approval_required" if requires_approval else "within_mandate", "expires_at": min([policy.now() + timedelta(minutes=5), expiry] + [policy.parse_time(v) for v in deadlines]).isoformat(), "authority": snapshot, "approval_reasons": reasons, "budget_excess": money(excess), "approval_request": None, "approved": False, "approval": None}
        offer["fingerprint"] = fingerprint(offer)
        session["offer"] = offer
        session["can_confirm"] = not requires_approval
        if excess:
            session["budget_exception"] = {"status": "available", "original_budget": money(budget), "total": money(subtotal), "excess": money(excess), "explanation": None, "fingerprint": offer["fingerprint"], "version": session["version"]}
    return session


def register_routes(app, db, buyer, approver, identity, limit):
    def quote_for(session, scope):
        from .preferences import enforce_hard
        enforce_hard(session, db, scope)
        session.update(schema_version=2, requester_actor=scope.get("actor_id"), requester_principal=scope.get("principal_id"), buyer_name=scope.get("name", "Buyer"))
        session["workspace_name"] = scope.get("workspace_name")
        quote(session, db.spent(scope["buyer_id"]))
        if session.get("approval", {}).get("reasons"):
            problems = assignment_blockers(session, db.workspace_authority(scope["buyer_id"], scope["customer_id"]))
            if problems:
                session["approval"]["can_request"] = False
                session["approval"]["blockers"] = list(dict.fromkeys(session["approval"]["blockers"] + problems))

    def selected_line(product_id, quantity, unit):
        try:
            product = product_facts.normalize(product_id)
        except (ValueError, KeyError):
            fail("product_missing", "Choose a product in the current catalog.", 404)
        if product.get("deleted"):
            fail("product_deleted", "This product is no longer offered.", 422)
        return {"id": policy.uid("line"), "requested_label": product["name"],
            "quantity": format(D(quantity), "f"), "unit": unit, "dietary": [], "origin": None,
            "max_unit_price": None, **copy.deepcopy(ITEM_OPTIONS),
            "selected_product_id": product["id"], "selection_reason": "Selected directly from the catalog."}

    def load(id, scope):
        result = db.get("procurement", id, scope["buyer_id"])
        if not result or result["customer_id"] != scope["customer_id"]:
            fail("not_found", "Purchasing session not found in your customer scope.", 404)
        return result

    def compare_save(old, new, *, snapshot=None):
        with db.tx() as c:
            row = c.execute("SELECT body FROM aimo_documents WHERE kind=? AND id=? AND buyer_id=?" + (" FOR UPDATE" if db.backend == "postgres" else ""), ("procurement", old["id"], old["buyer_id"])).fetchone()
            if not row or json.loads(row[0]) != old:
                fail("version_conflict", "This cart changed in another request. Reload it before editing.")
            c.execute("UPDATE aimo_documents SET body=? WHERE kind=? AND id=? AND buyer_id=?", (json.dumps(new), "procurement", old["id"], old["buyer_id"]))
            if snapshot is not None:
                c.execute("INSERT INTO aimo_documents(kind,id,buyer_id,body) VALUES(?,?,?,?) ON CONFLICT(id) DO NOTHING", ("approval_snapshot", snapshot["id"], new["buyer_id"], json.dumps(snapshot)))

    def exact_version(session, data):
        if data.version is not None and data.version != session["version"]:
            fail("version_conflict", "This request changed. Reload the exact current version before deciding.")

    def history(session, action, scope, reason=None):
        entry = {"action": action, "actor": scope.get("name", scope["role"]), "actor_id": scope.get("actor_id"), "principal_id": scope.get("principal_id"), "at": policy.now().isoformat(), "reason": reason, "fingerprint": (session.get("offer") or {}).get("fingerprint"), "version": session["version"]}
        session.setdefault("decision_history", []).append(entry)
        return entry

    def validate_snapshot(session):
        offer = session.get("offer")
        if not offer or offer.get("schema_version") != 2 or not session.get("requester_actor") or not session.get("requester_principal"):
            fail("buyer_review_required", "Refresh this older draft as buyer before requesting or deciding approval.")
        if fingerprint(offer) != offer["fingerprint"] or offer.get("authority") != authority() or not policy.parse_time(offer.get("expires_at")) or policy.parse_time(offer["expires_at"]) <= policy.now():
            fail("stale_offer", "Policy or quotation changed or expired. Refresh and review the basket again.")
        if offer.get("requested_requirements") != requirements(session) or offer.get("requester_actor") != session["requester_actor"] or offer.get("requester_principal") != session["requester_principal"]:
            fail("offer_changed", "The basket no longer matches its reviewed requirements. Refresh before continuing.")
        if session.get("cancelled") or session.get("rejection") or session.get("changes_requested"):
            fail("decision_closed", "This request is closed. The buyer must revise or refresh before a new request.")
        return offer

    def revalidate_exact(session, scope):
        offer = validate_snapshot(session)
        snapshot = authority()
        if offer.get("approval_reasons"):
            problems = assignment_blockers(session, db.workspace_authority(scope["buyer_id"], scope["customer_id"]))
            if problems:
                fail("manager_unavailable", " ".join(problems))
        if offer["total_cents"] + db.spent(scope["buyer_id"]) > int(D(snapshot["cumulative_limit"]) * 100):
            fail("cumulative_cap", "Remaining workspace allowance is insufficient. Financial approval cannot override this hard limit.")
        from .preferences import enforce_hard
        constrained = copy.deepcopy(session)
        enforce_hard(constrained, db, scope)
        if requirements(constrained)["items"] != requirements(session)["items"]:
            fail("preferences_changed", "Dietary restrictions changed. Refresh and review the cart before continuing.")
        evidence = lookup(session, [line["id"] for line in offer["lines"]])
        deadlines = [policy.parse_time(offer["expires_at"])]
        for line in offer["lines"]:
            try:
                product = product_facts.normalize(line["id"])
            except ValueError:
                fail("catalog_changed", "A product is no longer available. Refresh and review the basket.")
            exact_units = Fraction(0)
            fresh = commercial(product, D(line["quantity_sales_units"]), evidence, offer["requested_date"])
            if fresh["issues"] or fresh["unit_price"] != line["unit_price"] or fresh["line_total"] != line["line_total"]:
                fail("revalidation_failed", "Price, stock or delivery changed. Refresh the basket and review it again.")
            for request_line in session["lines"]:
                if request_line.get("selected_product_id") == product["id"]:
                    if suitability(product, request_line) or product.get("deleted") or product.get("deposits") or product.get("variable_unit"):
                        fail("catalog_changed", "Product evidence changed. Refresh and review the basket.")
                    candidate = next((candidate for candidate in request_line["candidates"] if candidate["id"] == product["id"]), None)
                    _, pack = item_facts(product, request_line["quantity"], request_line["unit"])
                    if pack is None or candidate is None or str(pack) != candidate["pack_quantity"]:
                        fail("catalog_changed", "Pack conversion changed. Refresh and review the basket.")
                    exact_units += Fraction(D(request_line["quantity"])) / Fraction(pack)
            if round_sales_units(product, exact_units) != D(line["quantity_sales_units"]):
                fail("catalog_changed", "Pack order increment changed. Refresh and review the basket.")
            deadline = policy.parse_time(fresh.get("valid_until"))
            if deadline is None:
                fail("invalid_deadline", "Supplier commitment deadline is unknown.")
            deadlines.append(deadline)
        return deadlines

    def public(session, scope=None):
        # Commercial raw data remain server-side and in immutable basket evidence.
        result = copy.deepcopy(session)
        result["original_request"] = next((entry.get("text", "") for entry in result.get("messages", []) if entry.get("role") == "user"), "Purchasing request")
        result["request_title"] = result["original_request"][:180]
        if result.get("source_meal_plan"):
            meal = result["source_meal_plan"]
            title = str(meal.get("dish") or "Meal ingredient plan")
            servings = meal.get("request", {}).get("servings")
            result["request_title"] = title[:180]
            result["original_request"] = title + (f" for {servings} servings." if servings is not None else ".") + " Exact ingredient quantities and dietary groups are preserved in this saved meal plan."
        result.setdefault("buyer_name", "Buyer")
        result.setdefault("workspace_name", None)
        result.setdefault("decision_history", [])
        for entry in result["decision_history"]:
            entry.pop("actor_id", None)
            entry.pop("principal_id", None)
        result.setdefault("submitted_at", None)
        approval = result.get("approval", {})
        review_context = current_review_context(db, session) if not result.get("receipt") else None
        if scope and scope.get("role") == "approver":
            assignment = review_context["assignment"] if review_context else db.workspace_authority(scope["buyer_id"], scope["customer_id"])
            approval["decision_blockers"] = decision_blockers(session, scope, assignment)
            approval["can_decide"] = bool(approval.get("pending") and not approval["decision_blockers"])
        current_day = result.get("constraints", {}).get("delivery_date")
        current_notes = []
        for note in result.get("interpretation_notes", []):
            previous_deadline = re.match(r"Interpreted the delivery deadline as (\d{4}-\d{2}-\d{2})", note)
            if previous_deadline and previous_deadline[1] != current_day:
                continue
            current_notes.append(note)
        result["interpretation_notes"] = current_notes
        for line in result["lines"]:
            for candidate in line.get("candidates", []):
                candidate["product_details"] = {key: candidate.get("product", {}).get(key) for key in ["id", "name", "brand", "manufacturer", "vendor", "category", "origin_codes", "origin_evidence", "claims", "certifications", "ingredients", "allergens", "storage", "min_storage_temperature", "max_storage_temperature", "nutrition", "image_url", "image_status", "temperature_condition", "source", "updated_at", "sales_unit", "base_unit", "base_units_per_sales_unit", "allowed_lot_size", "kg_per_sales_unit", "liters_per_sales_unit", "pieces_per_sales_unit", "conversion_evidence", "conversion_issues", "reliability", "carbon_group_estimate", "organic", "organic_evidence"]}
                candidate.pop("product", None)
                candidate.pop("commercial", None)
        if result.get("offer"):
            result["offer"] = {k: result["offer"][k] for k in ["id", "fingerprint", "expires_at", "total", "status", "approved"]}
        review_blockers = []
        if review_context is not None:
            review = current_review(session, db, context=review_context)
            review_blockers = review["blockers"]
            approval.update(cumulative_spent=review["cumulative_spent"], cumulative_remaining=review["cumulative_remaining"])
            approval["blockers"] = list(dict.fromkeys(approval.get("blockers", []) + review_blockers))
            if review_blockers:
                result.update(can_confirm=False, order_status="NEEDS_CLARIFICATION", review_state="BLOCKED")
                approval["can_request"] = False
                if not result.get("rejection") and not result.get("changes_requested") and not result.get("cancelled"):
                    result["assistant_message"] = review_blockers[0]
        if result.get("receipt"):
            result["review_state"] = "SIMULATED_ORDER_SUBMITTED"
        elif result.get("cancelled"):
            result["review_state"] = "CANCELLED"
        elif result.get("changes_requested"):
            result["review_state"] = "CHANGES_REQUESTED"
        elif result.get("rejection"):
            result["review_state"] = "REJECTED"
        elif review_blockers:
            result["review_state"] = "BLOCKED"
        elif approval.get("approved") and result.get("can_confirm"):
            result["review_state"] = "APPROVED"
        elif approval.get("pending") and approval.get("can_decide", True):
            result["review_state"] = "PENDING_APPROVAL"
        elif approval.get("pending") and result.get("review_state") != "BLOCKED":
            result["review_state"] = "PENDING_APPROVAL"
        result.pop("requester_actor", None)
        result.pop("requester_principal", None)
        result.pop("pending_key", None)
        return result

    app.state.public_procurement_session = public

    def reuse_session(old, scope, options):
        session = base_session(scope, options.get("mode") or old["mode"], old.get("use_model", False))
        session["lines"] = copy.deepcopy(old["lines"])
        for line in session["lines"]:
            line["id"] = policy.uid("line")
            line.pop("candidates", None)
        session["constraints"] = copy.deepcopy(old["constraints"])
        session["constraints"]["delivery_date"] = options.get("date")
        if options.get("budget") is not None:
            session["constraints"]["budget"] = options["budget"]
        for key in ["messages", "interpretation_notes", "recipe_notes", "recipe_request", "source_meal_plan", "source_recipe"]:
            if key in old:
                session[key] = copy.deepcopy(old[key])
        session["recipe_review_required"] = bool(session.get("recipe_notes"))
        session["interpretation_notes"] = [note for note in session.get("interpretation_notes", []) if not note.startswith("Interpreted the delivery deadline as ")]
        session["ambiguities"] = copy.deepcopy(old.get("ambiguities", []))
        if options.get("date"):
            session["ambiguities"] = [value for value in session["ambiguities"] if not re.search(r"delivery date|delivery deadline", value, re.I)]
        session["reused_from"] = old["id"]
        session["interpretation_source"] = "Reused purchasing request"
        from .preferences import enforce_hard
        enforce_hard(session, db, scope)
        quote_for(session, scope)
        db.save("procurement", session["id"], scope["buyer_id"], session)
        db.audit(policy.uid("audit"), scope["buyer_id"], "procurement_reused", {"session_id": session["id"], "source_id": old["id"]})
        return public(session)

    app.state.reuse_procurement_session = reuse_session

    @app.post(PREFIX, response_model=ProcurementSessionResponse, response_model_exclude_unset=True)
    def create(data: CreateSession, scope=Depends(buyer)):
        limit("procurement-" + scope["buyer_id"], 30)
        if not catalog.load_catalog():
            fail("catalog_missing", "The authorized challenge catalog is required.", 503)
        session = base_session(scope, data.mode, data.use_model)
        interpret_into(session, data.message)
        if data.apply_preferences:
            from .preferences import apply_saved
            apply_saved(session, db, scope, data.message)
        if data.date is not None:
            session["constraints"]["delivery_date"] = data.date.isoformat()
        if data.budget is not None:
            session["constraints"]["budget"] = str(data.budget)
        quote_for(session, scope)
        db.save("procurement", session["id"], scope["buyer_id"], session)
        db.audit(policy.uid("audit"), scope["buyer_id"], "procurement_created", {"session_id": session["id"], "version": 1})
        return public(session)

    @app.post(PREFIX + "/from-product", response_model=ProcurementSessionResponse, response_model_exclude_unset=True)
    def from_product(data: FromProduct, scope=Depends(buyer)):
        limit("procurement-" + scope["buyer_id"], 30)
        session = base_session(scope, data.mode)
        session["lines"] = [selected_line(data.product_id, data.quantity, data.unit)]
        session["constraints"].update(delivery_date=data.date.isoformat() if data.date else None, budget=str(data.budget) if data.budget is not None else None)
        session["messages"] = [{"role": "user", "text": f"{data.quantity} {data.unit} of {session['lines'][0]['requested_label']}"}]
        session["ambiguities"] = []
        session["interpretation_source"] = "Catalog selection"
        from .preferences import apply_saved
        apply_saved(session, db, scope, hard_only=not data.apply_preferences)
        issues = suitability(product_facts.normalize(data.product_id), session["lines"][0])
        if issues:
            fail("product_ineligible", " ".join(issues), 422)
        quote_for(session, scope)
        db.save("procurement", session["id"], scope["buyer_id"], session)
        db.audit(policy.uid("audit"), scope["buyer_id"], "procurement_created", {"session_id": session["id"], "source": "catalog"})
        return public(session)

    @app.post(PREFIX + "/from-meal-plan", response_model=ProcurementSessionResponse, response_model_exclude_unset=True)
    def from_meal_plan(data: FromMealPlan, scope=Depends(buyer)):
        limit("procurement-" + scope["buyer_id"], 30)
        plan = db.get("meal_plan", data.plan_id, scope["buyer_id"])
        if not plan or plan.get("customer_id") != scope["customer_id"]:
            fail("plan_not_found", "Meal plan not found in your customer scope.", 404)
        if not catalog.load_catalog():
            fail("catalog_missing", "The authorized challenge catalog is required.", 503)
        plan_lines = plan.get("lines", [])
        if not 1 <= len(plan_lines) <= 24:
            fail("invalid_plan", "This saved plan has no supported ingredient lines.", 422)
        if any(index < 0 or index >= len(plan_lines) for index in data.selections):
            fail("invalid_selection", "A selection refers to a line outside the saved meal plan.", 422)
        request = plan.get("request", {})
        session = base_session(scope, data.mode)
        session["constraints"].update(delivery_date=data.date.isoformat() if data.date else None, budget=str(data.budget) if data.budget is not None else None, preferences="cheapest" if request.get("priority") == "price" else "quality" if request.get("priority") == "quality" else "balanced")
        session["interpretation_source"] = "Saved meal plan; exact stored quantities without language-model reconstruction."
        session["recipe_notes"] = [plan.get("recipe_note", "Saved meal recipe requires chef review."), f"Recipe source: {request.get('recipe_source', 'unknown')}. Review the saved grams, yield, product purpose, dietary evidence and separate preparation before accepting this basket."]
        session["interpretation_notes"] = list(session["recipe_notes"])
        session["recipe_review_required"] = True
        session["recipe_request"] = None
        session["ambiguities"] = []
        session["source_meal_plan"] = {"id": plan["id"], "dish": plan.get("dish"), "cohorts": copy.deepcopy(plan.get("cohorts", {})), "request": copy.deepcopy(request)}
        session["messages"] = [{"role": "user", "text": f"Prepare a shopping basket from saved meal plan {plan['id']}; retain its exact ingredient quantities and selected products."}]
        for index, source_line in enumerate(plan_lines):
            quantity = decimal(source_line.get("required_kg"))
            if quantity is None or quantity <= 0 or quantity > 1000000:
                fail("invalid_plan", "A saved ingredient quantity is unsupported. Rebuild the meal plan.", 422)
            pid = data.selections.get(index)
            if pid is not None:
                allowed = {str(candidate.get("product_id")) for candidate in source_line.get("candidates", [])}
                if pid not in allowed:
                    fail("invalid_selection", "Choose only an actual candidate shown for that saved ingredient line.", 422)
                try:
                    product_facts.normalize(pid)
                except ValueError:
                    fail("product_missing", "A selected product no longer exists in the authorized catalog. Rebuild the plan.", 422)
            query = str(source_line.get("search_query", "")).strip()
            if not query:
                fail("invalid_plan", "A saved ingredient lacks a catalog search query. Rebuild the meal plan.", 422)
            explicit_dietary = source_line.get("dietary")
            dietary = list(explicit_dietary) if isinstance(explicit_dietary, list) else (["gluten_free"] if source_line.get("gluten_free_required") else [])
            # Shared non-meat ingredients serve the vegetarian group too. No
            # name or recipe choice grants a missing catalog dietary claim.
            meat = "beef" in query.casefold()
            if explicit_dietary is None and not meat and (request.get("vegetarian", 0) > 0 or "vegetarian" in source_line.get("ingredient", "").casefold()):
                dietary.append("vegetarian")
            origin = source_line.get("origin") if "origin" in source_line else source_line.get("meat_origin") if meat else None
            options = copy.deepcopy(ITEM_OPTIONS)
            options.update(preferred_brand=source_line.get("preferred_brand") or request.get("preferred_brand"), preferred_origin=source_line.get("preferred_origin") or request.get("preferred_origin"))
            session["lines"].append({"id": policy.uid("line"), "requested_label": query, "quantity": str(quantity), "unit": "kg", "dietary": dietary, "origin": origin if origin in ["finland", "eu"] else None, "max_unit_price": None, **options, "selected_product_id": pid, "selection_reason": "Selected explicitly in the saved kitchen plan." if pid else None, "meal_plan_line": {"index": index, "ingredient_id": source_line.get("ingredient_id"), "ingredient": source_line.get("ingredient"), "servings": source_line.get("servings"), "grams_per_serving": source_line.get("grams_per_serving"), "original_required_kg": str(quantity)}})
        if data.apply_preferences:
            from .preferences import apply_saved
            apply_saved(session, db, scope, apply_priority=False)
        from .preferences import enforce_hard
        enforce_hard(session, db, scope)
        for line in session["lines"]:
            if line.get("selected_product_id"):
                product = product_facts.normalize(line["selected_product_id"])
                issues = suitability(product, line)
                units, _ = item_facts(product, line["quantity"], line["unit"])
                if issues or units is None or product.get("deposits") or product.get("variable_unit"):
                    fail("meal_selection_ineligible", "No verified suitable product selected for " + line["requested_label"] + ". " + " ".join(issues or ["A valid fixed purchasing conversion is required."]), 422)
        quote_for(session, scope)
        db.save("procurement", session["id"], scope["buyer_id"], session)
        db.audit(policy.uid("audit"), scope["buyer_id"], "meal_plan_quoted", {"plan_id": plan["id"], "session_id": session["id"], "selections": data.selections, "recipe_review_required": True})
        return public(session)

    @app.get(PREFIX + "/{id}", response_model=ProcurementSessionResponse, response_model_exclude_unset=True)
    def get(id: str, scope=Depends(identity)):
        return public(load(id, scope), scope)

    @app.get(PREFIX + "/{id}/verify", response_model=ReceiptVerificationResponse, response_model_exclude_unset=True)
    def verify(id: str, scope=Depends(identity)):
        session = load(id, scope)
        receipt = session.get("receipt")
        offer = session.get("offer")
        stored = db.order(receipt["id"], scope["buyer_id"]) if receipt else None
        if not stored or not offer:
            fail("receipt_missing", "No simulated receipt is recorded for this cart.", 404)
        integrity = hmac.compare_digest(stored["fingerprint"], fingerprint(offer)) and stored["offer_id"] == offer["id"] and stored["items"] == offer["lines"] and stored["total"] == offer["total"]
        return {"receipt_id": stored["id"], "integrity_valid": integrity, "scope_valid": stored["buyer_id"] == scope["buyer_id"] and stored["customer_id"] == scope["customer_id"], "simulated": True, "verification_scope": "Gateway-held receipt consistency and exact basket hash; not an independent signature, supplier order, stock reservation or proof of delivery."}

    @app.post(PREFIX + "/{id}/actions", response_model=ProcurementSessionResponse, response_model_exclude_unset=True)
    def action(id: str, data: Action, scope=Depends(buyer)):
        limit("procurement-" + scope["buyer_id"], 60)
        old = load(id, scope)
        if old.get("cancelled"):
            fail("cart_cancelled", "This basket was cancelled. Reuse it from History to start a fresh draft.")
        if old["version"] != data.version:
            fail("version_conflict", "This cart changed. Reload the current version.")
        if old.get("receipt") or old.get("checkout_pending"):
            fail("cart_closed", "This basket is confirmed or being confirmed. Start another purchasing session.")
        session = copy.deepcopy(old)
        session["version"] += 1
        line = next((line for line in session["lines"] if line["id"] == data.line_id), None)
        if data.action in ["select_product", "set_quantity", "remove_line", "set_query"] and line is None:
            fail("line_missing", "Choose a line in this cart.", 422)
        if data.action == "message":
            if not data.message:
                fail("message_required", "Enter a purchasing change.", 422)
            interpret_into(session, data.message)
        elif data.action == "select_product":
            try:
                product = product_facts.normalize(data.product_id)
            except (ValueError, KeyError):
                fail("invalid_selection", "Choose an actual catalog product.", 422)
            from .preferences import enforce_hard
            enforce_hard(session, db, scope)
            issues = suitability(product, line)
            if issues:
                fail("product_ineligible", " ".join(issues), 422)
            line["selected_product_id"] = product["id"]
            line["selection_reason"] = "Selected explicitly by the customer."
            session["last_selected_line_id"] = line["id"]
        elif data.action == "add_product":
            if not data.product_id:
                fail("product_required", "Choose a catalog product.", 422)
            if len(session["lines"]) >= 24:
                fail("line_limit", "The current cart has 24 requests. Start another cart.", 422)
            added = selected_line(data.product_id, data.quantity or D(1), data.unit or "packages")
            session["lines"].append(added)
            from .preferences import apply_saved
            apply_saved(session, db, scope, apply_priority=False)
            issues = suitability(product_facts.normalize(data.product_id), added)
            if issues:
                fail("product_ineligible", " ".join(issues), 422)
            session["messages"].append({"role": "user", "text": f"Add {added['quantity']} {added['unit']} of {added['requested_label']}"})
        elif data.action == "set_quantity":
            if data.quantity is None:
                fail("quantity_required", "Enter a positive quantity.", 422)
            line["quantity"] = str(data.quantity)
            if data.unit:
                line["unit"] = data.unit
        elif data.action == "set_query":
            if not data.query or not data.query.strip():
                fail("query_required", "Enter a product or SKU to search for this ingredient.", 422)
            line["requested_label"] = data.query.strip()
            line["selected_product_id"] = None
            line["retrieval_queries"] = []
            line.pop("selection_reason", None)
        elif data.action == "remove_line":
            session["lines"] = [p for p in session["lines"] if p["id"] != line["id"]]
        elif data.action == "set_budget":
            session["constraints"]["budget"] = str(data.budget) if data.budget is not None else None
        elif data.action == "set_date":
            session["constraints"]["delivery_date"] = data.date.isoformat() if data.date else None
            session["interpretation_notes"] = [note for note in session.get("interpretation_notes", []) if not note.startswith("Interpreted the delivery deadline as ")]
            session["ambiguities"] = [a for a in session.get("ambiguities", []) if "date" not in a.lower() and "delivery" not in a.lower()]
        elif data.action == "acknowledge_recipe":
            session["recipe_review_required"] = False
            session["recipe_acknowledged_at"] = policy.now().isoformat()
        quote_for(session, scope)
        compare_save(old, session)
        db.audit(policy.uid("audit"), scope["buyer_id"], "procurement_updated", {"session_id": id, "version": session["version"], "action": data.action, "change": data.model_dump(mode="json", exclude_none=True), "offer_fingerprint": (session.get("offer") or {}).get("fingerprint")})
        return public(session)

    @app.post(PREFIX + "/{id}/request-approval", response_model=ProcurementSessionResponse, response_model_exclude_unset=True)
    def request_approval(id: str, data: ApprovalRequest, scope=Depends(buyer)):
        limit("request-approval-" + scope["buyer_id"], 30)
        old = load(id, scope)
        previous_request = (old.get("offer") or {}).get("approval_request") or {}
        explanation = (data.explanation or "").strip() or None
        if old.get("approval", {}).get("pending") and previous_request.get("previous_fingerprint") == data.fingerprint and previous_request.get("explanation") == explanation and previous_request.get("actor_id") == scope.get("actor_id"):
            return public(old, scope)
        exact_version(old, data)
        if old.get("receipt") or old.get("checkout_pending") or old.get("cancelled"):
            fail("cart_closed", "This basket is confirmed, cancelled or being confirmed.")
        offer = validate_snapshot(old)
        if not hmac.compare_digest(offer["fingerprint"], data.fingerprint) or not old.get("approval", {}).get("can_request"):
            fail("request_blocked", "Request approval only for the exact reviewed basket after resolving all hard blockers.")
        if old.get("requester_actor") != scope.get("actor_id") or old.get("requester_principal") != scope.get("principal_id"):
            fail("buyer_review_required", "Refresh the draft as its current buyer before submitting an approval request.")
        revalidate_exact(old, scope)
        session = copy.deepcopy(old)
        session["version"] += 1
        at = policy.now().isoformat()
        request = {"submitted_at": at, "explanation": explanation, "actor_id": scope["actor_id"], "principal_id": scope["principal_id"], "reasons": old["approval"]["reasons"], "requested_budget": old["approval"]["requested_budget"], "budget_excess": old["approval"]["budget_excess"], "previous_fingerprint": offer["fingerprint"]}
        session["offer"].update(id=policy.uid("basket"), session_version=session["version"], approval_request=request)
        session["offer"]["fingerprint"] = fingerprint(session["offer"])
        session.update(submitted_at=at, review_state="PENDING_APPROVAL", can_confirm=False)
        session["approval"].update(pending=True, can_request=False, explanation=explanation)
        if session.get("budget_exception"):
            session["budget_exception"].update(status="requested", requested_at=at, explanation=explanation, fingerprint=session["offer"]["fingerprint"], version=session["version"])
        session["assistant_message"] = "Your exact basket and financial exception request are saved for an independent authorized approver. Nothing has been submitted as an order."
        entry = history(session, "request_approval", scope, explanation)
        compare_save(old, session, snapshot=session["offer"])
        db.audit(policy.uid("audit"), scope["buyer_id"], "basket_approval_requested", {"session_id": id, "snapshot_id": session["offer"]["id"], **entry})
        return public(session, scope)

    @app.post(PREFIX + "/{id}/approve", response_model=ProcurementSessionResponse, response_model_exclude_unset=True)
    def approve(id: str, data: Fingerprint, scope=Depends(approver)):
        old = load(id, scope)
        exact_version(old, data)
        if old.get("receipt") or old.get("checkout_pending"):
            fail("cart_closed", "This basket is confirmed or being confirmed.")
        if old.get("cancelled"):
            fail("cart_cancelled", "This basket was cancelled. Reuse it from History to start a fresh draft.")
        offer = old.get("offer")
        if not offer or offer["status"] != "approval_required" or not hmac.compare_digest(offer["fingerprint"], data.fingerprint):
            fail("not_approvable", "Approve only the exact current basket requiring a spend exception.")
        reasons = decision_blockers(old, scope, db.workspace_authority(scope["buyer_id"], scope["customer_id"]))
        if reasons:
            fail("self_approval_forbidden", " ".join(reasons), 403)
        if (old.get("rejection") or {}).get("fingerprint") == offer["fingerprint"]:
            fail("basket_rejected", "This exact basket was rejected. The buyer must revise or refresh it before another decision.")
        if fingerprint(offer) != offer["fingerprint"] or offer["authority"] != authority() or policy.parse_time(offer["expires_at"]) <= policy.now():
            fail("stale_offer", "Refresh the basket and obtain a new exact approval.")
        if offer.get("approved"):
            return public(old, scope)
        if not old.get("approval", {}).get("pending") or not offer.get("approval_request"):
            fail("approval_not_requested", "The buyer must explicitly request approval for this exact basket first.")
        revalidate_exact(old, scope)
        session = copy.deepcopy(old)
        session["version"] += 1
        session["offer"]["approved"] = True
        session["offer"]["approval"] = {"approver": scope["name"], "approver_role": "approver", "actor_id": scope["actor_id"], "principal_id": scope["principal_id"], "fingerprint": offer["fingerprint"], "approved_at": policy.now().isoformat(), "expires_at": offer["expires_at"], "session_version": offer["session_version"], "decision_version": session["version"], "covered_reasons": offer["approval_reasons"]}
        session["approval"].update(status="approved", approved=True, pending=False, can_request=False)
        session["can_confirm"] = True
        session["review_state"] = "APPROVED"
        session["order_status"] = "READY_TO_ORDER"
        session["clarification_questions"] = [question for question in session["clarification_questions"] if not question["prompt"].startswith("Item subtotal exceeds your requested budget")]
        if session.get("budget_exception"):
            session["budget_exception"]["status"] = "approved"
        session["assistant_message"] = "This exact basket and its recorded financial exceptions are approved. The buyer must explicitly submit the simulation before the quotation expires."
        history(session, "approve", scope)
        compare_save(old, session)
        db.audit(policy.uid("audit"), scope["buyer_id"], "basket_approved", session["offer"]["approval"])
        return public(session, scope)

    @app.post(PREFIX + "/{id}/reject", response_model=ProcurementSessionResponse, response_model_exclude_unset=True)
    def reject_basket(id: str, data: Rejection, scope=Depends(approver)):
        limit("reject-" + scope["buyer_id"], 30)
        old = load(id, scope)
        exact_version(old, data)
        if old.get("receipt") or old.get("checkout_pending"):
            fail("cart_closed", "This basket is confirmed or being confirmed.")
        offer = old.get("offer")
        if not offer or offer["status"] != "approval_required" or not hmac.compare_digest(offer["fingerprint"], data.fingerprint):
            fail("not_rejectable", "Reject only the exact current basket requiring a spend exception.")
        reasons = decision_blockers(old, scope, db.workspace_authority(scope["buyer_id"], scope["customer_id"]))
        if reasons:
            fail("self_approval_forbidden", " ".join(reasons), 403)
        if fingerprint(offer) != offer["fingerprint"]:
            fail("stale_offer", "The basket changed. Reload it before making a decision.")
        if (old.get("rejection") or {}).get("fingerprint") == offer["fingerprint"]:
            return public(old, scope)
        if offer.get("approved"):
            fail("decision_recorded", "This exact basket was already approved. The buyer must revise it before a different decision.")
        if not old.get("approval", {}).get("pending") or old.get("changes_requested") or old.get("cancelled"):
            fail("approval_not_requested", "This basket has no pending approval request.")
        session = copy.deepcopy(old)
        session["version"] += 1
        session["rejection"] = {"approver": scope["name"], "approver_role": "approver", "fingerprint": offer["fingerprint"], "rejected_at": policy.now().isoformat(), "reason": (data.reason or "").strip() or None}
        session["approval"].update(status="rejected", approved=False, pending=False, can_request=False)
        session["can_confirm"] = False
        session["order_status"] = "NEEDS_CLARIFICATION"
        session["review_state"] = "REJECTED"
        if session.get("budget_exception"):
            session["budget_exception"]["status"] = "rejected"
        session["assistant_message"] = "The approver rejected this basket. Review the decision, then revise or refresh the basket before requesting a new approval."
        history(session, "reject", scope, session["rejection"]["reason"])
        compare_save(old, session)
        db.audit(policy.uid("audit"), scope["buyer_id"], "basket_rejected", {"session_id": id, **session["rejection"]})
        return public(session, scope)

    @app.post(PREFIX + "/{id}/request-changes", response_model=ProcurementSessionResponse, response_model_exclude_unset=True)
    def request_changes(id: str, data: ChangesRequest, scope=Depends(approver)):
        old = load(id, scope)
        exact_version(old, data)
        if old.get("receipt") or old.get("checkout_pending") or old.get("cancelled"):
            fail("cart_closed", "This basket is closed or being confirmed.")
        offer = old.get("offer") or {}
        if not hmac.compare_digest(offer.get("fingerprint", ""), data.fingerprint) or not old.get("approval", {}).get("pending"):
            fail("approval_not_requested", "Request changes only for the exact pending basket.")
        if fingerprint(offer) != offer.get("fingerprint"):
            fail("stale_offer", "The exact basket or policy changed. Reload and request a fresh buyer review.")
        reasons = decision_blockers(old, scope, db.workspace_authority(scope["buyer_id"], scope["customer_id"]))
        if reasons:
            fail("self_approval_forbidden", " ".join(reasons), 403)
        reason = data.reason.strip()
        if not reason:
            fail("reason_required", "Describe the changes required from the buyer.", 422)
        session = copy.deepcopy(old)
        session["version"] += 1
        session["changes_requested"] = {"approver": scope["name"], "fingerprint": offer["fingerprint"], "reason": reason, "at": policy.now().isoformat()}
        session["approval"].update(status="changes_requested", approved=False, pending=False, can_request=False)
        session.update(can_confirm=False, order_status="NEEDS_CLARIFICATION", review_state="CHANGES_REQUESTED", assistant_message="The approver requested changes. Edit the basket, refresh it and submit a new exact approval request.")
        if session.get("budget_exception"):
            session["budget_exception"]["status"] = "changes_requested"
        entry = history(session, "request_changes", scope, reason)
        compare_save(old, session)
        db.audit(policy.uid("audit"), scope["buyer_id"], "basket_changes_requested", {"session_id": id, **entry})
        return public(session, scope)

    @app.post(PREFIX + "/{id}/cancel", response_model=ProcurementSessionResponse, response_model_exclude_unset=True)
    def cancel(id: str, data: Cancellation, scope=Depends(buyer)):
        old = load(id, scope)
        exact_version(old, data)
        if old.get("receipt") or old.get("checkout_pending"):
            fail("cart_closed", "A confirmed or submitting simulation cannot be cancelled here.")
        if old.get("cancelled"):
            return public(old, scope)
        session = copy.deepcopy(old)
        session["version"] += 1
        session["cancelled"] = {"actor": scope["name"], "at": policy.now().isoformat(), "reason": (data.reason or "").strip() or None}
        session["approval"].update(status="cancelled", approved=False, pending=False, can_request=False)
        session.update(can_confirm=False, review_state="CANCELLED", order_status="NEEDS_CLARIFICATION", assistant_message="This draft was cancelled. Its history is preserved and no order or payment was made.")
        entry = history(session, "cancel", scope, session["cancelled"]["reason"])
        compare_save(old, session)
        db.audit(policy.uid("audit"), scope["buyer_id"], "basket_cancelled", {"session_id": id, **entry})
        return public(session, scope)

    @app.post(PREFIX + "/{id}/confirm", response_model=ProcurementSessionResponse, response_model_exclude_unset=True)
    def confirm(id: str, data: Fingerprint, key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128), scope=Depends(buyer)):
        old = load(id, scope)
        offer = old.get("offer")
        if not offer or not hmac.compare_digest(offer["fingerprint"], data.fingerprint):
            fail("offer_changed", "Review and confirm the exact current basket.")
        prior = db.existing(offer, key)
        if prior:
            restored = copy.deepcopy(old)
            restored.update(receipt=prior, can_confirm=False, checkout_pending=False, order_status="SIMULATED_ORDER_CONFIRMED")
            compare_save(old, restored)
            return public(restored)
        exact_version(old, data)
        if not old["can_confirm"] or fingerprint(offer) != offer["fingerprint"] or offer["authority"] != authority() or policy.parse_time(offer["expires_at"]) <= policy.now():
            fail("confirmation_blocked", "Resolve constraints and obtain any required approval for an unexpired basket.")
        if old.get("checkout_pending") and old.get("pending_key") != key:
            fail("checkout_pending", "Retry confirmation with its original idempotency key.")
        deadlines = revalidate_exact(old, scope)
        pending = copy.deepcopy(old)
        pending.update(checkout_pending=True, pending_key=key)
        pending["version"] += 1
        compare_save(old, pending)
        receipt = {"id": policy.uid("sim-basket"), "offer_id": offer["id"], "buyer_id": scope["buyer_id"], "customer_id": scope["customer_id"], "status": "simulated", "simulated": True, "items": offer["lines"], "total": offer["total"], "currency": "EUR", "price_scope": "tax-inclusive item subtotal; other charges excluded", "requested_date": offer["requested_date"], "mode": offer["mode"], "fingerprint": offer["fingerprint"], "approval": offer.get("approval"), "idempotent_replay": False, "notice": "Simulated order only. No supplier order, reservation, invoice or payment was created."}
        receipt["budget_exception"] = copy.deepcopy(old.get("budget_exception"))
        try:
            receipt = db.commit(offer, key, receipt, int(D(authority()["cumulative_limit"]) * 100), min(deadlines).isoformat())
        except Exception:
            recover = copy.deepcopy(pending)
            recover.update(checkout_pending=False)
            recover["version"] += 1
            compare_save(pending, recover)
            raise
        final = copy.deepcopy(pending)
        final.update(receipt=receipt, checkout_pending=False, can_confirm=False, order_status="SIMULATED_ORDER_CONFIRMED", assistant_message="Your simulated order is confirmed. No real purchase or payment was made.")
        final["version"] += 1
        compare_save(pending, final)
        return public(final)
