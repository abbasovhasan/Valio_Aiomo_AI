# A4TB · Valio Aimo — delivery record

Public entry point: **[A4TB · Valio Aimo](https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site)**. Sites supplies the branded HTTPS origin; Modal runs the React/FastAPI application and private persistent SQLite volumes. Buyer and approver codes remain private. All confirmations are simulated. No real purchase, stock reservation, invoice, payment or final Junction submission is authorized or claimed.

## Reviewer entry points

- [Website checking guide](WEBSITE_CHECK_GUIDE.txt): plain-language steps, private code location, expected behavior and limitations.
- [Demo guide](DEMO.md): repeatable purchasing, conflict, meal and trust scenarios.
- [Customer journey](CUSTOMER_JOURNEY.md): request/clarification/cart/approval/result behavior.
- [Acceptance record](ACCEPTANCE_RECORD.md): requirement-to-evidence mapping and final source/handoff record.
- [Deployment](DEPLOYMENT.md): runtime, persistence, financial controls and release procedure.

Source repository: private `abbasovhasan/Valio_Aiomo_AI`, branch `codex/aimo-order-desk`. The previous procurement release is `ff0384c`; the extended release is identified by the final handoff and Git history on this same private branch.

## Implemented application

Smart order processes measured multi-product requests into a persistent versioned basket. Actual catalog IDs and supported evidence determine suitability; deterministic calculations convert kg/L/pieces/packages, obey lot rules and consolidate duplicate SKUs before rounding. Product choices, quantity/search edits, budgets and delivery dates recalculate the cart. A complete basket may require exact separate manager approval before buyer confirmation. The same idempotency key returns one simulated receipt, and read-only verification checks the saved record.

The saved Meal planner bridge carries exact recipe quantities, dietary groups, sourcing and selected products into quotation. Missing facts remain blockers. Trust scenarios retains the original outside-agent milk workflow, failure rehearsals, approval/resume and stale-offer repair.

The deployed extension adds hard versus soft brand/origin/organic controls, semantic query expansion with explicitly chosen replacements, bounded broader candidate checks, `OUT_OF_STOCK`/issue codes, per-unit prices and exact basket comparison deltas. Customer-facing disclosures now include supplied ingredients/allergens/storage/provenance and a fuller saved receipt. Pydantic response models validate monetary strings, statuses, quantities and nullable facts and publish the response schema through OpenAPI. Accounts, preferences, local OCR/ASR, microphone capture and reviewed combined input are also deployed. See the final evidence below.

## Verification actually established

| Scope | Observed evidence | Boundary |
| --- | --- | --- |
| Current backend/frontend | **171 backend tests passed** and production build passed | Local isolated test ledgers; `start.sh` also returned HTTP 200 on a separate port |
| Current hosted extension | **47 public HTTP checks passed in 103.44 s** | Accounts/cookies/isolation, preferences, repeated edits, budget/date/version boundaries, exact private approval, simulated confirm/retry/verify/recovery, real local media and actual NVIDIA/Valio reads |
| Hosted persistence | Previous manager-approved receipt survived new deployment; SQLite/simulated-only health, C67 frontend and typed OpenAPI observed | Existing shared synthetic spend preserved; private QA synthetic ledgers only |
| Registered-state restart | **13 checks passed** after stopped-writer redeployment: same remembered cookie, password login, preferences, spend and three receipts/approval records recovered | Protected backup passed SQLite integrity; no new orders; report remains ignored |
| Browser primary journey | Registration/Remember Me, saved preferences, OCR/audio edit/combine, sort/filter without cart mutation, budget/date correction, complete €14 receipt and reload | Local CUA interaction with isolated real catalog/fixture ledger; audio clip is authored |
| Browser approval/recipe | Separate manager approved exact €1,725 private cart; buyer confirmed and verified; expired quote blocked until buyer refreshed. Explicit overlap20 resolved; 500-diner meal plan transferred 11 requirements and exact 17 Nov date, with fresh chef review and missing-claim blockers | All confirmations simulated; recipes are proposed, not certified |
| Browser/device | Desktop 1440×1000 and mobile 390×844 receipt layouts inspected, no horizontal overflow; native keyboard filter/sort exercised; public new interface observed with no captured console errors | Owner separately confirmed real public-site microphone transcript; not broad accent/noisy-kitchen/handwriting coverage |
| Text/media evaluation | Selected Lightning 7/7 authored cases, 18/18 checks; local parser 6/7. Actual hosted local OCR 444 ms and ASR 1,800 ms backend time | Small authored benchmark; no universal model-accuracy claim. See model-selection report |
| Performance | Warm three-item fixture quote ~1,040→147 ms with preserved results | Cold index build slower (~1,912 ms first search), ~47.6 MiB additional memory; no load SLA |
| Catalog contract | All 17,546 normalized product-detail records validated | Shape compatibility, not product safety or commercial completeness |
| Historical PostgreSQL concurrency | Real Aiven TLS and isolated spend/idempotency checks passed | Hosted runtime remains single-writer SQLite |

[Acceptance record](ACCEPTANCE_RECORD.md) maps the current requirements to this evidence; [extended acceptance](EXTENDED_ACCEPTANCE.md) covers personalization, identity, media and model evaluation. Private release scanning and commit/push are recorded with the final source handoff. Raw reports and credentials stay in ignored `.local/`.

## Demonstration and operating limits

Use a small basket for repeatable confirmation checks; each committed demonstration consumes the persistent shared synthetic cap. Never reset it automatically or edit the database between judge interactions. Repeated local QA uses an isolated temporary ledger. The operator-only reset documented in README is an explicit local rehearsal action after preserving evidence.

NVIDIA interpretation and Valio price/stock selection are independent controls. Fixture prices and stock are authored; product identities come from the supplied catalog. Provider failures remain visible and never silently switch to fixtures. Unknown charges are disclosed, and the simulation confirms an item subtotal rather than a final commercial charge. Missing product claims, conflicting packages, unsupported deposits/variable weights or unavailable delivery facts can block a basket.

`./start.sh` provides the local application. Hosted operation is one container/one writer with persistent volume commits before mutation acknowledgement. Cold starts and sequential requests are expected. Sessions persist and expire; authentication throttles persist; broader distributed controls require a scaling redesign. These are operating boundaries, not claims of production certification.

## Historical milk release evidence

The earlier milk trust release passed 31 backend tests, real Aiven/Valio/NVIDIA smoke calls, an independent external-agent HTTP commitment/retry/verification flow and PostgreSQL concurrency checks. In an isolated namespace, six distinct €1,150 commitments under a €6,000 cap produced five successes and one rejection; four duplicate retries returned the same receipt. Temporary tables were removed. This remains evidence of the transaction design, not a fresh cloud database result.

A later local browser report contains 12 desktop/mobile checks of the retained trust and meal-planning views. An 87.48-second captioned fixture video at ignored `.local/demo/aimo-order-desk-draft.mp4` and the local pitch PDF/PPTX demonstrate that earlier milk flow. They are secondary historical trust artifacts; no new generic-cart recording or public video upload is claimed.

The earlier source release scanned 52 staged files and checked the original four data hashes. The prior procurement release `ff0384c` scanned 39 staged files and preserved those hashes before its private push. The extended release receives its own staged-source scan and original-dataset hash verification before its private push. Earlier hosting-blocked/in-memory-session notes describe superseded milestones, not current deployment state. Source and dataset restrictions remain active.
