# Role demo, product evidence and generic catalog QA

Reviewed 15 November 2026, Europe/Helsinki. Scope: the complete role/detail refinement and subsequent complete purchasing-workspace/financial/comparison extension, baseline commit `36c43b9`, and explicitly identified changes under development. Source inspection is distinguished from executed checks. The earlier 285-test/349-category release is historical evidence, not proof that this refinement is deployed. The later supplied screenshot identifies a two-product fixture-price/policy example audited below.

## Actual screen inventory

The customer app is one React SPA: `/` and the backend's non-API fallback serve the shell. Navigation uses component state, not separate `/login`, `/products` or `/approvals` page routes. API paths below are separate server resources.

| Screen / entry point | Actual implementation and scope | Required current browser review |
| --- | --- | --- |
| Initial Smart order / brand home | `main.tsx` tab `purchase`, `ProcurementDesk`; unsigned visitors see request entry and sign-in actions | First impression, empty/loading/error states, primary action, early date/budget |
| Account/sign-in dialog | `AuthDialog`: Buyer/Approver cards and common Remember Me; secondary Use an account → Account sign-in/Create workspace/Access code; logout and private-manager shortcut preserved | Both cards, standard forms, password/field validation, dialog keyboard/focus and recovery |
| Buyer Smart order | Composer, text/voice/image/camera, clarification, candidates, sorting/filtering, quantity/search edits, saved preferences and cart | Full request→choice→review flow; preserve unrelated lines and restrictions |
| Products | `ProductWorkspace`: paginated catalog, category/brand/origin/diet filters, selection/quantity/unit panel, add to current/new cart | Names/SKU/partials, pagination, filters/reset, unquoted products, replacement and selection preservation |
| Product detail view | Shared native right drawer on desktop /bottom sheet on mobile replaces baseline inline expansion; compact title/SKU and full name once in scroll body | Open/close/body scroll without changing cards/cart/selection; keyboard/Escape/backdrop/focus return; independent Compare/Cart layouts |
| Cart / review / result | `ProcurementDesk` desktop sidebar, new compact mobile cart; review dialog and immutable simulated receipt with verification | Direct edits/removal, budget/date, price/stock gaps, exact review, retry/reload and read-only verification |
| Approver | Baseline reuses saved-cart approver view; new scoped queue/workspace uses `/api/v1/approvals` | Intentional shared demo handoff; queue→exact approve/reject→buyer sees outcome; no buyer privileges |
| Meal planner | `MealPlanner`, diner cohorts/overlap, editable grams, draft export, saved-plan quotation | Rebuild invalidation, source/chef review, exact bridge quantities/date/budget and hard dietary blockers |
| History | `HistoryPanel`: open/reuse/archive/restore/remove, paging and retained purchasing evidence | Every action/reload, scope isolation, removal confirmation and empty/error states |
| Buying preferences | `PreferencesPanel` in purchasing workspaces; extension requires removal from History | Mandatory restrictions versus optional defaults, search, exclusions, save/clear, current-cart re-quote |
| Demo tools | Operator menu: Data & model settings, Trust scenarios, Decision recorder, Gateway API, About trust | Progressive disclosure, correct workspace gating, no nonfunctional visible controls |
| Trust scenarios / recorder / gateway | `main.tsx` tabs `desk`, `recorder`, `gateway`; shared legacy mandate lab, run events and technical API reference | Legacy permissions/scenarios retained; private/quick-demo identity must not inherit the Aurora mandate |
| About / legacy evidence overlays | Existing explanation and evidence overlays in `main.tsx`; no separate settings dashboard | Close/Escape/focus, mobile containment, source accuracy; preserve existing artifacts |

## Server interface inventory

| Family | Actual endpoints / authorization |
| --- | --- |
| Authentication | `POST /api/v1/session`; `GET/DELETE /session`; `POST /auth/login`, `/auth/register`; new `GET/POST /auth/demo`. Existing cookie/token validation stays server-side; demo access is gated by `AIMO_DEMO_MODE=true` and fixed isolated identities, never a client-chosen private workspace. |
| Workspace / preferences | Authenticated `GET /workspace`; buyer `GET/PUT /preferences`. |
| Discovery / input | Authenticated `GET /products` and `/products/search`; buyer multipart `POST /input/image`, `/input/audio`; media extraction cannot purchase. |
| Procurement | Buyer `POST /procurement/sessions`, `/from-product`, `/from-meal-plan`; scoped `GET /{id}`, `/verify`; versioned buyer `POST /{id}/actions`, `/confirm`; approver exact-fingerprint `/approve` and new `/reject`. |
| Approvals / history | New approver `GET /approvals`; buyer `GET /history`, `GET/PATCH/DELETE /history/{id}`, `POST /history/{id}/reuse`. |
| Planning | Buyer `POST /meal-plans`, scoped `GET /meal-plans/{plan_id}`. |
| Retained trust API | Shared-mandate `POST /runs`, scoped `GET /runs/{id}`, `/offers/{id}`, `/receipts/{id}` and receipt verification; separate offer approve/revalidate/simulated commit actions. |
| Operations / AX | Public `/health`, generated `/openapi.json`, `/docs`, `/redoc`; these technical surfaces do not authorize buyer/approver mutations. |

