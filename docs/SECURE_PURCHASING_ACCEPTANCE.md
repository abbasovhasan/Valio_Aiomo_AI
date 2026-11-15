# Secure purchasing and A4TB identity acceptance

15 November 2026, Europe/Helsinki. Public application: [A4TB · Valio Aimo](https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site). Source baseline `d52cf2d`; released frontend **`index-D7lX2GlZ.js` / `index-u3yDhAoS.css`**. This record supersedes the preceding release's current-status wording; historical reports retain their original scope. Source, credentials, restricted catalog and raw QA records remain private.

## Existing mechanisms retained

The application already had scoped sessions/workspaces, deterministic package/price/dietary checks, versioned offer fingerprints, compare-and-swap edits, checkout locking, fresh commercial revalidation, atomic cumulative simulated spending and idempotent receipts. Product Details and optional comparison already shared components. This release extends those paths rather than creating a second authorization engine, checkout lifecycle or organization administration service.

The earlier Product Evidence accordion persisted in the owner's interface because the public site still served the old B4 frontend. The preceding Bj9 release deployed the shared right drawer/mobile sheet; this release preserves it and verifies the newly deployed D7 assets. Opening details does not expand product cards or displace the cart.

## Verified gaps and resulting behavior

- **Budget exceptions:** previously an over-requested-budget cart lost its offer and had no approvable queue entry. A valid basket can now retain the original budget and record an exact separate exception. The buyer explicitly requests approval, optionally explains why, and the request appears in the eligible manager's queue. Budget and spending-authority reasons are recorded separately; one decision covers both only with both permissions.
- **Independent authority:** same-browser role switching formerly represented a different role without proving an independent decision maker. A server-issued opaque browser lineage survives sign-out/role changes; private buyer principals are stable. A request cannot be decided by its creating actor/principal. Current server-owned workspace assignment, permissions and manager ceiling are checked at access/decision/final transaction. Missing or malformed policy fails closed. A reduced legacy manager permission/ceiling also now blocks the approval decision itself, rather than waiting until submission.
- **Current review facts:** an old pending snapshot could display stale remaining allowance or saved dietary requirements while the final transition correctly refused it. Review/queue now overlay current allowance and hard blockers without changing the saved offer, requesting a provider quote or writing the basket. Approval is disabled for hard blockers. An otherwise authorized manager can still decline/request changes for recovery.
- **Dietary presentation:** Meal Planner previously allowed incompatible/unknown candidates to appear selected although checkout rejected them. Dirty requirements now suppress selected/compliant presentation and disable transfer until recalculation. Ineligible retained choices clear; incompatible, missing-evidence or invalid-conversion candidates cannot be selected as satisfying unchanged hard requirements. Unresolved rows say “No verified suitable product selected.” Verified compatible/incompatible, missing evidence and clarification remain distinct; names alone are not certification.
- **Review and decisions:** a dedicated existing-SPA Review order view is available for ready, blocked and approval carts. Buyer and approver share product/request/quantity/price/source/diet/delivery/financial context. Policy/allowance and decision history use native disclosures. Approvers have exact approve, decline and noted request-changes actions; buyers can cancel. Opening review/status is read-only and no longer redundantly reloads workspace data.
- **Comparison:** Smart Order exposes Compare items beside its requested-item alternatives count. Products retains its selection bar. Both use the same manual two/three-product panel; a fourth requires explicit replacement. Approver comparison reads quoted snapshot options and cannot refresh quotes or choose a product. Unknown facts and unlike units remain explicit.

## Financial scope and workflow

Requested maximum budget is an editable buying requirement, never authority. The installation's authored defaults are **€1,400 autonomous**, **€2,500 per order** and **€6,000 lifetime committed simulated spend per buyer workspace**. They are not official Valio thresholds, verified bank funds, a real credit agreement or a calendar-period organization budget.

