# Procurement interface — small design system

The customer task is to describe a need, review real products and confirm a simulated cart. The interface prioritizes that content over branding, implementation details or explanatory copy. This refinement preserves the existing React/FastAPI application and partner integrations; it adds no UI framework or state-management dependency.

## Structure and responsibility

- **Smart order:** one composer and one primary Build/Update cart action. Text, microphone, uploaded image and camera capture enter the same editable request. Delivery date and budget are visible before ordering.
- **Products:** broad catalog search, server pagination and declared filters; select a real SKU, choose quantity/unit, inspect the current quote and add it to the active draft. Missing pricing is “Requires quote”, never zero or a reason to hide eligible catalog products.
- **Cart:** the same server-owned draft across Smart order and Products. Single-request quantities and removal are directly editable; aggregate cohort quantities stay traceable to their separate requirements. A complete eligible basket proceeds to explicit simulated confirmation.
- **History:** saved requests and orders with open, reuse, archive/restore and personal-history removal. Audit/order retention is separate from hiding an entry.
- **Preferences:** mandatory food restrictions are separate from optional buying priorities. Restriction controls are searchable; uncertified/unknown evidence cannot be shown as safe. Optional defaults do not override hard instructions.
- **Demo tools:** quotation-source/text-interpreter controls and the existing trust/API evidence are opt-in operator context. These settings do not make customers choose an image reader. The customer path defaults to live commercial reads; authored prices remain labelled when deliberately selected.

`ProcurementDesk` retains the current cart and shared constraints. `ProductWorkspace`, `HistoryPanel`, `PreferencesPanel` and `MultimodalInput` have focused responsibilities. Products stays mounted across customer navigation so query/filter/page/selection context survives; hidden requests are cancelled. Scoped account changes still clear the old customer's UI state.

## Visual tokens

Reuse the existing CSS variables and restrained palette rather than introduce a theme framework:

| Role | Values used in customer surfaces |
|---|---|
| Main text | `#203f32`, `#243f32` |
| Secondary text | `#52664a` |
| Primary action | `#214d37` with white text |
| Canvas / surfaces | existing `#f4f3ed`, paper `#fcfcf7`, white tables/forms |
| Dividers | existing border `#dedfd4`, quiet neutral green borders |
| Selected / success | pale green surface, dark green text/check |
| Warning | dark brown `#80522e` on pale warning surface |
| Error | dark red/brown with explicit text, not color alone |

Customer text uses a small scale: 24 px page heading, 15–17 px product/section heading, 13–14 px primary inputs, 12–13 px body/table controls and 11–12 px secondary evidence. Use 8/12/16/20/24 px spacing steps. The retained operator demonstration has legacy styling; it is not the customer layout template.

## Component behavior

- Buttons name the action: Search, Select, Add to cart, Apply, Reuse, Archive, Review cart. Each screen has a clear primary action; supporting actions remain quiet.
- Inputs keep visible labels and explicit units. Whole sales-package quantities, required dimensional quantity and surplus must not be confused.
- Product cards show identity, package, relevant price and availability first. Details, conversion provenance, deeper filters and operator settings use progressive disclosure.
- Selected products remain visible when local filters exclude them. Counts and Reset view make the effect of filtering explicit. Unknown values do not satisfy verified-attribute filters.
- Loading retains text/status, not an unnamed spinner. Failed quotes preserve the product/draft and explain the missing evidence. Stale server versions reload authoritative state rather than overwrite it.
- Global search keeps active filter chips and Reset filters visible outside its disclosure. Server-applied mandatory dietary/ingredient restrictions remain visible and survive that reset. Products preserves query, filters, page and selection when the customer switches destinations.
- History reuse creates a new draft with fresh quotation and no inherited approval/receipt. Removing a personal entry does not erase immutable audit/order records.
- Four input methods are Type a message, Voice input, Upload image and Take a photo. Audio-file upload is absent; live microphone transcription retains the audio API. Media extraction shows editable text before adding it, and never submits automatically. Pending permissions, recording, extraction, camera preview and an unreviewed result block Build/Update; Add or Discard releases review. New capture cannot replace unreviewed text, while typing/editing stays available. Camera/microphone access is explicit; cancellation, navigation and unmount stop current or late-granted tracks. Captured photos use the same image validation/OCR path as uploads.
- Image reading is automatic, with plain disclosure of external processing and nonconfidential demonstration use. Customers do not choose an image provider or per-image consent checkbox. The shared browser path validates original JPEG/PNG signatures and the 5 MiB byte limit, respects orientation, avoids upscaling and draws a fresh raster bounded to 1600 px before upload. Metadata/filename removal and current-request cancellation checks also apply to native-camera files; backend pixel and byte defenses remain independent. Provider provenance stays in the API rather than the customer text review.
- Native controls, focus outlines, semantic tables, labelled disclosures and status/error announcements support keyboard and assistive technology use. Touch targets receive extra space; checkbox graphics are not stretched.

On narrow screens, catalog rows and receipt tables become stacked readable entries, filters use one column and the cart follows the work area. Keep the same information/actions instead of shrinking desktop columns into unreadable content. Use motion only for purposeful scrolling/loading; honor reduced-motion preferences. These choices target accessible behavior but do not claim complete WCAG certification.

