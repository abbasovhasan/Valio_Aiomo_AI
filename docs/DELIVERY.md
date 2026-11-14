# A4TB · Valio Aimo — delivery record

Public entry point: **[A4TB · Valio Aimo](https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site)**. Sites supplies the branded HTTPS origin; Modal runs the React/FastAPI application and private persistent SQLite volumes. Buyer and approver codes remain private. All confirmations are simulated. No real purchase, stock reservation, invoice, payment or final Junction submission is authorized or claimed.

## Reviewer entry points

- [Website checking guide](WEBSITE_CHECK_GUIDE.txt): plain-language steps, private code location, expected behavior and limitations.
- [Demo guide](DEMO.md): repeatable purchasing, conflict, meal and trust scenarios.
- [Customer journey](CUSTOMER_JOURNEY.md): request/clarification/cart/approval/result behavior.
- [Acceptance record](ACCEPTANCE_RECORD.md): requirement-to-evidence mapping and final source/handoff record.
- [Deployment](DEPLOYMENT.md): runtime, persistence, financial controls and release procedure.

Source repository: private `abbasovhasan/Valio_Aiomo_AI`, branch `codex/aimo-order-desk`. Earlier `ff0384c`/`947e417` releases remain historical. Final B4 deployment/continuity/long-name and Bk layout proof passed; unchanged CFF media/owner proof retains its named scope. Implementation `829207f` was reviewed, scanned and pushed to private `codex/aimo-order-desk`.

## Implemented application

Smart order processes measured multi-product requests into a persistent versioned basket. Actual catalog IDs and supported evidence determine suitability; deterministic calculations convert kg/L/pieces/packages, obey lot rules and consolidate duplicate SKUs before rounding. Product choices, quantity/search edits, budgets and delivery dates recalculate the cart. A complete basket may require exact separate manager approval before buyer confirmation. The same idempotency key returns one simulated receipt, and read-only verification checks the saved record.

The saved Meal planner bridge carries exact recipe quantities, dietary groups, sourcing and selected products into quotation. Missing facts remain blockers. Trust scenarios retains the original outside-agent milk workflow, failure rehearsals, approval/resume and stale-offer repair.

The current continuation adds paginated Products, direct catalog add/replace and persistent personal History. Hard dietary/exclusion defaults affect search, alternatives, meal planning and the cart; request provenance lets saved-only restrictions clear on re-quotation while preserving explicit requirements. Verified `nonAllergen FREE_FROM` evidence is retained; contained/trace contradictions and unknown certification remain blockers. Failed quotations preserve eligible drafts with nullable prices. The four inputs are text, local microphone voice, image upload and photo capture; audio-file upload is removed. Original JPEG/PNG images up to 5 MiB are resized, then automatically read by NVIDIA with actual local OCR fallback. Output stays editable, plain privacy text replaces provider/checkbox controls, and server decompression guards remain. Typed responses, evidence and simulator authority are preserved.

## Verification actually established

