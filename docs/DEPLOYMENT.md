# A4TB · Valio Aimo — deployment

15 November 2026. Public entry: **[A4TB · Valio Aimo](https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site)**. Sites proxies the authenticated React/FastAPI app on Modal, with explicitly enabled controlled demo roles. Shared buyer/approver access and invitation-gated private accounts are supported. Repository, catalog and runtime credentials remain private. All orders are simulated; deployment does not submit the Junction entry.

Technical origin: `https://hasan-abbasov--aimo-order-desk-web.us-east.modal.run`. The branded Sites address is the customer-facing URL; the Modal workspace prefix is infrastructure naming.

## Runtime and persistence

- One CPU, 1,536 MiB, zero minimum warm containers, maximum one container/input, 300-second idle scale-down and 180-second request timeout.
- Four original SHA-256-verified restricted datasets in a private catalog volume; none in Git or public assets.
- Separate private SQLite volume stores users, preferences, hashed sessions/revocations, authentication throttles, carts, personal history metadata, approvals, receipts and synthetic spend. Volume commits complete before acknowledging mutations. History removal hides a personal entry; it does not erase purchasing evidence.
- Runtime keys/codes use a named Modal Secret. The Aiven password is not uploaded. Local PostgreSQL remains available with CA/hostname verification; its allowlist was not widened.
- Tesseract English/Finnish runs in the image. Public pretrained Whisper base weights are bundled at build time, not downloaded during hosted requests. `scripts/prepare_multimodal.py` records pinned model provenance/license; private challenge data is not used to train a model.
- Speech remains server-local Whisper; optional text interpretation is unchanged. Ordinary images now attempt NVIDIA automatically with actual local OCR fallback on provider failure, under a plain nonconfidential-demo privacy notice. Explicit API `provider=local` stays offline; `cloud_consent=false` is rejected before an external read. Original JPEG/PNG files up to 5 MiB are resized to at most 1,600 pixels in the browser; server 12 MP/decompression guards remain. Uploaded media is not persisted.
- The Sites proxy preserves secure cookies on the same HTTPS origin, blocks cross-origin mutations and does not cache API responses. Current application policy allows same-origin camera and microphone access; image capture uses the existing sanitized OCR endpoint. No credentials/catalog live in proxy source.

