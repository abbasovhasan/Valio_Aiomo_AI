# A4TB · Valio Aimo

Describe a kitchen's purchasing needs, compare catalog products and review a complete simulated basket. Deterministic checks enforce quantities, dietary evidence, budget and delivery; permitted spend exceptions require exact separate approval.

Built for Junction 2026's Valio Aimo Trusted Trade Agents challenge. **All orders are simulated. No final Junction submission was performed; the last observed entry was Draft. Source remains private.**

## Hosted application

Open **[A4TB · Valio Aimo](https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site)** and use the private buyer/approver codes from this installation's ignored `.local/access.json`. This public Sites frontdoor proxies the application on Modal; the source repository, runtime secrets and restricted catalog remain private. Never put codes in URLs or public messages. All orders remain simulated.

**Smart order** is the primary workflow: type, speak, upload an image or take a photo, edit the extracted text, compare products and package surplus, and review a priced basket. Set delivery and budget before ordering. **Products** searches the complete catalog with pagination, filters and direct cart selection. **History** opens, reuses, archives or removes personal entries while preserving receipts and audit records. Saved hard restrictions affect search, alternatives, meal planning and cart validation. **Meal planner** transfers a reviewed plan into the same cart; **Demo tools** retains the shared milk trust scenarios and technical controls.

Final `index-B4p90PsT.js` is deployed with **285 passing backend tests**, **12 fresh continuity checks** and a passing hosted long-name regression. Repeated product choices/reload preserve one search form per line; all saved identities, preferences, spending and receipts survived. Bk layout and CFF media/owner evidence remain valid for unchanged controls. Implementation `829207f` was reviewed, scanned and pushed to private `codex/aimo-order-desk`. See [current status](PROJECT_STATUS.md) and the [final QA report](docs/FINAL_QA_REPORT.md).

See [implementation and acceptance plan](docs/IMPLEMENTATION_PLAN.md) and [hosting details](docs/DEPLOYMENT.md).

## Run

