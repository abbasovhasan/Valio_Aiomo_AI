Valio Aimo customer discovery — 14 November 2026

**Decision.** Focus the prototype on a hotel-group buyer delegating a purchase within a chef-approved assortment, with explicit handling of an exception. The wholesaler can verify the buyer agent's authority and expose appropriate product, fixed-price, and availability information through an open interface. This is a proposed solution to the published challenge, informed by real customer workflows. It has not yet been validated through our own customer interviews.

**Published customer evidence.**

| Evidence | What we learned | Implication for our hypothesis |
| --- | --- | --- |
| Valio Aimo's September 2026 customer interviews | Kasperitalo uses Aromi with contract products. Wilderness Hotels uses a chef-defined assortment. Caffitella values continuity during system outages. | Fit existing customer systems, preserve purchasing policy, and make interruptions recoverable. |
| January 2026 product article reporting customer interviews | Recipes had been scattered across documents. Minun Aimo now supports AI-assisted recipe import, margin calculation, and recipe-to-cart ordering. | Treat these as existing capabilities rather than presenting a replacement recipe assistant as the innovation. |
| Arto Rastas customer story, September 2023 | Ingredient cost and staff hours matter to the economics of lunch service. | Measure purchase cost and human effort while preserving product suitability. |
| Current customer acquisition page, reporting an autumn 2025 survey of 141 people | Valio reports that 88% found ordering easy and 84% rated delivery reliability good. | Avoid claiming the current webshop is generally broken. These are company-published survey results, not our research. |
| Delivery-wholesale product page | Current capabilities include multiple baskets, amendments to confirmed orders, and visible product, availability, sales-unit and price information. | The challenge concerns trusted execution by an external agent on top of a functioning human service. |
| Click-and-collect instructions | A product can become unavailable during picking. | Availability can change. This is evidence for that specific service; do not assume its rules apply unchanged to delivery wholesale. |

