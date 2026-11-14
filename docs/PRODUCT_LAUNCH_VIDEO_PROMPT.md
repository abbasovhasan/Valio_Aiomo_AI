# A4TB · Valio Aimo — Product Launch and Demonstration Video Production Prompt

**Creative title:** One Kitchen. Fifty Guests. One Smart Order.

**Assignment:** You are the motion designer, editor and narrator producing a premium product launch film from the actual application. Follow this document as the production brief, recording script, storyboard and editorial specification. Make the kitchen's purchasing decision the story. Every application image must come from the real application. Explanatory titles may sit outside the application frame; they must never impersonate application output.

**Two deliverables for the eventual video producer:** a **2:20 optional launch master** and a **1:55 Junction submission cut**. The earlier authenticated Junction guide records a two-minute maximum. Use the 1:55 version for submission unless the current official rules explicitly permit longer. The 2:20 master is not established as submission-compliant.

**Scope of this document's creation:** prompt only. No application code was changed, and no video, animation, screenshot, screen recording or media asset was created for this brief. Recording and export instructions below are instructions for the person who later produces the film.

## 1. Product and challenge overview

The current customer-facing brand is **A4TB · Valio Aimo**. Older project and submission documents use **Aimo Order Desk**. Match the current application branding throughout the film; do not alternate product names. The product is a Junction 2026 prototype for Valio Aimo's **Trusted Trade Agents** challenge.

A professional kitchen describes measured purchasing requirements, discovers actual catalogue products, reviews product evidence and package quantities, and prepares a basket. The server checks requirements and purchasing authority before saving a **simulated order**. An optional model can interpret requests and propose grounded searches; the server owns product validation, quantity arithmetic, money, permissions and confirmation.

Valio Aimo already has online purchasing and AI-assisted services. The opportunity demonstrated here is a purchasing assistant connected to an enforceable, inspectable request-to-order process within an existing wholesaler relationship. Do not claim to have invented online wholesale ordering or recipe-to-cart services.

The integration reads prices and date-specific availability from **one Valio Aimo challenge sandbox**. There is no demonstrated multi-wholesaler marketplace, supplier negotiation, payment, production order placement or delivery booking. The order gateway and receipt are this project's simulator.

### Junction requirements and source status

Requirements checked **14 November 2026, Europe/Helsinki**:

