# A4TB · Valio Aimo — demonstration

Open **[A4TB · Valio Aimo](https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site)** and sign in with the private buyer code. The public Sites entry point proxies the code-gated application on Modal; the source remains private. Do not put credentials into the URL or share them publicly. Every confirmation is a simulated order.

1. Choose **Stock the breakfast kitchen**, then **Build my cart** in explicitly labelled rehearsal mode. Inspect selected SKUs, quantities, whole-pack surplus, subtotal and source.
2. Enter **Reduce the butter to 5 kg**. Milk and cheese remain selected. Set a very small budget to see the hard conflict; explicitly increase it to continue. Product search can find other catalog options while preserving diet/origin constraints.
3. Review and confirm the simulated order. **Verify receipt** checks the saved simulator record. Reload to recover the same order. No supplier purchase, invoice or payment occurs.
4. Open **Meal planner**. Build the editable 500-diner plan; inspect the four dietary groups and origin evidence. Choose products, set date and **Quote this shopping plan**. Smart order preserves the recipe and choices; missing product claims/conversions block checkout. Acknowledge recipe review only after actually reviewing it.
5. For current synthetic commercial evidence choose **Live sponsor sandbox** and NVIDIA interpretation on a new order. Example: **20 litres of lactose-free milk and 5 kg of butter by Monday. Budget €500. Choose the cheapest suitable products.** Actual deployed NVIDIA interpretation and Valio price/availability reads were verified on 14 November; current results may differ. Provider outages remain visible and do not switch to fixtures.
6. Use **Trust scenarios** for the existing exact manager-approval, hard dietary failure and stale-offer repair demos documented below. The buyer cannot approve itself. Whole-basket Smart order approval uses the same separately authenticated manager role under its own authored demo policy.

The shared synthetic cumulative cap applies to all confirmed demonstrations. Do not reset it automatically or change policy to make a failed scenario appear successful. Use a temporary local ledger for repeated QA.

---

## Original milk trust demonstration

The following script covers the original milk Trust scenarios retained inside A4TB · Valio Aimo. Every order is simulated and no final Junction submission is authorized. A local fixture video was recorded, as described below; no public upload is claimed.

## Two-minute story

| Time | On screen | Say |
| --- | --- | --- |
| 0:00-0:15 | The brief and mandate | "A hotel needs at least 1,000 litres of lactose-free milk. Its agent may search, compare and spend within a mandate. The receiving gateway decides what it may commit." |
| 0:15-0:35 | Run the buyer task; show source label | "This run uses [live Valio sandbox / labelled fixture]. We search the catalog first, then ask for price and availability for a shortlist. We check sales packs, dates and dietary evidence." |
| 0:35-0:55 | A controlled failure or blocked alternative | "Here is the attractive shortcut. It fails this exact rule. The model cannot turn a missing dietary claim into permission, and a budget approval cannot make an invalid product valid." |
| 0:55-1:15 | Rewind & Repair / permitted offer | "We can recover by choosing a compliant offer. If it exceeds delegated spend, it becomes a concrete exception for the authorized person. The evidence and the changed terms are visible." |
| 1:15-1:35 | Separate approver identity and exact offer | "Approval belongs to this buyer, basket, quantity, delivery date, total and offer version. A change needs revalidation. The agent cannot approve itself." |
| 1:35-1:50 | Commit, then retry | "The gateway commits one simulated order atomically against cumulative spend. The same request key returns the same receipt." |
| 1:50-2:00 | Receipt and API evidence | "This is an inspectable decision, not a reassuring chat response. An independent client can use the same versioned API. Live evidence is clearly separated from the simulator." |

Rehearse against the actual current UI and local run instructions in README before recording. Never narrate a live model call when the selected mode is deterministic. Keep credentials, restricted catalog text and account details out of the recording.

## Rehearsal order

1. Run `./start.sh` and check `/health`. Open the local desk shown in README. Sign in with this installation's buyer code; it maps to the example buyer on the server. Keep codes out of recordings.
2. Select **Rehearsal fixture**, **Clear runway**, at least **1,000 litres** and the intended delivery date. Send to buyer agent. Confirm the fixture source label before narrating it. The representative baseline fixture offers a €1,150 autonomous purchase under a €1,400 delegated limit.
3. Inspect the offer's product, dimensional quantity, date, price and mandate checks. Commit the **simulated** order, then retry that same request. Inspect the same receipt identifier.
4. Select **The milk runs out** and run again. This is an authored shortage, not a report about a real supplier. The primary schedule fails; the compliant UHT alternative is a €1,870 fixture offer, above delegated spend but below the €2,500 exception ceiling. Buyer commitment before approval must fail.
5. Open sign-in and authenticate the separate approver, **Leena Koski**, the example procurement manager. Approve the exact displayed offer. Sign back in as buyer and commit. The model never receives the approver credential.
6. Select **A tempting shortcut** to show a cheaper ordinary-milk candidate blocked by dietary evidence, or **Quantity unknown** to show that the Terminal sentinel is not stock. Explain why approval cannot waive either failure.
7. Select **The offer changes** to create an intentionally stale offer. Refresh/revalidate and inspect the new offer. Prior approval does not transfer. Changing the quantity/date and sending a new request also creates a new decision.
8. Open **Decision recorder** to inspect the factual sequence, then **Gateway API** to show the documented contract. The independent live client command below demonstrates enforcement outside the browser.
9. If the live sponsors are reachable, select **Live sponsor sandbox**, keep the ordinary baseline, enable **Use NVIDIA Nemotron agent**, and run one bounded request. Show actual provenance. If they are unavailable, preserve the explicit failure and switch modes deliberately.

