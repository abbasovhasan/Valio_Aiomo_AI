# A4TB · Valio Aimo

**Good judgment. On the record.** Describe a kitchen's purchasing needs, compare catalog products and review a complete simulated basket. Deterministic checks enforce quantities, dietary evidence, budget and delivery; permitted spend exceptions require exact separate approval.

Built for Junction 2026's Valio Aimo Trusted Trade Agents challenge. **All orders are simulated. No final Junction submission was performed; the last observed entry was Draft. Source remains private.**

## Hosted application

Open **[A4TB · Valio Aimo](https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site)** and use the private buyer/approver codes from this installation's ignored `.local/access.json`. This public Sites frontdoor proxies the application on Modal; the source repository, runtime secrets and restricted catalog remain private. Never put codes in URLs or public messages. All orders remain simulated.

**Smart order** is the primary workflow: describe multiple products, review catalog candidates and package surplus, change quantities/budget/date, resolve choices, and confirm a complete priced basket. Unresolved constraints block checkout. **Meal planner** supports editable recipes and transfers a saved plan with its selections into the same quotation/cart workflow. **Trust scenarios** retains the original milk approval/repair demo.

See [implementation and acceptance plan](docs/IMPLEMENTATION_PLAN.md) and [hosting details](docs/DEPLOYMENT.md).

## Run

