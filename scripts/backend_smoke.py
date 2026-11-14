"""Read-only sponsor connectivity / typed inference smoke; prints no credentials.
Run from repository root: .venv/bin/python scripts/backend_smoke.py
"""

import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import upstream, catalog
from backend.config import CUSTOMER, LOCAL
from backend.store import Store

report = {}
db = Store()
report["aiven"] = {
    "active": db.backend == "postgres",
    "storage": db.backend,
    "tls": "verify-full" if db.backend == "postgres" else "not applicable",
    "concurrency_bound": 2,
    "note": db.note,
}
try:
    e = upstream.sponsor_lookup(CUSTOMER, "2026-11-16", catalog.DEFAULT_IDS)
    report["valio"] = {
        "status": "live_success",
        "source": e["source"],
        "fetched_at": e["fetched_at"],
        "products": [
            {
                "id": x["productId"],
                "tax_inclusive_unit_price": x.get("catalogPrice", {}).get(
                    "valueWithTax"
                ),
            }
            for x in e["price"]["products"]
        ],
    }
except upstream.UpstreamError as e:
    report["valio"] = {"status": "failed", "reason": str(e)}
try:
    a = upstream.rank_with_nvidia(
        [catalog.product(i) for i in catalog.DEFAULT_IDS],
        {
            "quantity_liters": 1000,
            "date": "2026-11-16",
            "diet": "lactose_free",
            "brief": "Aurora Hotel breakfast milk",
        },
    )
    report["nvidia"] = a
except upstream.UpstreamError as e:
    report["nvidia"] = {"status": "failed", "reason": str(e)}
(LOCAL / "integration-report.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