The fixture numbers above are authored demonstration values, not promised live prices. A live run combined with a controlled scenario contains an explicit injected change; it must be narrated as a rehearsal over live base evidence. The typed quantity/date fields are authoritative; editing prose alone does not rewrite the mandate.

The cumulative cap is €6,000 and persists across runs. Do not reset it during a judge's inspection. For a fresh local rehearsal after saving evidence, the operator-only reset is deliberate and deletes only this prototype's synthetic records:

```bash
.venv/bin/python scripts/backend_reset.py --confirm-example-data
```

Independent live agent command actually exercised during the build:

```bash
.venv/bin/python scripts/agent_client.py --mode live --model --commit --output .local/external-live-proof.json
```

It returned a real NVIDIA typed proposal, live sandbox evidence, an Aiven-persisted simulated receipt, duplicate-same confirmation and scoped record verification. Full verification boundaries are in SPONSORS and DELIVERY.

## Thirty-second pitch

"A4TB · Valio Aimo lets a kitchen delegate a purchase without delegating unlimited authority. An external agent finds a suitable offer through typed tools. Our gateway checks the buyer's mandate, product evidence, packs, date and spend. It can proceed, request approval for an exact exception, or block an invalid shortcut. Rewind & Repair shows the failed check and a permitted recovery. The final receipt is simulated, persistent and safe to retry."

## Three-minute pitch

"Professional kitchens already have ordering systems. Valio Aimo's customer stories describe contract products and chef-defined assortments. The challenge is letting an outside agent work within that existing relationship, while the buyer and wholesaler retain control.

Our example hotel needs at least 1,000 litres of lactose-free milk for breakfast service. The buyer agent searches a supplied catalog and asks the live sandbox for price and date-specific availability for a small shortlist. It does not send the entire catalog to a model or infer that a litre is a kilogram.

The memorable part is what happens when an offer fails. Rewind & Repair exposes the exact check. A forbidden dietary change is invalid. A permitted commercial exception can go to a separately authenticated approver. A compliant offer inside the mandate can proceed. Those are three different outcomes, enforced by gateway code.

Approval is bound to the exact offer. Changed quantities, date, total or expiry require revalidation. The commitment transaction checks cumulative spend and idempotency, so parallel or repeated requests cannot quietly spend beyond the mandate or create duplicate simulated orders.

The application shows factual evidence and a decision receipt. The same versioned API is callable by an independent external client. The model proposes through tools; it does not own permissions. Sponsor sandbox lookups and our order simulator are visibly distinguished.

This is a narrow, working prototype using synthetic policy and challenge data. We have not measured customer savings or claimed production readiness. The next step is to validate the handoff with a real buyer and approver, and agree the supplier's reservation and order contract. Today the demonstration proves that useful autonomy can have an inspectable, enforceable boundary."

## Difficult judge questions

**Does this place a real Valio order?** No. The published sandbox exposes price and availability, not order placement. We own and label the simulated order gateway. Lookup does not reserve stock.

**Why use a model at all?** It helps an external agent translate a need and choose tools/candidates. Deterministic validation handles authority, units, money and commitment. Inspect the actual run's provenance: deterministic mode is not represented as model use.

**What prevents the agent approving itself?** The server assigns identity from credentials/session, and approval requires a distinct authorized approver. A client role field is not authority. Approval binds the exact offer.

**Can approval override an allergen rule?** No. Unknown dietary evidence stays unknown. Hard suitability rules are invalid outcomes, not commercial exceptions.

**How do you prevent split orders or concurrency bypasses?** Commitment checks and updates cumulative spend in one database transaction, with uniqueness rules for idempotency. Refer to executed concurrency tests in DELIVERY.

**Are the carbon and reliability numbers guarantees?** No. Reliability is historical delivered-quantity ratio; carbon is a product-group estimate per kilogram. Neither is a measured on-time probability or individual SKU footprint.

**Have customers validated this?** Published workflows and a user-supplied Valio Aimo worker conversation informed the implementation. This is discovery evidence, not measured customer validation. The hotel and mandate remain authored examples.

**Is the source open?** The API contract is documented. The source is in a private repository under the user's instruction. Organizer source access and the recorded event licensing/publicity requirements need owner review. Restricted datasets will not be published.

**What if NVIDIA or the supplier API fails?** The live run records a bounded failure. An explicit labelled fixture mode keeps the local workflow demonstrable; it never silently becomes live evidence.

## Video storyboard and recording status

A real **87.48-second local fixture rehearsal** was recorded at `.local/demo/aimo-order-desk-draft.mp4` with captions and no audio. It shows the actual gateway UI, shortage, separate approval, idempotent receipt, recorder and stale-offer repair. It is explicitly a fixture demonstration; the live sponsor proof is separate. No public upload has been made. Review every frame before deciding whether to publish it; recording does not submit any Junction entry. The reproducible recording source is `scripts/record_demo.py`.