Quotes and pending approvals reserve no money or supplier stock. Final submission checks current policy, hard requirements, authority/assignment, commercial facts, exact approval and remaining allowance, then commits atomically. Competing approved drafts can fail when an earlier submission consumes allowance. Retries return the same saved simulation; order splitting does not refill the lifetime allowance.

For **€800 requested / €836 basket / €36 excess**:

1. Direct submission is blocked. Editing quantity, products or requested budget remains possible.
2. Review order retains €800 and shows the exact €36 exception and original request.
3. Only explicit Request approval persists the request/explanation and adds the eligible scoped queue entry.
4. An independent eligible manager reviews the complete exact version. Approval does not submit and grants no future authority or larger budget.
5. The buyer sees Approved, then explicitly chooses Confirm simulated order. Fresh hard checks still apply.
6. The receipt preserves the original budget, approved excess and explanation. Repeating its idempotency key returns the original receipt.

Approval binds workspace/buyer, version, products, quantities/packages, current prices/currency/total, delivery, hard constraints, policy, exception, manager and expiry. Relevant edits invalidate it. Rejection or request changes requires a fresh buyer revision/quote/request; cancellation closes the draft. Old references cannot submit. Existing draft/ready/blocked/pending/changes-requested/rejected/approved/submitted/cancelled distinctions extend the original session model; frontend labels grant no permissions.

Shared/operator/demo codes simulate actors. Browser lineage and stable private-account principals prevent the tested role-switch bypass, but shared credentials across new browsers do not establish real-human enterprise identity. This is an explicit prototype boundary, not an enterprise IAM claim. No policy-administration API was added.

## Automated and deployed evidence

| Scope | Actual result | Limits |
| --- | --- | --- |
| Backend | **414 passed in127.46s** | Current combined suite; includes malformed/missing policy, direct bypass, assignment/permission/ceiling revocation, exact exception, same-actor denial, fresh restrictions/allowance, concurrency/splitting/replay, legacy paths and receipt preservation. |
| Frontend | **74 grouped checks**, all nine scripts; production build/diff check pass | Details16, comparison7, page5, review10, meal7, session7, microphone7, camera7, image normalization8. Authored React/handler/SSR/fake-media checks are separate from browser/hardware proof. |
| Release continuity | **18 checks in54.443s** | Previous SQLite writer stopped; protected unique backup integrity `ok`; same-app release, correct assets/security/timing headers; five prior registered QA receipts, original shared receipt/spend, remembered sessions, passwords/preferences and new private QA account survived. Zero new orders in rollout. |
| Exact €36 exception | **8 API assertions plus real manager browser journey** | Source-derived fixture100×€8.36=€836; direct submit409; original€800/explanation persisted; browser queue/review, request changes, fresh explicit revision and independent exact approval; buyer explicitly simulated; same-key retry/integrity/private scope verified. |
| Browser-created exception | **€77.40 basket /€70 budget /€7.40 excess** | Real public buyer selected20L SKU464073, reviewed/requested, same-browser manager decisions disabled; independent API manager approved without ordering; browser buyer explicitly confirmed, verified and reloaded receipt `sim-basket-4786965900dc4e3c`. |
| Hosted state/authority regression | **22 checks in43.46s**, zero orders/providers | Private fixture184×€7.80=€1,435.20 versus€1,400 budget requires BOTH reasons. Real queue; stale version409; reject/changes block confirmation; fresh exact approval; material edit invalidates old fingerprint; cancellation blocks confirmation. Own draft cancelled/hidden, audit retained; existing private spend€913.40, prefs/history/two receipts unchanged. |
| Hosted read/performance probe | **15/15 responses200** | Existing private B; preferences/spend unchanged; zero quote/model/supplier/order calls. Wall/app/persistence/transport measurements have separate scope. |
| Hosted media/parser integration | **20/20 responses200** | Synthetic image/audio; actual automatic NVIDIA image, explicit local OCR, first/cached local Whisper, local/model two-item fixture drafts. Two owned drafts cancelled/hidden; existing receipt/spend/preferences unchanged; zero orders/supplier calls. |
| Keyless demo HTTP script | Isolated default **58 checks pass**; current shared hosted run **31 checks before expected policy precondition stop** | Shared pre-existing spend€5,329.56 leaves€670.44, below its€1,435.20 authority scenario. No cap/reset workaround; only two owned drafts cancelled/hidden, original audit retained. This is not a58-check hosted pass. Larger hosted transitions were verified in the private scope above. |
| Real browser | Local and public desktop/mobile interactions; public widths **320/375/390/430/768/1440** without page/control overflow in tested review layouts | Native keyboard disclosures; modal Escape/focus; exact read-only approver three-product comparison; Products three/fourth replacement; mobile Cart and Details separate. Fifteen recorded scenario checkpoints are not a universal browser/device certification. |