Sources: [customer interviews](https://www.valioaimo.fi/artikkelit/pinnalla-nyt/gallup-mita-digipalveluita-hyodynnat/), [recipe service](https://www.valioaimo.fi/artikkelit/pinnalla-nyt/reseptisi-ja-katelaskenta-minun-aimossa/), [Arto Rastas](https://www.valioaimo.fi/artikkelit/asiakastarinat/arto-rastas-ja-lounaan-uudet-tuulet/), [survey](https://www.valioaimo.fi/asiakkaaksi/), [delivery wholesale](https://www.valioaimo.fi/asiakkaaksi/toimitustukku/), [click-and-collect](https://www.valioaimo.fi/asiakkaaksi/pikatukut/tilaa-nouda-ohje/).

These are customer statements and operational descriptions published by Valio Aimo. They establish useful workflows, not the frequency or severity of an unserved need. An October 2026 University of Eastern Finland account of a study interviewing 25 restaurant entrepreneurs also identifies ingredient and staffing costs as pressures. That is industry context, not evidence that those respondents need an autonomous purchasing agent. [University research account](https://www.uef.fi/fi/artikkeli/tutkimuksessa-selvitettiin-miten-yrittajat-kokevat-ravintola-alan-haasteet-ravintolan-pahin)

**The two problems we must connect.**

The kitchen's proposed job to be done: “Fulfil the purchasing need for the planned service, using suitable products and our commercial rules, with human attention concentrated on decisions that need it.” Contract assortment, price, quantity, and delivery date constrain the decision. A cheap but unsuitable or late product does not fulfil the need.

Valio Aimo's stated challenge: define how an external purchasing agent can read and act on its systems while preserving authority, appropriate data access, interoperability, and the customer relationship. The brief identifies exposure to agents and platform control as strategic concerns. It does not provide measured customer demand for a specific new interface. [Challenge brief](https://hackjunction.app/participate/45/challenges/327)

Our bridge is an executable purchasing mandate and a documented request-to-order interaction. The external buyer agent does useful search and planning. The gateway checks the agent's identity, customer scope, constraints, and authority before commitment. A human gets a concrete exception to review. The accepted order and supporting facts can be inspected afterward.

**The initial target user.** Use a synthetic hotel-group purchasing persona inspired by the published predefined-assortment workflow. A chef/procurement manager defines permitted products and the buyer operates within that policy. Do not suggest that Wilderness Hotels has reported the hypothetical shortage, approval delays, or overspending we demonstrate. Their published account is positive about the current service.

For the first implementation, use one customer account, one delivery date, one small basket, and one named approver. The demo's approved SKU list, budgets, authority levels, and approver are explicitly authored example policy. The supplied catalog and APIs do not contain real customer mandates, purchase histories, kitchen inventory, recipes, or measured approval delays.

**Proposed demonstration.** The buyer needs lactose-free breakfast milk by a given date. The default permitted product is not feasible in a controlled exception scenario. The agent identifies alternatives and compares suitability, effective package quantity, cost, and delivery. It can commit an eligible alternative within its mandate, request approval for a permitted deviation, or stop when no compliant offer exists. Clearly distinguish live sandbox facts from controlled simulator fixtures. A lookup is not proof of reservation or completed delivery.

Show the human exactly what changed and why it needs attention. Approval is bound to the basket, customer, date, and current offer. A price or basket change triggers revalidation. A retry must not create a second order. These controls are proposed design decisions to test, not claims about Valio's existing production implementation.

**What remains unproven.**

| Hypothesis | Evidence needed at the venue |
| --- | --- |
| Buyer teams lose material time rechecking purchasing constraints | Walk through the most recent real order that required manual correction; count steps and time. |
| Approved-assortment exceptions are frequent or costly enough to matter | A recent example, its frequency, and who resolves it. |
| A budget or substitution approval is the right human handoff | Existing role/rule, actual approver, and the information they need. |
| Buyers want this from an external agent in their existing software | Which systems they order through today and where the agent should live. |
| The wholesaler can accept our proposed order contract | Mentor feedback on identity, commitment, expiry, and the missing mock order endpoint. |

Do not claim unmeasured reductions such as “90% less work,” guaranteed fulfilment, improved actual delivery reliability, or universal demand. First measure human interactions, constraint preservation, completion, exception handling, latency, and duplicate prevention on an explicit scenario set. A synthetic evaluation demonstrates prototype behavior; it does not establish market-wide savings.

**A 10-minute mentor/customer conversation.** Ask for a recent event rather than opinions about AI:

1. “Please walk us through the last order that needed correction or a substitute. What happened from the original need to the accepted order?”
2. “Who did each step, which systems were involved, and where did someone have to wait or check information again?”
3. “Which decisions could an agent make tomorrow under existing purchasing policy? Which must always stop for a person?”
4. “How often does this situation happen, and what was the consequence last time?”
5. “What evidence would make the proposed order acceptable without redoing the search?”
6. “If this worked, would it belong in the buyer's system, Minun Aimo, or a shared interface? Who would approve using it?”

For the implementation mentor, add: “The published API has no order operation. Should we own the order simulator, and what constitutes a committed order in this challenge?”

Start with Minni Ruhtinas for the online-sales workflow, Hanna Forsström or Pirjo Kaartinen for commercial/customer fit, and Tommi Nurmi-Aro, Ville Takanen, or Riku Tapper for authority and integration. These names and roles are from the challenge brief. No messages or interview requests have been sent.

**Two-person execution budget.** At the 03:23 Helsinki research check, the verified deadline leaves about 30.5 hours. Use a 30-hour planning budget with a small margin; these are elapsed wall-clock blocks, with the two teammates working in parallel.

| Elapsed time | Result |
| --- | --- |
| 0–1 hour | Validate the buyer problem, choose the scenario, agree the interface, and verify credentials/connectivity. |
| 1–6 hours | First request-to-simulated-order path with supplied price and availability calls. |
| 6–12 hours | Enforced mandate, approval/resume, persisted receipts, and usable human review interface. |
| 12–15 hours | One exception, stale approval, retries, and meaningful sponsor integration. |
| 15–21 hours | Rest and integration contingency. Stagger only if useful to the team. |
| 21–25 hours | Scenario evaluation, deployment, corrections, and demonstration rehearsal. |
| 25–28 hours | Two-minute video, deck PDF, source/API notes, and sponsor evidence. |
| 28–30 hours | Final link checks, submit as FINAL, verify submission, and retain deadline margin. |

Person 1 owns catalog, backend, agent tools, and policy enforcement. Person 2 owns human review, approvals UX, demo, and submission assets. Both agree the contract first and test each other's path. AI coding assistance can support both streams. Credits make tools available; their value depends on a shared specification and verified integration.

**Verified resource distinction.** The detailed OpenAI Hackerpack gives personal Codex usage, not OpenAI API credits. Anthropic's offer gives $20 Claude API credits per participant. Gemini's offer is team-based access subject to eligibility; the page does not state a fixed dollar amount. Aiven lists $50 signup credits, Verda advertises €200 compute/inference credits, and Modal lists $100 per participant. User-reported redemption is accepted, while exact balances and enabled providers have not been inspected. [Developer offers](https://hackjunction.app/participate/45/hackerpacks), [Codex details](https://hackjunction.app/participate/45/hackerpacks/70), [Claude details](https://hackjunction.app/participate/45/hackerpacks/67)

Retain Codex and Aiven as natural tech-challenge targets. Select one runtime model based on demonstrated tool-use quality and available access; Gemini gives a coherent additional tech-challenge target, while existing Claude API credits can support experimentation. A real customer workflow and reliable purchasing controls remain the basis for selecting features.
