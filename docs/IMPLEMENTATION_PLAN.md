# Procurement delivery plan and acceptance record

Reviewed 14 November 2026 (Europe/Helsinki). This plan extends the retained milk trust demonstration into the requested purchasing workflow. The extended public A4TB release is deployed and verified: 171 backend tests, production build, 47 hosted checks, 13 restart checks and scoped interactive browser journeys passed. [ACCEPTANCE_RECORD.md](ACCEPTANCE_RECORD.md) records the exact evidence and limits.

## Repository assessment

| Area | Evidence and finding | Decision |
|---|---|---|
| Architecture | `backend/app.py`, `policy.py`, `store.py`: FastAPI modular monolith, React client, transactional receipt ledger | Retain working gateway and generic JSON persistence |
| Stack | React 19/TypeScript/Vite; Python/FastAPI/Pydantic; Decimal; PostgreSQL or SQLite | Suitable for typed AI tools and reliable arithmetic |
| Implemented before this update | Three-SKU milk mandate, NVIDIA shortlist, Valio price/availability reads, exact approval, stale repair, idempotency, audit; review-only meal planning | Keep all existing routes and scenarios |
| Missing before this update | Free text could not author a multi-item cart; no generic priced cart, saved conversation, basket approval or checkout | Add isolated generic procurement module and primary Smart order UI |
| Technical limitations found in audit | Earlier in-memory login/rate counters; private restricted catalog; incomplete package/dietary facts; static demo identity | Login hashes are now persisted; keep one hosting writer and unknown hard facts. Authentication throttles, private accounts and Remember Me are now persisted; general business rate counters remain process-local and real supplier identity is outside the simulator |
| Bugs/inconsistencies found | Meal cohorts rounded separately; ambiguous dietary overlap; sales-unit versus dimensional price limits; repeated query line IDs; post-refresh retry keys | Aggregate before rounding; explicit overlap; dimensional limits; distinct cohort identities; durable retry keys and read-only receipt verification |
| Reusable components | Auth, store transactions, sponsor clients, static catalog, visual system, milk policy/tests | Preserve rather than rebuild |
| Improvements | Generic metadata/conversions; persisted versioned carts; structured interpretation; customer controls; aggregate approval; explicit preference/discovery/comparison contracts | Implemented and deployed in separate modules; the acceptance record distinguishes final runtime/browser evidence from historical results |
| Demo risks | Sponsor outages, missing product claims, proposed recipe safety, cold starts, quote expiry, synthetic spending cap | Label fixtures and unknowns; error recovery; refresh exact quote; rehearse complete supported cart |

## Stack decision

| Option | Compatibility | Tradeoff | Decision |
|---|---|---|---|
| Existing React + FastAPI | Reuses all working UI, Python policy and provider clients | Two build toolchains, one deployment | Selected |
| Next.js + TypeScript server | Good integrated UI | Rewrites working Python gateway and monetary policy | No demonstrated benefit |
| ASP.NET Core | Strong validation and transactions | New stack and integration rewrite under event constraints | Defer |
| Aiven PostgreSQL | Existing TLS-verified service, shared ledger concurrency | Hosting requires restricted static egress; never open allowlist broadly | Retain local integration |
| SQLite + Modal private volume | Small single-instance demo, transactional, no new database egress | Must have exactly one writer and persist before mutation response; no horizontal scaling | Hosted demo path |
| Sites/Workers | Available website hosting tooling | Worker runtime cannot directly run existing FastAPI/TCP PostgreSQL | Use as public branded proxy; retain sponsor-compatible Python backend |

## Source of truth and model boundaries

The 17,546-record challenge catalog establishes identity and structured specifications. It does not establish current availability. Authorized sandbox price/availability endpoints establish customer/date-specific synthetic commercial facts. Fixture mode supplies visibly authored test prices/stock and is never a network fallback. Public webshop research is contextual only. Historical delivery ratio is quantity delivered divided by quantity ordered, not an on-time probability. Carbon is a category estimate per kg. All four original raw-file SHA-256 values are checked before private hosting upload.

`product_facts.py` retains nullable brand/manufacturer/category, ingredients/allergens, origin, storage, timestamps, sales/base units, fixed net mass/volume and provenance. The public response exposes a safe product-details subset for customer inspection. Missing dietary claims, deposits, variable weight, inconsistent units and unknown terminal stock prevent confirmation. Exact SKU, lexical/category matches, bounded model-proposed semantic query expansions and supplier substitution links discover actual catalog IDs. A semantic or supplier-linked replacement needs explicit choice and all hard checks. Ranking is not proof of suitability. No unsupported density conversion is performed.

`interpretation.py` uses a validated NVIDIA tool output when selected, or an explicitly identified local structured parser. Model selection is independent of live versus fixture price/stock mode. It proposes requirements and related search terms only; it cannot approve, calculate authoritative totals, modify spend or execute orders. Required brand/origin/organic fields remain separate from soft preferences. Quality means review of available specifications, not an invented quality score. The local parser supports measured lists, dimensional price limits and common follow-ups; unsupported interpretations become visible questions. Bolognese amounts are illustrative chef-review assumptions, never an official recipe. Materially overlapping percentages require clarification; explicit disjoint groups do not need a redundant overlap question. The existing Meal planner remains the editable detailed recipe tool.

