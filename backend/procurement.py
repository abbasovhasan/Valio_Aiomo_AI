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
from pydantic import BaseModel, ConfigDict, Field

from . import catalog, policy, upstream, product_facts
from .config import MANDATE

D = Decimal
PREFIX = "/api/v1/procurement/sessions"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateSession(Strict):
    message: str = Field(min_length=1, max_length=3000)
    mode: Literal["fixture", "live"] = "fixture"
    use_model: bool = False
    date: Date | None = None
    budget: Decimal | None = Field(default=None, ge=0, le=1000000, decimal_places=2)


class Action(Strict):
    version: int = Field(ge=1)
    action: Literal[
        "message", "select_product", "set_quantity", "remove_line", "set_budget",
        "set_date", "set_query", "quote", "acknowledge_recipe",
    ]
    message: str | None = Field(default=None, min_length=1, max_length=3000)
    line_id: str | None = Field(default=None, max_length=80)
    product_id: str | None = Field(default=None, max_length=80)
    query: str | None = Field(default=None, min_length=1, max_length=120)
    quantity: Decimal | None = Field(default=None, gt=0, le=1000000, decimal_places=3)
    unit: Literal["L", "kg", "pieces", "packages"] | None = None
    budget: Decimal | None = Field(default=None, ge=0, le=1000000, decimal_places=2)
    date: Date | None = None


class FromMealPlan(Strict):
    plan_id: str = Field(min_length=1, max_length=80)
    selections: dict[int, str] = Field(default_factory=dict, max_length=24)
    mode: Literal["fixture", "live"] = "fixture"
    date: Date | None = None
    budget: Decimal | None = Field(default=None, ge=0, le=1000000, decimal_places=2)


class Fingerprint(Strict):
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


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
    return {
        "id": "customer-confirmed-demo-basket-v1",
        "assortment": "Customer explicitly reviews selected real catalog products; hard dietary evidence remains mandatory.",
        "autonomous_limit": MANDATE["autonomous_limit"],
        "exception_limit": MANDATE["exception_limit"],
        "cumulative_limit": MANDATE["cumulative_limit"],
        "expires_at": MANDATE["expires_at"],
        "confirmation_required": True,
        "orders": "simulated_only",
    }


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
    for row in result["availability"]["products"]:
        p = product_facts.normalize(str(row["productId"]))
        for schedule in row.get("scheduleLines", []):
            schedule["salesUnit"] = p["sales_unit"]
    return result


def lookup(session, ids):
    return (upstream.sponsor_lookup if session["mode"] == "live" else fixture_lookup)(
        session["customer_id"], session["constraints"]["delivery_date"], ids
    )


def item_facts(product, quantity, unit):
    units = product_facts.units_for(product, D(quantity), unit)
    key = {"L": "liters_per_sales_unit", "kg": "kg_per_sales_unit", "pieces": "pieces_per_sales_unit"}.get(unit)
    pack = D(1) if unit == "packages" else decimal(product.get(key)) if key else None
    return units, pack


