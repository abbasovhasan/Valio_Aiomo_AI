Valio Aimo / Junction 2026 — research and recommended direction

Reviewed on 14 November 2026. Official requirements, observations from the supplied files, and our proposed design are distinguished below. This is the discovery brief for choosing the build. API contracts were read in the browser; authenticated price and availability requests have not yet been exercised. No submission, account signup, credit redemption, or external upload was performed.

**The problem and the people involved.** Valio Aimo's “Trusted Trade Agents” challenge asks how an external purchasing agent can interact with a foodservice wholesaler: discover products, obtain fixed prices and availability, then place an order within delegated authority or get human approval. Valio Aimo wants to explore the interface and operating model for that interaction while retaining control of data, trust, and the customer relationship. The challenge models today's webshop and backend, ahead of a future marketplace. [Official challenge](https://hackjunction.app/participate/45/challenges/327)

There are four distinct actors: a professional kitchen with a purchasing need, its external purchasing agent, Valio Aimo's interface to the mock backend, and a human authorized to approve exceptions. A chef currently has to translate a need into product searches, check units and dietary properties, compare prices and delivery feasibility, and obtain permission to spend. Our prototype should make those steps visible and reliable.

**The official core requirements.**

| Requirement | What the judges should see working |
| --- | --- |
| Product, price, and availability lookup | An external client receives structured product results with current prices and date-specific availability. |
| Inquiry followed by order placement | A request leads to a committed simulated order and receipt using fixed prices. |
| Permissions and human approval | Authority is enforced by the receiving system, with a real approval state when needed. |

Optional directions are delivery and sustainability comparison, substitutions and other exceptions, and traceability/explanation. Although substitutions are optional as a feature direction, the scoring explicitly gives 15% to robustness. A narrow exception path is a sensible part of the MVP. An audit record is also helpful evidence for the autonomy and controls criterion. Payments such as x402/Nevermined are context, not a requirement. A particular MCP implementation, native mobile app, model provider, blockchain, model training, or a complete marketplace is not prescribed. [Official challenge](https://hackjunction.app/participate/45/challenges/327)

**The official Valio Aimo scoring.**

| Criterion | Weight | Our implementation priority |
| --- | ---: | --- |
| Working end-to-end demo | 30% | Complete one real request-to-receipt flow first. |
| Solving the problem and user need | 20% | Preserve quantity, dietary requirements, date, and budget. |
| Autonomy and controls | 20% | Enforce delegated authority and record decisions. |
| Robustness to exceptions | 15% | Demonstrate a shortage, late delivery, or a changed offer. |
| Openness and credible production path | 15% | Publish a documented, versioned interface and honest assumptions. |

The first three criteria together account for 70%. The main challenge awards €4,000, €2,000, and €1,000 to its top three teams. These facts come from the [challenge page](https://hackjunction.app/participate/45/challenges/327).

**What must be submitted.** The [participant guide](https://hackjunction.app/participate/45/guide) lists project name, punchline, description, selected challenge, technologies, a publicly viewable video of at most two minutes, demo and source links, source-publicity and crediting information, pitch deck PDF, team phone numbers, and a Discord username. It says to change the project from DRAFT to FINAL. Drafts are not reviewed.

The live [submission form](https://hackjunction.app/participate/45/project) has limits of 30 characters for the name, 200 for the punchline, and 5,000 for the description. Its presentation upload accepts several formats up to 20 MB; preparing a PDF satisfies the guide. It has a separate multi-select for tech challenges. Some guide items are not visible as separate fields in the current form, so verify the final flow and team information before submission.

The guide and the public event schedule agree: final submissions open Saturday, 14 November 2026 at 12:00 and close Sunday, 15 November at 10:00 Helsinki time (UTC+02:00). Rechecked at approximately 03:23 on Saturday, leaving about 30 hours 37 minutes. We were before the opening of that window. The platform header's “Closed” label therefore does not establish that final submissions have ended; the earlier warning overstated that uncertainty. Do not infer a different deadline from the countdown. The guide permits multiple challenge entries, limits teams to 1–4, requires code to be written during the event apart from open-source libraries, requires organizer access to the source, and says project submissions are MIT-licensed. Partner material retains its own terms. Attend the live peer review to remain eligible for the overall main prize. The guide gives differing end times for peer review in different sections, so confirm the assigned review slots. [Participant guide](https://hackjunction.app/participate/45/guide), [public event schedule](https://hackjunction.app/hackathons/junction-2026)

**The supplied resources and what we verified.**

The four original files are saved locally under `data/raw/` and excluded from Git. `SOURCES.json` records their exact URLs, sizes, and SHA-256 checksums. `DATA_PROFILE.json` contains reproducible statistics from `profile_data.py`. The portal says the data is synthetic, imperfect, and restricted to this challenge. [Resource portal](https://junction26.valioaimo.fi/)

| Resource | Observed contents | Design consequence |
| --- | --- | --- |
| Product JSON | 17,546 unique product IDs, 648 distinct vendor names, 349 category codes, approximately 87 MB | Ingest once. Normalize and search locally rather than sending the catalog to a model. |
| Product JSON Schema | Field definitions for units, packaging, claims, deposits, and substitutions | Use it to preserve the meaning of the source data. |
| Delivery reliability CSV | 4,425 unique matching products, 25.22% catalog coverage | Missing values stay unknown. |
| Carbon footprint CSV | 11,033 unique matching products, 62.88% catalog coverage | Label group estimates and coverage. |
| Pricing API | Customer/date-specific fixed prices, comparison units, tax, validity and error flags | Fetch after finding a small candidate set. |
| Availability API | Sales units, cutoffs, earliest availability date, sales blocks, logistics model | Check actual feasibility before proposing an order. |

All CSV IDs match the catalog with no duplicate IDs in either CSV. Join catalog `id` to CSV/API `productId` as strings. Delivery reliability is the historical proportion of ordered quantity that was delivered. It is not a measured probability of arriving on time. Carbon values are average kg CO2-equivalent per kg for the product group, not individual-product measurements. A category-level average cannot establish that one brand has a better footprint than another within that category.

Only 189 products have nonempty explicit substitution rules, totaling 250 edges. Manufacturer substitutions are useful candidates, but still require dietary, availability, quantity, and authority checks. 6,622 products have different base and sales units. 506 have deposit items. Manufacturer packaging data is nonempty for 14,474 products; its completeness still varies. Product images are referenced by media IDs, but image files are not supplied.

The catalog has 17,546 Finnish names, 17,544 English names, and 16,100 Swedish names. Only 7,205 products have a nonempty `allergen` classification and 5,119 a nonempty `nonAllergen` classification. These counts describe populated fields, not the number of products proven safe or unsafe. Product/category/unit code descriptions are partly missing. Do not invent their meanings or fill missing dietary evidence with guesses.

**What the API actually provides.** The published [OpenAPI contract](https://junction26.valioaimo.fi/openapi.json) and [Swagger reference](https://junction26.valioaimo.fi/docs) expose these operations:

| Operation | Role |
| --- | --- |
| `GET /api/ping` | Authentication/connectivity check. |
| `POST /api/price` | Prices for a narrowed product set. |
| `POST /api/availability` | Availability for a narrowed product set. |
| `GET /api/products/download` | Static catalog download redirect. |
| `GET /api/delivery-reliability/download` | Static reliability download redirect. |
| `GET /api/carbon-footprint/download` | Static carbon download redirect. |

There is no published order, approval, reservation, or product-search endpoint in this contract. Our likely implementation needs a local search layer and a clearly identified simulated order service. Confirm with a mentor whether a separate ordering contract or webshop sandbox has been announced. The challenge page says webshop test-account details would be shared separately when available. Do not imply that our receipt came from a sponsor-provided order API if it came from our simulator.

Both dynamic POST endpoints take `customer`, `requestedDate` as a date, and `products` as 1–1,000 product codes. The API requires `X-API-Key`. The published key was found on the challenge page; credentials are intentionally omitted from these notes and belong in server-side environment configuration. Customer numbers do not change the mock responses, but the documentation explicitly says real prices and availability are customer-specific.

The docs prohibit a design that frequently retrieves dynamic data for all products and mention undisclosed rate limits. Search static data first, then query a small shortlist. Preserve customer/date keys and freshness when caching. Respect 422 validation errors and handle throttling and timeouts with bounded retries.

Important availability semantics: `timeNow` is Helsinki server time; `closingTime` is an ordering cutoff; `availableDate` can be later than the requested date; empty `scheduleLines` mean no current deliverable date; product and line `salesBlock` flags both matter. Terminal products return `availableAmount=999999` because actual supplier quantity is unknown. Display that as unknown quantity, rather than a million units of verified stock.

Important pricing semantics: the catalog price is per sales unit; `comparisonPrice` is per comparison unit (KG or L); tax and price validity are returned; `error=true` means a price was not found. Use returned tax values rather than hardcoding a rate. Missing prices never mean free products. Record the tax basis used by budgets, include known deposits, and mark unsupported charges explicitly. A price lookup does not itself reserve stock or bind a future order.

**Our recommended concept: Aimo Trust Gateway.** A professional kitchen delegates a bounded purchasing task. An external buyer agent searches and compares through our documented gateway. The gateway enforces the buyer's authority, presents any permitted approval request to the responsible person, and commits an order in a simulator. Both buyer and wholesaler can inspect the resulting receipt and factual decision record.

Suggested punchline: “A trusted purchasing gateway that turns kitchen needs into approved, traceable orders.” This is our proposed name and positioning, not an official Valio Aimo product.

Deliver one responsive web application backed by an API, plus a small external agent client that calls the API. The web application is the human review surface. The independent client is evidence that an outside agent can use the interface. A native phone application adds little to the required workflow. A form or chat box is a useful input mechanism, but agent calls, enforcement, and the receipt must actually work.

The MVP has four human views: purchasing request, candidate comparison, authority/approval, and order receipt with a decision timeline. Keep request constraints and changes explicit. A reviewer should see exactly why the agent chose a product, which alternatives failed, and why approval is needed. Show tool inputs/results and concise reasons, not private model chain-of-thought.

The proposed implementation separates language interpretation and planning from deterministic enforcement. A model converts the need into a typed request and calls tools. Code validates quantities, product evidence, dates, prices, budgets, and allowed substitutions. The model cannot authorize itself by declaring an order approved.

Represent the buyer's authority as a purchase mandate: buyer/customer ID, agent identity, allowed operations, categories or products, per-order and cumulative spend, dietary rules, delivery requirements, permitted substitutions, expiry, and approver. Identity, customer scope, and authority must be checked server-side. A client-supplied customer number or budget is not proof of authority. The mock API key authenticates access to the sponsor sandbox; it does not supply our per-agent permission model.

Distinguish three outcomes: within authority (can proceed), eligible for human approval (pause with a concrete basket), and invalid (blocked until corrected). A forbidden dietary change is not the same as a budget overrun. Bind approval to the exact buyer, lines, quantities, delivery date, total, and offer version. Changed prices, baskets, or dates trigger revalidation and, when appropriate, new approval. Add an idempotency key and a database uniqueness rule so retries cannot create a second order. Enforce cumulative spend atomically to prevent concurrent or split orders bypassing a cap.

Use a versioned HTTPS/JSON interface described with OpenAPI and JSON Schema. Persist a factual audit trail with source references, timestamps, rule results, approvals, and order identifiers. A small verification script can check a signed offer or receipt if time permits; explain that it proves issuer/integrity, not that future stock is reserved or that the supplied product facts are independently true. A documented HTTP API is enough for the openness requirement. MCP can be a thin adapter after the core is stable. Keep the architecture independent of the chosen model provider.

**A concrete demo story.** Start with the brief's own example: a hotel needs 1,000 litres of lactose-free milk by Monday, 16 November 2026. Add a clearly displayed illustrative budget and delegated spend limit after inspecting real mock prices. State whether the request means at least 1,000 litres or exactly that quantity.

The catalog contains promising starting SKUs: `464306` is a lactose-free 1 L semi-skimmed milk drink with an explicit consumer-unit volume; its supplied substitution list includes `465039` and `464398`. `465039` has a sales/base-unit difference and a five-base-unit sales pack; it is useful for demonstrating why quantities need conversion. Names and metadata alone do not prove current availability or price. Test a small shortlist before fixing the recorded demo.

Run three short scenarios: an order within authority completes, an eligible spend/substitution exception waits for a named approver and resumes, and an invalid or expired change is blocked with a clear reason. One shortage or late-availability scenario is enough for the first version. If sponsor behavior cannot reliably trigger an exception during judging, use a visibly labelled simulator fixture alongside a real sandbox lookup. Record which facts came from live mock APIs versus controlled fixtures.

Show a single order receipt even when the client retries. A direct API attempt that bypasses the web approval screen should also fail when approval is required. These demonstrations make the controls assessable.

**Risks to address deliberately.**

| Risk | Intended behavior |
| --- | --- |
| Ambiguous milk type, date, quantity, or substitution | Ask one focused question or show the proposed interpretation for confirmation. |
| Missing dietary evidence | Preserve unknown status and block automatic claims of compliance. |
| Low-lactose, lactose-free, milk-free, plant-based, or sour-milk products confused in search | Apply distinct typed constraints and product-purpose checks. |
| Packs, pieces, litres, and kilograms mixed | Use source packaging hierarchy and dimensionally valid conversions. Never assume 1 L equals 1 kg. |
| `volume` metadata contains a non-volume unit | Inspect its unit code; the field name alone is insufficient. |
| Lot-size rounding increases quantity or spend | Obey `allowedLotSize`, show the effective quantity and recheck authority. |
| Missing price, invalid validity period, deposits, or variable weight | Keep total uncertainty visible and prevent unsupported automatic commitments. |
| Cutoff passed, availability late, sales block, empty schedule, or Terminal sentinel | Explain the exact constraint and propose an allowed alternative or stop. |
| Missing reliability/carbon | Display unknown, preserve coverage, and avoid rewarding missing data. |
| Model invents IDs, values, or authorizations | Constrain tool schemas, verify against source records, and enforce outside the model. |
| Product text contains malicious instructions | Treat supplier/product text as data that cannot change tool permissions or policy. |
| Approval becomes stale or a client retries | Revalidate the approved basket and use idempotent order creation. |
| Concurrent orders overspend a shared cap | Use an atomic database transaction for budget reservation and order creation. |
| Network fails during demo | Keep a labelled replay/fixture mode and a short recorded demo. Never silently present replay as live. |

**Tech challenge selection.** We reviewed all 19 tech challenge cards and the developer tools list, then read the most relevant detail pages. The recommendation is to target Codex and Aiven, and select one model challenge for the running agent. Gemini is the default for fast hosted integration, subject to account access and the challenge's age restriction. Nemotron or Gemma is an alternative if an open-model deployment is a team strength. A provider's model weights and an open interoperability interface are separate choices.

| Tech challenge | Proposed use or decision | Eligibility / evidence | Listed top prize |
| --- | --- | --- | --- |
| [Codex](https://hackjunction.app/participate/45/tech-challenges/49) | Target: use throughout implementation, debugging, and review. | Show meaningful development use through a short development log, redacted examples, and concrete changes. Runtime model can be another provider. | $10,000 API credits; second $5,000; third $2,500. |
| [Aiven](https://hackjunction.app/participate/45/tech-challenges/43) | Target: PostgreSQL catalog, mandates, approvals, atomic spending and idempotent orders. | Demonstrate why persistence and transaction behavior are central. Criteria: meaningful use 40%, implementation 30%, solution impact 20%, creativity 10%. | €1,000; second €750; third €500. |
| [Gemini API](https://hackjunction.app/participate/45/tech-challenges/48) | Default model target: intent extraction and tool-driven purchase planning. | Show grounded outputs and evaluations. Explain why Gemini matters. Participation and Google accounts restricted to people aged 18+. | €4,000 plus $1,000 Google Cloud credits per member; second €2,000; third €1,000. |
| [Nemotron](https://hackjunction.app/participate/45/tech-challenges/46) | Strong alternative: model performs the buyer agent's core tool workflow. | Brief specifically requires Nemotron 3.5 Super VL and an explanation of output improvements. Its example API model string names a different variant; confirm the exact eligible endpoint with mentors. | Two winning teams, one RTX 5080 each as listed. |
| [Gemma](https://hackjunction.app/participate/45/tech-challenges/47) | Alternative model target with Modal or Verda hosting if setup is familiar. | Gemma must be meaningful in the working solution. Do not add several models without a useful role. | €1,000 for each of three teams. |
| [Verda](https://hackjunction.app/participate/45/tech-challenges/56) | Conditional: open-model inference or parallel evaluation workload. | Strong entries show why compute is necessary and a scaling path; process summary and Discord post required by platform brief. Confirm the advertised Nemotron endpoint/model. | Platform lists $10,000 credits, then $2,500/$2,500; vendor blog uses EUR, so confirm currency. |
| [Modal](https://hackjunction.app/participate/45/tech-challenges/40) | Conditional alternative to Verda: host an open model and agent API. | Model/agent infrastructure must be central. Criteria: use 40%, ambition 25%, impact 20%, deployed demo 15%. | $2,000 cash plus $3,000 credits. |
| [ElevenLabs](https://hackjunction.app/participate/45/tech-challenges/50) | Optional voice input/readback for a busy chef after the core flow works. | Working voice interaction should drive the same purchasing flow. Useful orders still need visible confirmation of parsed quantities. | Wireless earbuds. |
| [CRACI](https://hackjunction.app/participate/45/tech-challenges/42) | Optional CI and software-build provenance. | CI on CRACI is required; winning criteria favor technical depth and creative use of its API/provenance, rather than only changing a runner. Build provenance does not verify product claims. | LEGO set per team member; additional runner-up prizes. |
| [MongoDB Atlas](https://hackjunction.app/participate/45/tech-challenges/55) | Alternative database if the team already knows it. | Use one main data store; avoid duplicating Aiven data for eligibility. | M5Stack IoT kit. |
| [Tiger Data](https://hackjunction.app/participate/45/tech-challenges/53) | Alternative database for a project centered on event analytics. | Current files contain no stock/price history series; event analytics would come from our own runs. | Stream Deck Mini. |
| [Vultr](https://hackjunction.app/participate/45/tech-challenges/54) | Alternative hosting if already familiar. | Has limited domain-specific differentiation for this prototype. | M5Stack mini programmable monitor. |
| [Entire](https://hackjunction.app/participate/45/tech-challenges/51) | Development-workflow option if the team already uses its session/context tools. | Requires meaningful use of its collaboration capabilities and evidence of workflow efficiency. Keep credentials out of shared sessions. | Mini portable projector. |
| [Context.dev](https://hackjunction.app/participate/45/tech-challenges/44) | Defer unless public web verification becomes a real core need. | At least one endpoint must visibly drive the core demo; repository, demo, and endpoint note required. Web content cannot replace sponsor price/stock truth. | €750; second €250; third swag. |
| [Oxylabs](https://hackjunction.app/participate/45/tech-challenges/32) | Defer for the same scope reason as Context.dev. | Runtime Web API use and source URLs required; headline describes search plus scrape. Hackerpack offer requires a card and renews after the discounted month unless cancelled. | €1,000 Apple gift voucher per winning team, plus $500 credits per member. |
| [Cloudinary](https://hackjunction.app/participate/45/tech-challenges/41) | Defer: visual media is not central to the required interface. | Specified tool use and an additional submission form required. Catalog image files are not supplied. | $500 Amazon gift cards per team member as listed. |
| [Solana](https://hackjunction.app/participate/45/tech-challenges/52) | Defer: on-chain payments are outside our chosen MVP. | Needs a meaningful blockchain use case. | Unruggable hardware wallets. |
| [Arduino UNO Q](https://hackjunction.app/participate/45/tech-challenges/45) | Defer: inventory sensors add a separate hardware build. | UNO Q and physical/edge-AI demonstration expected. | UNO Q and Plug and Make kit per winning team member. |
| [Atech](https://hackjunction.app/participate/45/tech-challenges/29) | Defer: hardware sourcing/sensing is a separate scope. | Atech modules, physical demo, source/project, and summary post required. | Pro Atech kit; runner-up kits and swag. |

The [developer offers](https://hackjunction.app/participate/45/hackerpacks) include $100 worth of personal Codex usage per participant, Aiven signup credits of $50, Gemini access for eligible teams (up to 400), €200 Verda credits as advertised, and $100 Modal credits per participant. The detailed [OpenAI offer](https://hackjunction.app/participate/45/hackerpacks/70) explicitly excludes API credits and a paid subscription: it provides 2,500 Codex usage credits valid for 30 days after redemption. Do not budget that offer as runtime API funding. [Anthropic's offer](https://hackjunction.app/participate/45/hackerpacks/67) is $20 in Claude API credits per participant. The user reports having already collected credits; the pages establish available offers, not their personal redeemed balances. Access, billing, and provider terms must be checked during setup. We have not created accounts or redeemed anything on the user's behalf.

For prize strategy, one working solution can target several tech challenges, but the cost is implementation and presentation time. Default to Codex + Aiven + Gemini. If the team chooses an open-model route, substitute the model and hosting pair after a short tool-use reliability check. Do not use Gemini, Gemma, and Nemotron together merely to tick three boxes. A Verda/Gemma or Modal/Gemma combination is coherent if hosting provides a concrete benefit. A Verda/Nemotron combination depends on obtaining the exact model required by NVIDIA.

**A provisional implementation plan.** The user confirms two people who can cover the required development, with Codex/Claude and partner credits available. The verified deadline leaves approximately 30.5 hours as of the research check. Keep the first complete flow within the first six build hours and reserve time for rest, validation, and submission. The following order is the dependency sequence.

1. Validate scope with Valio Aimo mentors, resolve the missing order contract and submission status, choose one buyer scenario, and establish a measurable definition of done.
2. Load the static catalog and side tables. Preserve source metadata. Define typed purchase requests, offers, permissions, approval states, and receipts. Test a small real price/availability shortlist.
3. Build the gateway search/lookup calls and a persisted order simulator. Enforce identity, budget, product/date constraints, approval, and idempotency at the API boundary.
4. Connect one model-powered external buyer agent. Get the first full request-to-receipt path working before expanding the interface.
5. Build the small web review surface and the approval/resume path. Add one shortage/late-delivery scenario and stale-approval protection.
6. Demonstrate constraints, repeat/retry behavior, and direct API attempts. Record tool logs and measure completion, corrections, latency, approval correctness, and duplicate prevention on a small scenario suite. Report observed results rather than invented savings percentages.
7. Integrate the chosen sponsor services meaningfully. Keep a record of Codex's contribution. Make the deployed demo accessible to judges.
8. Reserve the final hours for the video, deck PDF, README/API contract, final links, and tech-challenge explanations. USER OVERRIDE: prepare reviewable submission materials only; never submit the project as FINAL or change its submission status. Rehearse the live peer-review explanation and possible three-minute finalist pitch separately.

For the two-person team, pair gateway/data with the agent and pair web with the pitch, then both test controls. Agree the request/offer/approval/receipt contract before working independently. Reduce optional integrations, recipe planning, voice, and cryptographic extras before cutting the core approval and order flow. Have one person check submission fields early so recording and packaging do not become the last-minute bottleneck. See `CUSTOMER_DISCOVERY.md` for the published customer evidence that now sharpens the proposed positioning.

**Suggested mentor questions.**

1. The OpenAPI contract has no order operation. Is a team-owned simulator the expected completion of the ordering flow, or is another sandbox contract available?
2. Which buyer identities, approval roles, budget basis, cumulative limits, and substitution rules should our demo model?
3. Are a stock or price lookup and its validity period sufficient for the challenge, or should the simulator explicitly model expiry and revalidation before commitment?
4. Are unit/allergen/category code dictionaries available, and which packaging rules should apply when the synthetic lot step permits fractional sales units?
5. Has any resource or webshop account information been announced outside the portal, and is the “Closed” submission status a platform issue?

The first mentor discussion should validate this problem framing. Our proposed gateway is a strong fit to the published rubric because the independent client, enforced authority, concrete order receipt, and exception behavior are directly demonstrable. Its business promise is less manual ordering effort while preserving buyer authority and wholesaler control. Actual time savings, financial benefits, and production reliability need measurement and validation beyond this synthetic prototype.