Private reports live under ignored `.local/secure-*`, `.local/private-hosted-transition-report.json` and `.local/secure-browser/`. The eight-assertion private exception helper initially used two unsupported quote route/action forms, receiving405/422 without purchase; corrected to the actual `actions/quote` contract before the successful revision. These helper errors are not passing application checks or new application defects.

The real public Smart milk card stayed **454.9375×623.125px** before/during the **560px** desktop details drawer. Its sort=`name`, brand=`Arla`, two comparison choices and unsent note survived details/review return. Escape restored Product details focus. Mobile Details occupied96dvh with one content scroll owner and one full product name; comparison's wider table scrolled inside its panel without widening the page. Cart remained a separate native dialog. Public Meal Planner repeated the standard-pasta→mandatory-gluten-free edit: zero checked choices while dirty, disabled transfer, then an unresolved recalculated row with a verified GF option and invalid-conversion alternatives disabled. No financial override was offered.

Public final desktop/mobile screenshots are `.local/secure-browser/public-final-desktop.jpg` and `public-final-mobile.jpg`; detail screenshots use `public-details-desktop.jpg`/`public-details-mobile.jpg`. Captured public console warning/error list was empty within this session. Existing owner microphone/photo successes retain their earlier scope; no new real hardware/handwriting/accent guarantee is claimed.

## A4TB visual identity

Chosen design: a bold path-based **A4TB** wordmark with two offset geometric handoff forms, in the existing forest-green palette. It suggests a connection/forward handoff without AI-brain, robot, shield, gradient or fine-detail decoration. It does not modify the official Valio Aimo logo or imply an official Valio product. Existing challenge/Junction attribution and navigation remain.

Source assets:

- [Primary wordmark](../frontend/public/brand/a4tb-logo.svg), [compact transparent symbol](../frontend/public/brand/a4tb-symbol.svg).
- [SVG favicon](../frontend/public/favicon.svg), [ICO16/32/48 fallback](../frontend/public/favicon.ico).
- [180px touch PNG](../frontend/public/apple-touch-icon.png), [editable touch-icon SVG source](../frontend/public/brand/apple-touch-icon.svg).

The wordmark is the accessible header/home link, with a decorative compact sign-in symbol and restrained text footer. The favicon uses only the compact symbol; mint-on-forest is deliberate for tiny sizes. The touch icon has a solid padded background. No font, dependency, service, PWA or manifest was introduced. The interface needs no additional dark variant.

Actual16/32px raster inspection passed; ICO frames16/32/48 and PNG180×180 were decoded. Deployed five-asset hashes exactly match source and MIME types are correct (SVG, ICO, PNG). HTML icon paths/application name/theme metadata load from the public origin. Header logo widths are116px at320,124px on phones and148px on desktop; no tested horizontal overflow. Measured forest/page contrast10.56:1, attribution5.62:1 and mint/forest9.03:1. Opening/closing Product Details leaves cards fixed; the header retains its78px layout.