| Requirement | What is supported by the available evidence | Production consequence |
|---|---|---|
| Event edition and deadline | The official [Junction 2026 event page](https://hackjunction.app/hackathons/junction-2026) was freshly accessible. It lists the 13–15 November event, submissions opening 14 November at 12:00 and final submissions 15 November at 10:00, UTC+02:00. | Use 2026 branding. Dates here are Helsinki time. |
| Video length and visibility | Earlier authenticated research in `research/CHALLENGE_RESEARCH.md` records a **publicly viewable video of at most two minutes**, from the official [participant guide](https://hackjunction.app/participate/45/guide). The guide could not be freshly reopened during this audit. | Prepare **1:55** as the submission-duration cut. Retain five seconds of headroom. Treat 2:20 as an optional launch master. |
| Format and hosting | No freshly accessible official requirement was found for MP4, codec, resolution, frame rate, aspect ratio or a particular video host. A YouTube-only restriction was not verified. | The export settings in section 18 are recommendations. Check the current authenticated form before choosing a public host. |
| Challenge demo | Earlier authenticated research records product/price/availability lookup, inquiry through order, and permissions/human approval requirements from the official [Valio Aimo challenge](https://hackjunction.app/participate/45/challenges/327). That page could not be freshly reopened. | Show request, actual products, a blocked constraint, human correction, confirmation and a simulated receipt. Separate-manager approval is implemented but is not exercised by this small basket. |
| Challenge judging | Earlier authenticated research records end-to-end demo 30%, user need 20%, autonomy/controls 20%, robustness 15%, openness/credible production path 15%. These weights were not freshly reverified. | Allocate most runtime to the real application and its decision boundary. Do not present the weights as a newly checked rule. |
| General judging | The freshly accessible [official 2026 website](https://2026.hackjunction.com/) describes partner track selection, face-to-face peer review and final pitches/jury. | The film supports the demo; it does not replace participation requirements. |
| Other materials | Earlier guide research records project details, demo/source links, crediting/source information, a PDF deck and team contact details. The public website also states an MIT open-source condition. Partner data has separate terms. | This brief neither publishes source/data nor changes the submission. Source access and submission fields remain the owner's responsibility. |

Access failures are verification limits, not evidence that a rule changed. Do not substitute rules from another year or another Junction event. Do not submit, upload or change a project from Draft to Final as part of this prompt-writing task.

## 2. Video objective

By the end, a judge should understand one complete decision: **a chef converts a known ingredient need into a reviewed basket, sees that it exceeds the stated item budget, explicitly changes that budget, and confirms a saved simulated order.**

The memorable moment is the stop: both products have been found, but the basket cannot be confirmed under the original €100 budget. The assistant does not silently relax the constraint. The buyer makes the commercial decision.

Show value through observable behavior: measured requirements stay attached to real products; package quantities and item costs are visible; dietary evidence can be inspected; the budget blocks confirmation; the buyer controls the next step; the receipt can be checked afterward. Do not promise measured time savings, successful real delivery or production readiness.

## 3. Target audience

- Junction judges assessing a working product, meaningful controls and exception handling.
- Professional kitchen buyers and chefs who understand ingredient quantities, packs and service deadlines.
- Valio Aimo stakeholders evaluating how an external purchasing assistant could interact with a controlled wholesale interface.

Assume viewers understand a shopping basket but have never seen this product. Explain the consequence of each action before introducing technical terminology. Keep implementation details in this brief rather than adding them to the customer flow.

## 4. Customer problem

Use an **authored breakfast-service scenario**, not a customer testimonial. A chef is preparing a kitchen for **50 guests** and has already decided that replenishment requires **20 litres of lactose-free milk and 5 kg of butter**. Salted butter is acceptable for this purchasing need. These two lines are a replenishment list, not a complete breakfast menu or a nutritionally validated recipe.

The chef needs to translate litres and kilograms into sellable packages, check the milk's declared lactose-free evidence, inspect the requested delivery date and compare the resulting item subtotal with a budget. Finding a product name alone does not resolve those decisions. A plausible product can still create the wrong quantity, rely on missing evidence or exceed the budget.

The initial **€100 item budget** is an authored purchasing constraint. After review, this fictional buyer is authorized to change that request's budget to **€200**. This is the buyer changing their own brief; it is not manager approval, a change to server spending authority or a waiver of dietary requirements.

Do not create a montage suggesting Valio Aimo's existing webshop is broken. Represent the problem with a concise editorial list of decisions, followed immediately by the real application.

## 5. Unique value proposition

**From a kitchen's measured need to a reviewable purchasing decision, with evidence and controls carried through to confirmation.**

The distinction is the connection between stages: request → actual catalogue records → sellable quantities and item costs → explicit constraint outcome → buyer review → saved simulated receipt. A conversational answer alone is insufficient; the basket must pass the receiving server's checks.

Use the supporting line **“Describe. Compare. Review.”** Avoid “fully autonomous procurement,” “guaranteed safe,” “best price across all suppliers” or “orders delivered instantly.”

## 6. Verified product capabilities

### Evidence standard

This brief was prepared from the current source, actual supplied catalogue records, existing tests and recorded QA. Read-only, in-memory parsing/quotation checks reproduced the exact two-SKU scenario below, including the €100 block and €200 recovery. **No new browser journey, live supplier/model call or receipt creation was performed for this brief.** Expected receipt behavior is supported by code and earlier documented acceptance; the eventual producer must capture a genuine successful receipt during rehearsal.

The existing `docs/FINAL_QA_REPORT.md` records backend regression tests, frontend builds, deployment/continuity checks and scoped browser/provider/media evidence. Consult its current release entry rather than older build references elsewhere in the repository. Those records are existing engineering evidence, not customer outcomes or a suite rerun for this document.

| Capability | Supported behavior | How to represent it |
|---|---|---|
| Smart order | Multiple measured product requirements, persistent draft, product choices, quantity/query edits, date/budget changes and validation. | Central workflow. Use exact input and exact SKU searches. |
| Product Search / Product Workspace | Customer tab is **Products**; multilingual/partial-name, brand, category and SKU search, pagination, declared filters and direct cart addition. | Show exact-SKU lookup briefly. “Product Workspace” is an internal component name, not a visible tab. |
| Recommendations | Evaluates retrieved candidates; related search and supplier-linked substitutions exist with explicit customer choice where required. | Show genuine choices. Do not imply global catalogue optimization or perfect culinary matching. |
| Product evidence | Ingredients/allergens, declared claims, origin, package conversions, available-date and provenance where supplied. Missing information stays unknown. | Inspect the milk's actual evidence. Never imply lactose-free is milk-allergy safe. |
| Quantities | Dimensional conversion, whole-pack/lot rounding, aggregation and surplus disclosure. | This basket is exactly 20 × 1 L and 10 × 500 g. **No surplus occurs.** |
| Constraints | Hard dietary/specification rules, item budget, date, quote freshness and purchasing authority. | Show the €100 budget failure, then the buyer's explicit correction. Date checking is not a delivery guarantee. |
| Saved preferences | Mandatory food restrictions/exclusions and separate soft brand/origin/organic/priority defaults. Hard restrictions affect search and validation. | Establish clean synthetic-account defaults off-camera. Do not remove genuine restrictions to force success. |
| Speak Your Order | Actual UI label **Voice input**. Microphone → local Whisper transcription → editable review → explicit add/build. | Controls may be visible. The central filmed request is typed; do not imply it was transcribed. |
| Images/camera | Upload image / Take a photo → bounded normalized image → automatic NVIDIA reader with local OCR fallback → editable review. | Available capability, outside the timed demo. No invented extraction result or automatic order submission. |
| Optional text agent | NVIDIA interpretation and grounded search proposals; local structured parsing also works. | Core rehearsal leaves NVIDIA text unchecked. Do not narrate a live model call. |
| Human control | Buyer review and explicit confirmation. Separate authenticated manager approval for eligible authority exceptions binds an exact basket. | This €107.10 basket uses buyer review; it does not need separate manager approval under default policy. |
| Order processing | Revalidation, atomic synthetic spending, idempotency and a persisted simulated receipt. | Record actual confirmation. No supplier purchase, payment, invoice or reservation is created. |
| Verification/history | Saved receipt consistency/scope checks; personal history open/reuse/archive/removal. Reuse needs fresh checks. | Show Verify receipt. Do not equate verification with independent certification or fulfillment. |
| Meal planner | Reviewable bolognese/lentil example, editable quantities and overlapping dietary cohorts, transfer to Smart order. Unknown evidence can block completion. | Omit from this story. Do not infer an arbitrary 50-person menu was generated or fulfilled. |
| Integrations | One Valio sandbox for commercial reads; optional NVIDIA; hosted persistent SQLite, with an exercised PostgreSQL development option. | Do not show multiple negotiating suppliers or describe Aiven as the current hosted database. |

Useful implementation evidence, relative to the repository: `frontend/src/ProcurementDesk.tsx` (customer workflow and receipt), `ProductWorkspace.tsx`, `MultimodalInput.tsx`, `PreferencesPanel.tsx`; `backend/procurement.py` (fixture pricing, quotation, set_query, budget and confirmation), `product_facts.py`, `interpretation.py`, `upstream.py`; `tests/test_procurement.py`, `test_catalog_search.py`, `test_product_facts.py`; `docs/FINAL_QA_REPORT.md` and `docs/EXTENDED_ACCEPTANCE.md`.

Known boundaries: generic “butter” search may retrieve lexical matches such as cocoa/nut butter; the chef must choose the intended product. Some catalogue conversions contradict their product names and are correctly blocked. A Terminal stock sentinel is not known inventory. Do not construct a shortage/allergen-rescue sequence from those unrelated cases. Unknown evidence must remain visible.

## 7. Selected real-world scenario

### Locked rehearsal configuration

| Setting | Exact value |
|---|---|
| Application | [Hosted A4TB · Valio Aimo](https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site), or the prepared local application at `http://127.0.0.1:8000` |
| Entry point | `/`; use in-app tabs. Do not invent `/smart-order` or `/products` page URLs. |
| Role | Buyer, in a dedicated synthetic workspace with default preferences and enough remaining synthetic authority |
| Date | **17 November 2026**; enter `2026-11-17` using the date control |
| Initial Maximum budget (€) | **100** |
| Quote source | **Authored fixture prices & stock** |
| Text model | **Use NVIDIA for nonconfidential demo requests** unchecked |
| Exact request | `20 litres of lactose-free milk and 5 kg of butter. Show me suitable options.` |
| Milk line Product search | **464073**, then **Find products** |
| Butter line Product search | **475797**, then **Find products** |
| Corrected Maximum budget (€) | **200**, then cart-side **Apply requirements** |
| Final action | **Review & confirm** → **Confirm simulated order** → **Verify receipt** |

### Verified expected basket — authored commercial facts

| Catalogue identity | Sales package | Sellable quantity | Fixture price including tax | Line subtotal |
|---|---|---:|---:|---:|
| **464073 — Valio whole milk 1 l lactose free UHT** | 1 L per ST | 20 ST = 20 L | €3.87 / ST | €77.40 |
| **475797 — Valio butter 500 g salted** | 0.5 kg per ST | 10 ST = 5 kg | €2.97 / ST | €29.70 |
| **Item subtotal** | Both requirements met exactly | No surplus | Delivery/service charges excluded | **€107.10** |

These product identities and package facts come from the actual supplied challenge catalogue. Prices and stock come from the application's **authored fixture**, not observed supplier offers. Non-default SKU fixture pricing is deterministic in `backend/procurement.py`; do not substitute the upstream client's generic fallback price.

With budget €100: **€7.10 over budget**, confirmation blocked. The exact expected clarification is:

> Item subtotal exceeds your hard budget by €7.10. Increase the budget explicitly, change products or reduce quantities.

With budget €200: item subtotal remains **€107.10**, remaining item budget **€92.90**, both selections/quantities and the milk's lactose-free requirement are preserved. Expected response: **“Your complete item-price basket is ready for review.”** Separate manager approval is not required under the default policy. Actual UI currency punctuation may follow its locale; preserve the real rendering.

The 50 guests are editorial context. The app does not calculate these quantities from guest count, check kitchen inventory, certify a menu or prove that every breakfast ingredient is allergen-safe. The lactose-free restriction applies to the milk line; the chosen butter is not represented as lactose-free.

## 8. Creative direction

Use the clarity of **Linear** and the calm hierarchy of **Apple Notes** as references for restraint, spacing, focus and readable interaction. Adapt those principles to the existing application; do not copy their interfaces, assets or branding.

- **Visual foundation:** actual warm paper surfaces, dark green typography, quiet dividers and compact product cards. Paper `#fcfcf7`; forest `#153f32`; muted `#758078`; border `#dedfd4`; orange `#c96740`; mint `#c5edb4`. Existing customer surfaces also use canvas `#f4f3ed` and action green `#214d37`.
- **Typography:** use the app's DM Sans for body and Manrope where consistent with its branding. A restrained Georgia display accent may appear in the opening title. Do not restyle text inside recordings. At 1080p, editorial titles 64–80 px, supporting copy 34–42 px, captions 32–36 px and the source disclosure at least 26 px.
- **Composition:** one dominant object or decision per shot. App footage occupies roughly 80–90% of frame width, with detail crops when needed. Reserve a consistent lower strip for captions and provenance rather than covering product evidence or buttons.
- **Motion:** 180–280 ms UI highlight entrances; 350–550 ms editorial title reveals; 650–900 ms camera reframes. Use smooth ease-out/ease-in-out with no bounce, elastic overshoot, spinning screens or continuous drifting.
- **Transitions:** clean cuts tied to user actions; at most 6–8-frame dissolves for editorial cards. Use position continuity when moving from product to cart. No page-flip, portal or dramatic glitch transitions.
- **Highlights:** a 2–3 px mint/forest outline, subtle background dim and a short leader line. At most one highlighted region at a time. Keep the application's warning text and disabled state legible.
- **Cursor:** normal pointer, deliberate paths, no decorative trails. Hold 0.5–1 second before significant clicks. Never add a click effect to a control that was not clicked.
- **Background:** flat warm paper. A static, almost imperceptible paper texture is optional for the producer; no asset is required. No robots, neural networks, neon grids or meaningless 3D.
- **Honesty:** never redraw results, fabricate a card, replace a disabled button with an enabled one or animate an unobserved success. Clearly label explanatory diagrams and shortened waits.

## 9. Complete timestamped storyboard — optional 2:20 launch master

All intervals below are **start-inclusive/end-exclusive**, at 30 fps. Total: **140 seconds / 4,200 frames**. Sub-beats cover each scene's complete interval. Narration timing is locked in section 10. Every application scene carries the provenance label from section 11.

### Scene 01 — The service ahead

1. **Time:** 00:00–00:10.
2. **Objective:** Establish a real kitchen need immediately.
3. **Screen:** 00:00–00:02 warm paper; 00:02–00:05 “One kitchen. Fifty guests.”; 00:05–00:10 two plain ingredient lines. No fictional purchasing dashboard.
4. **Application page:** None; this is an editorial scenario card.
5. **User action:** None.
6. **Exact input:** None sent to the app. Editorial quantities are 20 L lactose-free milk and 5 kg butter.
7. **Expected application response:** Not applicable; no output is implied.
8. **Motion:** Title fades/rises 12 px over 450 ms; ingredient lines enter one at a time, 350 ms each.
9. **Camera:** Locked, centered typography, generous margins.
10. **Transition:** Clean cut to Scene 02 at 00:10.
11. **On-screen text:** “One kitchen. Fifty guests.” / “20 L lactose-free milk” / “5 kg butter”; small “Illustrative breakfast-service scenario”.
12. **Voice-over:** “Fifty guests for breakfast. The chef already knows the shopping list: twenty litres of lactose-free milk, and five kilos of butter.”
13. **Audio:** Quiet musical pulse begins at 00:00; one restrained paper/tap accent at 00:02. No kitchen audio implying filmed customer research.
14. **Duration:** 10 seconds.
15. **Capture/assets:** No application capture. Producer creates the typography later; no stock footage is necessary.
16. **Audience understanding:** These are the chef's requirements, not AI-generated portion calculations.
17. **Supporting feature:** The following Smart order flow accepts these measured requirements; this opening itself is authored context.

### Scene 02 — The decisions behind the list

1. **Time:** 00:10–00:22.
2. **Objective:** Explain why two ingredient names are not yet an order.
3. **Screen:** 00:10–00:14 quantity labels become “Litres → sales packages”; 00:14–00:18 dietary/date labels appear; 00:18–00:22 “Item budget: €100” joins the same list.
4. **Application page:** None; explanatory decision list outside any app frame.
5. **User action:** None.
6. **Exact input:** No app input. Scenario date shown as “Requested: 17 Nov 2026”.
7. **Expected application response:** Not applicable.
8. **Motion:** Each requirement aligns to the same vertical grid; avoid floating icons or invented calculations.
9. **Camera:** Locked; no pan through imaginary webshops.
10. **Transition:** Match the green “Review” emphasis to the app frame entering Scene 03.
11. **On-screen text:** “Packages” / “Dietary evidence” / “Requested date: 17 Nov 2026” / “Item budget: €100”.
12. **Voice-over:** “But buying means more than finding a name: checking packages, dietary evidence, the requested date, and whether the items fit the budget.”
13. **Audio:** Music continues quietly; soft ticks as each decision appears, never a warning siren.
14. **Duration:** 12 seconds.
15. **Capture/assets:** Typography only, constructed later by the producer.
16. **Audience understanding:** A catalogue match must still become a suitable, affordable purchasing decision.
17. **Supporting feature:** Actual package/evidence/date/budget checks shown in subsequent scenes.

### Scene 03 — Introduce the actual workbench

1. **Time:** 00:22–00:32.
2. **Objective:** Reveal the product and connect the story to its real interface.
3. **Screen:** 00:22–00:25 actual empty Smart order page; 00:25–00:29 emphasize composer and adjacent Cart; 00:29–00:32 settle on the input area. Four existing input buttons may remain visible.
4. **Application page:** **Smart order**, at the application root.
5. **User action:** Open Smart order; no request submitted yet. Credentials and fixture setup were completed off-camera.
6. **Exact input:** None during this shot.
7. **Expected application response:** Empty composer headed “What do you need?” and Build cart; Cart has no confirmed result.
8. **Motion:** Real page appears in a restrained frame; one 700 ms reframe from whole page to composer/cart.
9. **Camera:** Begin full application, end around 120% crop. Do not shrink the UI to make room for a diagram.
10. **Transition:** Continuous framing into Scene 04.
11. **On-screen text:** “A4TB · Valio Aimo” / “Describe. Compare. Review.” plus persistent provenance label.
12. **Voice-over:** “A4TB connects that purchasing brief to real catalogue products, a reviewable basket, and checks that govern confirmation.”
13. **Audio:** Slight musical lift on reveal; no technological whoosh.
14. **Duration:** 10 seconds.
15. **Capture/assets:** R01, 8–12 seconds of clean empty-page footage, including still handles.
16. **Audience understanding:** This is a purchasing workbench, with actual products and a cart.
17. **Supporting feature:** ProcurementDesk, shared customer cart, four available input methods. This typed demo makes no speech or vision inference claim.

### Scene 04 — Enter the chef's brief

1. **Time:** 00:32–00:48.
2. **Objective:** Make the input and constraints fully reproducible.
3. **Screen:** 00:32–00:36 set date; 00:36–00:39 enter budget; 00:39–00:45 type/paste the request; 00:45–00:48 click Build cart and show the real Checking state.
4. **Application page:** **Smart order**, controls above “What do you need?”.
5. **User action:** Set **Delivery date**; enter **Maximum budget (€)**; fill composer; click **Build cart** once.
6. **Exact input:** Date `2026-11-17`; budget `100`; request `20 litres of lactose-free milk and 5 kg of butter. Show me suitable options.`
7. **Expected application response:** Request processing produces two measured lines. Show only actual loading/output captured; no fabricated token-by-token answer.
8. **Motion:** Outline the date, then budget, then request. Do not highlight all three simultaneously.
9. **Camera:** Stable medium crop containing labels, text and Build cart; small reframe as needed to keep the clicked button visible.
10. **Transition:** Cut on the completed real response to Scene 05. A removed wait is labelled “Sequence shortened”.
11. **On-screen text:** “Chef-defined quantities” / “Requested date: 17 Nov 2026” / “Item budget: €100”. Request text remains readable in the UI.
12. **Voice-over:** “The chef sets a requested date and a hundred-euro item budget, then enters the two measured ingredients. These quantities come from the chef.”
13. **Audio:** Very light real typing/click sounds, below speech; retain music bed.
14. **Duration:** 16 seconds.
15. **Capture/assets:** R02, 25–45 seconds raw, including the full actual response and 3-second holds.
16. **Audience understanding:** The buyer defines the requirements before product selection.
17. **Supporting feature:** Date/budget controls, structured text parsing and explicit Build cart.

### Scene 05 — Resolve the exact catalogue choices

1. **Time:** 00:48–01:02.
2. **Objective:** Ground the basket in two verified records rather than an imagined recommendation.
3. **Screen:** 00:48–00:51 show two separate request groups; 00:51–00:56 milk exact-SKU search/result; 00:56–01:02 butter exact-SKU search/result and the two Selected states.
4. **Application page:** **Smart order → Products** result groups; these are the groups within Smart order, not the Products navigation tab.
5. **User action:** In the original milk line's **Product search**, enter `464073`, click **Find products**; in the original butter line enter `475797`, click **Find products**. If a genuine candidate remains unselected, click its **Choose** button. A single viable direct result normally auto-selects; do not add a fictitious Choose click.
6. **Exact input:** Milk query `464073`; butter query `475797`. Required quantities stay 20 L and 5 kg. Search can change the line headings to these SKU strings.
7. **Expected application response:** Exact real product names/IDs from section 7; Selected cards; milk retains lactose-free requirement; both item quantities remain intact. The €100 budget can already produce Review requirements.
8. **Motion:** Use clean cuts between the two genuine searches; a thin outline tracks each SKU/name. Mark condensed action/wait passages “Sequence shortened”.
9. **Camera:** Crop to one line at a time, then reframe to the cart. Keep SKU and product name visible together.
10. **Transition:** Match the selected milk card into its evidence view.
11. **On-screen text:** “Actual catalogue records” / “Milk · SKU 464073” / “Butter · SKU 475797”.
12. **Voice-over:** “The chef chooses the intended catalogue records. The milk keeps its lactose-free requirement; the butter remains a separate ingredient with its own quantity.”
13. **Audio:** Quiet click on each real search/selection; no success fanfare while a budget problem remains.
14. **Duration:** 14 seconds.
15. **Capture/assets:** R03, 45–90 seconds raw. Preserve complete before/after states and the actual selection behavior.
16. **Audience understanding:** Search assists a deliberate purchasing choice; it does not certify every lexical match as appropriate.
17. **Supporting feature:** SKU search, set_query preserving hard requirements, candidate evaluation and actual cart selection.

### Scene 06 — Make quantity and evidence inspectable

1. **Time:** 01:02–01:18.
2. **Objective:** Show what makes the selected products understandable.
3. **Screen:** 01:02–01:07 milk package/order fields; 01:07–01:11 butter package/order fields; 01:11–01:18 the milk's expanded Product evidence, including declared claims and the allergen caveat.
4. **Application page:** **Smart order**, selected cards → **Product evidence**.
5. **User action:** Scroll deliberately between selected cards; click the milk card's **Product evidence**; scroll within the page to the relevant evidence. Do not toggle or change a dietary restriction.
6. **Exact input:** None. Existing requirements stay 20 L milk and 5 kg butter.
7. **Expected application response:** Milk 1 L/ST, 20 ST, 20 L; butter 0.5 kg/ST, 10 ST, 5 kg. Actual lactose-free claim and ingredient/allergen fields are visible. No surplus is shown for this basket.
8. **Motion:** Editorial arithmetic appears outside the app frame: “20 × 1 L = 20 L”, then “10 × 500 g = 5 kg”. Retain the actual source panel; no invented safety badge.
9. **Camera:** Detail crops must keep a field label with its value; pan only after a reading hold. Hold the evidence caveat for at least 3 seconds.
10. **Transition:** Clean cut to Products navigation.
11. **On-screen text:** “Sellable quantities, visible” / the two equations / “Lactose-free ≠ milk-allergy safe”.
12. **Voice-over:** “Twenty one-litre packs, and ten five-hundred-gram packs. The evidence panel exposes the declared claims and ingredients. Lactose-free does not mean safe for a milk allergy.”
13. **Audio:** Music softens under the evidence sentence; no chime suggesting safety certification.
14. **Duration:** 16 seconds.
15. **Capture/assets:** R04, 30–60 seconds raw, with evidence and quantity fields readable. No screenshots are required.
16. **Audience understanding:** Quantities are converted transparently, and suitability is grounded in supplied evidence with visible limits.
17. **Supporting feature:** Verified package conversion, product details, explicit dietary/allergen normalization and source disclosure.

### Scene 07 — Keep catalogue exploration available

1. **Time:** 01:18–01:30.
2. **Objective:** Show that the buyer can inspect a known product directly, outside the conversational shortlist.
3. **Screen:** 01:18–01:21 open Products; 01:21–01:25 search exact milk SKU; 01:25–01:28 show row/Select and package details; 01:28–01:30 return to Smart order.
4. **Application page:** Navigation **Products**, then **Smart order**. The **Review cart** button may also return to the cart.
5. **User action:** Click **Products**; enter `464073` under **Search products**; click **Search**; click the result's **Select** to inspect; return via **Smart order** or **Review cart**. **Do not click Add to cart:** the item is already present.
6. **Exact input:** `464073`. No quantity, product or budget changes.
7. **Expected application response:** Exact record appears, with the existing real package/source information. Selected inspector opens. Existing two-item cart is preserved; no duplicate line is added.
8. **Motion:** Simple tab-to-content crop; keep search/result relationship clear. No catalogue-count animation.
9. **Camera:** Medium crop of Search products and result, then wider cart framing on return.
10. **Transition:** Cut to the preserved cart and budget warning.
11. **On-screen text:** “Search the catalogue directly” / “Same purchasing context”.
12. **Voice-over:** “The Products workspace also lets the buyer inspect a known SKU directly, while keeping the purchasing context available.”
13. **Audio:** One navigation click; unchanged understated music.
14. **Duration:** 12 seconds.
15. **Capture/assets:** R05, 20–40 seconds raw. Record the unchanged cart before and after navigation.
16. **Audience understanding:** The customer retains a direct product-discovery route and control over what enters the basket.
17. **Supporting feature:** ProductWorkspace exact search, selection inspector and retained shared cart.

### Scene 08 — The meaningful stop

1. **Time:** 01:30–01:43.
2. **Objective:** Make the budget boundary unmistakable.
3. **Screen:** 01:30–01:34 show €107.10 item subtotal beside €100 budget; 01:34–01:39 hold the actual €7.10 over-budget clarification; 01:39–01:43 show disabled Review & confirm and its explanatory state.
4. **Application page:** **Smart order**, global clarification and Cart.
5. **User action:** Scroll/reframe to the actual budget message and cart. No new budget entry is necessary: €100 has applied since Scene 04. Do not pretend to click a disabled confirmation control.
6. **Exact input:** None; the existing maximum budget remains `100`.
7. **Expected application response:** Review requirements; item subtotal €107.10; budget balance −€7.10; exact clarification quoted in section 7; Review & confirm disabled. The suggested “Raise the item budget to €107.10” action may appear, but is not clicked in this script.
8. **Motion:** A single orange outline joins subtotal and budget, then moves to the real warning. Hold; let the stopped workflow be the dramatic beat.
9. **Camera:** Close enough to read €107.10/€100/€7.10 without covering the warning or disabled button.
10. **Transition:** Straight cut to the buyer editing Maximum budget (€), with the warning still contextually visible.
11. **On-screen text:** “€107.10 in items” / “€100 item budget” / “€7.10 over budget” / “Confirmation blocked”.
12. **Voice-over:** “Then the important stop: these items total a hundred and seven euros, ten cents. That exceeds the budget. Confirmation stays blocked.”
13. **Audio:** Reduce music by another 2–3 dB at the stop; one soft low click. No alarm or fabricated error sound from the app.
14. **Duration:** 13 seconds.
15. **Capture/assets:** R06, 15–25 seconds raw, with at least 5 seconds holding the complete warning and blocked action.
16. **Audience understanding:** Finding products does not authorize spending beyond the brief.
17. **Supporting feature:** Server hard-budget validation and can_confirm gating. This is a purchasing constraint, not a staged supplier shortage.

### Scene 09 — The buyer makes the decision

1. **Time:** 01:43–01:54.
2. **Objective:** Show an explicit human correction without changing product suitability.
3. **Screen:** 01:43–01:47 edit cart Maximum budget (€) to 200; 01:47–01:50 click Apply requirements and show real refresh; 01:50–01:54 hold Ready to review, unchanged subtotal and €92.90 remaining.
4. **Application page:** **Smart order → Cart** requirement form.
5. **User action:** Use cart-side **Maximum budget (€)**, then **Apply requirements**. This button is distinct from the earlier controls' **Apply**.
6. **Exact input:** `200`; requested delivery stays `2026-11-17`.
7. **Expected application response:** Both selected SKUs/quantities and milk restriction preserved; €107.10 item subtotal; €92.90 budget remaining; “Your complete item-price basket is ready for review.” Review & confirm becomes available if no other blocker exists.
8. **Motion:** Replace orange emphasis with a quiet forest outline after the genuine response. Do not animate a manager approval stamp.
9. **Camera:** Keep budget edit and button in one shot, then reframe to response/cart numbers.
10. **Transition:** Continue directly into the review action.
11. **On-screen text:** “Buyer changes the item budget: €200” / “Same products. Same requirements.” / “€92.90 item budget remaining”.
12. **Voice-over:** “The buyer explicitly raises this request's item budget to two hundred euros. The products and dietary requirement stay unchanged.”
13. **Audio:** Restore the prior music level after readiness appears; restrained tap, no fanfare.
14. **Duration:** 11 seconds.
15. **Capture/assets:** R07, 15–30 seconds raw, including actual refresh and a 4-second final hold.
16. **Audience understanding:** The human changes the commercial instruction; the assistant never silently relaxes it.
17. **Supporting feature:** Versioned set_budget/date handling, fresh quotation and preserved hard requirements.

### Scene 10 — Review and record the simulated order

1. **Time:** 01:54–02:06.
2. **Objective:** Complete the demonstrated workflow with genuine customer confirmation.
3. **Screen:** 01:54–01:57 show item subtotal/date/selected products; 01:57–02:00 click Review & confirm and hold the confirmation review; 02:00–02:03 click Confirm simulated order and retain real processing; 02:03–02:06 reveal the actual saved receipt.
4. **Application page:** **Smart order → Cart → confirmation review → simulated receipt**.
5. **User action:** **Review & confirm**, then **Confirm simulated order**, once each. If confirmation takes longer, shorten only the wait with disclosure, never replace its result.
6. **Exact input:** No new text. Confirm the existing two-SKU basket for 17 November 2026, €107.10 in items.
7. **Expected application response:** “Simulated order recorded.” / “Your order, on the record.” Actual generated reference, two items, requested date and item subtotal. No reference is predetermined in this brief. The receipt states no supplier order, invoice or payment was created.
8. **Motion:** Follow the real confirmation panel; one subtle focus on the resulting reference. No truck, payment tick or supplier logo approval animation.
9. **Camera:** Medium cart crop for both clicks, then wider receipt crop retaining the simulation notice.
10. **Transition:** Hold the receipt and continue into verification.
11. **On-screen text:** “Review first. Confirm explicitly.” / “Simulated order recorded” / “No supplier order, invoice or payment”.
12. **Voice-over:** “After reviewing the items and date, the buyer confirms a simulated order. The saved receipt records the decision; no supplier purchase is made.”
13. **Audio:** One subtle confirmation tone only after actual success. Music continues beneath narration.
14. **Duration:** 12 seconds.
15. **Capture/assets:** R08, 30–60 seconds raw. Keep complete processing, genuine receipt and warnings in the source take.
16. **Audience understanding:** A real application result has been saved, with an explicit simulation boundary.
17. **Supporting feature:** Confirmation review, server revalidation, atomic/idempotent simulated processing and persistent receipt.

### Scene 11 — Check the saved decision

1. **Time:** 02:06–02:14.
2. **Objective:** Show inspectability after confirmation and connect the result to practical value.
3. **Screen:** 02:06–02:08 click Verify receipt; 02:08–02:12 hold actual verification text; 02:12–02:14 retain the receipt as the closing line begins visually.
4. **Application page:** **Smart order → saved receipt**.
5. **User action:** Click **Verify receipt** once; wait for the real response.
6. **Exact input:** None. Use the genuine receipt created in Scene 10.
7. **Expected application response:** “The saved receipt matches this recorded order. This verifies our simulator record.” Do not infer supplier acceptance or an external signature.
8. **Motion:** Outline the saved-record verification message once, then remove emphasis.
9. **Camera:** Locked readable close-up; do not zoom into an invented hash animation.
10. **Transition:** Six-frame dissolve from paper receipt surface into the matching closing card.
11. **On-screen text:** “Choices explained. Decisions reviewable.” / “Saved simulator record verified”.
12. **Voice-over:** “The buyer can verify the saved record: clear quantities, visible constraints, and a decision they can inspect.”
13. **Audio:** Soft verification tap after success; begin a gentle musical resolution.
14. **Duration:** 8 seconds.
15. **Capture/assets:** R09, 10–20 seconds raw, with a 5-second verified-state hold.
16. **Audience understanding:** The result remains inspectable; verification concerns the simulator's saved record.
17. **Supporting feature:** Scoped persisted receipt integrity/consistency check.

### Scene 12 — A restrained, memorable close

1. **Time:** 02:14–02:20.
2. **Objective:** Leave one product idea and an honest closing identity.
3. **Screen:** 02:14–02:16 current brand; 02:16–02:20 supporting line and prototype notice. Hold the final composition to the last frame.
4. **Application page:** None; editorial closing card.
5. **User action:** None.
6. **Exact input:** None.
7. **Expected application response:** Not applicable.
8. **Motion:** 400 ms fade/8 px rise for brand; 300 ms supporting-line fade; no logo morph.
9. **Camera:** Locked.
10. **Transition:** End exactly at 02:20. No extra end slate, black tail or credits beyond the duration.
11. **On-screen text:** “A4TB · Valio Aimo” / “Describe. Compare. Review.” / “Junction 2026 prototype · Simulated orders”.
12. **Voice-over:** “A4TB. From a kitchen's need to a decision you can inspect.”
13. **Audio:** Resolve gently; finish the fade by 02:19.8 without cutting a spoken word.
14. **Duration:** 6 seconds.
15. **Capture/assets:** Producer-created typography only; use existing permitted branding, not a new generated logo.
16. **Audience understanding:** The product's value is a transparent, controlled purchasing decision.
17. **Supporting feature:** Synthesis of the demonstrated workflow; no new capability is introduced.

## 10. Exact English voice-over — 2:20 master

Read conversationally, with precise consonants and an unhurried tone. Pronounce A4TB as **“A-four-T-B”**, “litres” naturally, and euros clearly. Use the timed speech windows below; remain silent in the specified holds. Aim roughly 125–145 spoken words per minute, varying naturally with the sentence. Record a scratch read before final animation timing. Do not accelerate the recording to fit; trim optional visual holds first while preserving these scene boundaries.

| Speech window | Exact narration | Pause/hold |
|---|---|---|
| 00:00.6–00:09.4 | Fifty guests for breakfast. The chef already knows the shopping list: twenty litres of lactose-free milk, and five kilos of butter. | 00:00.0–00:00.6 opening breath; 00:09.4–00:10.0 hold. Brief natural pause after “breakfast.” |
| 00:10.5–00:21.0 | But buying means more than finding a name: checking packages, dietary evidence, the requested date, and whether the items fit the budget. | 00:10.0–00:10.5 and 00:21.0–00:22.0 silent. |
| 00:22.5–00:31.1 | A4TB connects that purchasing brief to real catalogue products, a reviewable basket, and checks that govern confirmation. | 00:31.1–00:32.0 visual hold. |
| 00:32.5–00:44.6 | The chef sets a requested date and a hundred-euro item budget, then enters the two measured ingredients. These quantities come from the chef. | 00:44.6–00:48.0 type/click/loading hold. |
| 00:48.5–01:00.0 | The chef chooses the intended catalogue records. The milk keeps its lactose-free requirement; the butter remains a separate ingredient with its own quantity. | 01:00.0–01:02.0 selected-state hold. |
| 01:02.4–01:16.4 | Twenty one-litre packs, and ten five-hundred-gram packs. The evidence panel exposes the declared claims and ingredients. Lactose-free does not mean safe for a milk allergy. | Brief pause after each sentence; 01:16.4–01:18.0 caveat hold. |
| 01:18.5–01:28.0 | The Products workspace also lets the buyer inspect a known SKU directly, while keeping the purchasing context available. | 01:28.0–01:30.0 return-to-cart hold. |
| 01:30.4–01:41.0 | Then the important stop: these items total a hundred and seven euros, ten cents. That exceeds the budget. Confirmation stays blocked. | 0.4-second pause after “stop”; 01:41.0–01:43.0 blocked-state hold. |
| 01:43.4–01:52.8 | The buyer explicitly raises this request's item budget to two hundred euros. The products and dietary requirement stay unchanged. | 01:52.8–01:54.0 ready-state hold. |
| 01:54.4–02:05.5 | After reviewing the items and date, the buyer confirms a simulated order. The saved receipt records the decision; no supplier purchase is made. | 02:05.5–02:06.0 hold; pause after “simulated order.” |
| 02:06.3–02:13.6 | The buyer can verify the saved record: clear quantities, visible constraints, and a decision they can inspect. | 02:13.6–02:14.0 hold. |
| 02:14.3–02:19.5 | A4TB. From a kitchen's need to a decision you can inspect. | Short brand pause; 02:19.5–02:20.0 music/end hold. |

Keep subtitles verbatim to the spoken recording. Do not insert an unscripted “AI places the order” line, a savings claim, a testimonial or an unfilmed manager approval.

## 11. Exact on-screen text

The following are **editorial overlays**, separate from actual UI text. Do not replace native labels, product names, warnings or receipts with these overlays.

| Master interval | Overlay copy |
|---|---|
| 00:02–00:10 | **One kitchen. Fifty guests.** / **20 L lactose-free milk** / **5 kg butter** / small: **Illustrative breakfast-service scenario** |
| 00:10–00:22 | **Packages** / **Dietary evidence** / **Requested date: 17 Nov 2026** / **Item budget: €100** |
| 00:22–00:32 | **A4TB · Valio Aimo** / **Describe. Compare. Review.** |
| 00:32–00:48 | **Chef-defined quantities**; then **Requested date: 17 Nov 2026**; then **Item budget: €100**. Show sequentially. |
| 00:48–01:02 | **Actual catalogue records** / **Milk · SKU 464073** / **Butter · SKU 475797** |
| 01:02–01:18 | **Sellable quantities, visible** / **20 × 1 L = 20 L** / **10 × 500 g = 5 kg** / **Lactose-free ≠ milk-allergy safe** |
| 01:18–01:30 | **Search the catalogue directly** / **Same purchasing context** |
| 01:30–01:43 | **€107.10 in items** / **€100 item budget** / **€7.10 over budget** / **Confirmation blocked** |
| 01:43–01:54 | **Buyer changes the item budget: €200** / **Same products. Same requirements.** / **€92.90 item budget remaining** |
| 01:54–02:06 | **Review first. Confirm explicitly.** / **Simulated order recorded** / **No supplier order, invoice or payment** |
| 02:06–02:14 | **Choices explained. Decisions reviewable.** / **Saved simulator record verified** |
| 02:14–02:20 | **A4TB · Valio Aimo** / **Describe. Compare. Review.** / **Junction 2026 prototype · Simulated orders** |

**Persistent label on every application shot, including detail crops:**

> Challenge catalogue · Authored fixture prices & stock · Simulated orders

Use a readable, quiet two-line treatment if necessary. Maintain it from 00:22 through 02:14 in the master and on every application shot in the short cut. It must remain present when the app's own Demo prices badge is outside the crop.

**Additional small label on edited waits/actions:** “Sequence shortened”. Never use “real time” for a condensed sequence.

**Price-scope footer when subtotal/budget/receipt is emphasized:** “Tax-inclusive items · Delivery/service charges excluded”. Keep the application's “Availability is not a reservation” notice readable at least once, and repeat it editorially if the native text cannot fit the selected crop.

Do not show every overlay for an entire scene. Reveal one short idea at a time. For silent viewing, preserve the problem, exact requirements, budget failure, explicit change and simulated result through these labels plus subtitles.

## 12. Motion graphics instructions

1. **Build the story from real states.** Empty composer → actual request → returned lines → selected records → evidence → preserved cart → blocked budget → corrected budget → confirmation → receipt → verification. Do not reverse those states or cut a failed take into a successful take as though they were one continuous transaction.
2. **Use conceptual graphics sparingly.** The opening list explains the work. It is not a reconstructed production Valio webshop. If an explanatory arrow is used, label the relationship “Request → Catalogue → Checks → Buyer review”; do not invent multiple agents negotiating with suppliers.
3. **Animate quantities only from verified values.** Milk 20 × 1 L; butter 10 × 0.5 kg. No excess-packs or waste-reduction claim applies to this basket. A number reveal must finish before narration moves to the next fact.
4. **Show the budget comparison as a decision.** Put €107.10 and €100 on the same baseline; identify the €7.10 gap. Keep the real blocked action visible. After the buyer's edit, show €200 and €92.90 remaining; €107.10 never changes in this recovery.
5. **Protect meaning during zooms.** Keep product identity with the SKU, units with quantities, warning with affected action, and “simulated” with the receipt. Crop for readability, not to hide qualification.
6. **Use controlled scale.** A full-page view should normally remain at or above 80% of capture scale. Use detail crops up to roughly 140–160% from a sufficiently sharp source, with no blurry enlargement. Capture higher resolution if needed.
7. **Respect real interaction timing.** Record uncut source takes. Real idle waits may be removed with “Sequence shortened”; do not animate a faster fake answer or imply an SLA. Do not speed up readable evidence/warnings.
8. **Use one accent at a time.** Forest for focus, orange for the blocked budget, mint for actual ready/verified states. Pair color with words. Do not attach green “safe” shields to foods.
9. **Keep layout consistent.** Suggested 96 px title-safe outer margin; captions in a dedicated lower region; provenance above captions or in a reserved top strip. Never cover a field the viewer needs to read.
10. **Avoid redundant spectacle.** No avatars, synthetic chef testimonial, autogenerated kitchen footage, fake terminal walls, 3D trucks, model-brain graphic or celebrity-style narration is required.

## 13. Real application recording instructions

### Preflight — complete before the clean take

- Use the hosted URL in section 7 or the already prepared local app. If local startup is needed, follow the existing README (`./start.sh`); do not change code, patch validation, reset accounts or redeploy to make this video work.
- Use a dedicated synthetic buyer workspace with default saved preferences, no genuine customer information and enough remaining synthetic spend. Sign in **off-camera**. Do not expose access codes, passwords, invitation codes, browser autofill, `.env`, developer tools, private reports or account contacts.
- Open **Smart order**. If an old draft is shown, **New request** starts a separate draft without deleting earlier receipts. Do not delete history or reset the spending ledger as part of recording.
- Before creating the new session, open **Demo tools → Data & model settings**. In the resulting **Demo settings**, set **Quotation source → Authored fixture prices & stock**. Leave **Use NVIDIA for nonconfidential demo requests** unchecked. The quotation source is locked once a session exists; restart with New request if necessary. Collapse settings without switching the source back.
- Check **Buying preferences** in this synthetic workspace. Mandatory restrictions must be empty for this exact two-line rehearsal; the request itself applies lactose-free to milk. Use a fresh demonstration account rather than removing someone's genuine allergy restrictions. Default priority is **Balanced · let me compare**. A globally saved lactose-free or milk-allergy restriction could legitimately block the chosen butter.
- Set **Delivery date = 2026-11-17** before **Maximum budget (€) = 100**. Confirm the date remains visible when setting the budget. Avoid relative “tomorrow”/“Monday” wording.
- Date-sensitive operation matters: delivery must remain within the app's permitted current-to-next-30-days window, and the authored purchasing policy expires **30 November 2026 at 21:59:59 UTC**. On the audit date, 17 November is valid. If recording later, use a legitimately valid date and update every related title/narration/receipt reference consistently. Changing the date does not bypass an expired policy. If the policy has expired, obtain an appropriately maintained application before recording; do not falsify the receipt or modify code for the film.
- A ready quote lasts up to approximately **five minutes**, bounded by policy/evidence expiry. Finish confirmation within its displayed validity. If it expires, click **Refresh prices & availability**, review the new state and record that state honestly. Never hide a blocker behind editing.
- Use desktop recording with notifications off, a clean browser profile and no private tabs/bookmarks visible. Capture an application viewport around 1440 × 900 or larger at a sharp native scale; master delivery is 1920 × 1080. Give UI detail enough pixel area. Record cursor and actual loading states. Do not inject CSS or use a fake interface.
- Run one rehearsal through the final receipt before committing to the edit. The source/in-memory checks in this brief do not substitute for that rehearsal. If any expected value differs, investigate source mode, preferences, quantities, policy and quote freshness; do not paint over the discrepancy.

### Shot-by-shot capture recipes

**R01 — Empty Smart order; supports Scene 03.**

Open Smart order after the off-camera setup, before typing. Show “What do you need?”, date/budget controls, four input methods and empty Cart. Do not click media controls. Record 8–12 seconds with 3-second still handles. Highlight composer-to-cart relationship. Expected: no order or product result yet.

**R02 — Request entry; supports Scene 04.**

Record setting date `2026-11-17`, then budget `100`, then typing/pasting the exact sentence from section 7. Click Build cart once. Record the complete real response and both measured line groups, including any initial questions. Raw length 25–45 seconds, longer if required by the app. Highlight the entered constraints, not assumed perfect candidate ranking.

**R03 — Exact record resolution; supports Scene 05.**

In the original milk group's Product search, replace its current query with `464073`; Find products. Wait. Expect the named 1 L lactose-free UHT milk record, 20 L requirement preserved. In the original butter group's Product search, enter `475797`; Find products. Expect the named salted 500 g butter, 5 kg requirement preserved. The single eligible record normally auto-selects. If it shows Choose instead, click that actual button after inspection. Record each whole search/response and a 4-second Selected hold. Raw length 45–90 seconds. Expect two items, €107.10 item subtotal, €100 budget and blocked confirmation. Do not click the Products tab's Add to cart during these searches.

**R04 — Evidence and packs; supports Scene 06.**

Record the milk's 1 L sales package, 20 ST order and 20 L effective quantity; then the butter's 0.5 kg sales package, 10 ST and 5 kg. Click milk Product evidence. Record actual Declared dietary claims, Ingredients & allergen evidence, relevant package/source fields and the lactose/milk-allergy caveat. Raw length 30–60 seconds. No safety claim should be inferred from an unlisted allergen. Do not manufacture a surplus label; both requirements fit exactly.

**R05 — Products lookup without cart mutation; supports Scene 07.**

Click navigation Products. Search products: `464073`; Search. Expect that exact catalogue record. Click Select to inspect it; the inspector's initial quantity/unit are browsing defaults, not a replacement of the existing 20 L cart requirement. Do not click Add to cart. Return via Smart order or Review cart. Record the two original items before/after, raw 20–40 seconds. If any filters were left active in the synthetic browsing workspace, Reset filters before searching; mandatory saved restrictions are separate and cannot be bypassed by that button.

**R06 — Actual budget stop; supports Scene 08.**

With the same cart and budget still 100, record the exact €7.10 over-budget clarification, subtotal €107.10, budget and disabled Review & confirm. Do not attempt a fake disabled-button click. Hold the message at least 5 seconds; record 15–25 seconds total. The native Raise the item budget to €107.10 option is a real proposed action, not an automatic change, and is not used in this take.

**R07 — Explicit correction; supports Scene 09.**

In Cart → Maximum budget (€), enter `200`; click Apply requirements. Keep requested delivery unchanged. Record actual processing. Expect Ready to review, the exact complete-basket response, unchanged selected IDs/quantities, €107.10 item subtotal, €92.90 remaining and an available Review & confirm. Raw 15–30 seconds. If anything else is unresolved, stop and resolve it openly before the clean take. No manager login belongs in this under-threshold story.

**R08 — Genuine confirmation; supports Scene 10.**

Refresh prices & availability first if the displayed quote is stale; recheck values. Record Review & confirm, the real confirmation review, then Confirm simulated order once. Capture full processing and the genuine resulting reference, requested date, item rows and subtotal. Expected headings: “Simulated order recorded.” and “Your order, on the record.” Keep the no-supplier-order/invoice/payment notice. Raw 30–60 seconds plus a 6-second receipt hold. A lost response is not permission to invent success; reopen the saved state and inspect it. Do not start another new purchase just to get another receipt shot.

**R09 — Verify; supports Scene 11.**

On that same saved receipt, click Verify receipt. Record the complete response: “The saved receipt matches this recorded order. This verifies our simulator record.” Hold 5 seconds, raw 10–20 seconds total. Verify receipt is not a purchase retry and does not demonstrate supplier fulfillment. Retain the real generated reference consistently across final shots; never type a plausible replacement ID.

### If rehearsal does not match

Use the actual warning to diagnose the discrepancy. A live source will not necessarily have fixture prices. A changed saved restriction may correctly reject the butter. A stale date, expired quote/policy or exhausted synthetic cap can block confirmation. Do not silently substitute a different product, erase a dietary rule, edit the screen or narrate a failed request as success. Rehearse on a valid configured environment; if unavailable, the film must clearly end at the actual reviewed/blocked state and its script must be revised before production. This storyboard's successful ending is contingent on capturing the genuine successful simulator path.

**Optional input-method pickup, outside both timed cuts:** If the owner later wants separate instructional footage, Voice input → microphone permission → speak the exact request → Stop & transcribe → Review extracted text → edit Editable extracted text → Add to request → Build cart. The microphone limit is 30 seconds. Images similarly require review/add; use only nonconfidential demonstration JPEG/PNG originals up to 5 MiB. Neither media extraction automatically creates an order. This pickup is not required to tell the selected story and must not be spliced into the typed take as though it caused that result.

## 14. Differentiation from existing solutions

| Comparison | Demonstrated additional value | Evidence in the film |
|---|---|---|
| Existing wholesale e-commerce | A measured brief, product evidence, sellable quantities and constraint outcome are connected in one reviewed workflow. Existing Valio services remain acknowledged. | Scenes 04–06. |
| Manual procurement work | The buyer can inspect pack arithmetic, sources and budget consequences without reconstructing those facts from a chat response. | Scene 06 and the cart. |
| Basic catalogue search | Finding a SKU does not end the process; the basket must also meet the request's rules before confirmation. | Scenes 07–09. |
| Ordinary AI chatbot | Generated advice cannot grant spending permission. The actual server blocks the over-budget basket, and the buyer explicitly changes the brief. | Scenes 08–10. |
| An ordering assistant without inspectable controls | The saved simulated outcome preserves items, date, price scope and a verifiable internal record. | Scenes 10–11. |

Describe these as the demonstrated design, not a claim that every competing assistant lacks them. The documented versioned HTTP/OpenAPI gateway and independent agent client provide a credible integration path, but are not an extra filmed claim unless genuine client footage is separately captured. Do not imply this typed fixture take exercised a live external model or supplier API.

## 15. Business benefits

- **Less repeated translation of needs into packages:** the film shows litres/kilograms alongside sales packages. Human suitability review remains necessary.
- **Clearer product decisions:** the viewer can inspect the actual SKU and supplied evidence rather than trust an unsupported sentence.
- **Visible spending consequences:** the €7.10 budget gap is explicit, with an enforced stop and an intentional buyer correction.
- **Human control at the point of commitment:** review and confirmation are separate visible actions; the request's budget is not silently widened.
- **A reviewable saved result:** the same simulator receipt can be checked after confirmation.

These are mechanism-based benefits demonstrated by the film. Do not quantify hours saved, lower food waste, carbon reductions, increased revenue, fewer allergy incidents or procurement savings. No measured customer improvement or testimonial exists for this scenario. The change from €100 to €200 is a budget decision, not a saving.

## 16. Required assets

The future producer needs only:

- Clean real application recordings **R01–R09** from the same synthetic scenario and genuine resulting receipt.
- Existing permitted application/brand treatment, or plain typeset “A4TB · Valio Aimo”. No new logo or partner endorsement is needed.
- Editorial opening/closing typography and simple outlines/equations specified above, created during later video production.
- The exact English narration, recorded cleanly; accurate English subtitle file plus a captioned export.
- Appropriately licensed minimal instrumental music and a small set of restrained click/tap accents, or silence where clearer.

No screenshots are mandatory; genuine held recording frames can supply the pauses. No customer portrait, testimonial, generated kitchen image, animation asset pack, stock supplier offer, invented invoice, synthetic receipt or fake UI is required. Do not show raw restricted catalogue files, API keys or private reports. Use only the two necessary product records as they appear in the actual application, subject to the challenge's display terms.

Keep all source takes with enough context to audit the selected edit. Suggested production filenames: `R01_empty`, `R02_request`, `R03_catalogue_choices`, `R04_evidence`, `R05_products`, `R06_budget_stop`, `R07_budget_change`, `R08_simulated_receipt`, `R09_verification`. These are future production labels, not files created by this brief.

## 17. Music and sound design

Use a warm, sparse instrumental bed at approximately 90–110 BPM: muted percussion, soft keys/plucks and a restrained sustained texture. No vocals, dramatic risers or cinematic impacts. The emotional curve is focused preparation → useful clarity → brief pause at the blocked budget → calm resolution after the human decision.

Record voice in a quiet, dry environment at 48 kHz. Keep narration centered, clear and consistent. Suggested final web mix: approximately **−16 LUFS integrated**, peaks at or below **−1 dBTP**. These are production targets, not verified Junction requirements. Keep music roughly 18–24 dB below narration by ear and duck it further for the budget/evidence sentences. Avoid a noisy bed during silence holds.

Clicks should correspond to actual recorded interactions. Add only a small editorial accent after real readiness, confirmation or verification. Do not imply that a sound was emitted by the application. Resolve the music within the exact runtime; no audible tail extends the short cut past its limit.

## 18. Export specifications

Unless the current authenticated Junction requirements state otherwise, use these **recommended** settings:

| Item | Setting |
|---|---|
| Container | MP4 |
| Resolution / aspect | 1920 × 1080, 16:9 |
| Frame rate | Constant 30 fps, progressive |
| Video codec | H.264, High profile, broadly compatible playback; approximately 12–20 Mbps VBR, adjusted for readable UI |
| Color | Standard SDR Rec.709; check that greens and warnings remain distinguishable |
| Audio | AAC, 48 kHz, stereo, approximately 192–256 kbps |
| Narration / subtitles | English voice-over; accurate English captions, no more than two lines at once |
| Launch master | Exactly 02:20 / 4,200 frames; optional use outside submission unless longer is explicitly allowed |
| Junction cut | Exactly 01:55 / 3,450 frames, including every opening/end frame and audio tail |
| Caption delivery | Captioned MP4 plus matching SRT/VTT sidecar when the selected host supports it |
| Naming | `A4TB_Valio_Aimo_Launch_140s.mp4`; `A4TB_Valio_Aimo_Junction_115s.mp4` |

For silent comprehension, check the export muted from beginning to end. The requirements, two selected SKUs, package quantities, over-budget state, buyer's budget change and simulated result must remain understandable through visuals and captions. Keep captions/source labels outside the UI action area; reposition them for individual shots rather than covering a key warning. Use readable contrast and retain labels with units. Do not rely on color or sound alone.

Before any later publication, verify the chosen video's link works without the viewer's private login and that the current form accepts that host. A raw MP4 is an export format, not proof that a submission platform accepts direct uploads. No particular host, maximum video filesize or platform-specific link restriction was verified here. Uploading and final submission are outside the creation of this prompt.

## 19. Short two-minute version — complete 1:55 submission cut

**Target:** 115 seconds / 3,450 frames at 30 fps. Use this version for the recorded two-minute Junction limit. Retain the full customer problem, actual request, product evidence, enforced budget stop, human change, confirmation and saved result. Do not speed the 2:20 narration up to fit.

### Exact shortened timeline, visuals, actions and revised narration

The scenario, two SKUs, date, fixture prices, initial €100 and corrected €200 budget remain identical. R01–R09 remain the source takes; no new transaction is necessary. Every application shot retains the persistent fixture/simulation label, and edited waits retain “Sequence shortened”.

| Scene / interval / duration | Required visual and exact action | Exact revised English narration and speech window | Exact editorial text / motion |
|---|---|---|---|
| **S01 · 00:00–00:08 · 8s** | Editorial scenario card, then the two chef-defined quantities. No application output claimed. | **00:00.4–00:07.6:** “Fifty breakfast guests. Twenty litres of lactose-free milk. Five kilos of butter. Every purchase needs a decision.” Hold 00:07.6–00:08.0. | “One kitchen. Fifty guests.” / “20 L lactose-free milk · 5 kg butter” / small “Illustrative scenario”. Same restrained reveal as master. |
| **S02 · 00:08–00:16 · 8s** | Compact decision list: packs, evidence, date, budget. Transition into actual empty Smart order at the end. | **00:08.3–00:15.6:** “The chef must still check packages, dietary evidence, a requested date, and the item budget.” Hold 00:15.6–00:16.0. | “Packages · Evidence · Date · Budget”; no fake webshop. |
| **S03 · 00:16–00:24 · 8s** | R01 actual Smart order, composer and Cart in one readable frame. No provider call implied. | **00:16.3–00:23.5:** “A4TB connects the brief to real catalogue products, a reviewable basket, and checks before confirmation.” Hold 00:23.5–00:24.0. | “A4TB · Valio Aimo” / “Describe. Compare. Review.” plus provenance. |
| **S04 · 00:24–00:38 · 14s** | R02 date `2026-11-17`, budget `100`, exact full request, Build cart, real response. Use the same input sentence from section 7. | **00:24.5–00:35.8:** “The chef enters the measured ingredients, sets the requested date, and starts with a hundred-euro item budget. The quantities are the chef's.” Hold 00:35.8–00:38.0 for click/response. | “Requested: 17 Nov 2026” / “Item budget: €100” / “Chef-defined quantities”. Move outline date → budget → request. |
| **S05 · 00:38–00:52 · 14s** | R03 per-line Product search `464073` → Find products; `475797` → Find products. Preserve actual automatic Selected behavior; Choose only if genuinely needed. | **00:38.4–00:49.8:** “Two catalogue choices become the basket. The milk retains its lactose-free requirement, while the butter has its own quantity. The chef reviews both.” Hold 00:49.8–00:52.0. | “Actual catalogue records” / “Milk · SKU 464073” / “Butter · SKU 475797”. Disclose shortened sequence. |
| **S06 · 00:52–01:05 · 13s** | R04 package fields, then milk Product evidence and allergen caveat. Retain both real quantities. | **00:52.3–01:04.4:** “Twenty one-litre packs. Ten five-hundred-gram packs. The evidence panel exposes the declared claims and ingredients. Lactose-free does not mean milk-allergy safe.” Hold 01:04.4–01:05.0. | “20 × 1 L = 20 L” / “10 × 500 g = 5 kg” / “Lactose-free ≠ milk-allergy safe”. No surplus animation. |
| **S07 · 01:05–01:18 · 13s** | R06 actual €107.10 subtotal, €100 budget, €7.10 clarification and disabled Review & confirm. No fake click. | **01:05.4–01:16.7:** “The items total a hundred and seven euros, ten cents: seven euros, ten over budget. Confirmation is blocked until the buyer changes the request.” Hold 01:16.7–01:18.0. | “€107.10 in items” / “€100 item budget” / “€7.10 over budget” / “Confirmation blocked”. Music dips. |
| **S08 · 01:18–01:30 · 12s** | R07 enter cart budget `200`; Apply requirements; actual Ready to review, same products/date/subtotal and €92.90 remaining. | **01:18.4–01:28.6:** “The buyer explicitly raises this request's item budget to two hundred euros. The selected products and the milk's dietary requirement remain unchanged.” Hold 01:28.6–01:30.0. | “Buyer changes item budget: €200” / “Same requirements” / “€92.90 remaining”. Gentle forest emphasis after real response. |
| **S09 · 01:30–01:43 · 13s** | R08 Review & confirm → genuine review panel → Confirm simulated order → actual saved receipt. Keep source/date/amount and simulation warning. | **01:30.4–01:41.7:** “After review, the buyer confirms a simulated order. The receipt records the selected items and requested date. No supplier order, invoice or payment is created.” Hold 01:41.7–01:43.0. | “Review. Confirm.” / “Simulated order recorded” / “No supplier order, invoice or payment”. No fulfillment imagery. |
| **S10 · 01:43–01:50 · 7s** | R09 Verify receipt; actual saved-record verification text. Retain genuine reference and simulation scope. | **01:43.3–01:49.5:** “Verify the saved record: clear quantities, visible constraints, a decision to inspect.” Hold 01:49.5–01:50.0. | “Saved simulator record verified” / “Choices explained. Decisions reviewable.” One outline; no external certification badge. |
| **S11 · 01:50–01:55 · 5s** | Closing typography; end on held card at exactly 01:55. | **01:50.2–01:54.4:** “A4TB. Describe. Compare. Review.” Hold 01:54.4–01:55.0. | “A4TB · Valio Aimo” / “Describe. Compare. Review.” / “Junction 2026 prototype · Simulated orders”. Music resolves by 01:54.8. |

This table is the complete revised short-cut voice-over in chronological order; read only its narration cells, with the specified pauses. Do not carry over the master-only Products-workspace sentence.

### Exact changes from the master

- Opening reduced from 10 to 8 seconds; problem 12 to 8; product reveal 10 to 8; request 16 to 14; evidence 16 to 13; verification 8 to 7; close 6 to 5.
- **Remove master Scene 07 / Products-tab detour entirely** (12 seconds). Product discovery remains proven inside Smart order; do not claim a direct Products-tab interaction occurred in the short cut.
- Keep catalogue selection and budget stop at 14 and 13 seconds. Give recovery 12 seconds and confirmation 13 seconds, allowing the central decision and explicit simulated confirmation to remain readable.
- The closing is revised to the exact shorter wording above. No extra credits, source slate, black tail or host-branded outro may extend the 1:55 file.

The short cut must preserve the real cause/effect chain: request constraints → selected products → over-budget block → buyer edit → ready state → explicit simulated confirmation → genuine saved-record verification. Removing the direct Products-tab detour does not remove the central catalogue grounding.

## 20. Final production checklist

### Product truth and reproducibility

- [ ] Current application branding and actual visible control labels are used; no fictional page routes or fabricated UI.
- [ ] Fifty guests are identified as scenario context; ingredient quantities come from the chef, not an unshown recipe/portion engine.
- [ ] Milk SKU **464073**, butter SKU **475797**, 20 L/5 kg, exact package quantities and fixture pricing match the recorded application.
- [ ] The butter is not described as lactose-free; no whole-meal allergen-safety or dietary certification claim appears.
- [ ] “Challenge catalogue · Authored fixture prices & stock · Simulated orders” remains readable on every application crop.
- [ ] Fixture commercial facts are never described as live offers. No live text-model inference is claimed for the local-parser take.
- [ ] €107.10 is consistently an **item subtotal**; delivery/service exclusions and non-reservation scope remain clear.
- [ ] Original budget €100, actual €7.10 block, explicit buyer change to €200 and €92.90 remaining appear in the correct causal order.
- [ ] No manager approval is implied for this basket. No dietary rule or server authority is silently waived.
- [ ] Required date and policy/quote validity are checked at recording time. Expired state is refreshed or resolved honestly.
- [ ] Confirmation is captured from the real app, with the genuine generated reference and no invented successful transaction.
- [ ] Receipt verification is described as checking the simulator record; no supplier acceptance, reservation, payment or delivery is implied.

### Story, readability and sound

- [ ] The viewer can identify the customer, the purchasing problem, the assistant's role and the human decision without prior project knowledge.
- [ ] The actual application occupies the majority of the demonstration; opening/closing titles remain brief.
- [ ] Product names, units, warnings and clicked controls remain readable at 1920 × 1080 and in a normal embedded player.
- [ ] Every shortened wait/action sequence is labelled; no speed, latency or savings claim is invented.
- [ ] Captions match the final narration; voice-over and screen state agree; the complete film remains understandable muted.
- [ ] Music supports the voice; clicks match real actions; no fake safety/fulfillment sound or imagery changes the meaning.
- [ ] No generic robot/neural-network montage, excessive neon, dramatic transition, testimonial or numerical outcome claim appears.
- [ ] No credentials, private account details, restricted raw dataset views or secret-bearing developer panels appear in any frame.

### Delivery and Junction use

- [ ] The optional launch master is exactly **2:20** and is not labelled submission-compliant without current official permission.
- [ ] The submission-duration cut is exactly **1:55**, including captions, closing frames and audio tail; it remains below the earlier recorded two-minute maximum.
- [ ] MP4/H.264/AAC, 1080p, 16:9 and 30 fps are treated as recommended settings, subject to the authenticated current form.
- [ ] Current official duration, public-viewing and host requirements are checked before any later upload. Source-access/licensing obligations are handled separately from restricted challenge data.
- [ ] This brief's creation has produced only the requested production prompt. It does not create media, modify the application, publish source or finalize a Junction submission.

**Final creative instruction:** Make the audience remember the moment a found basket is still not permitted to proceed. Then show the buyer's explicit decision and the real saved simulated result. Let the working product, its evidence and its boundaries carry the story.