Prerequisites: Node.js 20.19+ or 22.12+, npm, Python 3.12+, and [uv](https://docs.astral.sh/uv/). The prepared machine already has these. From this project:

```bash
./start.sh
```

Open **http://127.0.0.1:8000**. Open your desk with the **buyer** code from ignored `.local/access.json`, or use that invitation under **Create workspace** for a separate username/password account. To approve an exception, sign in separately using the **approver** code; a private workspace's approval shortcut fills its scope. Codes are never bundled into frontend assets. Sessions last eight hours, or 30 days with **Remember me**; hashed tokens, expiry and revocation persist across server restarts. Registration creates an isolated simulator workspace, not a supplier customer contract.

`start.sh` installs pinned dependencies, prepares public OCR/speech assets when absent, builds React and serves FastAPI. First setup requires network access. For prepared offline ordering, use `AIMO_STORAGE=sqlite ./start.sh`, open **Demo tools → Data & model settings**, choose fixture quotations, leave NVIDIA text interpretation unchecked and use text or local voice. Ordinary image input automatically attempts NVIDIA before local fallback; explicit `provider=local` remains available to API/rehearsal callers. Fixture prices alone do not disable image processing or an independently selected text model. NVIDIA trial inputs must be nonconfidential demonstration content.

The prepared `.env`, `.local/aiven-ca.pem` and `data/raw/` are preserved and ignored. A fresh clone requires the challenge-restricted catalog obtained legitimately through the resource portal. Do not commit or redistribute it. `.env.example` documents optional integration names; never paste credentials into browser URLs or frontend code.

## Try the customer workflow

1. Set an optional maximum budget and a delivery date, then request “20 litres of lactose-free milk and 5 kilograms of butter.” Ordinary ordering uses live sandbox quotations; fixture/model controls are under **Demo tools**.
2. Inspect package surplus, alternatives and **Product evidence**. Search **Products** for cheese, browse further results, select an ordering unit/quantity and add a product to the cart.
3. Try **Type a message**, **Voice input**, **Upload image** or **Take a photo**. Normal JPEG/PNG photos up to 5 MiB are resized to at most 1,600 pixels before reading. Images automatically try NVIDIA, with local OCR fallback on provider failure; voice stays local Whisper. Correct text before adding it. No provider selector/checkbox or audio-file upload remains in the customer flow; media never directly changes a cart.
4. Save a mandatory dietary restriction or ingredient exclusion in **Buying preferences**. Current drafts are revalidated. Removing a saved-only restriction requires a fresh quote; an explicit request restriction remains in force. Missing evidence does not establish compliance.
5. Lower the budget to €1 and observe the block, then correct it. Review and confirm a **simulated** order; verify and reload its receipt. Use **History** to open/reuse/archive/remove requests. Reuse requires a fresh quote and any recipe review/approval.
6. Use **Meal planner** for the 500-diner bolognese example. Dietary overlap must be explicit, the recipe needs chef review, and missing catalog claims remain blockers.

The step-by-step [plain-text checking guide](docs/WEBSITE_CHECK_GUIDE.txt) includes accounts, Remember Me, media, manager approval and expected failures.

## Retained trust rehearsals

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

The hosted Modal application uses persistent SQLite in a private volume and one writer. Accounts, preferences, sessions, history, carts, approvals, receipts and spend survive restarts. Local Aiven uses full CA/hostname verification and at most two connections; its allowlist was not widened. Catalog search stays on the server. Optional NVIDIA text receives necessary intent/a shortlist, never the full catalog or credentials. Automatic image reading sends sanitized images under a nonconfidential-demo notice and respects explicit API denial. Actual deployed text interpretation, Valio reads and default NVIDIA vision passed; extraction leaves purchasing state unchanged.

## Verify

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/backend_smoke.py
.venv/bin/python scripts/backend_postgres_check.py
npm run build --prefix frontend
# Hosted extension: isolated QA accounts; simulated spending only:
.venv/bin/python scripts/extended_smoke.py --url https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site --live
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

This operator command is never exposed over HTTP and never runs automatically during retries. It resets only the shared simulator's offers, approvals, orders/audit and synthetic spend. Registered private accounts, their preferences, sessions, carts and receipts are preserved.

## Live, controlled and simulated

- **Live sponsor sandbox:** actual authenticated Valio price/availability reads. These are synthetic challenge commercial facts, not production offers or reservations.
- **NVIDIA agent:** optional Nemotron 3.5 Lightning text interpretation or a typed Trust shortlist; selected text passed 7/7 authored cases and 18/18 checks, not a general accuracy claim. Automatic Super VL image reading falls back to local OCR on provider failure. API provenance remains honest; deterministic purchasing policy still applies.
- **Speech and images:** local Whisper base; automatic sanitized image reading with Tesseract fallback/explicit offline API option. Output stays editable, uploads are bounded and not stored, and extraction never changes a cart automatically. The owner previously confirmed actual public-site microphone transcription. Pathological/corrupt images may still be rejected; server pixel/decompression defenses remain.
- **Rehearsal fixture:** authored dynamic prices/availability, visibly labelled; real supplied catalog metadata is still used. No silent network fallback.
- **Controlled failures:** named overlays on fixture or live evidence. Their injected fields are recorded explicitly.
- **Order/approval gateway:** our implementation. No published sponsor order endpoint is used. No payments, real purchases or supplier orders occur.
- **Receipt verification:** gateway-held record consistency and offer hash, not a digital signature, product safety certification, future stock guarantee or proof of delivery.

Delivery reliability means historical delivered quantity ratio, not on-time probability. Carbon is a group-average estimate per kilogram; the app makes no litre-to-kilogram assumption or invented carbon savings. Lactose-free milk is not milk-allergy safe.

## Review assets

- [Product and concept choice](docs/PRODUCT.md)
- [Current model evaluation and trade-offs](docs/AI_MODEL_SELECTION.md) and [actual NVIDIA usage](nvidia_usage.txt)
- [Extended acceptance evidence](docs/EXTENDED_ACCEPTANCE.md)
- [Two-minute demo and pitch scripts](docs/DEMO.md)
- [87-second local fixture demo](.local/demo/aimo-order-desk-draft.mp4) (local artifact; not uploaded)
- [Local draft pitch PDF](docs/pitch/aimo-order-desk-draft.pdf) and [editable deck](docs/pitch/aimo-order-desk-draft.pptx)
- [Submission copy — DRAFT](docs/SUBMISSION_DRAFT.md)
- [Sponsor evidence and credit ledger](docs/SPONSORS.md)
- [Hosted architecture and operating limits](docs/DEPLOYMENT.md)
- [Current status](PROJECT_STATUS.md) and [delivery / wake-up review](docs/DELIVERY.md)

A commercial rollout needs real customer mandates, identity federation, distributed limits for horizontal scaling, broader load/device testing, supported deposits/variable-weight charges, provider terms suitable for confidential customer data, and an actual wholesaler order contract. This deployed challenge prototype does not claim production certification or measured customer savings. Event source-access/MIT requirements and challenge-data restrictions remain separate from this private source release.

## Worker-interview update

Open **Meal planner** for the new bolognese/lentil planning workflow: editable recipe quantities, overlapping dietary cohorts, sourcing preferences, local catalog candidates, evidence gaps and a draft JSON shopping plan. The detailed planner keeps its draft export and can now quote a saved plan into Smart order, carrying ingredient quantities, dietary cohorts, source and selected products. The complete basket requires fresh validation and explicit recipe review before simulated confirmation.

Customer spend thresholds can be set by the operator using `AIMO_AUTONOMOUS_LIMIT`, `AIMO_EXCEPTION_LIMIT`, and `AIMO_CUMULATIVE_LIMIT` in the ignored environment (EUR, restart required). Policy changes invalidate uncommitted offers/approvals. See [interview requirements, delivered changes and remaining gaps](docs/INTERVIEW_GAPS.md).