## UX, DX and agent boundaries

The interface consumes stable catalog IDs and server-calculated nullable prices/quantities. View sorting/filtering never changes hard requirements or invents arithmetic. Cart mutations remain versioned API actions; server eligibility, inventory, budget, approval and idempotency checks are authoritative. UI simplification removes redundant presentation and moves context to the right destination; it does not remove purchasing safeguards or backend capabilities.

Sibling React keys include the control kind (`query-`, `quantity-`, `candidates-`) as well as the stable line identity. A concrete key collision previously duplicated search controls during repeated product choices; real browser reconciliation checks now confirm one product-search form per request. Per-request search accepts 200 characters, preserving the longest actual catalog names through follow-ups; global catalog queries retain their 500-character limit.

Build/render checks support integration; actual customer acceptance still requires the root's browser and deployed API checks. Physical camera permission/capture must be observed on an available device, rather than claimed from a static preview.

## Media regression tests

With the existing frontend dependencies installed, run from the repository root:

```sh
node tests/frontend/microphone_controls.cjs
node tests/frontend/camera_controls.cjs
node tests/frontend/image_normalization.cjs
```

These tests execute the real `MultimodalInput` handlers with deferred permission promises, fake device streams, a fake recorder and canvas callbacks. They cover duplicate microphone requests, cancellation and stale callbacks, stream cleanup, camera failures, and capture/transcription through pending editable review and explicit Add/Discard. They add no dependencies and write reports only to ignored `.local/` files. The final runs passed **7 microphone checks**, **7 grouped camera checks**, and **8 image-normalization checks**. This is isolated async-control evidence, not browser acceptance, OCR/ASR accuracy, or actual microphone/camera verification.

The final local backend regression run passed **285 tests in 83.21 seconds**, including source-derived follow-up coverage for all 13 actual catalog names longer than 120 characters. The production build passed (`index-B4p90PsT.js`). Root-run local browser checks cover Products searches/pagination/context preservation, shared date/budget state, mixed-cart follow-up, uploaded-image review and pending microphone/camera cancellation. The public `CFFEDfEi` image release passed **12 continuity checks** and **4 automatic-image API checks** confirming the actual configured vision provider. The owner reported correct real microphone transcription on the prior public build, including their accent, and confirmed that the physical phone/photo retest on `CFFEDfEi` works with editable text. These are individual qualitative hardware successes, not general accuracy/device-compatibility measurements. Full public-release/mobile evidence belongs to [FINAL_QA_REPORT.md](FINAL_QA_REPORT.md).

The final public `B4p90PsT` asset, health and same-origin camera/microphone policy were verified. **12 continuity checks passed in 69.561 seconds**, preserving accounts, preferences, simulated spending, five QA receipts and older shared receipts; a new protected backup was created, with zero orders. **Three hosted long-name checks passed** for the longest actual product name (155 characters): a two-package draft followed by an explicit EUR 150 budget change retained its ID, SKU, full name, quantity and date. That check made no orders, model or supplier calls and left spending unchanged. No additional physical-device or layout claim is inferred from this input-limit-only release.

The `BkM4NY18` reconciliation fix passed four local and two public repeated product choices with exactly two query forms for two requests, no console errors, and a ready EUR 67.20 cart retained after reload. Clean desktop 1440×1000 (scroll width 1425) and mobile 390×844 (scroll width 375) views were visually inspected without horizontal overflow; all four inputs remained visible. Earlier `AADxbAJX` checks also verified readable catalog cards and preserved page/search context. The final `B4p90PsT` input-limit-only change leaves this tested layout and media behavior intact.

The latest root-run local browser check read a **13.86 MP, 338,326-byte JPEG** into correct editable shopping-list text through the automatic endpoint, with provider/consent controls absent. An original **5,242,881-byte** image was rejected without a stuck media state. The `CFFEDfEi` public browser repeated the high-resolution read, edited butter from 5 to 4 kg, kept Build disabled until Add, and preserved typed context, date 17 November and EUR 200 budget when added. The owner then confirmed the same sub-5 MB phone photo worked with editable text and no 12 MP error. The normalization tests separately use an authored 15 MP PNG with fake browser decode/canvas; they are not the basis for the owner-device claim.

## Primary references

- [Apple Human Interface Guidelines — design principles](https://developer.apple.com/design/human-interface-guidelines/design-principles/): clear hierarchy, context, feedback and safety.
- [Apple Human Interface Guidelines — search fields](https://developer.apple.com/design/human-interface-guidelines/search-fields): broad discovery with relevant results and discoverable filtering.
- [Linear — behind the latest design refresh](https://linear.app/now/behind-the-latest-design-refresh): content priority and consistent interface structure.
- [Linear — UI refresh](https://linear.app/changelog/2026-03-12-ui-refresh): coherent navigation, headers and view controls.

The implementation adapts these interaction principles; it does not copy proprietary assets, branding or a complete reference layout.

Image API references: [createImageBitmap orientation](https://developer.mozilla.org/en-US/docs/Web/API/Window/createImageBitmap), [Image decode lifecycle](https://developer.mozilla.org/en-US/docs/Web/API/HTMLImageElement/decode), and [canvas encoding](https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/toBlob).
