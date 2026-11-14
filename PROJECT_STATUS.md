# A4TB · Valio Aimo — project status

14 November 2026, Europe/Helsinki. Open **[A4TB · Valio Aimo](https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site)**. Public Sites HTTPS proxies the React/FastAPI application on Modal. Source, catalog and credentials remain private. All orders are simulated.

## Delivered

- **Smart order:** persistent multi-product conversation, actual catalog retrieval, grounded semantic query proposals, dietary/origin/brand constraints, precise package conversion and surplus, customer choices, budgets and delivery dates. Prices, permissions and commitments remain deterministic.
- **Discovery and personalization:** up to 16 retrieved candidates, sort/filter/compare controls, per-unit prices and complete basket changes. Saved brand/origin/organic/priority defaults apply to new carts; explicit requirements take precedence. Cheapest selection uses rounded item totals; other priorities and unresolved choices remain customer-controlled.
- **Text, voice and images:** server-local Tesseract OCR and Whisper base speech recognition, microphone or audio-file input, editable extraction and combined text. No direct media-to-cart mutation. Optional NVIDIA image processing requires explicit consent. Uploaded media is bounded, sanitized and not stored.
- **Accounts:** invitation-gated private registration, scrypt passwords, scoped accounts/preferences/carts/receipts, separate manager authorization, eight-hour sessions or 30-day Remember Me, persistent hashed tokens/revocation and login throttles.
- **Meal planner:** editable proposed/customer recipe quantities, explicit overlapping dietary cohorts, chosen catalog products and exact delivery transfer to Smart order. Fresh recipe acknowledgement and verified dietary evidence are required. Unknown evidence blocks unsafe confirmation.
- **Trust and saved result:** exact cart/freshness approval, atomic synthetic spending, idempotent simulated confirmation, complete item/date/approval receipt and read-only consistency verification. Retained milk Trust scenarios remain available in the shared demonstration.
- **Hosted runtime:** one Modal CPU, 1,536 MiB memory, one container/input, private catalog and SQLite state volumes; commit before mutation acknowledgement. Local Aiven TLS integration retained without widening its allowlist.

## Executed verification

- **171 backend tests passed in the final rerun (32.55 s)**; production frontend build passed. Actual `start.sh` startup returned HTTP 200 using a separate local ledger.
- **47 checks through the public URL passed** in 103.44 seconds: accounts/cookies, private-scope isolation, preferences, repeated edits, stale versions, budgets, exact manager approval, simulated confirm/retry/verify/recovery, OCR/speech, origin protection and actual selected NVIDIA + Valio reads. Only private QA synthetic ledgers changed; the shared ledger was preserved.
- A further **13-check restart recovery passed**: the existing 30-day cookie, account password, preferences, synthetic spend and three saved receipts/approval records survived a stopped-writer redeployment. A protected backup passed SQLite integrity checks; no new order was created.
- The previous approved receipt survived deployment, and hosted OpenAPI publishes typed monetary/quantity/status contracts. Current frontend asset `index-C67pl32K.js` was observed over HTTPS.
- Local CUA browser journeys exercised registration/Remember Me, preferences, combined image/audio edits, discovery controls without cart mutation, budget/date correction, saved receipt/reload, separate private manager approval, expired-quote recovery, dietary overlap and exact 17 November meal-plan transfer. Desktop 1440×1000 and mobile 390×844 receipt views were inspected; no horizontal overflow. Public release loaded with no captured console errors. The owner separately confirmed correct live microphone transcription.
- Final selected NVIDIA Lightning benchmark: **7/7 authored cases, 18/18 checks**, six actual network calls, median 6,119 ms. Local parser: 6/7 cases, median 147 ms. These small synthetic measurements do not establish universal accuracy. Local media and performance trade-offs are documented in [model selection](docs/AI_MODEL_SELECTION.md).
- A safe static catalog index reduced the measured warm three-item fixture quotation from about 1,040 to 147 ms while preserving results. The cold first search increased to about 1,912 ms and the index used about 47.6 MiB extra memory.

## Operating boundaries

This is a deployed challenge simulator using restricted synthetic catalog/commercial data. Delivery/service fees are excluded. Missing claims, ambiguous packages, unsupported variable weights/deposits or unavailable delivery evidence can block a basket. All suggested recipes require chef review; allergy safety and commercial production readiness are not certified. NVIDIA trial processing is opt-in for nonconfidential demonstration content. Broader accents/noisy kitchens/handwriting, enterprise identity and horizontal scale are outside the measured coverage.

The observed November Modal usage report was **$0.04369075** at the release check, not a final bill or remaining balance. Previously verified controls were a $100 Junction grant, $101 hard usage cap and no payment method. No card, top-up, paid plan, real supplier order or final Junction submission was added. See [deployment](docs/DEPLOYMENT.md), [acceptance](docs/ACCEPTANCE_RECORD.md), [guide](docs/WEBSITE_CHECK_GUIDE.txt) and [delivery](docs/DELIVERY.md). The private release commit is identified by Git history and the final handoff.
