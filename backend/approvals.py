"""Scoped pending basket decisions; approval never bypasses hard constraints."""

import json
from typing import Literal

from fastapi import Depends, Query
from pydantic import BaseModel, Field

from . import policy
from .procurement import fingerprint, decision_blockers, current_review_context, current_review
from .procurement_contract import DateText, FingerprintText, MoneyText, TimestampText


class PendingApproval(BaseModel):
    id: str
    version: int = Field(ge=1)
    created_at: TimestampText
    requested_date: DateText
    subtotal: MoneyText
    currency: Literal["EUR"]
    fingerprint: FingerprintText
    expires_at: TimestampText
    status: Literal["pending", "expired"]
    can_approve: bool
    can_reject: bool
    line_count: int = Field(ge=1)
    buyer_name: str
    workspace_name: str | None
    request_title: str
    submitted_at: TimestampText
    reasons: list[Literal["requested_budget", "spending_authority"]]
    requested_budget: MoneyText | None
    budget_excess: MoneyText
    explanation: str | None
    authority_limit: MoneyText
    cumulative_remaining: MoneyText | None
    cumulative_spent: MoneyText
    blockers: list[str]
    review_state: Literal["PENDING_APPROVAL", "BLOCKED"]
    decision_blockers: list[str]
    can_request_changes: bool


class ApprovalQueue(BaseModel):
    items: list[PendingApproval]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


def register_routes(app, db, approver, limit):
    @app.get("/api/v1/approvals", response_model=ApprovalQueue)
    def pending_approvals(limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0), scope=Depends(approver)):
        with db.tx() as c:
            rows = c.execute("SELECT body FROM aimo_documents WHERE kind=? AND buyer_id=?", ("procurement", scope["buyer_id"])).fetchall()
        entries = []
        now = policy.now()
        context = current_review_context(db, scope)
        for row in rows:
            session = json.loads(row[0])
            offer = session.get("offer") or {}
            if (
                session.get("customer_id") != scope["customer_id"]
                or session.get("receipt") or session.get("checkout_pending")
                or offer.get("status") != "approval_required" or offer.get("approved")
                or (session.get("rejection") or {}).get("fingerprint") == offer.get("fingerprint")
                or not session.get("approval", {}).get("pending") or not session.get("submitted_at")
                or session.get("changes_requested") or session.get("cancelled")
            ):
                continue
            # Queue entries refer to a current, verifiable basket. An expired
            # basket remains visible for review but cannot be approved.
            expiry = policy.parse_time(offer.get("expires_at"))
            if not expiry or fingerprint(offer) != offer.get("fingerprint"):
                continue
            expired = expiry <= now
            blocked = decision_blockers(session, scope, context["assignment"])
            review = current_review(session, db, context=context)
            original = next((message.get("text", "") for message in session.get("messages", []) if message.get("role") == "user"), "Purchasing request")
            entries.append({
                "id": session["id"], "version": session["version"],
                "created_at": session["created_at"], "requested_date": offer["requested_date"],
                "subtotal": offer["total"], "currency": "EUR", "fingerprint": offer["fingerprint"],
                "expires_at": offer["expires_at"], "status": "expired" if expired else "pending",
                "can_approve": not expired and not blocked and not review["blockers"], "can_reject": not blocked, "can_request_changes": not blocked, "line_count": len(session["lines"]),
                "buyer_name": session.get("buyer_name", "Buyer"), "request_title": original[:180], "submitted_at": session["submitted_at"],
                "workspace_name": session.get("workspace_name"),
                "reasons": session["approval"].get("reasons", []), "requested_budget": session["approval"].get("requested_budget"), "budget_excess": session["approval"].get("budget_excess") or "0.00", "explanation": session["approval"].get("explanation"),
                "authority_limit": offer["authority"]["autonomous_limit"], "cumulative_remaining": review["cumulative_remaining"], "cumulative_spent": review["cumulative_spent"], "decision_blockers": blocked,
                "blockers": review["blockers"], "review_state": "BLOCKED" if review["blockers"] else "PENDING_APPROVAL",
            })
        entries.sort(key=lambda entry: (entry["submitted_at"], entry["id"]), reverse=True)
        return {"items": entries[offset:offset + limit], "total": len(entries), "limit": limit, "offset": offset}
