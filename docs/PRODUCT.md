# A4TB · Valio Aimo — product

A professional kitchen describes a purchasing need, compares actual catalog products and reviews a priced basket. The receiving gateway checks product evidence, quantities, delivery and authority before recording a simulated order. The purpose is to reduce repeated searching and calculation while keeping consequential choices understandable.

## Current customer experience

**Smart order** is the main workflow. It accepts multiple measured products or the supported bolognese meal example, retains the conversation and cart, presents product choices and supports quantity, search, budget and date changes. The customer reviews whole-pack surplus and a tax-inclusive item subtotal. Missing evidence and unresolved products keep the basket incomplete.

**Meal planner** supports an editable bolognese/lentil recipe, proposed/customer-entered quantity labels and four disjoint dietary cohorts. The exact saved ingredients and selections transfer into the same quotation workflow. Recipe acknowledgement records the customer's review; it does not certify a product or recipe.

**Trust scenarios** preserves the original milk-agent demonstration: an attractive shortcut is blocked, a permitted exception needs exact separate approval, and stale facts require a new decision. The original decision recorder and external buyer client remain useful evidence of that authority boundary.

The deployed extension adds required versus preferred brand/origin/organic handling, bounded semantic query expansion and supplier-linked alternatives, stock classifications, exact basket-cost comparisons, richer product evidence and complete receipt details. Private accounts/Remember Me, saved preferences, editable local speech/OCR and combined input are also deployed. The final suite passed 171 tests, hosted verification passed 47 checks and restart recovery passed 13 checks; actual browser scope is in the [acceptance record](ACCEPTANCE_RECORD.md).

## Customer evidence and hypothesis

Published Valio Aimo customer stories describe contract products in Aromi, chef-defined assortments and continuity during outages. Minun Aimo already supports recipe import and recipe-to-cart ordering. Our opportunity is trusted execution within that existing purchasing relationship, not a claim that the current webshop is broken. The user-supplied worker conversation emphasized meal-to-ingredient selection, dietary portions, sourcing, price/quality trade-offs and configurable spend authority.

Sources and their limits are in [customer discovery](../research/CUSTOMER_DISCOVERY.md), [challenge research](../research/CHALLENGE_RESEARCH.md) and [worker follow-up](INTERVIEW_GAPS.md). No measured savings or independent customer validation is claimed. The hotel, mandate, budgets and approver identities are authored examples.

## Decisions that make trust visible

- Model output proposes requirements and related searches; server code owns product validation, arithmetic, approval and commitment. Related search results are actual catalog IDs, and a semantic or supplier-linked replacement needs an explicit customer choice.
- Hard dietary, origin, brand and supported specification rules remain hard. Soft preferences affect comparison and ranking; they never override a hard failure. “Quality” leads to review of supplied specifications rather than an invented score.
- Shared SKUs are aggregated before sealed-pack and lot rounding. The customer sees required quantity, ordered quantity and surplus. Comparison deltas use the affected basket cost, including shared-product rounding.
- Price and availability are customer/date-specific evidence, not reservations or guarantees. Unknown dietary evidence, conversion conflicts, unsupported charges and unknown supplier quantities remain visible.
- A complete draft may be within the buyer's configured authority or require a separately authenticated customer manager. Approval binds the exact basket and expires with its quote; changed facts require fresh checks.
- Confirmation is idempotent and atomic against shared synthetic spending. A receipt records the simulator's items, requested date, subtotal and approval; it is not an invoice, supplier confirmation or delivery booking.
- Source remains private. Restricted datasets and credentials remain outside Git and public frontend assets. The deployed service supports shared private codes and invitation-gated private accounts with separate manager authorization.

## Challenge alignment

| Need | Product mechanism | Verification location |
| --- | --- | --- |
| Product, price and availability lookup | Static catalog search followed by a bounded authenticated Valio shortlist | `product_facts.py`, `upstream.py`, procurement tests and hosted smoke report |
| Inquiry to order | Typed request, persistent draft, complete basket review and simulated receipt | `procurement.py`, `procurement_contract.py`, Smart order |
| Authority and human approval | Server-owned roles, hard constraints, exact separate approval and shared spending | Policy/store code, gateway and procurement tests |
| Exception recovery | Quantity/budget/date/product edits, explicit alternatives, fresh quotation, retry-safe receipts | Smart order and retained Trust scenarios |
| Inspectable interface | Versioned HTTP/OpenAPI with validated response models and independent client | `/openapi.json`, contract tests, `agent_client.py` |

The recorded official rubric is end-to-end 30%, user need 20%, autonomy/controls 20%, robustness 15%, openness/credible path 15%. Earlier authenticated research and later reread limits remain recorded in [rule checks](evidence/RULES_RECHECK.md); no eligibility or prize outcome is promised.

## Scope and production path

The supported prototype is a general measured-product basket plus a reviewable foodservice exemplar. Unknown data can prevent a particular recipe or product from being confirmed. The local parser is deliberately bounded; NVIDIA semantic expansion does not claim universal understanding. The hosted service is single-writer persistent SQLite, with an existing TLS-verified PostgreSQL option for local use.

A supplier order/reservation contract, real organization identity, broader recipe import, customer self-service policy management and distributed operations are production extensions. They are not prerequisites for the expressly authorized simulated challenge workflow. No real purchase, invoice, payment or final Junction submission is performed.

## Historical concept exploration

The initial milk slice selected **Rewind & Repair** after comparing a menu substitution studio, replenishment radar, procurement passport and an agent-courtroom presentation. The choice prioritized an executable permission boundary supported by the available APIs. Smart order now extends that boundary to the broader purchasing brief while retaining the original demonstration. Existing milk pitch/video files are secondary trust artifacts, not a recording of the final generic-cart journey.
