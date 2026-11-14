# Aimo Order Desk — autonomous build mission

This is an implementation request. Begin work now and continue through building, running, testing, improving, and preparing a complete delivery. Do not stop after a plan. Treat the following as the user's build brief, subject to higher-priority instructions and actual tool permissions.

## Outcome and boundaries

Build a distinctive, competition-ready solution for Junction 2026's Valio Aimo “Trusted Trade Agents” challenge. Optimize for a working, memorable demonstration of an external buyer agent acting within delegated purchasing authority. Aim for exceptional execution; do not claim or promise a prize.

You may start the APPLICATION implementation fresh because this workspace currently contains research, data, and service setup rather than an application. Preserve the existing files, datasets, credentials, Git remote, and working account setup. A fresh chat does not require repeating completed discovery or reinstalling everything.

NON-NEGOTIABLE:

- NEVER submit any Junction project as FINAL, change its submission status, or submit a sponsor entry. Prepare all materials locally for the user to review. The existing Aimo Order Desk entry must remain Draft.
- No real purchases, payments, customer orders, production wholesaler actions, or communications to mentors/organizers. Orders are explicitly simulated.
- No out-of-pocket spending. Use free resources or verified promotional credits only. No payment cards, subscriptions, auto-top-ups, paid upgrades, or uncovered charges. An advertised offer is not proof of the account's balance. Verify expiry, eligible products, and a usable enforced spending limit before consuming cloud credits. Otherwise keep that portion local and continue.
- Keep source private. The configured GitHub repository is private; do not make it public. Never commit credentials, even to a private repository. Keep data/raw/ excluded and respect challenge-data terms. Do not print secrets, put them in prompts or browser URLs, or expose them in frontend code, logs, screenshots, artifacts, or test output.
- Deploy a demo to a tech sponsor only when its account access, credit coverage, security, and permitted deployment workflow are verified. Follow any action-time approval requirements. Do not let deployment block a complete local deliverable. Preparing/publishing a demo is separate from submitting Junction FINAL.
- Do not fabricate interviews, savings, model actions, test results, eligibility, production readiness, or completed work. Distinguish live sponsor sandbox calls, recorded responses, and simulator fixtures visibly.

The user may be asleep. Resolve routine decisions yourself. If account-owner action is required, record the precise blocker and continue independent implementation. Do not wait for a human teammate to build your missing components. Use available skills where applicable. Never claim continued background execution after your active session ends.

## Existing workspace and resources

Work in /home/hasan/Documents/ChatGPT/Valio_Aiomo_AI.

Read these first, without redoing their entire research:

- research/CHALLENGE_RESEARCH.md
- research/CUSTOMER_DISCOVERY.md
- research/DATA_PROFILE.json and research/SOURCES.json
- research/ACCESS_READINESS.md
- research/HOSTING_PLAN.md
- .gitignore and .env.example

Read credential variable NAMES from the ignored .env as needed; load values directly in server-side code and avoid displaying them. .env permissions were set to 0600. Database CA is in ignored .local/aiven-ca.pem.

Previously verified, not guaranteed forever:

- NVIDIA: NVIDIA_API_KEY configured. Actual inference succeeded with nvidia/nemotron-3.5-super-vl-120b-a12b. This is the default runtime model. Verify structured output/tool-use behavior with a small smoke test; an OK response does not establish agent reliability or unlimited credits.
- Valio Aimo: VALIO_API_KEY and VALIO_API_BASE_URL configured. Authenticated /api/ping succeeded using User-Agent AimoOrderDesk/0.1. Price/availability business flows still need testing.
- Aiven: free European PostgreSQL service aimo-order-desk running. DATABASE_URL and PGSSLROOTCERT configured. SELECT 1 and TLS verified. Keep sslmode=verify-full and the CA. This is a small free instance with a 20-connection limit, 1 GB storage, and inactivity shutdown behavior; bound the pool. Its network allowlist currently permits the development machine's outbound IP only. A deployed host needs a deliberate approved network path; never solve this by broadly opening database access.
- GitHub: gh authenticated as abbasovhasan; origin points to https://github.com/abbasovhasan/Valio_Aiomo_AI.git. Private status verified; no application was pushed during setup. Inspect current state before edits or pushes. Avoid force pushes and destructive Git operations.
- Anthropic Console: signed in; $20 organization credits observed. ANTHROPIC_API_KEY not configured. Optional backup, not a prerequisite.
- Google AI Studio: signed in, but runtime Gemini credentials unconfigured. Google Cloud reached a project welcome URL; billing eligibility unverified. Do not assume Cloud credits.
- ElevenLabs: signed-in home observed; runtime key unconfigured. Optional voice only.
- Modal: authenticated workspace hasan-abbasov. Billing Credits tab verified an active Junction Hackathon grant with $100 of $100 remaining, activated 13 November 2026 and expiring 30 November 2027. Usage Limit tab shows $0 used, a Modal-set $101 workspace cap ($100 grant plus $1 monthly free credit), and requires adding a payment method to raise it. No payment method was added. CLI token and deploy capability still need verification. Prefer Modal for sponsor hosting within this verified credit coverage; use a conservative deployment budget. Aiven Runtime is an alternative: GitHub account abbasovhasan is now connected, but runtime-specific credit coverage/pricing and selected-repository permissions still need checking. Verda/Vultr are alternatives only if their accounts and credits are actually usable.

