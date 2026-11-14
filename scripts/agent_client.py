#!/usr/bin/env python3
"""Independent buyer agent: HTTP tool interface, no UI or privileged role switch.

Buyer credentials are loaded locally or from AIMO_BUYER_CODE; never printed.
With --model a real NVIDIA typed shortlist tool drives candidate IDs sent to the
receiving gateway. This process can never approve an exception.
"""

import argparse, json, os, sys, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import httpx
from backend import upstream
from backend.config import ROOT, access_codes

p = argparse.ArgumentParser()
p.add_argument("--base-url", default="http://127.0.0.1:8000")
p.add_argument("--mode", choices=["live", "fixture"], default="fixture")
p.add_argument("--model", action="store_true")
p.add_argument("--scenario", default="baseline")
p.add_argument("--date", default="2026-11-16")
p.add_argument("--quantity", type=float, default=1000)
p.add_argument("--commit", action="store_true")
p.add_argument("--output", default=".local/agent-last-run.json")
args = p.parse_args()
with httpx.Client(base_url=args.base_url, timeout=90) as c:
    r = c.post("/api/v1/session", json={"access_code": access_codes()["buyer"]})
    r.raise_for_status()
    candidates = []
    for pid in ["464306", "464398", "465039"]:
        r = c.get("/api/v1/products", params={"q": pid})
        r.raise_for_status()
        candidates.extend(r.json()["products"])
    model = None
    ids = None
    if args.model:
        model = upstream.rank_with_nvidia(
            candidates,
            {
                "quantity_liters": args.quantity,
                "date": args.date,
                "diet": "lactose_free",
            },
        )
        ids = model["tool_calls"][0]["arguments"]["product_ids"]
    request = {
        "quantity_liters": args.quantity,
        "date": args.date,
        "mode": args.mode,
        "scenario": args.scenario,
        "use_model": False,
        "brief": "Independent external HTTP buyer agent; lactose-free breakfast milk.",
    }
    if ids:
        request["candidate_ids"] = ids
    r = c.post("/api/v1/runs", json=request)
    r.raise_for_status()
    run = r.json()
    report = {
        "external_client": "scripts/agent_client.py",
        "gateway": args.base_url,
        "model": model,
        "run": run,
        "receipt": None,
    }
    if args.commit and run["recommended_offer_id"]:
        o = next(o for o in run["offers"] if o["id"] == run["recommended_offer_id"])
        if o["status"] == "within_mandate":
            key = "external-" + uuid.uuid4().hex
            r = c.post(
                "/api/v1/offers/" + o["id"] + "/commit",
                headers={"Idempotency-Key": key},
            )
            r.raise_for_status()
            report["receipt"] = r.json()
            retry = c.post(
                "/api/v1/offers/" + o["id"] + "/commit",
                headers={"Idempotency-Key": key},
            )
            retry.raise_for_status()
            report["duplicate_returned_same_receipt"] = (
                retry.json()["id"] == r.json()["id"]
            )
            verification = c.get("/api/v1/receipts/" + r.json()["id"] + "/verify")
            verification.raise_for_status()
            report["verification"] = verification.json()
        else:
            report["pause"] = (
                "Human approval required; buyer agent cannot approve itself."
            )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                "run_id": run["id"],
                "evidence_mode": run["mode"],
                "model_status": model["status"] if model else "not_requested",
                "outcomes": [
                    {
                        "sku": o["product"]["id"],
                        "decision": o["status"],
                        "total": o["total"],
                    }
                    for o in run["offers"]
                ],
                "receipt_id": report["receipt"]["id"] if report["receipt"] else None,
                "duplicate_same": report.get("duplicate_returned_same_receipt"),
                "output": str(output),
            },
            indent=2,
        )
    )
