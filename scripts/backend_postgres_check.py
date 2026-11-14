"""Real Aiven TLS + atomic concurrency checks in a unique temporary table namespace.

Uses the free existing service, max two DB connections. Does not touch application
simulation receipts or spend. Temporary test tables are dropped in finally.
"""

import json, sys, uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.store import Store, StoreError
from backend import policy
from backend.config import BUYER, LOCAL

name = "aimocheck_" + uuid.uuid4().hex[:10]
db = Store(postgres=True, namespace=name)
if db.backend != "postgres":
    raise SystemExit("Aiven unavailable. Did not claim PostgreSQL coverage.")
report = {
    "storage": db.backend,
    "namespace": "isolated temporary tables",
    "concurrency_bound": 2,
}
try:
    with db.tx() as c:
        report["postgres_version"] = c.execute("SHOW server_version").fetchone()[0]
        row = c.execute(
            "SELECT ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid()"
        ).fetchone()
        report["tls_active"] = row[0]
        report["tls_version"] = row[1]
    offers = [
        {
            "id": "offer-" + str(i),
            "buyer_id": BUYER,
            "fingerprint": str(i) * 64,
            "total_cents": 115000,
            "total": "1150.00",
            "status": "within_mandate",
            "expires_at": (policy.now() + timedelta(minutes=5)).isoformat(),
        }
        for i in range(6)
    ]

    def place(i):
        try:
            return db.commit(
                offers[i],
                "check-key-" + str(i),
                {"id": "sim-check-" + str(i)},
                600000,
                offers[i]["expires_at"],
            )["id"]
        except StoreError as e:
            return e.code

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(place, range(6)))
    report["concurrent_distinct_successes"] = sum(s.startswith("sim-") for s in results)
    report["cap_rejections"] = results.count("cumulative_cap")
    report["spent_cents"] = db.spent()
    assert (
        report["concurrent_distinct_successes"] == 5
        and report["cap_rejections"] == 1
        and db.spent() == 575000
    )
    i = next(i for i, r in enumerate(results) if r.startswith("sim-"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        retries = list(pool.map(lambda _: place(i), range(4)))
    report["duplicate_retries_return_same"] = (
        len(set(retries)) == 1 and db.spent() == 575000
    )
    assert report["duplicate_retries_return_same"]
    report["status"] = "passed"
finally:
    with db.tx() as c:
        for table in ["aimo_orders", "aimo_audit", "aimo_documents", "aimo_accounts"]:
            c.execute("DROP TABLE IF EXISTS " + table)
report["temporary_tables_removed"] = True
(LOCAL / "postgres-check.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