def round_sales_units(product, exact):
    """Round aggregated rational requirements without recurring-decimal drift."""
    lot = decimal(product.get("allowed_lot_size"))
    if lot is None or lot <= 0 or exact <= 0 or product.get("variable_unit"):
        return None
    step = Fraction(lot).numerator
    return D(-(-exact.numerator // (exact.denominator * step)) * step)


def base_session(scope, mode, use_model=False):
    return {"id": policy.uid("procurement"), "version": 1, "buyer_id": scope["buyer_id"], "customer_id": scope["customer_id"], "mode": mode, "use_model": use_model, "created_at": policy.now().isoformat(), "messages": [], "lines": [], "constraints": {"budget": None, "currency": "EUR", "delivery_date": None, "preferences": "balanced"}, "receipt": None, "checkout_pending": False}


def commercial(product, units, evidence, day):
    issues = []
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
    start, end = policy.parse_time(cp.get("validFrom")), policy.parse_time(cp.get("validTo"))
    if not start or not end or not start <= now <= end or not start.date().isoformat() <= day <= end.date().isoformat():
        issues.append("Price validity does not cover now and the requested delivery date.")
    tax = price.get("tax") if isinstance(price.get("tax"), dict) else {}
    if decimal(tax.get("taxRate")) is None:
        issues.append("Tax information is missing.")
    cutoff = policy.parse_time(stock.get("closingTime"))
    if not cutoff or cutoff <= now:
        issues.append("Ordering cutoff is unavailable or passed.")
    if not stock or stock.get("salesBlock", True):
        issues.append("Supplier sales permission is missing or blocked.")
    available = D(0)
    possible_dates = []
    unknown = False
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
        if when <= day:
            # Schedule lines are alternatives/snapshots, never assumed additive.
            available = max(available, amount)
            if units is not None and amount >= units:
                possible_dates.append(when)
    if units is None:
        issues.append("No verified dimensional conversion into sellable packs.")
    elif available < units:
        issues.append("Available quantity is unknown." if unknown else f"Only {available} {product['sales_unit']} confirmed by {day}; {units} needed.")
    fetched = policy.parse_time(evidence.get("fetched_at"))
    if not fetched or not -30 <= (now - fetched).total_seconds() <= 300:
        issues.append("Supplier evidence is stale or has no valid timestamp.")
    total = unit_price * units if unit_price is not None and units is not None else None
    deadlines = [v for v in [end, cutoff, fetched + timedelta(minutes=5) if fetched else None] if v]
    return {
        "unit_price": money(unit_price) if unit_price is not None else None,
        "price_decimal": str(unit_price) if unit_price is not None else None,
        "line_total": money(total) if total is not None else None,
        "availability": "available" if units is not None and available >= units else "unknown" if unknown else "insufficient",
        "available_sales_units": str(available),
        "delivery_date": min(possible_dates) if possible_dates else None,
        "issues": issues,
        "valid_until": min(deadlines).isoformat() if len(deadlines) == 3 else None,
        "evidence": {"source": evidence["source"], "fetched_at": evidence["fetched_at"], "price": price, "availability": stock},
    }


def requirements(session):
    return {
        "items": [{"id": line["id"], "query": line["requested_label"], "quantity": line["quantity"], "unit": line["unit"], "dietary": line["dietary"], "origin": line.get("origin"), "max_unit_price": line.get("max_unit_price")} for line in session["lines"]],
        "budget": session["constraints"]["budget"],
        "delivery_date": session["constraints"]["delivery_date"],
        "preference": session["constraints"]["preferences"],
        "notes": session.get("interpretation_notes", []),
        "ambiguous_fields": session.get("ambiguities", []),
        "recipe_request": session.get("recipe_request"),
    }


def interpret_into(session, message):
    from .interpretation import interpret
    previous_recipe = session.get("recipe_request")
    previous_recipe_notes = session.get("recipe_notes", [])
    previous_review_required = session.get("recipe_review_required", False)
    result = interpret(message, prior=requirements(session) if session["lines"] else None, use_model=session["use_model"])
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
            "dietary": item.get("dietary", []), "origin": item.get("origin"),
            "max_unit_price": item.get("max_unit_price"),
            "selected_product_id": old.get("selected_product_id") if old else None,
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


def quote(session, spent):
    session["offer"] = None
    session["receipt"] = None
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
        products = product_facts.search(line["requested_label"], 16, line["dietary"], line.get("origin"))
        products.sort(key=lambda p: (bool(product_facts.suitability(p, line["dietary"], line.get("origin"))), product_facts.units_for(p, D(line["quantity"]), line["unit"]) is None))
        products = products[:4]
        if line.get("selected_product_id") and line["selected_product_id"] not in [p["id"] for p in products]:
            try:
                products.append(product_facts.normalize(line["selected_product_id"]))
            except ValueError:
                line["selected_product_id"] = None
        product_map[line["id"]] = products
        ids.extend(p["id"] for p in products)
    ids = list(dict.fromkeys(ids))
    evidence = lookup(session, ids) if ids and valid_day else None
    for line in session["lines"]:
        line["candidates"] = []
        for p in product_map[line["id"]]:
            units, pack = item_facts(p, line["quantity"], line["unit"])
            issues = product_facts.suitability(p, line["dietary"], line.get("origin"))
            if units is None:
                issues.extend(p.get("conversion_issues", []))
            if p.get("deleted"):
                issues.append("Product is deleted.")
            if p.get("variable_unit"):
                issues.append("Variable-weight commercial charges are unsupported.")
            if p.get("deposits"):
                issues.append("Deposit charges need a supported charge calculation.")
            commercial_facts = commercial(p, units, evidence, day) if evidence else {"issues": ["Set a valid delivery date to obtain a quotation."], "unit_price": None, "line_total": None, "availability": "not_queried", "delivery_date": None}
            issues.extend(commercial_facts["issues"])
            limit = decimal(line.get("max_unit_price"))
            price = decimal(commercial_facts.get("price_decimal"))
            if limit is not None and (price is None or pack is None or pack <= 0 or price / pack > limit):
                issues.append(f"Price per requested {line['unit']} exceeds the €{limit} limit or is unknown.")
            line["candidates"].append({
                "id": p["id"], "name": p["name"], "sales_unit": p["sales_unit"],
                "pack_quantity": str(pack) if pack is not None else None, "pack_unit": line["unit"],
                "quantity_sales_units": str(units) if units is not None else None,
                "effective_quantity": str(units * pack) if units is not None and pack is not None else None,
                "requested_quantity": line["quantity"],
                "surplus_quantity": str(units * pack - D(line["quantity"])) if units is not None and pack is not None else None,
                "unit_price": commercial_facts["unit_price"], "line_total": commercial_facts["line_total"],
                "availability": commercial_facts["availability"], "delivery_date": commercial_facts["delivery_date"],
                "attributes": {"brand": p.get("brand"), "claims": p.get("claims", []), "origin_codes": p.get("origin_codes", [])},
                "issues": issues, "source": evidence["source"] if evidence else "local_challenge_catalog", "product": p,
                "commercial": commercial_facts,
            })
        viable = [c for c in line["candidates"] if not c["issues"]]
        if not line.get("selected_product_id"):
            if len(viable) == 1:
                line["selected_product_id"] = viable[0]["id"]
                line["selection_reason"] = "Only quoted candidate satisfies all verified constraints."
            elif viable and session["constraints"]["preferences"] == "cheapest":
                chosen = min(viable, key=lambda c: D(c["line_total"]))
                line["selected_product_id"] = chosen["id"]
                line["selection_reason"] = "Lowest rounded item subtotal among the quoted compliant candidates."
        selected = next((c for c in line["candidates"] if c["id"] == line.get("selected_product_id")), None)
        line["issues"] = selected["issues"] if selected else ["Choose a suitable product."] if viable else ["No quoted candidate satisfies every requirement."]
        line["status"] = "EXACT_MATCH" if selected and not selected["issues"] else "CONSTRAINT_CONFLICT" if selected else "AMBIGUOUS_MATCH" if viable else "NOT_FOUND" if not line["candidates"] else "CONSTRAINT_CONFLICT"
        if line["issues"]:
            questions.append({"id": "choose-" + line["id"], "line_id": line["id"], "prompt": f"Review {line['requested_label']}: " + " ".join(line["issues"]), "options": [{"id": c["id"], "label": c["name"], "action": "select_product", "payload": {"line_id": line["id"], "product_id": c["id"]}} for c in viable]})
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
    if remaining is not None and remaining < 0:
        blockers.append(f"Item subtotal exceeds your hard budget by €{money(-remaining)}. Increase the budget explicitly, change products or reduce quantities.")
        all_valid = False
    snapshot = authority()
    if subtotal > D(snapshot["exception_limit"]) or spent + int(subtotal * 100) > int(D(snapshot["cumulative_limit"]) * 100):
        blockers.append("The whole basket exceeds the configured exception ceiling or shared cumulative cap.")
        all_valid = False
    expiry = policy.parse_time(snapshot["expires_at"])
    if not expiry or expiry <= policy.now():
        blockers.append("The demonstration purchasing policy has expired.")
        all_valid = False
    for i, text in enumerate(blockers):
        questions.append({"id": f"constraint-{i}", "line_id": None, "prompt": text, "options": []})
    requires_approval = subtotal > D(snapshot["autonomous_limit"])
    session["approval"] = {"status": "required" if all_valid and requires_approval else "not_required" if all_valid else "blocked", "threshold": snapshot["autonomous_limit"], "approved": False, "policy": snapshot}
    session["cart"] = {"items": cart_items, "subtotal": money(subtotal) if all_priced else None, "total": None, "unknown_charges": ["Delivery and service charges are outside this item-price simulation; no final commercial charge is quoted."], "budget_remaining": money(remaining) if remaining is not None else None, "currency": "EUR", "price_scope": "tax-inclusive item subtotal"}
    session["clarification_questions"] = questions
    impossible = valid_day and any(not line["candidates"] or all(c["issues"] for c in line["candidates"]) for line in session["lines"])
    session["order_status"] = "READY_TO_ORDER" if all_valid else "CANNOT_FULFILL" if impossible else "NEEDS_CLARIFICATION"
    session["assistant_message"] = "Your complete item-price basket is ready for review." if all_valid else "Review the highlighted choices and requirements to complete your basket."
    if all_valid:
        offer = {"id": policy.uid("basket"), "buyer_id": session["buyer_id"], "customer_id": session["customer_id"], "session_id": session["id"], "session_version": session["version"], "lines": cart_items, "requested_requirements": requirements(session), "requested_date": day, "total": money(subtotal), "total_cents": int(subtotal * 100), "currency": "EUR", "mode": session["mode"], "status": "approval_required" if requires_approval else "within_mandate", "expires_at": min([policy.now() + timedelta(minutes=5), expiry] + [policy.parse_time(v) for v in deadlines]).isoformat(), "authority": snapshot, "approved": False, "approval": None}
        offer["fingerprint"] = fingerprint(offer)
        session["offer"] = offer
        session["can_confirm"] = not requires_approval
    return session


def register_routes(app, db, buyer, approver, identity, limit):
    def load(id, scope):
        result = db.get("procurement", id, scope["buyer_id"])
        if not result or result["customer_id"] != scope["customer_id"]:
            fail("not_found", "Purchasing session not found in your customer scope.", 404)
        return result

    def compare_save(old, new):
        with db.tx() as c:
            row = c.execute("SELECT body FROM aimo_documents WHERE kind=? AND id=? AND buyer_id=?" + (" FOR UPDATE" if db.backend == "postgres" else ""), ("procurement", old["id"], old["buyer_id"])).fetchone()
            if not row or json.loads(row[0]) != old:
                fail("version_conflict", "This cart changed in another request. Reload it before editing.")
            c.execute("UPDATE aimo_documents SET body=? WHERE kind=? AND id=? AND buyer_id=?", (json.dumps(new), "procurement", old["id"], old["buyer_id"]))

    def public(session):
        # Commercial raw data remain server-side and in immutable basket evidence.
        result = copy.deepcopy(session)
        for line in result["lines"]:
            for candidate in line.get("candidates", []):
                candidate.pop("product", None)
                candidate.pop("commercial", None)
        if result.get("offer"):
            result["offer"] = {k: result["offer"][k] for k in ["id", "fingerprint", "expires_at", "total", "status", "approved"]}
            if not result.get("receipt") and policy.parse_time(result["offer"]["expires_at"]) <= policy.now():
                result["can_confirm"] = False
                result["assistant_message"] = "This quotation expired. Refresh prices and availability before confirming."
        result.pop("pending_key", None)
        return result

    @app.post(PREFIX)
    def create(data: CreateSession, scope=Depends(buyer)):
        limit("procurement-" + scope["buyer_id"], 30)
        if not catalog.load_catalog():
            fail("catalog_missing", "The authorized challenge catalog is required.", 503)
        session = base_session(scope, data.mode, data.use_model)
        interpret_into(session, data.message)
        if data.date is not None:
            session["constraints"]["delivery_date"] = data.date.isoformat()
        if data.budget is not None:
            session["constraints"]["budget"] = str(data.budget)
        quote(session, db.spent(scope["buyer_id"]))
        db.save("procurement", session["id"], scope["buyer_id"], session)
        db.audit(policy.uid("audit"), scope["buyer_id"], "procurement_created", {"session_id": session["id"], "version": 1})
        return public(session)

    @app.post(PREFIX + "/from-meal-plan")
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
        session["constraints"].update(delivery_date=data.date.isoformat() if data.date else None, budget=str(data.budget) if data.budget is not None else None, preferences="cheapest" if request.get("priority") == "price" else "balanced")
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
            dietary = ["gluten_free"] if source_line.get("gluten_free_required") else []
            # Shared non-meat ingredients serve the vegetarian group too. No
            # name or recipe choice grants a missing catalog dietary claim.
            meat = "beef" in query.casefold()
            if not meat and (request.get("vegetarian", 0) > 0 or "vegetarian" in source_line.get("ingredient", "").casefold()):
                dietary.append("vegetarian")
            origin = source_line.get("meat_origin")
            session["lines"].append({"id": policy.uid("line"), "requested_label": query, "quantity": str(quantity), "unit": "kg", "dietary": dietary, "origin": origin if meat and origin in ["finland", "eu"] else None, "max_unit_price": None, "selected_product_id": pid, "selection_reason": "Selected explicitly in the saved kitchen plan." if pid else None, "meal_plan_line": {"index": index, "ingredient": source_line.get("ingredient"), "servings": source_line.get("servings"), "grams_per_serving": source_line.get("grams_per_serving"), "original_required_kg": str(quantity)}})
        quote(session, db.spent(scope["buyer_id"]))
        db.save("procurement", session["id"], scope["buyer_id"], session)
        db.audit(policy.uid("audit"), scope["buyer_id"], "meal_plan_quoted", {"plan_id": plan["id"], "session_id": session["id"], "selections": data.selections, "recipe_review_required": True})
        return public(session)

    @app.get(PREFIX + "/{id}")
    def get(id: str, scope=Depends(identity)):
        return public(load(id, scope))

    @app.get(PREFIX + "/{id}/verify")
    def verify(id: str, scope=Depends(identity)):
        session = load(id, scope)
        receipt = session.get("receipt")
        offer = session.get("offer")
        stored = db.order(receipt["id"], scope["buyer_id"]) if receipt else None
        if not stored or not offer:
            fail("receipt_missing", "No simulated receipt is recorded for this cart.", 404)
        integrity = hmac.compare_digest(stored["fingerprint"], fingerprint(offer)) and stored["offer_id"] == offer["id"] and stored["items"] == offer["lines"] and stored["total"] == offer["total"]
        return {"receipt_id": stored["id"], "integrity_valid": integrity, "scope_valid": stored["buyer_id"] == scope["buyer_id"] and stored["customer_id"] == scope["customer_id"], "simulated": True, "verification_scope": "Gateway-held receipt consistency and exact basket hash; not an independent signature, supplier order, stock reservation or proof of delivery."}

    @app.post(PREFIX + "/{id}/actions")
    def action(id: str, data: Action, scope=Depends(buyer)):
        limit("procurement-" + scope["buyer_id"], 60)
        old = load(id, scope)
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
            if not any(c["id"] == data.product_id for c in line.get("candidates", [])):
                fail("invalid_selection", "Select one of this line's actual catalog candidates.", 422)
            line["selected_product_id"] = data.product_id
            line["selection_reason"] = "Selected explicitly by the customer."
            session["last_selected_line_id"] = line["id"]
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
            line.pop("selection_reason", None)
        elif data.action == "remove_line":
            session["lines"] = [p for p in session["lines"] if p["id"] != line["id"]]
        elif data.action == "set_budget":
            session["constraints"]["budget"] = str(data.budget) if data.budget is not None else None
        elif data.action == "set_date":
            session["constraints"]["delivery_date"] = data.date.isoformat() if data.date else None
            session["ambiguities"] = [a for a in session.get("ambiguities", []) if "date" not in a.lower() and "delivery" not in a.lower()]
        elif data.action == "acknowledge_recipe":
            session["recipe_review_required"] = False
            session["recipe_acknowledged_at"] = policy.now().isoformat()
        quote(session, db.spent(scope["buyer_id"]))
        compare_save(old, session)
        db.audit(policy.uid("audit"), scope["buyer_id"], "procurement_updated", {"session_id": id, "version": session["version"], "action": data.action, "change": data.model_dump(mode="json", exclude_none=True), "offer_fingerprint": (session.get("offer") or {}).get("fingerprint")})
        return public(session)

    @app.post(PREFIX + "/{id}/approve")
    def approve(id: str, data: Fingerprint, scope=Depends(approver)):
        old = load(id, scope)
        if old.get("receipt") or old.get("checkout_pending"):
            fail("cart_closed", "This basket is confirmed or being confirmed.")
        offer = old.get("offer")
        if not offer or offer["status"] != "approval_required" or not hmac.compare_digest(offer["fingerprint"], data.fingerprint):
            fail("not_approvable", "Approve only the exact current basket requiring a spend exception.")
        if fingerprint(offer) != offer["fingerprint"] or offer["authority"] != authority() or policy.parse_time(offer["expires_at"]) <= policy.now():
            fail("stale_offer", "Refresh the basket and obtain a new exact approval.")
        if offer.get("approved"):
            return public(old)
        session = copy.deepcopy(old)
        session["version"] += 1
        session["offer"]["approved"] = True
        session["offer"]["approval"] = {"approver": scope["name"], "approver_role": "approver", "fingerprint": offer["fingerprint"], "approved_at": policy.now().isoformat(), "expires_at": offer["expires_at"]}
        session["approval"].update(status="approved", approved=True)
        session["can_confirm"] = True
        compare_save(old, session)
        db.audit(policy.uid("audit"), scope["buyer_id"], "basket_approved", session["offer"]["approval"])
        return public(session)

    @app.post(PREFIX + "/{id}/confirm")
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
        if not old["can_confirm"] or fingerprint(offer) != offer["fingerprint"] or offer["authority"] != authority() or policy.parse_time(offer["expires_at"]) <= policy.now():
            fail("confirmation_blocked", "Resolve constraints and obtain any required approval for an unexpired basket.")
        if old.get("checkout_pending") and old.get("pending_key") != key:
            fail("checkout_pending", "Retry confirmation with its original idempotency key.")
        # Revalidate exact SKU quantities and commercial facts before atomically
        # consuming shared synthetic spend. No new product choice happens here.
        evidence = lookup(old, [line["id"] for line in offer["lines"]])
        deadlines = [policy.parse_time(offer["expires_at"])]
        for line in offer["lines"]:
            product = product_facts.normalize(line["id"])
            exact_units = Fraction(0)
            fresh = commercial(product, D(line["quantity_sales_units"]), evidence, offer["requested_date"])
            if fresh["issues"] or fresh["unit_price"] != line["unit_price"] or fresh["line_total"] != line["line_total"]:
                fail("revalidation_failed", "Price, stock or delivery changed. Refresh the basket and review it again.")
            # Current catalog suitability and pack sizes must match the reviewed facts.
            for request_line in old["lines"]:
                if request_line.get("selected_product_id") == product["id"]:
                    if product_facts.suitability(product, request_line["dietary"], request_line.get("origin")) or product.get("deleted") or product.get("deposits") or product.get("variable_unit"):
                        fail("catalog_changed", "Product evidence changed. Refresh and review the basket.")
                    old_candidate = next(c for c in request_line["candidates"] if c["id"] == product["id"])
                    _, pack = item_facts(product, request_line["quantity"], request_line["unit"])
                    if pack is None or str(pack) != old_candidate["pack_quantity"]:
                        fail("catalog_changed", "Pack conversion changed. Refresh and review the basket.")
                    exact_units += Fraction(D(request_line["quantity"])) / Fraction(pack)
            if round_sales_units(product, exact_units) != D(line["quantity_sales_units"]):
                fail("catalog_changed", "Pack order increment changed. Refresh and review the basket.")
            deadline = policy.parse_time(fresh.get("valid_until"))
            if deadline is None:
                fail("invalid_deadline", "Supplier commitment deadline is unknown.")
            deadlines.append(deadline)
        pending = copy.deepcopy(old)
        pending.update(checkout_pending=True, pending_key=key)
        pending["version"] += 1
        compare_save(old, pending)
        receipt = {"id": policy.uid("sim-basket"), "offer_id": offer["id"], "buyer_id": scope["buyer_id"], "customer_id": scope["customer_id"], "status": "simulated", "simulated": True, "items": offer["lines"], "total": offer["total"], "currency": "EUR", "price_scope": "tax-inclusive item subtotal; other charges excluded", "requested_date": offer["requested_date"], "mode": offer["mode"], "fingerprint": offer["fingerprint"], "approval": offer.get("approval"), "idempotent_replay": False, "notice": "Simulated order only. No supplier order, reservation, invoice or payment was created."}
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
