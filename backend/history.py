"""Personal request history. Hiding an entry never deletes purchasing evidence."""

import copy
import json
from datetime import date as Date
from decimal import Decimal
from typing import Literal

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from . import policy
from .procurement_contract import MoneyText, OrderStatus, ProcurementSessionResponse, TimestampText


PREFIX = "/api/v1/history"


class HistoryEntry(BaseModel):
    id: str
    title: str
    created_at: TimestampText
    updated_at: TimestampText
    archived: bool
    order_status: OrderStatus
    line_count: int = Field(ge=0)
    total: MoneyText | None = Field(description="Known tax-inclusive item subtotal; unknown delivery/service charges are excluded.")
    currency: Literal["EUR"] = "EUR"
    receipt_id: str | None


class HistoryList(BaseModel):
    items: list[HistoryEntry]
    total: int
    limit: int
    offset: int


class HistoryEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    archived: bool


class ReuseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: Date | None = None
    budget: Decimal | None = Field(default=None, ge=0, le=1000000, decimal_places=2)
    mode: Literal["fixture", "live"] | None = None


class RemovalResponse(BaseModel):
    id: str
    removed: Literal[True] = True


def _not_found():
    raise HTTPException(404, {"code": "history_not_found", "message": "Request not found in your personal history."})


def _summary(session, state):
    title = next((entry.get("text", "") for entry in session.get("messages", []) if entry.get("role") == "user"), "Purchasing request")
    receipt = session.get("receipt") or {}
    cart = session.get("cart") or {}
    total = receipt.get("total")
    if total is None and cart.get("items"):
        total = cart.get("subtotal")
    return {
        "id": session["id"], "title": title[:180] or "Purchasing request",
        "created_at": session.get("created_at", ""),
        "updated_at": session.get("updated_at", session.get("created_at", "")),
        "archived": bool(state.get("archived")),
        "order_status": session.get("order_status", "NEEDS_CLARIFICATION"),
        "line_count": len(session.get("lines", [])),
        "total": total,
        "currency": "EUR", "receipt_id": receipt.get("id"),
    }


def register_routes(app, db, buyer, limit):
    def load(id, scope, *, include_removed=False):
        session = db.get("procurement", id, scope["buyer_id"])
        if not session or session.get("customer_id") != scope["customer_id"]:
            _not_found()
        state = db.get("history_state", "history-state-" + id, scope["buyer_id"]) or {}
        if state.get("removed") and not include_removed:
            _not_found()
        return session, state

    @app.get(PREFIX, response_model=HistoryList)
    def list_history(archived: bool = False, limit: int = Query(default=30, ge=1, le=100), offset: int = Query(default=0, ge=0), scope=Depends(buyer)):
        with db.tx() as c:
            rows = c.execute("SELECT body FROM aimo_documents WHERE kind=? AND buyer_id=?", ("procurement", scope["buyer_id"])).fetchall()
            states = c.execute("SELECT body FROM aimo_documents WHERE kind=? AND buyer_id=?", ("history_state", scope["buyer_id"])).fetchall()
        state_by_id = {body["session_id"]: body for row in states if (body := json.loads(row[0])).get("session_id")}
        items = []
        for row in rows:
            session = json.loads(row[0])
            state = state_by_id.get(session["id"], {})
            if session.get("customer_id") != scope["customer_id"] or state.get("removed") or bool(state.get("archived")) != archived:
                continue
            items.append(_summary(session, state))
        items.sort(key=lambda entry: (entry["created_at"], entry["id"]), reverse=True)
        return {"items": items[offset:offset + limit], "total": len(items), "offset": offset, "limit": limit}

    @app.get(PREFIX + "/{id}", response_model=ProcurementSessionResponse, response_model_exclude_unset=True)
    def get_history(id: str, scope=Depends(buyer)):
        session, _ = load(id, scope)
        return app.state.public_procurement_session(session)

    def change(id, scope, *, archived=None, remove=False):
        session, _ = load(id, scope, include_removed=remove)
        state_id = "history-state-" + id
        # Archive/remove share one locked metadata update. A concurrent archive
        # cannot resurrect an entry that the customer has already removed.
        with db.tx() as c:
            row = c.execute("SELECT body FROM aimo_documents WHERE kind=? AND id=? AND buyer_id=?" + (" FOR UPDATE" if db.backend == "postgres" else ""), ("history_state", state_id, scope["buyer_id"])).fetchone()
            state = json.loads(row[0]) if row else {"session_id": id, "archived": False, "removed": False}
            if state.get("removed") and not remove:
                _not_found()
            state.update(updated_at=policy.now().isoformat())
            if remove:
                state["removed"] = True
            if archived is not None:
                state["archived"] = archived
            c.execute("INSERT INTO aimo_documents(kind,id,buyer_id,body) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body", ("history_state", state_id, scope["buyer_id"], json.dumps(state)))
        return session, state

    @app.patch(PREFIX + "/{id}", response_model=HistoryEntry)
    def archive_history(id: str, data: HistoryEdit, scope=Depends(buyer)):
        limit("history-" + scope["buyer_id"], 60)
        session, state = change(id, scope, archived=data.archived)
        return _summary(session, state)

    @app.delete(PREFIX + "/{id}", response_model=RemovalResponse)
    def remove_history(id: str, scope=Depends(buyer)):
        limit("history-" + scope["buyer_id"], 60)
        change(id, scope, remove=True)
        return {"id": id, "removed": True}

    @app.post(PREFIX + "/{id}/reuse", response_model=ProcurementSessionResponse, response_model_exclude_unset=True)
    def reuse_history(id: str, data: ReuseRequest, scope=Depends(buyer)):
        limit("history-reuse-" + scope["buyer_id"], 30)
        session, _ = load(id, scope)
        # The existing purchasing gateway copies requirements and performs a
        # new quotation. It never transfers an old approval or receipt.
        return app.state.reuse_procurement_session(copy.deepcopy(session), scope, data.model_dump(mode="json"))
