# Worker interview → current procurement scope

14 November 2026, Europe/Helsinki. The user-supplied `dialogue_transcript.txt` is discovery evidence, not an API contract. An attached credential sheet was used only for authorized demo access; credentials are not reproduced here.

The worker emphasized meal-to-ingredient selection, dietary portions, sourcing, price/quality trade-offs and configurable customer spend authority. Webshop ordering is the primary channel; direct large-customer integrations are smaller. Purchasing should remain the focus. B2B onboarding requires a contract; the worker described invoicing after delivery, which does not establish universal payment terms or authorize invoice/payment automation.

## Requirement and current implementation

| Worker need | Current source and prior delivered baseline | Limit or next verification |
| --- | --- | --- |
| Need → ingredients → shopping basket | Supported bolognese/lentil example, editable grams, persisted meal plan and exact bridge to Smart order quotation | Proposed amounts require chef review; broader arbitrary recipe import is a future extension |
| Partial dietary portions | Total, vegetarian, gluten-free and overlap counts derive four disjoint cohorts; conversational overlap and inline input preserve the recipe | Final changed browser path pending; explicit group allocations should not trigger redundant overlap questions |
| Supplied versus proposed recipe | Source labels and editable customer-entered quantities are retained in the quoted basket | Customer-entered does not mean independently verified; no official recipe claim |
| Appropriate ingredient products | Shared ingredient-purpose ranking, actual catalog IDs, pack conversions and source evidence | Chef must review purpose and separate preparation; missing claims remain unknown |
| Finnish/EU sourcing | Required origin remains a hard catalog check; new soft-origin preference affects comparison/ranking | Country declarations are not a verified livestock provenance chain; final changed release pending |
| Price versus quality | Whole-pack quotation, per-requested-unit prices, exact affected-basket deltas and supplied product specifications | No verified quality score exists; quality preference keeps the meaningful product review with the customer |
| Brand and organic choice | Current source separates required versus preferred catalog brands and organic labels | Organic proof uses explicit catalog labels, not the word in a product name; final integrated release pending |
| Configurable spend authority | Validated operator settings for autonomous/exception/cumulative EUR limits; policy snapshots invalidate old offers | Customer self-service editing is optional future work; buyer text cannot alter authority |
| Historical delivery evidence | Supplied delivered/ordered quantity ratio with unknown coverage preserved | Not an on-time probability or future delivery guarantee |
| Contract and payment context | Simulator receipt and planner explain real contracts and invoice-after-delivery context | No actual contract, credit check, supplier invoice or payment operation |
| Fit with the webshop | Authorized read-only sign-in, search, date, pack/tax-price, availability and shared-basket observations recorded | Existing shared basket remained untouched; UI login does not provide a supported cart/order contract |

## Quotation and trust boundary

Meal planning itself remains review-only and makes no supplier request or commitment. **Quote this shopping plan** creates a separate scoped procurement session with the saved quantities and choices. It obtains bounded date-specific prices/availability and consolidates shared SKUs before rounding. Recipe acknowledgement, all hard requirements, a complete quoted basket and any exact separate approval are required for simulated confirmation. A plan ID is never directly committed through a milk offer endpoint.

The generic basket uses a separate authored customer-confirmed policy and does not broaden the original milk agent's approved assortment. A customer manager can approve an eligible exact spend exception; approval cannot waive diet, stock, unknown package facts or delivery failures.

Current continuation tests and final release gates are tracked in [ACCEPTANCE_RECORD.md](ACCEPTANCE_RECORD.md). The changed source must pass the root's final full suite, build, hosted and browser checks before it is described as a verified deployed revision.

## Try the supported example

Open **Meal planner** and build the default 500-diner plan: 370 meat standard, 30 meat gluten-free, 80 vegetarian standard, 20 vegetarian gluten-free. Edit grams or counts, rebuild and inspect actual product evidence. Select products, set the requested delivery date and use **Quote this shopping plan**. Smart order carries the saved plan into the priced workflow; unknown facts remain visible blockers. The draft export remains a draft.

For natural language, try the **Bolognese for 500 diners** example in Smart order. Materially ambiguous percentages need an overlap answer. Explicit disjoint serving counts do not need an additional assumption about overlap.

## Production extensions

A broader recipe importer, customer-admin mandates, supplier order/reservation integration, contract status and invoice status need separate design or supported contracts. Organization identity and distributed operations belong to a production rollout. None is a reason to pretend unsupported supplier facts exist or to withhold the permitted simulated challenge journey.

## Historical milestone

The interview update originally delivered a review-only planner while only the milk offer could be committed. The subsequent multi-product basket, saved-plan quotation bridge, exact basket approval and simulator supersede that limitation. Historical notes about summing per-cohort packs or missing multi-line quotation do not describe the current source.