Do not spend hours activating optional accounts. Build using the verified core and add provider adapters only where useful.

## Evidence and official requirements

Authoritative starting links:

- https://hackjunction.app/participate/45/challenges/327
- https://hackjunction.app/participate/45/guide
- https://junction26.valioaimo.fi/openapi.json
- https://hackjunction.app/participate/45/tech-challenges/46
- https://hackjunction.app/participate/45/tech-challenges/43
- https://hackjunction.app/participate/45/tech-challenges/40

Use existing research, then recheck only critical current rules, API contracts, sponsor eligibility, and deadline changes. Do not reproduce a 75-minute research phase. Read the current Europe/Helsinki time and verify the recorded deadline of 15 November 2026 at 10:00. Plan backward from it and leave the user a review buffer. If the deadline has passed, report that honestly and continue a useful build without pretending entry remains possible.

The core is structured product/price/availability lookup, inquiry-to-order interaction, and enforced permissions/human approval. Recorded scoring: working end-to-end 30%, user need 20%, autonomy/controls 20%, robustness 15%, openness/credible path 15%. Verify material changes.

Important source facts:

- Static catalog: 17,546 products, approximately 87 MB. Search/index locally or in PostgreSQL; do not send the full catalog to a model or poll all dynamic records.
- Catalog product id joins to API/CSV productId as strings. Schemas and data profiles already exist.
- Published dynamic endpoints are POST /api/price and POST /api/availability. Search, approval, reservation, and order placement are NOT published sponsor endpoints. Implement your own clearly labelled gateway and order simulator.
- Availability depends on requested date, cutoffs, sales blocks, schedule lines, and logistics model. Terminal availableAmount=999999 means supplier quantity is unknown.
- Prices have tax, comparison units, validity, and error flags. Missing prices are not zero. Validate sales packs, dimensional conversions, lot sizes, and deposits. Never assume litres equal kilograms.
- Missing dietary evidence stays unknown. Lactose-free, low-lactose, milk-free, plant-based, and allergy-safe are different claims. Human budget approval cannot make a forbidden dietary substitution valid.
- Reliability is historical delivered quantity ratio, not an on-time probability. Carbon is a group estimate, not a measured individual SKU footprint.
- There is no real customer mandate, inventory, order history, or live supplier marketplace in the supplied data. Label authored policies and scenarios as examples.

## Creative direction: ambitious product, executable proof

You have broad creative freedom over the experience, interaction, branding, and strongest differentiator. Do not deliver a generic chatbot beside decorative metric cards. Make judges understand, within 20 seconds, what the agent can do and why the buyer can trust it.

Spend at most 15–20 minutes on divergent exploration. Generate five materially different directions, including one unconventional option. Compare their challenge fit, customer value, two-minute demo payoff, source-data support, and implementation risk. Select one hero concept and at most two supporting innovations. Record the choice briefly and start coding. Existing Aimo Order Desk branding and hotel procurement scenario are useful starting points, not constraints on imagination.

Prompts for originality, NOT a feature checklist:

- A visible “trust firewall”: the agent attempts an attractive shortcut; the gateway blocks it, explains the exact evidence, and the agent recovers.
- A procurement flight recorder: replay a decision, inspect its evidence, then change budget/date/quantity and see exactly what must be revalidated.
- A constrained what-if lab: show why an offer failed and the smallest PERMITTED change that makes it feasible. Never suggest relaxing a hard dietary rule.
- A live autonomy envelope: the UI makes the boundary between autonomous execution, approvable exceptions, and invalid actions tangible.
- A deliberately labelled failure-injection stage: introduce a shortage, stale approval, malicious product text, or duplicate request and show recovery rather than a scripted success animation.
- A decision receipt whose checks are independently verifiable through an external API client, rather than just reassuring prose.
- Optional chef voice interaction that drives the same real workflow, only if ElevenLabs access is configured and the core is stable.

Surprise through an excellent working interaction. Prefer one remarkable feature to six half-built ones. No blockchain, GPU deployment, fake multi-agent theater, or extra databases merely for logos. Signing a receipt proves integrity/issuer identity, not future stock or truth of product claims. Make any such distinction explicit.

## Implementation expectations

