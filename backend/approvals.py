"""Scoped pending basket decisions; approval never bypasses hard constraints."""

import json
from typing import Literal

from fastapi import Depends, Query
from pydantic import BaseModel, Field

from . import policy
from .procurement import authority, fingerprint
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
        for row in rows:
            session = json.loads(row[0])
            offer = session.get("offer") or {}
            if (
                session.get("customer_id") != scope["customer_id"]
                or session.get("receipt") or session.get("checkout_pending")
                or offer.get("status") != "approval_required" or offer.get("approved")
                or (session.get("rejection") or {}).get("fingerprint") == offer.get("fingerprint")
            ):
                continue
            # Queue entries refer to a current, verifiable basket. An expired
            # basket remains visible for review but cannot be approved.
            expiry = policy.parse_time(offer.get("expires_at"))
            if not expiry or fingerprint(offer) != offer.get("fingerprint") or offer.get("authority") != authority():
                continue
            expired = expiry <= now
            entries.append({
                "id": session["id"], "version": session["version"],
                "created_at": session["created_at"], "requested_date": offer["requested_date"],
                "subtotal": offer["total"], "currency": "EUR", "fingerprint": offer["fingerprint"],
                "expires_at": offer["expires_at"], "status": "expired" if expired else "pending",
                "can_approve": not expired, "can_reject": True, "line_count": len(session["lines"]),
            })
        entries.sort(key=lambda entry: (entry["created_at"], entry["id"]), reverse=True)
        return {"items": entries[offset:offset + limit], "total": len(entries), "limit": limit, "offset": offset}