Prerequisites: Node.js 20.19+ or 22.12+, npm, Python 3.12+, and [uv](https://docs.astral.sh/uv/). The prepared machine already has these. From this project:

```bash
./start.sh
```

Open **http://127.0.0.1:8000**. Open your desk and use a generated **buyer** access code from the ignored `.local/access.json`. To approve an exception, sign in separately using the **approver** code from that file. Codes are never bundled into frontend assets. Do not publish them. Sessions last eight hours. Their hashes and revocations are stored in the database so valid sessions survive server restarts.

`start.sh` builds the React frontend and serves it from FastAPI. Dependencies install only when absent. For an offline fallback, use `AIMO_STORAGE=sqlite ./start.sh`, select **Rehearsal fixture** prices/stock and turn off NVIDIA interpretation to use the local parser. This combination still needs the supplied static catalog and makes no NVIDIA or Valio API requests. NVIDIA interpretation is an independent option; fixture prices alone do not disable that model request.

The prepared `.env`, `.local/aiven-ca.pem` and `data/raw/` are preserved and ignored. A fresh clone requires the challenge-restricted catalog obtained legitimately through the resource portal. Do not commit or redistribute it. `.env.example` documents optional integration names; never paste credentials into browser URLs or frontend code.

## Try it

1. Sign in as buyer. Leave at least 1,000 L, Monday 16 November 2026, and lactose-free milk. Run **Clear runway** in labelled fixture mode. Inspect every check and commit a simulated order. Retry: the same receipt returns, without spending again.
2. Select **The milk runs out**. The controlled shortage blocks the preferred €1,150 offer. The €1,870 UHT alternative preserves diet/date/quantity, but exceeds the authored €1,400 autonomous limit. Sign in as the separate approver, approve that exact fingerprint, sign back in as buyer and commit.
3. Select **The offer changes**. Inspect the expired offer, then **Refresh this exact offer**. Revalidation produces a new fingerprint and clears any inherited approval. The comparison shows what changed.
4. Try **A tempting shortcut**, **An untrusted instruction**, or **Quantity unknown**. Hard dietary evidence and unknown stock cannot be overridden by a human budget approval.
5. Switch to **Live sponsor sandbox**. Enable NVIDIA Nemotron for an actual typed shortlist; deterministic gateway code independently validates the result. A non-baseline scenario explicitly overlays a controlled failure on live evidence. Run it only when network access is available.

The brief's typed quantity and date are authoritative; free text provides context, not a way to change the hard mandate. These typed controls apply to the original milk Trust scenarios. Smart order extracts multi-product requirements from free text and uses a separate customer-confirmed basket policy; it does not widen the milk agent's authority.

## Outside agent and open API

Interactive OpenAPI: **http://127.0.0.1:8000/docs**. Contract: `/openapi.json`; health: `/health`.

```bash
.venv/bin/python scripts/agent_client.py --mode fixture --commit
.venv/bin/python scripts/agent_client.py --mode live --model --commit
```

The independent Python client signs in as the buyer, searches real IDs over HTTP, uses NVIDIA's `propose_candidates` typed tool, sends those candidate IDs to the gateway, commits only a permitted offer, retries and verifies the same receipt. It cannot approve itself. Detailed reports remain ignored in `.local/`.

## Architecture

```mermaid
flowchart LR
  Chef[Human brief / reviewer] --> Site[Sites public HTTPS frontdoor]
  Site --> UI[React order desk on Modal]
  Agent[Outside buyer client / NVIDIA Nemotron] -->|versioned typed HTTP| API[FastAPI trust gateway]
  UI -->|same-origin Sites proxy| API
  API --> Catalog[Local restricted catalog]
  API -->|small price + availability shortlist| Valio[Valio sandbox]
  Approver[Separate approver identity] -->|exact fingerprint| API
  API -->|atomic shared spending + uniqueness| DB[(Hosted SQLite volume / local PostgreSQL option)]
  DB --> Receipt[Simulated receipt + factual audit]
```

Authority belongs to the server. The original milk scenario has a chef-approved assortment and mandatory lactose-free evidence. Smart order uses a separate customer-confirmed basket policy with item-level dietary/origin constraints. Both enforce buyer/customer/approver scope, dimensional pack conversion, whole-pack lot steps, EUR tax-inclusive Decimal amounts, date/cutoff/sales-block/quantity/freshness checks, five-minute quote expiry and a shared €6,000 synthetic cumulative cap. Atomic transactions and uniqueness constraints enforce spending and idempotency. Approvals bind the exact buyer, products, quantities, date, subtotal, evidence and expiry. Changed facts require a new quote and approval.

The hosted Modal application deliberately uses persistent SQLite in a private volume and one writer. Sessions, carts, approvals, receipts and synthetic spend survive restarts. The local Aiven PostgreSQL option uses full hostname/CA verification and at most two concurrent connections; an unavailable local connection is explicitly reported as SQLite fallback. The Aiven allowlist was not widened for hosting. Catalog search runs in the backend. NVIDIA receives the request and necessary prior structured intent for interpretation, or a short normalized candidate list for the original external-agent shortlist; never the full catalog or credentials. Actual deployed NVIDIA interpretation and Valio sandbox price/availability reads were tested successfully; failures remain visible.

## Verify

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/backend_smoke.py
.venv/bin/python scripts/backend_postgres_check.py
npm run build --prefix frontend
# Optional local browser checks (browser download required once):
uv pip install --python .venv/bin/python -r requirements-browser.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/browser_verify.py
```

The Postgres check uses an isolated temporary schema and concurrency; it never resets the shared demonstration ledger. See [delivery](docs/DELIVERY.md) for exactly executed checks and current limitations. Browser checks must use the synthetic simulator; repeated local QA should use an isolated temporary ledger.

Demo commitments consume the shared synthetic cap. For a clean rehearsal, first save any ignored evidence reports you need, then deliberately reset **only** prototype simulator records:

```bash
.venv/bin/python scripts/backend_reset.py --confirm-example-data
```

This operator command is never exposed over HTTP and never runs automatically during retries. It removes Aimo offers, approvals, orders/audit and resets the synthetic buyer spend; original files and unrelated database schemas stay untouched.

## Live, controlled and simulated

- **Live sponsor sandbox:** actual authenticated Valio price/availability reads. These are synthetic challenge commercial facts, not production offers or reservations.
- **NVIDIA agent:** actual hosted Nemotron 3.5 Super VL typed interpretation in Smart order, or a function-call shortlist in Trust scenarios, when selected. Invalid output/provider failures remain visible; deterministic policy still applies.
- **Rehearsal fixture:** authored dynamic prices/availability, visibly labelled; real supplied catalog metadata is still used. No silent network fallback.
- **Controlled failures:** named overlays on fixture or live evidence. Their injected fields are recorded explicitly.
- **Order/approval gateway:** our implementation. No published sponsor order endpoint is used. No payments, real purchases or supplier orders occur.
- **Receipt verification:** gateway-held record consistency and offer hash, not a digital signature, product safety certification, future stock guarantee or proof of delivery.

Delivery reliability means historical delivered quantity ratio, not on-time probability. Carbon is a group-average estimate per kilogram; the app makes no litre-to-kilogram assumption or invented carbon savings. Lactose-free milk is not milk-allergy safe.

## Review assets

- [Product and concept choice](docs/PRODUCT.md)
- [Two-minute demo and pitch scripts](docs/DEMO.md)
- [87-second local fixture demo](.local/demo/aimo-order-desk-draft.mp4) (local artifact; not uploaded)
- [Local draft pitch PDF](docs/pitch/aimo-order-desk-draft.pdf) and [editable deck](docs/pitch/aimo-order-desk-draft.pptx)
- [Submission copy — DRAFT](docs/SUBMISSION_DRAFT.md)
- [Sponsor evidence and credit ledger](docs/SPONSORS.md)
- [Hosted architecture and operating limits](docs/DEPLOYMENT.md)
- [Current status](PROJECT_STATUS.md) and [delivery / wake-up review](docs/DELIVERY.md)

A production path needs real customer mandates, identity federation, distributed rate limits, stronger upstream schema validation, transaction contention/load checks, supported deposits/variable-weight charges, and an actual wholesaler order contract. This prototype does not claim production certification or measured customer savings. Event source-access/MIT requirements and challenge-data restrictions need owner review; the repository remains private.

## Worker-interview update

Open **Meal planner** for the new bolognese/lentil planning workflow: editable recipe quantities, overlapping dietary cohorts, sourcing preferences, local catalog candidates, evidence gaps and a draft JSON shopping plan. The detailed planner keeps its draft export and can now quote a saved plan into Smart order, carrying ingredient quantities, dietary cohorts, source and selected products. The complete basket requires fresh validation and explicit recipe review before simulated confirmation.

Customer spend thresholds can be set by the operator using `AIMO_AUTONOMOUS_LIMIT`, `AIMO_EXCEPTION_LIMIT`, and `AIMO_CUMULATIVE_LIMIT` in the ignored environment (EUR, restart required). Policy changes invalidate uncommitted offers/approvals. See [interview requirements, delivered changes and remaining gaps](docs/INTERVIEW_GAPS.md).