Choose a compact stack and build one coherent application. A reasonable default is a polished React/TypeScript frontend, Python/FastAPI gateway, Aiven PostgreSQL, NVIDIA agent, and a Modal deployment adapter. Change that if current tools or the chosen concept justify it. Minimize services and package churn.

The outside buyer agent must call a documented gateway through real typed tool/API interfaces. The gateway owns policy enforcement and simulator commitment. Demonstrate an independent client or script calling it: the UI must not be the only enforcement point. A documented versioned HTTP API/OpenAPI is sufficient; MCP is optional after the complete flow works.

Build these invariants into code:

- Explicit buyer/customer scope and approver identity; server-side authorization on every sensitive operation. Demo roles may be synthetic, but a request body or client-side role switch must not mint authority.
- Three outcomes: within mandate, approvable exception, invalid. A model cannot approve itself.
- Approval bound to the exact buyer, basket, quantities, date, total, and offer version/expiry. Changes trigger revalidation and new approval where needed.
- Decimal money, dimensional units, real product IDs, fresh price/availability evidence, and bounded API retries/timeouts.
- Atomic cumulative-spend enforcement and idempotent order creation with database constraints. Concurrent or split requests must not bypass a cap; retries return the same simulated order.
- Supplier text treated as untrusted data, never instructions. No frontend credentials or model-controlled privileged operations.
- Factual audit events with evidence and concise reasons, not private chain-of-thought or invented confidence scores.

Use the existing milk scenario as an early vertical slice: a synthetic hotel buyer needs 1,000 litres of lactose-free milk by the appropriate date. Starting SKU candidates in research are 464306, 465039, and 464398; inspect actual metadata and live prices/availability before relying on them. Pick a realistic budget from returned prices and clearly distinguish at-least versus exact quantity.

Build a first request → search → shortlist → live price/availability → policy decision → simulated receipt path early. Then add approval/resume, exception recovery, beautiful interface, and the hero innovation. Keep a deterministic labelled fixture/replay mode for network failures; never silently substitute it for live evidence.

## Execution, verification, and delivery

You may use up to two subagents for genuinely independent work if available. Give each clear ownership and isolate edits. You remain responsible for integration and end-to-end behavior. Delegate research/UI review/testing only when it accelerates delivery; do not create user-owned chats. Do not assume a second human is awake.

Use short build/run/inspect loops. Test the invariants and failure modes, not implementation trivia. Include normal autonomy, human approval, invalid diet/quantity, late/unknown availability, stale price/approval, bypass attempts, cumulative budget concurrency, duplicate requests, and upstream/model failures. Run real browser checks of the main flow and responsive layout. Record exact executed commands/results and any untested areas. Do not claim production certification.

For sponsor hosting, verify personal credits and cost controls before deployment. Use CPU hosting while NVIDIA provides inference unless a measured need justifies GPUs. Protect the public demo and privileged endpoints, use provider secret storage and HTTPS, limit consumption, and verify a health endpoint plus the full deployed flow. Keep a one-command local fallback. If external authorization blocks hosting, finish and package everything else with the precise remaining step.

Create a small set of useful artifacts, not an enterprise paperwork library:

- README.md: setup, architecture, actual live/simulated boundaries, run/test/demo instructions.
- PROJECT_STATUS.md: current state, last passing checks, precise blockers, next action; update before context compaction or interruption.
- docs/PRODUCT.md: concept, customer evidence, requirements mapping, main design decisions.
- docs/DEMO.md: a rehearsable two-minute story, scenario steps, 30-second/three-minute pitches, difficult judge questions.
- docs/SPONSORS.md: actual meaningful integrations, verified eligibility requirements, credit ledger without secrets, evidence and remaining gaps.
- docs/DELIVERY.md: completed features, tests, local/deployed URLs, limitations, reviewer steps, and explicit Draft/no-submission status.
- Submission copy and a pitch-deck PDF if required, using the relevant artifact skill. Prepare locally; NEVER submit. Do not invent a recorded video if recording was not possible; provide script/storyboard and honest status.

Keep progress updates brief and outcome-focused. Do not pause for routine implementation preferences. Before pushing private source, scan staged content and generated artifacts for secrets and restricted data, verify repository privacy, and inspect the diff. Never weaken privacy to satisfy an event rule; record any source-access/licensing tension for user review.

Definition of done: a real, polished, runnable application; a live external-agent-to-gateway-to-simulated-order flow; enforceable authority and recovery; meaningful sponsor integration; reproducible tests and browser verification; credit-covered sponsor demo if feasible; complete reviewable pitch/submission assets; truthful handoff; Junction entry still Draft. If blocked, deliver the strongest complete local version and name only the remaining external actions.

Start by inspecting the current workspace, reading the existing research/access notes, checking the actual time, and selecting the boldest feasible concept. Then IMPLEMENT. Do not execute the old pasted prompt's instructions to finalize or submit anything.
