> **Procurement deployment update — 14 November 2026.** The historical release record below is superseded where it describes milk-only scope, in-memory sessions or blocked hosting. Smart order now supports persisted multi-product carts, structured interpretation, editable constraints, whole-basket approval and simulated checkout. The meal planner transfers saved recipes into that cart. Modal HTTPS deployment is live; the deployed API exercised core cart/confirmation/retry/recovery and real NVIDIA + Valio reads. Current architecture, limitations and setup: [implementation plan](IMPLEMENTATION_PLAN.md), [deployment](DEPLOYMENT.md), and [project status](../PROJECT_STATUS.md). No final competition submission or real purchase occurred.

# Delivery — review before submitting

**14 November 2026, Europe/Helsinki. Aimo Order Desk is built and runnable. All orders are simulated. No Junction or sponsor submission was made and no submission status was changed.** The last observed Junction entry was Draft; current signed-in status could not be reread because account browser connections are unavailable.

## Start here when you wake up

1. Run `./start.sh` in this project and open **http://127.0.0.1:8000**. The QA server is stopped at handoff; the application does not continue running autonomously after this session. Buyer/approver codes are in ignored `.local/access.json`; never share them publicly.
2. Watch the local **87.48-second captioned fixture demo**: `.local/demo/aimo-order-desk-draft.mp4`. It is a real recording of the application, without audio; it has not been uploaded. Opening, approval, receipt and repair frames were inspected. The entire recording is visibly labelled as a rehearsal fixture, with simulated orders. Live sponsor integration is separately evidenced below.
3. Try the shortage flow: buyer signs in, **The milk runs out**, **Send to buyer agent**, inspect the blocked preferred offer and €1,870 UHT alternative. Sign in separately as Leena's approver identity, approve the exact offer, sign back in as buyer, commit, then retry. Inspect the same receipt and recorder.
4. Try **The offer changes** and **Refresh this exact offer**. Inspect the before/after comparison: expired → fresh, a new fingerprint, no inherited approval. A dietary failure can never be approved.
5. Review [pitch PDF](pitch/aimo-order-desk-draft.pdf), [editable PPTX](pitch/aimo-order-desk-draft.pptx), [draft submission copy](SUBMISSION_DRAFT.md), [two-minute demo script](DEMO.md), and [sponsor evidence](SPONSORS.md). Everything is prepared locally for your review.

The public schedule was freshly verified: **Sunday, 15 November 2026 at 10:00 Helsinki** is the recorded final-submission deadline. No automated submission is authorized. Authenticated challenge/guide pages could not be freshly reread; earlier detailed research and its verification limits are preserved.

## What works

- An editorial React/TypeScript order desk with an explicit kitchen brief, sales-unit offer cards, server-owned autonomy envelope, evidence inspector, factual decision recorder, exact approval and simulated receipt.
- **Rewind & Repair**: a failed rule is visible, a permitted alternative remains actionable, stale evidence creates a new offer, and a human cannot waive a hard dietary boundary.
- Versioned FastAPI/OpenAPI gateway, independent HTTP buyer script and real NVIDIA typed shortlist. The receiving gateway independently enforces policy; no model approve/commit tool exists.
- Real supplied catalogue IDs, explicit lactose-free evidence, unknown dietary facts preserved as unknown, count-based litre conversion, whole sealed sales packs/lot steps, tax-inclusive Decimal totals, date/cutoff/sales-block/stock checks, five-minute freshness and offer expiry. Changed tax basis, unit price or effective litres also require a new offer.
- Server-issued scoped buyer/approver sessions. Client roles, customer IDs, budgets and privileged fields cannot mint authority. Approver cannot commit; buyer cannot approve.
- Exact-offer approval binding; supplier refresh before commitment; cutoff, validity, freshness, mandate and approval deadlines checked again **inside** the spending transaction.
- Aiven PostgreSQL with verified-full TLS and the preserved CA, at most two concurrent connections, shared cap row lock, integer-cent ledger and database uniqueness. Explicit SQLite fallback preserves the same behavioural invariants.
- Original-key retries return the same receipt. Reusing a key for another offer or changing keys on an already committed offer is rejected. Concurrent distinct requests cannot exceed the cumulative cap.
- Explicit fixture mode and named controlled failure overlays. Upstream failures never silently become live fixture success. Security headers, same-origin mutation checks, rate limits and server-only credentials.

## Actual verification