Session risks addressed: a delayed initial `/session` response can race a newer login; a late old-session 401 can clear newer UI identity; same-buyer role changes need an intentional state reset/queue transition. The backend already revokes the current token when issuing a replacement and persists hashed tokens with expiry. There is no refresh-token flow to invent. Epoch/deferred-response/late-401 tests, local role/decision journeys, hosted role/reload/logout and server-side cookie/revocation checks now cover these paths; a cookie alone is not treated as proof.

## Unit evidence and confirmed findings

- Original files contain **17,546 products /349 untranslated category codes /17 sales-unit codes**. Sales-code counts: KI 8,005; ST 5,607; KG 1,068; PAK 880; BAG 697; RAS 328; PRK 320; BOT 310; smaller SK/CS/KLE/KRT/KAN/PAL/NIP/DSP/DZ groups also exist. There are no literal `L` sales/base codes in this snapshot.
- The supplied schema explicitly says internal sales/base/unit-ID translations are absent; `units.sizeInBaseUnits` supplies the ratio, and `allowedLotSize` is an order increment in sales units. Therefore KI is not globally labelled “case”. The [official UNECE vocabulary](https://vocabulary.uncefact.org/UnitMeasureCode) defines quantitative CLT/centilitre, LTR/litre, MLT/millilitre, KGM/kilogram and H87/piece; it does not decode these internal commercial codes. Its unrelated KI definition further rules out blindly sharing dictionaries.
- **50** actual consumer-level CLT records (45 BOT, five ST) were unsupported as litres. Verified conversion is declared centilitres÷100×sales/base ratio; price per litre is sales-unit price÷that capacity. Fixed-pack rounding still obeys whole packages and the declared lot step.
- **440** non-variable KG-sale/KG-base records have a declared 1:1 ratio. Quantity must round to the declared fractional KG lot, not a whole-package numerator. Four steak records also wrongly compared the 1-kg commercial price basis with 1.2/0.8/0.9-kg named multipacks. Those pack amounts match their lot steps; they are not a contradiction to a per-kg sale basis.
- H87 remains a separate unresolved contained-count issue: a source waste-bag unit declares 50 pieces while its base-unit ratio is one; a cake labelled 96×20g has H87=1920 and net mass 1.920kg. Neither base ST nor a blanket H87 conversion safely establishes individual contained pieces. “Consumer units” must remain distinct from contents. Variable weight, missing/conflicting physical facts, unsupported units and deposits retain honest blockers.

## Representative real-data scenarios A–J

| Scenario | Source-derived selection and essential assertions | Current scope |
| --- | --- | --- |
| A — Milk volume | Actual milk with verified litre capacity/lactose requirement; compare different pack capacities, rounded volume, price per litre and date/stock evidence | Current local/public milk draft, exact source conversions, mobile/desktop detail and independent pricing evidence passed |
| B — Other categories | Real syrup CLT, measured-weight produce/meat, flour/pasta and foodservice supplies as present in source names; category codes stay untranslated | All 50 CLT/440 fixed KG tests plus five-category hosted smoke and arbitrary-category local/public comparison passed |
| C — Multiple products | Products from distinct actual categories; independent line demands, aggregated same-SKU lots, subtotal and preserved choices | Aggregation regression plus local shared-SKU syrup consolidation and current public two-line draft passed |
| D — Alternatives | Multiple real candidates, sorts/filters, explicit replacement and comparative cost; detail view must not mutate cart | Local and public Smart/Products two/three comparison, fourth replacement, independent sorts and drawer geometry/preservation passed in the recorded scope |
| E — Not found | Guaranteed absent query and invalid catalog ID; honest empty/error, no invented product or zero price | Catalog no-match tests and actual local absent-product/partial-cart removal/recovery passed |
| F — Different units | All actual CLT conversions and fixed KG lots; ST/KI whole-pack counterexamples; unknown/variable conversions stay blocked | `tests/test_unit_semantics.py` current results below |
| G — Diets | Source positive/trace/free/unknown declarations, saved hard restrictions and conflicting labels; lactose-free ≠milk-allergy safe | Safety/presentation tests, local saved-mandatory restriction block/clear recovery and public milk-allergen details passed |
| H — Budget | Multi-product hard budget, deficient budget→explicit correction; price/pack totals remain deterministic | Financial regressions and local €174.70/€100 block→€85.60 recovery plus separate policy-boundary audit passed |
| I — Delivery | Supported source schedule evidence and deadlines; unknown/later availability stays explicit; no invented delivery booking | Failure/date tests, single editor→cart summary, persisted17 November and expired-quote blocking passed; live reads were bounded and authorized |
| J — Buyer/Approver | Explicit demo flag, isolated shared-demo queue, exact approval/rejection, role switch/reload, buyer resumes; no production scope or real order | Auth/queue tests,47 hosted HTTP checks, local exact decisions and public Buyer/Approver/logout/re-entry/reload passed |

## Twenty acceptance items → verification map

| # | Required result | Verification evidence |
| --- | --- | --- |
| 1 | Buyer/Approver cards | Actual dialog and both resulting role workspaces, keyboard and pointer |
| 2 | No typed demo code | Inspect browser request/flow; no credential material bundled in client |
| 3 | Sessions/role switching persist correctly | Delayed restoration/401 race checks, logout/expiry, refresh, Remember Me, cookie/backend role agreement |
| 4 | Standard auth preserved | Existing/new login/register tests and real standard-account sign-in/logout |
| 5 | Controlled demo security | Disabled-by-default flag, forged role/workspace/body rejection, CSRF/origin, private/legacy scope isolation and server authorization |
| 6 | No tall inline evidence card | Compare card rectangles before/open/close; dedicated responsive dialog; no orphan/duplicate controls |
| 7 | Organized detail information | Overview, purchasing, specs, ingredients/allergens and Sources; useful headings/focus/scroll |
| 8 | Accurate complete information | Safe actual fields retained, explicit absence/unknown/positive distinctions and essential hard warnings visible |
| 9 | Desktop comparison | Multiple cards/choices/sorts and unchanged layout when inspecting details |
| 10 | Mobile comparison | Same workflow at 320/375/390/430 widths and tablet; usable touch/keyboard/focus |
| 11 | Correct quantities/prices | New independent CLT/KG/pack/aggregation/public-quote regressions plus existing Decimal/budget/stock tests |
| 12 | Generic actual catalog | Preserve 17,546-record/349-category coverage; no SKU/name-specific arithmetic or global code-label guesses |
| 13 | Diverse categories tested | Source-derived A–I matrix; document unsupported physical metadata instead of claiming every unit works |
| 14 | All major screens reviewed | Screen inventory above with recorded local/public browser results |
| 15 | UI inconsistencies corrected | Concrete before/after observations; retained selection, source, warning, error and loading behavior |
| 16 | Mobile issues fixed | Major screens/dialogs/cart at specified widths, no overflow/clipping; actual-device limits stated |
| 17 | Both role workflows tested | Scenario J including approve/reject/expiry and intentional role handoff |
| 18 | Existing critical functionality retained | Auth, text/voice/image/camera, meal bridge, history/preferences, cart/approval/receipt and legacy demo regressions |
| 19 | Relevant tests pass | Final combined suite and production build after all edits, with actual command/count |
| 20 | Updated deployed browser verified | Final revision/assets/flag/persistence checked through public origin and real desktop/mobile journeys |

## Executed verification and practical scope

Read-only dataset/schema/unit inventory and official unit definitions were inspected. Initial new unit run found the four measured-KG multipack failures (15 passed /one failed). After the generic fix, `.venv/bin/python -m pytest tests/test_unit_semantics.py tests/test_product_facts.py tests/test_procurement_contract.py -q --tb=short` passed **53 tests in 6.70s**, including **17 new unit/evidence tests**. These verify all 50 CLT records and all 440 measured-KG records/lots; ST/KI whole-pack behavior; fractional price and same-SKU aggregation; stock 1.49kg versus required 1.5kg blocked, 1.50kg permitted; variable/conflicting unknowns; and public claim/origin/organic field preservation. No live lookup/model/confirmation occurred and isolated ledgers spent zero. This is targeted verification, not final acceptance.

The engine agent's subsequent full backend run passed **315 tests in 85.65s**, including all 17 unit tests and 13 dedicated demo-auth/queue tests. It precedes the later comparison/image/sort/planner extension and is not its final regression result. Keyless `scripts/role_demo_smoke.py` passed **46 checks in 4.953s** against an isolated FastAPI test server, then **46 checks in 4.623s** against the restarted current HTTP service at `http://127.0.0.1:8000`. It used five source-derived categories, real CLT and fractional-KG products, fixture quotes, queue rejection/revision/approval, exact fingerprints, session revocation and unchanged preferences/spend. The existing quick-demo spend of **€41.22** was preserved. It created **zero orders**, invoked no supplier/model, and disarmed its approval-only basket after review. Evidence: private `.local/role-demo-http-report.json`. The optional single-small-simulation flag was not executed.

The final current backend run after the History dish/servings title correction passed **360 tests in 113.48s**, exit 0 without warnings/failures. It includes the prior baseline, 15 custom-meal, 10 presentation, eight financial, four generic purpose and eight HTML-cache regressions, superseding earlier 348/352 runs. Frontend grouped checks passed **62 total**: product details 16, comparison 6, page state 5, meal 6, session 7, microphone 7, camera 7 and image normalization 8.

Current source assets are **index-Bj9bRlqq.js /index-BeA19jUu.css**. Root's actual local drawer retest at **320/375/390/430/768/1440px** verified phone 96dvh/desktop 560px placement, one scroll owner, unchanged keyed visible-card geometry, Escape/backdrop and close-focus restoration. Native Tab did not reach underlying cart controls, though browser-chrome/body transitions occurred; every Tab is not asserted to remain a dialog descendant. Products arbitrary-category two/three comparison, fourth replacement, sort preservation, adding only the selected Syrup and 1L→two 0.75L packs passed. Editable current image upload had no provider UI; unknown mandatory preference blocked and clearing recovered; About/Evidence Escape and meal-transfer cancel-focus/new-cart comparison clearing (J3) passed. Detailed scoped journeys are in `PRODUCT_REFINEMENT_REPORT.md`.

The earlier public **B4p90PsT** asset explains the owner's old accordion. The current Modal deployment publicly serves **index-Bj9bRlqq.js**. The actual sanitized private `.local/role-sheet-release-recovery-report.json` records **14 passed checks in 91.833s**, protected stopped-writer backup integrity **ok**, controlled-demo flag enabled, simulated-only backend and same-origin camera/microphone policy. Remembered private A/B sessions, preferences/spend, the existing password, **five registered-QA receipts** and original shared receipt/cumulative spend survived; **zero new orders**. Final HTML entry revalidation also passed at `/`, `/index.html` and `/products`; asset behavior is unchanged. Implementation `b166ca6` is reviewed, scanned and pushed privately. Public Approver queue/sign-out/Buyer re-entry/reload restored the same €74.70 draft and authoritative identity; the warning/error log was empty.

Actual hosted keyless HTTP smoke passed **47 checks in 95.582s** (`.local/role-demo-hosted-report.json`), with **zero orders/models/supplier calls** and quick-demo spend **€0.00→€0.00**. Public browser verified private-session restoration, quick Buyer/30-day remembering, a **20L milk/5kg butter €74.70 draft** without confirmation, and the six-width shared drawer: desktop 560×900px/phone 96dvh, one scroll owner/full name, unchanged milk-card rectangles/cart text and backdrop-close focus. Smart Compare (2)→(3) and comparison Details opened exactly one drawer; Escape restored Compare (3) focus/selections without changing the cart.

Public Products details/Escape retained potato salad/Forssan/name-descending/quantity one/rows and the in-view selection rectangle. The 155-character SKU471412 at 320px had one full name, a 78.64px header and no horizontal overflow. Arbitrary Syrup+Cucumber comparison added Flour as third; fourth Milk required explicit Cucumber replacement. The 320px 262px container scrolled its 589px table; one details bottom sheet returned to preserved Compare (3), with Smart order's independent three-item list/cart unchanged. Screenshots: `.local/role-demo-browser/hosted-desktop-details.jpg` and `.local/role-demo-browser/hosted-mobile-details.jpg`. These public priority gates passed; this does not claim a new exhaustive legacy/media/hardware retest.

The checking guide is `/home/hasan/Documents/ChatGPT/Valio_Aiomo_AI/docs/WEBSITE_CHECK_GUIDE.txt`. The explicitly authorized financial audit used only a two-product supplier price/availability read; no order or model call. User-owned `output/`, `tmp/` and video-prompt artifacts remain untouched; no paid resources or final Junction submission.

## Additional purchasing-workspace acceptance scope

The complete later directive requires the following work; this table is an evidence plan, not a delivered-feature claim.

| Requirement | Independent acceptance evidence required |
| --- | --- |
| Page-owned filters | Smart order filters do not alter Products state and vice versa; saved mandatory preferences intentionally remain global; cart choices persist through either page's search/filter/sort/reset. |
| Any two or three comparison | Manual selection only in Smart order/Products; any categories and later search pages; maximum three with clear replacement; explicit compare/open/close; aligned actual specs/unknowns and dimension-valid prices; choose preferred without implicitly selecting the entire set or losing the cart. |
| Genuine product images | Verified source media references/available assets, bounded image route and truthful missing-image fallback; no fabricated food/product identity; broken/loading states and mobile containment. |
| One cart editor | One authoritative date/budget editor; no conflicting duplicate controls; changes re-quote the same selected basket. |
| History scope | No Buying preferences panel within History; all original open/reuse/archive/restore/remove and evidence retention still work. |
| Custom meal planning | Editable dish/servings/date/budget/ingredients, add/remove/change/substitute, dietary portions and chef/source acknowledgement; shared purchasing engine and protected existing-cart handoff; illustrative defaults remain clearly declared. |
| Products discovery | Working recommended/price/name sorting in both directions, supported unit-price dimensions and source-backed filters; unknown prices do not become zero or rank as cheapest. |
| Scroll/layout review | Inspect full-page scrolling before adding nested containers; dialogs/cards, comparisons, cart and planner remain usable across required widths and keyboard interaction. |
| Preserved flows | Standard and quick-role auth, approval/rejection, media editing, mandatory preferences, receipts/history and legacy demo tools; latest combined tests/build and real local/public browser evidence. |

Bounded backend presentation review passed **10 tests in 2.06s** (`tests/test_product_presentation_data.py`): complete-filtered-catalog name order; explicitly quoted-page sales/kg/litre price sorts with unknowns last in both directions; bounded supplier requests; no inferred density; declared nutrition basis/precision/zero retained; no image URL invented from a media ID. Source-only performance measured global lactose-free discovery at **1.0587s**, and category 17300 with the same hard diet at **1.0134s** (258 hits). Both normalized all 17,546 source rows to retain accurate disjunctive category facets; category without a diet took **0.4336s**, normalizing only its 20 displayed rows. Peak process RSS was 629.86MiB. These are one-run local measurements, not production latency guarantees. Filtering before the safety pass would change the promised cross-category facet counts; no such shortcut or stale safety cache was introduced.

## Screenshot financial audit

The two actual source products are uniquely identified by their English names. Independent raw `BASE_UNIT_OR_EACH` net mass/volume, multiplied by the declared sales/base ratio, verifies **0.5kg per sales unit** for the 500g unsalted butter and **1L per sales unit** for the lactose-free UHT whole milk. Therefore **200kg =400 sales units** and **300L =300 sales units**; neither is an invented KI carton conversion. Supplier and fixture prices are per sales unit.

The screenshot arithmetic is exactly reproduced by the authored fixture: **400×€8.91 =€3,564; 300×€3.87 =€1,161; subtotal €4,725**. Against a customer budget of **€101,000**, the remaining budget is **€96,275**. The separate configured **€2,500 per-order purchasing-policy limit** legitimately blocks that basket; increasing the customer's budget does not grant purchasing authority. The configured **€6,000 cumulative allowance** is a different rule and only blocks when prior spend plus this basket exceeds it. Neither limit was enlarged, disabled or reset. The warning now distinguishes the two policy reasons from a true customer-budget shortfall.

A bounded authorized supplier read on 15 November for delivery 17 November returned current tax-inclusive catalog prices **€3.75 /€1.86**, independently yielding **€1,500 +€558 =€2,058** for those quantities. These are dated sandbox/customer-context observations, not promises of historical or future prices. Both returned `error=false`, EUR and price-validity evidence; butter `netPriceFound=false` does not erase its returned catalog price. The supplier's separately rounded butter comparison figure (€7.49/kg) must not replace the exact sales-price arithmetic (€3.75÷0.5kg =€7.50/kg). Stock/cutoff, tax, price validity, approval and freshness remain separate checks before any review. No confirmation or reservation was performed.

Audit evidence is private in `.local/screenshot-financial-audit.json`; it contains no API headers. A narrow authored-fixture correction reconciles its net-price evidence with its stable gross price using the row's declared tax rate, preserving legacy fixture prices. `.venv/bin/python -m pytest tests/test_financial_audit.py -q --tb=short` passed **8 tests in 5.50s**: the actual screenshot quantities/totals, distinct per-order/cumulative/customer-budget boundaries, four declared tax rates and unchanged legacy pricing. This targeted pass is not the final combined regression result. Current supplier prices are deliberately not frozen as permanent expected prices.
