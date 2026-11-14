"""Small transactional store: PostgreSQL row lock or SQLite BEGIN IMMEDIATE.

All money is integer cents in persistence. Decimal is used at the boundary.
A unique offer and idempotency key prevent multiple simulated commitments.
"""

import json
import os
import sqlite3
import threading
import re
from contextlib import contextmanager
from pathlib import Path
from .config import LOCAL, BUYER


class Store:
    def __init__(self, path=None, postgres=None, namespace="aimo"):
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,40}", namespace):
            raise ValueError("Invalid store namespace")
        self.namespace = namespace
        self.gate = threading.BoundedSemaphore(2)
        self.backend = "sqlite"
        self.note = "Local SQLite fallback; transactions and constraints enabled."
        self.path = str(path or LOCAL / "aimo.sqlite3")
        self.dsn = None
        if postgres is None:
            postgres = (
                os.getenv(
                    "AIMO_STORAGE",
                    "postgres" if os.getenv("DATABASE_URL") else "sqlite",
                )
                == "postgres"
            )
        if postgres:
            try:
                import psycopg

                dsn = os.environ["DATABASE_URL"]
                # Do not weaken the required identity validation even if a DSN changes.
                c = psycopg.connect(
                    dsn,
                    sslmode="verify-full",
                    sslrootcert=os.environ.get(
                        "PGSSLROOTCERT", str(LOCAL / "aiven-ca.pem")
                    ),
                    connect_timeout=6,
                )
                with c.cursor() as cur:
                    cur.execute(
                        "SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()"
                    )
                    if cur.fetchone() != (True,):
                        raise RuntimeError("TLS not active")
                c.close()
                self.backend = "postgres"
                self.dsn = dsn
                self.note = (
                    "Aiven PostgreSQL · verified TLS · at most 2 concurrent connections"
                )
            except Exception:
                self.note = "Aiven connection unavailable; explicitly using local SQLite. No network allowlist was changed."
        self.initialize()

    @contextmanager
    def tx(self):
        with self.gate:
            c = None
            try:
                if self.backend == "postgres":
                    import psycopg

                    c = psycopg.connect(
                        self.dsn,
                        sslmode="verify-full",
                        sslrootcert=os.environ.get(
                            "PGSSLROOTCERT", str(LOCAL / "aiven-ca.pem")
                        ),
                        connect_timeout=6,
                    )
                    yield Connection(c, True, self.namespace)
                else:
                    c = sqlite3.connect(self.path, timeout=15, check_same_thread=False)
                    c.execute("PRAGMA foreign_keys=ON")
                    c.execute("BEGIN IMMEDIATE")
                    yield Connection(c, False, self.namespace)
                c.commit()
            except Exception:
                if c:
                    c.rollback()
                raise
            finally:
                if c:
                    c.close()

    def initialize(self):
        with self.tx() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS aimo_accounts (buyer_id TEXT PRIMARY KEY, spent_cents BIGINT NOT NULL CHECK(spent_cents >= 0))"
            )
            c.execute(
                "INSERT INTO aimo_accounts (buyer_id,spent_cents) VALUES (?,0) ON CONFLICT(buyer_id) DO NOTHING",
                (BUYER,),
            )
            c.execute(
                "CREATE TABLE IF NOT EXISTS aimo_documents (kind TEXT NOT NULL, id TEXT PRIMARY KEY, buyer_id TEXT NOT NULL, body TEXT NOT NULL)"
            )
            c.execute(
                "CREATE TABLE IF NOT EXISTS aimo_orders (id TEXT PRIMARY KEY, buyer_id TEXT NOT NULL, offer_id TEXT UNIQUE NOT NULL, idempotency_key TEXT NOT NULL, fingerprint TEXT NOT NULL, total_cents BIGINT NOT NULL, body TEXT NOT NULL, UNIQUE(buyer_id,idempotency_key))"
            )
            c.execute(
                "CREATE TABLE IF NOT EXISTS aimo_audit (id TEXT PRIMARY KEY, buyer_id TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL)"
            )

    def save(self, kind, id, buyer, body):
        with self.tx() as c:
            c.execute(
                "INSERT INTO aimo_documents(kind,id,buyer_id,body) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
                (kind, id, buyer, json.dumps(body)),
            )

    def get(self, kind, id, buyer):
        with self.tx() as c:
            r = c.execute(
                "SELECT body FROM aimo_documents WHERE kind=? AND id=? AND buyer_id=?",
                (kind, id, buyer),
            ).fetchone()
            return json.loads(r[0]) if r else None

    def spent(self, buyer=BUYER):
        with self.tx() as c:
            r = c.execute(
                "SELECT spent_cents FROM aimo_accounts WHERE buyer_id=?", (buyer,)
            ).fetchone()
            return r[0] if r else 0

    def audit(self, id, buyer, kind, body):
        with self.tx() as c:
            c.execute(
                "INSERT INTO aimo_audit(id,buyer_id,kind,body) VALUES(?,?,?,?)",
                (id, buyer, kind, json.dumps(body)),
            )

    def commit(self, offer, key, receipt, cap, commit_not_after):
        with self.tx() as c:
            # Lock shared buyer account before looking at orders or consuming budget.
            row = c.execute(
                "SELECT spent_cents FROM aimo_accounts WHERE buyer_id=?"
                + (" FOR UPDATE" if self.backend == "postgres" else ""),
                (offer["buyer_id"],),
            ).fetchone()
            existing = c.execute(
                "SELECT fingerprint,body FROM aimo_orders WHERE buyer_id=? AND idempotency_key=?",
                (offer["buyer_id"], key),
            ).fetchone()
            if existing:
                if existing[0] != offer["fingerprint"]:
                    raise StoreError(
                        "idempotency_conflict",
                        "Idempotency key already belongs to a different offer.",
                    )
                r = json.loads(existing[1])
                r["idempotent_replay"] = True
                return r
            existing = c.execute(
                "SELECT body FROM aimo_orders WHERE offer_id=?", (offer["id"],)
            ).fetchone()
            if existing:
                raise StoreError(
                    "idempotency_key_mismatch",
                    "This offer is already committed under a different key. Retry its original Idempotency-Key.",
                )
            from .policy import now, parse_time
            from .config import MANDATE

            if parse_time(offer["expires_at"]) <= now():
                raise StoreError(
                    "stale_offer",
                    "Offer expired while waiting to commit. Revalidate and obtain new approval.",
                )
            if parse_time(MANDATE["expires_at"]) <= now():
                raise StoreError(
                    "mandate_expired", "Delegated authority expired before commitment."
                )
            deadline = parse_time(commit_not_after)
            if not deadline or deadline <= now():
                raise StoreError(
                    "evidence_expired",
                    "Supplier cutoff, price validity or evidence freshness expired while waiting to commit. Revalidate before retrying.",
                )
            if offer["status"] == "approval_required":
                approval = offer.get("approval") or {}
                if (
                    not offer.get("approved")
                    or approval.get("fingerprint") != offer["fingerprint"]
                    or approval.get("approver_role") != "approver"
                    or not parse_time(approval.get("expires_at"))
                    or parse_time(approval["expires_at"]) <= now()
                ):
                    raise StoreError(
                        "approval_required",
                        "Current exact human approval is required at commitment.",
                    )
            cents = offer["total_cents"]
            if not row or row[0] + cents > cap:
                raise StoreError(
                    "cumulative_cap",
                    "Cumulative mandate cap would be exceeded. Splitting orders does not change this limit.",
                )
            receipt["created_at"] = now().isoformat()
            c.execute(
                "INSERT INTO aimo_orders(id,buyer_id,offer_id,idempotency_key,fingerprint,total_cents,body) VALUES(?,?,?,?,?,?,?)",
                (
                    receipt["id"],
                    offer["buyer_id"],
                    offer["id"],
                    key,
                    offer["fingerprint"],
                    cents,
                    json.dumps(receipt),
                ),
            )
            c.execute(
                "UPDATE aimo_accounts SET spent_cents=spent_cents+? WHERE buyer_id=?",
                (cents, offer["buyer_id"]),
            )
            c.execute(
                "INSERT INTO aimo_audit(id,buyer_id,kind,body) VALUES(?,?,?,?)",
                (
                    "audit-" + receipt["id"],
                    offer["buyer_id"],
                    "simulated_order_committed",
                    json.dumps(
                        {
                            "receipt_id": receipt["id"],
                            "offer_id": offer["id"],
                            "total": offer["total"],
                            "fingerprint": offer["fingerprint"],
                        }
                    ),
                ),
            )
            return receipt

    def order(self, id, buyer):
        with self.tx() as c:
            r = c.execute(
                "SELECT body FROM aimo_orders WHERE id=? AND buyer_id=?", (id, buyer)
            ).fetchone()
            return json.loads(r[0]) if r else None

    def existing(self, offer, key):
        with self.tx() as c:
            # A reused key is checked before an offer retry. An OR query could
            # choose the offer row and conceal a conflicting key on another order.
            r = c.execute(
                "SELECT fingerprint,body FROM aimo_orders WHERE buyer_id=? AND idempotency_key=?",
                (offer["buyer_id"], key),
            ).fetchone()
            if r and r[0] != offer["fingerprint"]:
                raise StoreError(
                    "idempotency_conflict",
                    "Idempotency key already belongs to a different offer.",
                )
            if not r:
                prior = c.execute(
                    "SELECT body FROM aimo_orders WHERE buyer_id=? AND offer_id=?",
                    (offer["buyer_id"], offer["id"]),
                ).fetchone()
                if prior:
                    raise StoreError(
                        "idempotency_key_mismatch",
                        "This offer is already committed under a different key. Retry its original Idempotency-Key.",
                    )
            if r:
                result = json.loads(r[1])
                result["idempotent_replay"] = True
                return result


class Connection:
    def __init__(self, c, pg, namespace):
        self.c = c
        self.pg = pg
        self.namespace = namespace

    def execute(self, q, args=()):
        q = q.replace("aimo_", self.namespace + "_")
        return self.c.execute(q.replace("?", "%s") if self.pg else q, args)


class StoreError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)
