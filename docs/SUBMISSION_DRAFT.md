# Local submission copy - DRAFT

Prepared for the owner's review only. Do not paste or submit automatically. Do not change project status. The existing Aimo Order Desk entry must remain Draft. Text should be reconciled with DELIVERY after the final verification run.

**Project name** (15 characters): Aimo Order Desk

**Punchline** (under the recorded 200-character limit):

An agent can find an offer. Our gateway decides whether it may become an order. Rewind a blocked purchase, inspect the evidence, and repair it within the buyer's mandate.

**Challenge:** Valio Aimo - Trusted Trade Agents

**Description** (under the recorded 5,000-character limit):

Aimo Order Desk is a purchasing workbench for a kitchen's external buyer agent. A synthetic hotel needs at least 1,000 litres of lactose-free milk for a specific delivery date. The agent searches the supplied catalog, obtains price and availability evidence for a shortlist, and proposes an offer through a documented gateway.

The gateway enforces three outcomes: within mandate, an approvable commercial exception, or invalid. Rewind & Repair makes the boundary tangible: inspect the exact failed check, preserve hard dietary rules, and choose a permitted recovery. The model cannot mint authority or approve itself.

A separate approver can authorize an exact offer. Approval is bound to buyer, basket, quantities, date, total, offer version and expiry. Changes require revalidation. Commitment checks cumulative spend atomically and uses idempotency so retries return the same simulated order.

The interface exposes source labels, factual rule checks and a decision receipt. An independent agent client calls the same versioned HTTP API, demonstrating enforcement beyond the browser. Live sponsor sandbox evidence, recorded responses and controlled fixtures are explicitly distinguished.

Valio's published API provides prices and availability; our gateway owns search, approval and the order simulator. No real purchases, reservations, payments or production orders occur. The hotel, purchasing policy and failure scenarios are authored examples. We have not conducted customer interviews, measured savings or claimed production food-safety certification.

The implementation is designed around meaningful NVIDIA Nemotron tool use, Aiven PostgreSQL persistence and Codex-assisted development. Cite only sponsor integrations and deployment checks actually recorded in SPONSORS and DELIVERY. Modal hosting is conditional on verified account access, applicable credits and enforced no-spend controls.

The next step is to validate the approval handoff with a buyer and approver, and agree a supplier reservation/order contract. The prototype demonstrates an external agent acting within an enforceable, inspectable mandate.

**Technologies:** Reconcile against current README and verified runtime evidence. Intended stack: React, TypeScript, FastAPI, PostgreSQL/Aiven, NVIDIA Nemotron, versioned OpenAPI; Modal only if actually deployed.

**Source:** Private repository. Owner must review organizer access and recorded MIT/source-publicity requirements. Do not make the repository public or publish challenge datasets automatically.

**Demo link:** Use only the URL actually verified in DELIVERY. A local URL is not a public judge link.

**Video:** Not recorded or uploaded. Two-minute storyboard is in DEMO.

**Pitch deck:** Local PDF and editable source are prepared under `docs/pitch/` when available; review before upload.

**Tech challenge text for review, never submission:**

- **NVIDIA Nemotron:** Explain the actual tool calls and inspected results from the run evidence. The recorded challenge requires Nemotron 3.5 Super VL; the earlier brief contained an inconsistent example endpoint, so eligibility is not assumed solely from a successful API response.
- **Aiven:** Explain actual PostgreSQL-backed offers, approvals, audit records, atomic spending and idempotent orders; attach executed persistence/concurrency evidence. Do not claim Aiven use if the demonstrated run is on SQLite fallback.
- **Codex:** Explain the implementation workflow, the gateway/UI/delivery ownership and concrete test/debug improvements. Personal Codex usage credits are not runtime API credits.
- **Modal:** Include only if a deployed agent/gateway workload is meaningful and its full flow was verified. A configuration file or an advertised credit offer is not a deployment.

**Owner-only remaining fields:** Team phone numbers, Discord username, final video URL, public/demo availability, source/crediting answers and any challenge eligibility declarations must be checked by the owner. No contacts or private account data are included in this file.