| Executed command / check | Observed result |
| --- | --- |
| `./start.sh` | Frontend built; FastAPI started on loopback; `/health` reported PostgreSQL and simulated-only orders |
| `npm run build --prefix frontend` | TypeScript and Vite production build passed; latest bundle ~274 KB JS before gzip |
| `.venv/bin/python -m pytest -q` | **31 passed**, one upstream Starlette/httpx deprecation warning, **4.08 s** on latest semantic backend changes |
| `.venv/bin/python -m compileall -q backend scripts` | Passed; source subsequently formatted, no privileged behaviour added |
| `.venv/bin/python scripts/backend_smoke.py` | Actual Aiven TLS, live Valio price and availability, NVIDIA Nemotron typed function output succeeded |
| `.venv/bin/python scripts/agent_client.py --mode live --model --commit --output .local/external-live-proof.json` | Separate process used actual NVIDIA, real HTTP gateway, live Valio sandbox and Aiven simulated commitment; duplicate returned same receipt; scoped record verification valid |
| `.venv/bin/python scripts/backend_postgres_check.py` | Isolated real Aiven/PostgreSQL18.7/TLS1.3; six concurrent €1,150 commitments under €6,000 cap → five success/one rejection; four duplicate retries same receipt; temporary tables removed; rechecked after atomic-deadline fix |
| `.venv/bin/python scripts/browser_verify.py` | Real Chromium: **11 desktop/mobile checks passed**, **zero JavaScript errors**, 390px layout/navigation without horizontal overflow; buyer/approver/receipt/recorder/stale repair and accurate source labels exercised |
| `AIMO_STORAGE=sqlite` local TestClient smoke | Explicit offline fallback health, session, supplied catalogue, fixture run and within-mandate offer passed; no upstream calls or commitments |
| `.venv/bin/python scripts/record_demo.py` | Actual local fixture video, **87.48 s**, 12 caption cues, no public upload or real order |
| Pitch artifact QA | Seven-slide editable PPTX package/layout/font/import checks passed; PDF rendered with Poppler and visually inspected; authentic labelled shortage screenshot included |

The first Chromium attempt was interrupted when the unretained preview server ended; it was not claimed as a complete pass. A retained terminal server then completed the full suite, and the final source-label improvement was verified in the later 11-check pass. Browser automation targets only this local application, not signed-in account sessions. CUA account-browser inventory was empty.

Ignored evidence remains under `.local/`: integration report, external live proof, Postgres concurrency report, browser report, desktop/mobile screenshots, and the local video/captions. No raw response dumps or restricted catalogue are committed. After saving proof, explicit operator-only resets prepare a fresh synthetic ledger for review; no automatic reset exists over HTTP or during retries. At final handoff the synthetic spend is reset to **€0**.

## Deployment and remaining external actions

**No deployed URL is claimed. No Modal resource, secret, proxy, volume, card, top-up or paid plan was created.** The current account cannot be freshly inspected: no connected browser, no local Modal CLI/token configuration, and no Modal credential environment. Earlier account observations ($100 grant, 30 November 2027 expiry, $101 usage cap) are preserved as historical observations.

The concrete conditional adapter is `deploy_modal.py`; [DEPLOYMENT.md](DEPLOYMENT.md) names all remaining steps. The owner needs to verify applicable remaining promotional credits, enforced hard/net limits, no-card deploy access and a restricted Aiven egress route. The existing allowlist was not broadened. The adapter deliberately fails if private catalogue/CA mounting or persistent PostgreSQL access is absent. It is prepared source, not a tested deployment.

The local application is complete independently of hosting. Optional public video upload, organizer source access, source licensing/publicity questions, sponsor eligibility confirmation and any submission remain for owner review. **Do not change the Draft status or submit sponsor entries automatically.**

## Practical limits

This is a narrow synthetic hotel/milk task, not a real customer mandate or general food procurement system. The typed quantity/date control the request; prose is context. Budgets are authored policy. No labour savings, fulfilment improvement or customer interview is fabricated. Shipping and unsupported deposits/variable-weight charges are outside automatic commitment. Historical reliability is delivered quantity ratio; carbon is a group estimate per kg; no litre/kg equivalence or carbon savings are claimed.

Sessions and rate counters are single-process, in-memory demo controls; a restart ends sessions. PostgreSQL audit/order records persist, but the current browser's extra event view is not a multi-user operations console. A production path needs real identity federation, durable sessions/distributed rate limits, real supplier order/reservation contracts, stronger malformed-upstream schema coverage, retention/operations controls and customer validation. No hosted/browser-account checks, production load/failover, or actual supplier purchases were performed. One successful typed inference is not a model-reliability evaluation or proof of unlimited quota.

The source remains in the existing private GitHub repository on `codex/aimo-order-desk`. Review licensing/source access separately; no public repository or restricted dataset publication is authorized. Original prepared data, research, `.env` and CA remain preserved.

## Private source release

Source and local pitch assets were committed and pushed to the existing private repository on `codex/aimo-order-desk`. GitHub privacy was rechecked after the push: **private**, with that branch as default. No force push or public visibility change occurred. The staged scan checked **52 files**, known credential values, forbidden paths, decompressed PPTX/XML and extracted PDF text. It passed. All four original challenge files retain their recorded SHA-256 checksums; `.env` is still mode 0600. Raw data, database CA, credentials, runtime reports and the local video remain ignored. The final documentation-only release is also scanned before push.