| Scope | Observed evidence | Boundary |
| --- | --- | --- |
| Current backend/frontend | **285 backend tests in 83.21s**, final `index-B4p90PsT.js` deployed with healthy SQLite/simulator/policy | Private implementation `829207f` pushed after review and scanning |
| Final long-name regression | All 13 actual source names >120 characters passed local selection/follow-up;3 hosted checks on the longest 155-character product retained line/SKU/name/qty/date/budget/version | No orders/model/supplier calls, spend unchanged; personal QA entry hidden while audit retained |
| Final B4 continuity | **12 checks passed in 69.561s:** protected backup, remembered identities/preferences/spending, all five QA and old shared receipt retained | Zero new orders; prior Bk 12@90.887s/CFF 12@153.84s remain historical |
| Bk browser/render, unchanged in B4 | Four local choices/reload and repeated public choices kept 2 forms for 2 lines; final 20 L milk/4 kg butter draft ready at 17 November / €200, no order | Empty console warnings/errors; desktop 1440×1000/mobile 390×844 no overflow, four inputs visible |
| Earlier AAD hosted extension | **47 checks passed in 117.09 s**, including local OCR/ASR, live typed NVIDIA/Valio, scoped approval and simulator recovery | Shared Aurora spending unchanged; only private QA simulations. Predates final automatic image routing |
| Current complete-catalog QA | **12/12 local groups passed**, including all 349 category counts/names (698 API checks), 443-item pagination and kg/L/pieces/packages carts | Original four datasets; fixture quotations, isolated ledger, no orders/provider calls; 39.882-second total is not hosted latency |
| Hosted catalog/history | **12/12 hosted matrix groups passed in 378.345s**; 349-category/698-request sweep 310.544s; **13 history/release checks** passed | Four fixture drafts/one reuse, preferences preserved and QA-buyer spending zero; no orders/model/supplier calls. Catalog paths unchanged by final media update |
| Current safety/history | **103 tests passed** across preferences, search safety, history and interpretation; includes 50 safety and 9 history tests | Overlapping subsets of the full suite; explicit-vs-saved restrictions, fresh reuse, outage recovery and immutable record preservation |
| Current media handlers | **7 microphone + 7 camera + 8 normalization grouped checks passed** | Fake streams/recorders/canvas; cancellation/stale completion and raster validation; not physical-device/accuracy proof |
| Final default image service | **4 checks passed in 12.592 s:** no-query NVIDIA Super VL read, editable milk/butter text, explicit cloud denial and unchanged saved purchasing state | Actual provider source verified; 1,856 ms reported server time is one sample, not a latency guarantee |
| Current image browser regression | Public CFF read 13.86 MP JPEG (4200×3300, 338,326 bytes); editing/Add gating preserved context/date/budget. Local 5,242,881-byte original was rejected; provider controls absent | Server 12 MP defense retained; owner confirmed the same phone photo works after reload. One case, not general device/recognition coverage |
| Current local browser | Supplier-outage recovery; 40-diner cohorts 30/2/6/2; saved plan transferred 11 ingredients,17 November and€500 budget | Chef review/hard-rule blockers remained; final public rendering separately passed above |
| Previous C67 hosted extension | **47 public HTTP checks passed in 103.44 s** | Accounts/cookies/isolation, preferences, repeated edits, budget/date/version boundaries, exact private approval, simulated confirm/retry/verify/recovery, real local media and actual NVIDIA/Valio reads |
| Previous hosted persistence | Old manager-approved receipt survived C67 deployment; SQLite/simulated-only health, frontend and typed OpenAPI observed | Existing shared synthetic spend preserved; private QA synthetic ledgers only |
| Previous registered-state restart | **13 checks passed** after stopped-writer redeployment: same remembered cookie, password login, preferences, spend and three receipts/approval records recovered | Protected backup passed SQLite integrity; no new orders; report remains ignored |
| Previous browser primary journey | Registration/Remember Me, saved preferences, OCR/audio edit/combine, sort/filter without cart mutation, budget/date correction, complete €14 receipt and reload | Local CUA interaction with isolated real catalog/fixture ledger; audio clip is authored |
| Previous browser approval/recipe | Separate manager approved exact €1,725 private cart; buyer confirmed and verified; expired quote blocked until buyer refreshed. Explicit overlap20 resolved; 500-diner meal plan transferred 11 requirements and exact 17 Nov date, with fresh chef review and missing-claim blockers | All confirmations simulated; recipes are proposed, not certified |
| Previous browser/device | Desktop 1440×1000 and mobile 390×844 receipt layouts inspected, no horizontal overflow; native keyboard filter/sort exercised; C67 observed with no captured console errors | Owner separately confirmed real public-site microphone transcript; not broad accent/noisy-kitchen/handwriting coverage |
| Text/media evaluation | Selected Lightning 7/7 authored cases, 18/18 checks; local parser 6/7. Actual hosted local OCR 444 ms and ASR 1,800 ms backend time | Small authored benchmark; no universal model-accuracy claim. See model-selection report |
| Performance | Warm three-item fixture quote ~1,040→147 ms with preserved results | Cold index build slower (~1,912 ms first search), ~47.6 MiB additional memory; no load SLA |
| Catalog contract | All 17,546 normalized product-detail records validated | Shape compatibility, not product safety or commercial completeness |
| Historical PostgreSQL concurrency | Real Aiven TLS and isolated spend/idempotency checks passed | Hosted runtime remains single-writer SQLite |

[Acceptance record](ACCEPTANCE_RECORD.md) maps requirements to evidence; [extended acceptance](EXTENDED_ACCEPTANCE.md) covers personalization, identity, media and model evaluation, and [FINAL_QA_REPORT.md](FINAL_QA_REPORT.md) records this continuation's defects and release gates. The previous implementation release passed a 54-file private-source scan, original dataset hash verification and GitHub privacy check before its push; those scans do not certify the new diff. Raw reports and credentials stay ignored in `.local/`.

## Demonstration and operating limits

Use a small basket for repeatable confirmation checks; each committed demonstration consumes the persistent shared synthetic cap. Never reset it automatically or edit the database between judge interactions. Repeated local QA uses an isolated temporary ledger. The operator-only reset documented in README is an explicit local rehearsal action after preserving evidence.

NVIDIA interpretation and Valio price/stock selection are independent controls. Fixture prices and stock are authored; product identities come from the supplied catalog. Provider failures remain visible and never silently switch to fixtures. Unknown charges are disclosed, and the simulation confirms an item subtotal rather than a final commercial charge. Missing product claims, conflicting packages, unsupported deposits/variable weights or unavailable delivery facts can block a basket.

`./start.sh` provides the local application. Hosted operation is one container/one writer with persistent volume commits before mutation acknowledgement. Cold starts and sequential requests are expected. Sessions persist and expire; authentication throttles persist; broader distributed controls require a scaling redesign. These are operating boundaries, not claims of production certification.

## Historical milk release evidence

The earlier milk trust release passed 31 backend tests, real Aiven/Valio/NVIDIA smoke calls, an independent external-agent HTTP commitment/retry/verification flow and PostgreSQL concurrency checks. In an isolated namespace, six distinct €1,150 commitments under a €6,000 cap produced five successes and one rejection; four duplicate retries returned the same receipt. Temporary tables were removed. This remains evidence of the transaction design, not a fresh cloud database result.

A later local browser report contains 12 desktop/mobile checks of the retained trust and meal-planning views. An 87.48-second captioned fixture video at ignored `.local/demo/aimo-order-desk-draft.mp4` and the local pitch PDF/PPTX demonstrate that earlier milk flow. They are secondary historical trust artifacts; no new generic-cart recording or public video upload is claimed.

The earlier source release scanned 52 staged files and checked the original four data hashes. The prior procurement release `ff0384c` scanned 39 staged files and preserved those hashes before its private push. The extended release receives its own staged-source scan and original-dataset hash verification before its private push. Earlier hosting-blocked/in-memory-session notes describe superseded milestones, not current deployment state. Source and dataset restrictions remain active.
