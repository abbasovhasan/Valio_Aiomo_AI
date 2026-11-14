# A4TB · Valio Aimo — project status

14 November 2026, Europe/Helsinki. Open **[A4TB · Valio Aimo](https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site)**. The public Sites address proxies the React/FastAPI application on Modal. Buyer and approver access remains protected by separate private codes; the GitHub repository remains private.

## Current implementation

- **Smart order:** natural-language multi-product requests, actual catalog candidates, explicit dietary/origin constraints, dimensional pack conversion, package surplus, customer budget and delivery controls, persistent conversation/cart recovery, and versioned edits. Cheaper-product follow-ups preserve unrelated choices. Ingredient search changes preserve the line's hard requirements.
- **Meal planner:** editable recipe grams, customer/proposed source, overlapping dietary cohorts, sourcing preferences and draft export. A saved plan transfers its exact quantities, source and chosen products into Smart order. Shared SKUs are consolidated before whole-pack rounding. Fresh recipe acknowledgement and all hard checks are required before confirmation.
- **Product evidence:** shared purpose ranking prioritizes raw ingredients over prepared foods. Missing dietary evidence stays unknown. Contradictory package records, including the butter multipack mass conflict found during QA, block unsupported conversion.
- **Trust and confirmation:** separate customer-confirmed basket policy and original milk-agent mandate; exact separately authenticated manager approval; fresh price/stock/date revalidation; atomic shared synthetic spend; idempotent simulated orders and read-only receipt verification. A changed quote needs new approval.
- **Hosted storage:** private Modal volumes hold the restricted catalog and persistent SQLite sessions, carts, approvals, receipts and synthetic spending. The deployment is deliberately single-writer. The existing Aiven PostgreSQL integration remains available locally; its network allowlist was not widened for hosting.
- **Integrations:** actual deployed Valio sandbox price/availability reads and NVIDIA typed interpretation were tested successfully. Provider failures remain visible; authored fixture prices/stock and the local parser are explicitly selected alternatives.

## Verification and remaining limits

**Latest verification:** 89 backend tests passed in 16.12 seconds, with one existing Starlette/httpx deprecation warning. The frontend production build passed. All 14 real HTTP checks through the public Sites URL passed, covering authentication, multi-product follow-up/budget changes, stale-version rejection, fresh simulated confirmation, idempotency, receipt verification/state recovery and live NVIDIA/Valio integration. The public landing page and browser title were observed. The final hosted browser title, A4TB navigation branding and footer were verified after redeployment; broader challenge completion is not claimed.

The implementation still uses a synthetic customer policy and restricted challenge data. Unknown product evidence, unsupported deposits/variable-weight charges and unavailable delivery facts can block a basket. Delivery/service fees are excluded from the item-price simulation. Identity federation, horizontal scaling and a supported supplier order contract are not delivered. Current sponsored-credit consumption and remaining balances require the service dashboard; no current balance is asserted here.

All confirmations are **simulated orders only**. This work created no real supplier order, stock reservation, invoice or payment and performed no final Junction submission. The last observed competition entry was Draft; final submission remains the owner's action.

See [deployment and operating limits](docs/DEPLOYMENT.md), [demonstration guide](docs/DEMO.md), [implementation plan](docs/IMPLEMENTATION_PLAN.md) and [delivery record](docs/DELIVERY.md). Credentials, restricted datasets and raw runtime evidence remain outside Git and public frontend assets.
