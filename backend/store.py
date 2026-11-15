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
            c.execute(
                "CREATE TABLE IF NOT EXISTS aimo_users (username TEXT PRIMARY KEY, user_id TEXT UNIQUE NOT NULL, buyer_id TEXT UNIQUE NOT NULL, customer_id TEXT UNIQUE NOT NULL, name TEXT NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)"
            )

    def create_user(self, user):
        with self.tx() as c:
            created = c.execute("INSERT INTO aimo_users(username,user_id,buyer_id,customer_id,name,password_hash,created_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(username) DO NOTHING RETURNING username", tuple(user[key] for key in ["username", "user_id", "buyer_id", "customer_id", "name", "password_hash", "created_at"])).fetchone()
            if not created:
                raise StoreError("username_unavailable", "This username is unavailable. Choose another username.")
            c.execute("INSERT INTO aimo_accounts(buyer_id,spent_cents) VALUES(?,0)", (user["buyer_id"],))
            self._insert_workspace_authority(c, user["buyer_id"], user["customer_id"])

    @staticmethod
    def _insert_workspace_authority(c, buyer, customer, principals=None):
        from .config import MANAGER_PRINCIPAL, MANDATE
        assignment = {"buyer_id": buyer, "customer_id": customer, "active": True,
            "approver_principals": principals or [MANAGER_PRINCIPAL],
            "permissions": ["requested_budget", "spending_authority"], "max_total": MANDATE["exception_limit"],
            "assignment_source": "Operator policy assigns the configured demonstration manager to invitation-created workspaces; tokens remain bound to one workspace."}
        for kind, identifier, body in [("workspace_authority", "workspace-authority-" + buyer, assignment), ("workspace_registration", "workspace-registration-" + buyer, {"buyer_id": buyer, "authority_schema": 1})]:
            c.execute("INSERT INTO aimo_documents(kind,id,buyer_id,body) VALUES(?,?,?,?) ON CONFLICT(id) DO NOTHING", (kind, identifier, buyer, json.dumps(body)))

    def migrate_workspace_authority(self):
        """One compatibility migration, never regrant a marked/revoked scope."""
        from .config import CUSTOMER, QUICK_DEMO_BUYER, QUICK_DEMO_CUSTOMER
        marker = "workspace-authority-migration-v1"
        with self.tx() as c:
            c.execute("SELECT spent_cents FROM aimo_accounts WHERE buyer_id=?" + (" FOR UPDATE" if self.backend == "postgres" else ""), (BUYER,)).fetchone()
            if c.execute("SELECT id FROM aimo_documents WHERE kind=? AND id=? AND buyer_id=?", ("auth_migration", marker, BUYER)).fetchone():
                return False
            users = c.execute("SELECT buyer_id,customer_id FROM aimo_users").fetchall()
            scopes = [(BUYER, CUSTOMER, None), (QUICK_DEMO_BUYER, QUICK_DEMO_CUSTOMER, ["demo:approver"])] + [(row[0], row[1], None) for row in users]
            for buyer, customer, principals in scopes:
                registered = c.execute("SELECT id FROM aimo_documents WHERE kind=? AND id=? AND buyer_id=?", ("workspace_registration", "workspace-registration-" + buyer, buyer)).fetchone()
                if not registered:
                    self._insert_workspace_authority(c, buyer, customer, principals)
            c.execute("INSERT INTO aimo_documents(kind,id,buyer_id,body) VALUES(?,?,?,?)", ("auth_migration", marker, BUYER, json.dumps({"version": 1, "policy": "Explicit operator-wide demo manager assignment; no person-level or enterprise IAM claim."})))
        return True

    def workspace_authority(self, buyer, customer):
        record = self.get("workspace_authority", "workspace-authority-" + buyer, buyer)
        return record if self.valid_workspace_authority(record, buyer, customer) else None

    @staticmethod
    def valid_workspace_authority(record, buyer, customer):
        from decimal import Decimal, InvalidOperation
        if not isinstance(record, dict) or record.get("customer_id") != customer or record.get("buyer_id") != buyer or not isinstance(record.get("active"), bool):
            return False
        if not isinstance(record.get("approver_principals"), list) or not all(isinstance(value, str) and value for value in record["approver_principals"]):
            return False
        if not isinstance(record.get("permissions"), list) or not all(isinstance(value, str) and value in {"requested_budget", "spending_authority"} for value in record["permissions"]):
            return False
        if not isinstance(record.get("max_total"), str):
            return False
        try:
            maximum = Decimal(str(record.get("max_total")))
            return maximum.is_finite() and 0 <= maximum <= 1000000 and maximum == maximum.quantize(Decimal(".01"))
        except (InvalidOperation, TypeError, ValueError):
            return False

    def user(self, username):
        with self.tx() as c:
            row = c.execute("SELECT username,user_id,buyer_id,customer_id,name,password_hash,created_at FROM aimo_users WHERE username=?", (username,)).fetchone()
            return dict(zip(["username", "user_id", "buyer_id", "customer_id", "name", "password_hash", "created_at"], row)) if row else None

    def user_workspace(self, workspace_id):
        with self.tx() as c:
            row = c.execute("SELECT username,buyer_id,customer_id,name FROM aimo_users WHERE buyer_id=?", (workspace_id,)).fetchone()
            return dict(zip(["username", "buyer_id", "customer_id", "name"], row)) if row else None

    def save(self, kind, id, buyer, body):
        with self.tx() as c:
            if kind in {"preferences", "workspace_authority"}:
                c.execute("SELECT spent_cents FROM aimo_accounts WHERE buyer_id=?" + (" FOR UPDATE" if self.backend == "postgres" else ""), (buyer,)).fetchone()
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

            if not offer.get("session_id"):
                from .policy import mandate_snapshot
                try:
                    current_policy = mandate_snapshot()
                except Exception:
                    raise StoreError("policy_unavailable", "Trusted policy is incomplete at commitment.") from None
                if offer.get("mandate_snapshot") != current_policy:
                    raise StoreError("policy_changed", "Trusted policy changed before commitment. Refresh the offer.")
                if not offer.get("requester_actor") or not offer.get("requester_principal"):
                    raise StoreError("buyer_review_required", "Refresh this older unconfirmed offer as buyer before continuing.")

            if offer.get("session_id"):
                # The same transaction sees the checkout lock, latest policy,
                # saved hard restrictions and committed workspace spending.
                current_row = c.execute("SELECT body FROM aimo_documents WHERE kind=? AND id=? AND buyer_id=?" + (" FOR UPDATE" if self.backend == "postgres" else ""), ("procurement", offer["session_id"], offer["buyer_id"])).fetchone()
                current = json.loads(current_row[0]) if current_row else {}
                if not current.get("checkout_pending") or current.get("pending_key") != key or current.get("customer_id") != offer["customer_id"] or (current.get("offer") or {}).get("fingerprint") != offer["fingerprint"] or current.get("cancelled") or current.get("rejection") or current.get("changes_requested"):
                    raise StoreError("checkout_changed", "The exact current checkout state is no longer valid. Reload the basket.")
                from .procurement import authority, fingerprint
                try:
                    trusted = authority()
                except Exception:
                    raise StoreError("policy_unavailable", "Trusted purchasing policy is unavailable at commitment.") from None
                if offer.get("authority") != trusted or fingerprint(offer) != offer["fingerprint"]:
                    raise StoreError("policy_changed", "The policy or exact basket changed before commitment. Refresh and review again.")
                from decimal import Decimal
                if cap != int(Decimal(trusted["cumulative_limit"]) * 100) or Decimal(offer["total"]) > Decimal(trusted["exception_limit"]):
                    raise StoreError("authority_limit", "Current trusted purchasing limits do not authorize this basket.")
                if Decimal(offer["total"]) > Decimal(trusted["autonomous_limit"]) and offer.get("status") != "approval_required":
                    raise StoreError("approval_required", "The current buyer authority requires exact independent approval.")
                from .preferences import PreferenceResponse
                preference_row = c.execute("SELECT body FROM aimo_documents WHERE kind=? AND id=? AND buyer_id=?" + (" FOR UPDATE" if self.backend == "postgres" else ""), ("preferences", offer["buyer_id"], offer["buyer_id"])).fetchone()
                try:
                    saved = PreferenceResponse.model_validate(json.loads(preference_row[0]) if preference_row else {}).model_dump()
                except Exception:
                    raise StoreError("preferences_changed", "Current dietary restrictions cannot be validated. Refresh the basket.") from None
                for line in current.get("lines", []):
                    for requested, effective, defaults in [("requested_dietary", "dietary", "dietary_restrictions"), ("requested_excluded_ingredients", "excluded_ingredients", "excluded_ingredients")]:
                        expected = set(line.get(requested, line.get(effective, []))) | set(saved[defaults])
                        if expected != set(line.get(effective, [])):
                            raise StoreError("preferences_changed", "Dietary restrictions changed before commitment. Refresh the basket.")

            if not parse_time(offer.get("expires_at")) or parse_time(offer["expires_at"]) <= now():
                raise StoreError(
                    "stale_offer",
                    "Offer expired while waiting to commit. Revalidate and obtain new approval.",
                )
            if not parse_time(MANDATE.get("expires_at")) or parse_time(MANDATE["expires_at"]) <= now():
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
                assignment_row = c.execute("SELECT body FROM aimo_documents WHERE kind=? AND id=? AND buyer_id=?" + (" FOR UPDATE" if self.backend == "postgres" else ""), ("workspace_authority", "workspace-authority-" + offer["buyer_id"], offer["buyer_id"])).fetchone()
                assignment = json.loads(assignment_row[0]) if assignment_row else {}
                if not self.valid_workspace_authority(assignment, offer["buyer_id"], offer["customer_id"]):
                    raise StoreError("manager_authority_changed", "Trusted manager assignment is missing or invalid at commitment.")
                from decimal import Decimal, InvalidOperation
                try:
                    maximum = Decimal(str(assignment.get("max_total")))
                    authority_ok = maximum.is_finite() and maximum >= 0 and Decimal(offer["total"]) <= maximum
                except (InvalidOperation, TypeError, ValueError):
                    authority_ok = False
                required_permissions = set(offer.get("approval_reasons") or ["spending_authority"])
                if not assignment.get("active") or assignment.get("customer_id") != offer["customer_id"] or approval.get("principal_id") not in assignment.get("approver_principals", []) or not required_permissions.issubset(set(assignment.get("permissions", []))) or not authority_ok:
                    raise StoreError("manager_authority_changed", "Current manager assignment or authority does not cover this basket. Request a new eligible decision.")
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
                if offer.get("session_id") and (
                    not offer.get("approval_request")
                    or not approval.get("actor_id") or approval["actor_id"] == offer.get("requester_actor")
                    or not approval.get("principal_id") or approval["principal_id"] == offer.get("requester_principal")
                    or approval.get("session_version") != offer.get("session_version")
                    or set(approval.get("covered_reasons", [])) != set(offer.get("approval_reasons", []))
                    or current.get("approval", {}).get("status") != "approved"
                ):
                    raise StoreError("approval_required", "Independent approval must cover this exact version and every financial exception.")
                if not offer.get("session_id") and (not offer.get("requester_actor") or not offer.get("requester_principal") or not approval.get("actor_id") or not approval.get("principal_id") or approval["actor_id"] == offer["requester_actor"] or approval["principal_id"] == offer["requester_principal"]):
                    raise StoreError("approval_required", "A fresh offer and independent manager approval are required.")
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
