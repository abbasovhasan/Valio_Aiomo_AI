# Aimo Order Desk

An external buyer agent can find an offer. The receiving gateway decides whether it may become an order. Aimo Order Desk makes that boundary visible and testable.

## Hero concept: Rewind & Repair

A hotel needs at least 1,000 litres of lactose-free breakfast milk for a specific date. The agent searches a small shortlist, obtains date-specific price and availability evidence, and proposes an offer. The desk shows which checks passed, which failed, and the permitted next action. A cheap but unsuitable shortcut is blocked. A permitted budget exception goes to a separately authenticated approver. A valid offer produces one explicitly simulated order, even if the client retries.

The decision recorder lets a reviewer inspect the evidence behind the boundary. Revalidation treats changed quantities, date, basket, price or expiry as a new decision. The interface is a purchasing workbench rather than a conversation transcript.

Two supporting ideas serve this one concept: an executable purchasing mandate and a decision receipt that an independent HTTP client can inspect. There is no invented marketplace, payment system, blockchain or separate agent theatre.

## Brief concept comparison

Exploration was deliberately bounded before implementation. High/medium/low are qualitative design judgments, not user research results.

| Direction | Challenge fit | Buyer value | Two-minute payoff | Data support | Implementation risk |
| --- | --- | --- | --- | --- | --- |
| Rewind & Repair, selected | High: inquiry, permissions and order | Shows an actionable recovery | Block, repair, receipt | Strong: catalog + dynamic APIs | Medium: exact approvals and transactions |
| Menu substitution studio | Medium: more recipe work than authority | Useful to chefs | Attractive meal comparison | Weak: no supplied recipes/inventory | High: dietary and recipe inference |
| Autonomous replenishment radar | Medium | Anticipates shortages | Compelling alerts | Weak: no stock or order history | High: would need authored predictions |
| Procurement passport | High | Portable authority and receipts | Strong technical proof | Strong for contracts | Medium: risks a technical-only demo |
| Unconventional: agent courtroom | High for controls | Makes failure legible | Agent proposal cross-examined by rules | Strong | Medium: spectacle could obscure ordering |

Rewind & Repair keeps the memorable part of the courtroom idea while giving the buyer a real next action. The selected concept is authored product design, not an official Valio Aimo product.

## Customer evidence and hypothesis

Valio Aimo's published customer interviews describe contract products in Aromi, chef-defined assortments, and a need for continuity during outages. Its existing Minun Aimo product already supports recipe import, margin calculation and recipe-to-cart ordering. The opportunity tested here is delegated execution on top of a functioning purchasing service.

Sources and distinctions are recorded in [CUSTOMER_DISCOVERY.md](../research/CUSTOMER_DISCOVERY.md). We conducted no customer interviews and measured no labour or cost savings. The hotel persona, buyer mandate, budgets, approver and failure scenarios are synthetic examples. The hypothesis is that explicit constraints plus a focused approval handoff let a buyer delegate useful work without repeating every check.

## Requirements mapping

The recorded Valio challenge rubric is end-to-end 30%, user need 20%, autonomy/controls 20%, robustness 15%, and openness/credible path 15%. The authenticated challenge page could not be independently reread in this build session; see [current rule checks](evidence/RULES_RECHECK.md).

| Requirement | Product evidence |
| --- | --- |
| Structured product/price/availability lookup | Search static catalog first; dynamic calls for a bounded shortlist, with dates and provenance |
| Inquiry-to-order interaction | Typed request, offer, policy outcome and persisted simulated receipt |
| Permissions and human approval | Buyer/customer scope, server-owned roles, independent approver and exact offer binding |
| Robustness | Labelled failure rehearsals, invalid dietary choices, fresh evidence, duplicates and cumulative-cap concurrency |
| Open interface | Versioned FastAPI/OpenAPI contract and an independent agent client |

## Design decisions

- The model proposes through tools; deterministic gateway code owns authority and commitment.
- The three outcomes are within mandate, approvable exception and invalid. Human approval cannot waive hard dietary or dimensional rules.
- Money uses decimal arithmetic. Sales packs and lot sizes determine effective quantity. Litres and kilograms are different dimensions.
- A price or stock lookup is evidence at a moment in time, never a reservation or delivery guarantee.
- Live sponsor sandbox data, recorded responses and controlled fixtures have distinct labels. Upstream failure cannot silently become a successful live run.
- Supplier text is untrusted product data. It cannot change policy, roles or privileged operations.
- Receipts record factual checks and concise reasons. They do not expose private model reasoning or imply independently measured product truth.
- Source stays private. Restricted challenge data remains excluded from Git and public artifacts.

## Scope and credible next step

The prototype focuses on a narrow milk procurement task. It is not production food-safety advice, a complete wholesaler ordering system or an integration with a real customer account. Production work needs a supplier order/reservation contract, organizational identity and authorization, customer-specific mandates, operational monitoring, retention controls, and customer validation. The next useful field study is a walkthrough of one recent order correction with a buyer and the actual approver.