This is deliberately a single-writer deployment. Stop the previous writer before deploying. Do not increase replicas/inputs against the same SQLite file. Horizontal scaling requires a transactional shared database and distributed controls. A protected backup was saved before this release; no ledger reset was performed. [Modal ASGI hosting](https://modal.com/docs/guide/webhooks), [volume consistency](https://modal.com/docs/guide/volumes).

The previous release's local app/catalog/media sample observed about 882 MiB resident memory before an additional approximately 47.6 MiB static search index; that sample motivated the 1,536 MiB setting. Its warm three-item fixture quote improved about 7.1×, while cold index construction took longer. Current complete-catalog QA passed 12 matrix groups in 39.882 seconds, with exact category/brand prefiltering and page-only normalization where criteria permit. These separate local observations do not establish hosted latency or a load SLA.

## Financial controls

Read-only live dashboard verification on15November showed **$100.76 usable credits**, **$0.24 cycle usage covered by credits /$0 charges**, active Junction grant **$100 remaining**, expiry **30November2027**, enforced **$101 cap**, and a payment-method requirement to raise it. No card/top-up/subscription/cap change occurred. These are dated account observations, not a final bill or forecast. [Budget behavior](https://modal.com/docs/guide/budgets).

The measured resource decision changes only idle120→300s;1CPU/1536MiB/min0/max1container/input remain. At published base Functions CPU/memory reservation rates, the additional180sidle is about **$0.0029574/cycle** before regional or higher actual usage; scaled-to-zero time is unbilled. No continuously warm service or Modal Model API is introduced. Read [performance and cost evidence](SECURE_PURCHASING_PERFORMANCE.md) before later provisioning; do not infer current credits from historical grant records or preparation CSVs.

## Reproduce

Verify credit coverage and enforced cap first. Authenticate privately with `uv run --with modal modal setup` if needed. The prepared installation has the restricted datasets and public model bundle.

```bash
.venv/bin/python scripts/prepare_multimodal.py
npm run build --prefix frontend
uv run --with modal --with python-dotenv python scripts/deploy_sponsored.py
uv run --with modal modal app stop aimo-order-desk --yes
uv run --with modal modal deploy deploy_modal.py
```

The preparation script verifies and uploads only the four authorized catalog files and sets the private runtime secret without printing values. It does not upload `.env`, local access files, the Aiven credential or unrelated local files. Restrictive dataset terms still apply. Reuse the recorded Sites project for proxy changes; backend/frontend updates do not require a new Site.

## Current release evidence

**index-D7lX2GlZ.js /index-u3yDhAoS.css** is live with414 passing backend tests,74 frontend checks and18 rollout/continuity checks in54.443s. The previous writer was stopped and a unique protected backup passed integrity. Existing remembered sessions/passwords/preferences/spend, five registered QA receipts, the original shared receipt and the new isolated QA account survived. Current app/persistence Server-Timing fields distinguish handler time from durable-volume acknowledgement; actor-migration writes on GET are also committed before acknowledgement and the internal signal is removed publicly. No ledger reset occurred. The201s warm/423s zero-task observation and same-cookie/two-receipt cold recovery passed without new orders; precise shutdown timing can vary. New exact exception/transition/browser/idle evidence is in [secure purchasing acceptance](SECURE_PURCHASING_ACCEPTANCE.md).

## Historical B4 release evidence

Final `index-B4p90PsT.js` is publicly deployed with healthy SQLite/simulator/camera/microphone policy. Source passed **285 backend tests in 83.21s**; **12 fresh continuity checks passed in 69.561s**, preserving protected backup, remembered accounts/preferences/spending, all five QA receipts and old shared receipt, with zero new orders. Prior Bk 12@90.887s and CFF 12@153.84s remain historical records.

Bk fixed sibling React keys: four consecutive local choices/reload and repeated public choices kept exactly two query forms, with empty console warnings/errors. Desktop 1440×1000/mobile 390×844 had no overflow and four inputs visible. Final B4 only expands the product-name/input cap to 200; all 13 long source names passed locally, and 3 hosted checks on the longest 155-character name preserved full intent/selection/state without orders or provider calls. CFF media/owner evidence remains valid for unchanged paths.

The hosted catalog matrix passed **12/12 groups in 378.345 seconds** (349-category/698-request sweep: 310.544 seconds), plus **13 history/release checks**, four fixture drafts and one reuse. Preferences and zero QA-buyer spending were preserved, with no model/supplier calls or orders in that matrix. Earlier AAD passed 47 broader checks in 117.09 seconds, including NVIDIA text/Valio and explicit local OCR/ASR.

The unchanged CFF automatic image endpoint passed **4 checks in 12.592s**, actually using NVIDIA Super VL (1,856ms reported server time), respecting explicit cloud denial and leaving purchasing state unchanged. Public high-resolution review and the owner phone-photo retest passed; handler checks were 7 microphone/7 camera/8 normalization. These bounded cases are not general accuracy/hardware proof. Implementation `829207f` was reviewed, scanned and pushed to private `codex/aimo-order-desk`.

## Previous C67 hosted evidence

That release passed 171 backend tests and the production build. Its Modal deployment built the Python 3.12 OCR/ASR image successfully; HTTPS health, SQLite/simulated-only mode, asset `index-C67pl32K.js`, typed OpenAPI and the old manager-approved receipt were verified.

The **47-check extended hosted verifier passed** accounts/cookie policies, isolation, saved preferences, multi-item and repeated follow-ups, budgets/dates/version failures, private exact manager approval, simulated confirmation/idempotency/verification/recovery, real OCR/Whisper and actual Lightning/Valio reads. Default shared spend remained unchanged. A subsequent 13-check stopped-writer restart verified the same 30-day cookie, password login, preferences, synthetic spend and three receipts/approval records after redeployment, with a protected integrity-checked backup and no new orders. Uploaded clip recognition took 1,800 ms backend time and OCR 444 ms in this run; HTTP/network/queue time is additional. Live NVIDIA/Valio quotation was read-only.

Local browser interaction verified the full mixed-input cart and receipt/reload, private manager handoff, expired quote recovery, explicit overlap and exact dated meal-plan bridge. Desktop/mobile and keyboard checks passed within the recorded scope; the owner confirmed actual public-site microphone transcription. See [acceptance](ACCEPTANCE_RECORD.md) and [extended checks](EXTENDED_ACCEPTANCE.md).

```bash
.venv/bin/python scripts/extended_smoke.py --url https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site --live
```

The command creates/reuses isolated QA accounts with private ignored credentials and commits only simulated orders within their synthetic caps. It does not reset or consume the shared Aurora ledger. Reports omit credentials and media/transcript contents. Sessions last eight hours, or 30 days with Remember Me; authentication throttles/revocations persist. Broader multi-user load, distributed scale and a real supplier checkout are not claimed.