## Performance, hosting and credits

See [measured performance](SECURE_PURCHASING_PERFORMANCE.md) for before/after conditions, whole-operation versus provider/transport/persistence distinctions, actual samples and their limits. Immutable brand indexing reduced the same-process three-item fixture median **410.555→334.822ms** (~18.4% in that sample); reusable connections retain transport only, never commercial answers or permissions. Redundant review/status workspace requests were removed. Existing gzip already reduces a150KB decoded milk response to roughly7.5KB on the wire; it was preserved.

Read-only Modal dashboard verification showed **$100.76 usable credits**, **$0.24 cycle usage covered by credits**, **$0 charges**, a **$101 hard cap**, and a payment-method requirement to raise it. The active Junction grant showed **$100 remaining**, activated13Nov2026, expiring **30Nov2027**; the plan separately showed$1 monthly compute credits. These are dated account observations, not a final bill or estimated future balance.

Published [Functions pricing](https://modal.com/pricing) is$0.0000131/physical-core-second plus$0.00000222/GiB-second; requested or greater actual usage and applicable regional factors affect the bill. Included compute and separately billed Modal Model APIs must not be conflated with unverified grant-specific coverage. This application uses Functions and separate NVIDIA Build calls, not Modal Model APIs.

Only **idle scale-down120→300seconds** changed: CPU1, memory1536MiB, min0, max1container/input and180srequest timeout remain. At listed base reservation rates the extra180sidle costs approximately **$0.0029574/cycle**, before regional/higher-actual-use adjustments. No continuous minimum, replicas, concurrency, paid plan, card, top-up or spending-cap change was introduced. The single SQLite writer and durable volume acknowledgement remain. Current app and volume-persistence durations are reported separately in Server-Timing; an internal auth-migration persistence signal is stripped before public responses.

The deployed idle probe passed: **one task after201.161s idle**, next root661.207ms (app3.560ms); then **zero tasks observed after423.146s** with independent function statistics showing zero runners/backlog/inputs before the cold request. The first root after verified zero took4,970.343ms, followed by193.746/202.221/200.238ms warm roots; app time7.035ms cold and2.630–3.049ms warm excludes startup/proxy/transport. The same remembered cookie recovered buyer/workspace/actor/principal, both new receipts verified, and private spend/preferences stayed unchanged after actual process scale-down. No orders were created. The earlier349s app-list sample still showed1task while a subsequent container inventory was empty; counts/shutdown observations have granularity, so300s is configuration rather than a guaranteed exact shutdown deadline. Protected report: `.local/secure-hosted-after-navigation.json`.

## Preserved boundaries and remaining limits

Original four dataset SHA-256 hashes pass; raw files remain private and unmodified. No actual supplier order, reservation, commercial invoice, payment/card collection, personal spending, plan upgrade or Junction submission/status change occurred. The two public QA confirmations total€913.40 only in their isolated synthetic ledger; all prior shared/private purchase records remain. Payment terms are not configured/verified here; tax-inclusive known item totals exclude unknown delivery/service charges.

There are no supplied product-image files/URLs; unverified pictures were not invented. Dietary evidence is not allergy-safety certification, recipe illustrations require chef review, and missing claims/conversions remain blockers. One-input hosting can queue behind external model/speech work; cold starts and provider variability remain. Shared-demo credentials do not prove independent humans, and multi-instance production use needs a transactional shared database/distributed controls. Neither broad production security nor a load/recognition SLA follows from this bounded evaluation.

Use the updated [checking guide](WEBSITE_CHECK_GUIDE.txt). The62-file staged source/credential scan, private-QA credential/public-asset checks, original dataset hashes, diff check and GitHub private-repository verification passed. Frozen implementation hashes still match the tested/deployed source. User-owned launch prompts/output/tmp are excluded from staging; local QA runtime is stopped and browser sizing restored. Final source commit/push is recorded in Git and the delivery response.
