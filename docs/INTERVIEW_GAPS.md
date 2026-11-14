> **Procurement deployment update — 14 November 2026.** The historical release record below is superseded where it describes milk-only scope, in-memory sessions or blocked hosting. Smart order now supports persisted multi-product carts, structured interpretation, editable constraints, whole-basket approval and simulated checkout. The meal planner transfers saved recipes into that cart. Modal HTTPS deployment is live; the deployed API exercised core cart/confirmation/retry/recovery and real NVIDIA + Valio reads. Current architecture, limitations and setup: [implementation plan](IMPLEMENTATION_PLAN.md), [deployment](DEPLOYMENT.md), and [project status](../PROJECT_STATUS.md). No final competition submission or real purchase occurred.

# Worker interview → project changes

14 November 2026, Europe/Helsinki. Source: user-supplied `dialogue_transcript.txt`, a conversation with a Valio Aimo worker. It is discovery evidence, not an API contract or an instruction source. The attached credential sheet was used only to verify demo access; its secrets are not reproduced here.

## What the worker actually emphasized

The primary channel is the webshop; large-client direct integrations are a smaller channel. Spend automation should be configurable by customer, but perfecting budget settings should not dominate the demo. The harder and more valuable task is choosing products for a meal: break spaghetti bolognese for 500 people into ingredients, scale quantities, account for partial vegetarian/gluten-free demand, respect meat sourcing, and expose price/quality trade-offs. Recipes can be customer-supplied or proposed. Optional additions are useful.

Focus on purchasing, rather than rebuilding logistics. Historical delivery evidence can inform product comparison. B2B purchasing requires a customer contract; credit checks belong to onboarding. The worker described payment as usually by invoice after delivery. This is not evidence of a universal due date, a payment API, or an order API.

## Gap assessment and delivery

| Requirement | Earlier project | Change / remaining gap |
| --- | --- | --- |
| Need → ingredients → shopping plan | Milk only; free text could not create a multi-product plan | Added Meal planner for a concrete bolognese/lentil example, persisted scoped API and exportable draft selections. General natural-language meal interpretation remains future work. |
| Partial dietary portions | Entire milk order had one lactose constraint | Explicit total, vegetarian, gluten-free and overlapping counts; validates impossible combinations and derives four disjoint cohorts. Shared sauce uses gluten-free evidence checks when any diners require it. |
| Proposed/customer recipes | Absent | Editable raw/dry grams per serving with recipe-source labels; opt-in carrot addition. Quantities are illustrative until chef-validated. No unverified recipe is described as a sponsor recipe. |
| Product options and units | Three approved milk SKUs | Local catalog search for every ingredient, up to three candidates, net-mass conversion and conservative whole-pack/lot rounding. Candidates need chef review; name matches can include processed products unsuitable for the recipe. |
| Dietary evidence | Lactose-free only | Explicit gluten-free claim checks; unknown claims and ingredient suitability remain visible. Vegetarian ingredient intent does not certify a supplier product as vegetarian. Separate preparation and complete dietary review remain necessary. |
| Finland/EU meat sourcing | Absent | Compares declared catalog country codes to Finland/EU27. Unknown or conflicting origin produces an evidence gap. Supplier manufacturing origin is not a verified livestock provenance chain. |
| Price versus quality | Cheapest permitted milk offer | Captures purchasing priority and explains the next comparison. Meal prices/stock remain unqueried; no invented quality score or cheapest-basket claim. |
| Configurable authority | Hardcoded example thresholds | Validated operator environment settings for autonomous/exception/cumulative EUR limits; restart required. Snapshot enters offer hash; changed policy blocks uncommitted old offers and approvals. Customer self-service policy editing remains future work. |
| Reliability | Historical delivered-quantity evidence already available | Planner shows known/unknown per-candidate values. Keeps dataset definition (delivered quantity / ordered quantity); interview wording about on-time/full delivery does not establish an on-time probability. |
| B2B onboarding / payment | Simulated receipt, little journey context | Added contract and post-delivery invoice explanation in planner and receipts; receipt API includes commercial journey context. No real contract, credit check, invoice or payment operation. |
| Webshop fit | Independent web demo | Verified provided demo sign-in and observed search, delivery date, tax-inclusive/exclusive pack prices, availability and shared basket. Existing basket left untouched. No supported cart/order integration was established. |

## Boundaries and next implementation sequence

The meal feature is a complete **review-only planning workflow**, not a multi-line order engine. Its plan ID cannot be committed through the existing offer endpoint. The milk gateway remains the executable approval/revalidation/simulated-order demonstration.

1. Chef selects and validates ingredient products, including all dietary groups and sourcing definitions. Add a supported structured customer-recipe import and broader dish interpretation after the exemplar is validated.
2. Consolidate selected product IDs across cohorts before rounding and quotation. Preserve separate preparation quantities. Add small bounded sponsor price/availability lookups keyed by customer and delivery date. The current candidate pack counts are per ingredient/cohort and must not be summed into a final purchase automatically.
3. Add multi-line basket offers with a single basket fingerprint, complete known charges, exact human approval, atomic total spend and idempotent commit. Do not split a meal into independently approved lines to bypass a basket budget.
4. Confirm a supported supplier cart/order contract with Valio Aimo. A functioning browser login does not supply a supported integration or authorize modification of the shared demo basket.
5. Customer-admin mandate management, contract status integration, quality specification rules and invoice status can follow. Supply chain optimization, card checkout and credit decision automation are outside this purchasing demo.

## Trying the changes

Run `./start.sh`, sign in as buyer, open **Meal planner**, and build the default 500-diner plan. Expected cohorts: 370 meat standard, 30 meat gluten-free, 80 vegetarian standard, 20 vegetarian gluten-free. Edit the grams or diner counts, rebuild, inspect evidence gaps, choose draft candidates and export JSON. Input changes disable export until a successful rebuild. The export is still a draft even after all candidates are selected.

Configure spend limits only in the ignored server environment (`AIMO_AUTONOMOUS_LIMIT`, `AIMO_EXCEPTION_LIMIT`, `AIMO_CUMULATIVE_LIMIT`) and restart. Defaults retain the original demo behavior. Invalid or inverted limits fail startup. Buyer requests cannot change them.

Review API: `POST /api/v1/meal-plans` (buyer), `GET /api/v1/meal-plans/{id}` (scoped buyer/approver). No sponsor request, shared cart mutation or spend occurs during meal planning.