`procurement_contract.py` defines validated public session, candidate, cart, clarification, policy, offer, receipt and verification schemas. It preserves decimal-string amounts and nullable unknowns, rejects malformed successful responses and documents them through OpenAPI. Candidate price-per-unit and basket-delta semantics distinguish comparison information from a final commercial charge.

## Customer journey and workflows

| Stage / customer action | API and backend | State, validation and recovery |
|---|---|---|
| Open / sign in | `/session`; separate buyer and approver codes | Hashed, expiring sessions stored server-side; logout persists revocation; no frontend credentials |
| Describe products or supported meal | POST `/procurement/sessions` | Stores original request; schema-validates extracted items, hard diets, quantity/unit, budget, date and preference; unknown intent asks for clarification |
| Discover / rank | Generic local catalog search plus bounded sponsor reads | Exact/lexical/category/semantic-expanded/supplier-linked candidates; explicit hard rules and soft preferences; exact/ambiguous/conflict/out-of-stock/not-found classifications with issue codes |
| Resolve ambiguity / substitute | POST `/{id}/actions` select_product | Real candidate IDs only; preserves unaffected lines; unknown evidence remains blocked |
| Edit quantities / remove | Actions set_quantity/remove_line | Positive quantities, lot steps and dimensions; duplicate SKU requirements aggregate before rounding and stock allocation |
| Change budget or deadline | Actions set_budget/set_date or message | Recalculates whole basket; hard budget cannot be waived by manager; invalid dates remain questions |
| Shortage / delivery / diet failure | Candidate issues and clarification questions | Show verified quantity/date or unknown; user explicitly changes requirement/product or removes line; no silent relaxation |
| Refresh quote | Action quote | New fingerprint; old approvals invalid; no silent replacement; controlled errors retain prior saved state |
| Review recipe | Action acknowledge_recipe | Records explicit chef review acknowledgement; never certifies allergen safety |
| Review complete basket | Server cart subtotal, constraints, candidate evidence and comparison deltas | Partial cart never ready; shared-SKU rounding enters alternative cost impact; unknown shipping/service charges disclosed; confirmation limited to item-price simulation |
| Internal authorization | POST `/{id}/approve` | Separate customer manager identity, exact unexpired basket fingerprint; customer confirmation remains separate |
| Confirm | POST `/{id}/confirm`, Idempotency-Key | Rechecks SKU price/stock/date/conversions; freezes cart with compare-and-swap; atomic shared cap and unique receipt; retries reuse original key |
| Result / recovery | GET session and `/{id}/verify` | Truthful simulated items/date/subtotal/approval/next steps, consistency check; saved cart survives refresh; concurrent update returns 409 and reloads current version |

The original milk `/runs`, `/offers` and `/receipts` workflows continue under their original three-SKU mandate. The general customer-confirmed basket has a separate authored assortment policy and never widens autonomous milk authority.

## Implementation sequence and acceptance gates

1. **Audit / research:** repository evidence above; existing challenge research, dataset profiles and read-only webshop access record retained. No new webshop or production-cart writes.
2. **Generic engine:** typed requirements, catalog facts, conversions, versioned state and classification. Gate: measured multi-item input; exact quantities; no omitted unresolved lines; conservative diets.
3. **Cart / approval / simulation:** single basket fingerprint, fresh checks and atomic cents. Gate: known package round-up; duplicate SKU allocation; budget/stock/date failure; exact separate approval; one receipt on retries and concurrent updates.
4. **Customer UI:** Smart order primary; real choices; edits; constraints; sources; receipt. Gate: browser journey through request, follow-up, confirmation, reload and verification; desktop/mobile rendering.
5. **Hosting:** Modal private source/image and volumes; server-only keys; single writer; credit guardrails. Gate: HTTPS health, authentication, catalog matching, saved state, live sponsor/AI read, simulated checkout and deployed UI checks.
6. **Delivery:** private source scan, original hashes, commit/push, accurate docs and URL. Gate: no secrets/data staged; no real purchases/payments; no competition submission.

## Current release verification

The next gate is the root's final full backend suite, production build, deployment, hosted HTTP/OpenAPI and desktop/mobile browser checks for the changed revision, followed by the private-source scan and commit/push. [ACCEPTANCE_RECORD.md](ACCEPTANCE_RECORD.md) maps the original requirements to source and executed evidence. Any newly found derived-quantity or persisted-state compatibility failure must be fixed and rechecked before deployment.

## Supported scope and production extensions

The original brief requires grounded semantic discovery; it does not prescribe an embedding index. The implemented semantic query-expansion path is bounded and catalog-grounded. The supported foodservice exemplar is a reviewable bolognese/lentil plan; the brief does not require universal recipe generation or independent allergen certification. Unknown supplier evidence is an honest blocker rather than permission to invent facts.

Broader recipe import, organization identity federation, customer-admin policy editing, distributed limits and horizontal scaling are future/production work. A real supplier order/reservation integration depends on an authorized supported contract; the brief explicitly permits a clearly labelled simulated workflow when it is unavailable. These are disclosed scope limits, not self-imposed gates that replace the requested challenge acceptance criteria. Current source and deployed behavior must still prove every essential workflow before the goal is marked complete.
