# A4TB · Valio Aimo — deployment

14 November 2026. Public entry: **[A4TB · Valio Aimo](https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site)**. Sites proxies the code-gated React/FastAPI app on Modal. Shared buyer/approver access and invitation-gated private accounts are supported. Repository, catalog and runtime credentials remain private. All orders are simulated; deployment does not submit the Junction entry.

Technical origin: `https://hasan-abbasov--aimo-order-desk-web.us-east.modal.run`. The branded Sites address is the customer-facing URL; the Modal workspace prefix is infrastructure naming.

## Runtime and persistence

- One CPU, 1,536 MiB, zero minimum warm containers, maximum one container/input, 120-second idle scale-down and 180-second request timeout.
- Four original SHA-256-verified restricted datasets in a private catalog volume; none in Git or public assets.
- Separate private SQLite volume stores users, preferences, hashed sessions/revocations, authentication throttles, carts, approvals, receipts and synthetic spend. Volume commits complete before acknowledging mutations.
- Runtime keys/codes use a named Modal Secret. The Aiven password is not uploaded. Local PostgreSQL remains available with CA/hostname verification; its allowlist was not widened.
- Tesseract English/Finnish runs in the image. Public pretrained Whisper base weights are bundled at build time, not downloaded during hosted requests. `scripts/prepare_multimodal.py` records pinned model provenance/license; private challenge data is not used to train a model.
- Speech/OCR are server-local by default. Optional NVIDIA text and vision requests require visible opt-in for nonconfidential demo content; image use needs separate consent. No uploaded image/audio persistence.
- The Sites proxy preserves secure cookies and microphone access on the same HTTPS origin, blocks cross-origin mutations and does not cache API responses. No credentials/catalog live in its source.

This is deliberately a single-writer deployment. Stop the previous writer before deploying. Do not increase replicas/inputs against the same SQLite file. Horizontal scaling requires a transactional shared database and distributed controls. A protected backup was saved before this release; no ledger reset was performed. [Modal ASGI hosting](https://modal.com/docs/guide/webhooks), [volume consistency](https://modal.com/docs/guide/volumes).

Measured local app/catalog/media resident memory was about 882 MiB before the additional approximately 47.6 MiB static search index. The 1,536 MiB setting accommodates that measured workload. Warm three-item fixture quotations improved about 7.1×; first index construction costs extra cold-start time. Network/provider latency and sequential queueing remain visible, and these observations are not a load SLA.

## Financial controls

Account verification established a $100 Junction grant expiring 30 November 2027, a Modal-set $101 hard workspace cap, and no payment method; increasing the cap required adding one. No payment method, subscription or top-up was added. The November CLI billing CSV observed **$0.04369075** total at this release check. Usage reports can lag and include existing workspace activity; this is neither a final bill nor a remaining-balance claim. Read the dashboard and verify coverage before later provisioning. [Modal budget behavior](https://modal.com/docs/guide/budgets).

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

171 backend tests and the production frontend build passed. The current Modal deployment built the Python 3.12 OCR/ASR image successfully; HTTPS health, SQLite/simulated-only mode, current asset `index-C67pl32K.js`, typed OpenAPI and the old manager-approved receipt were verified.

The **47-check extended hosted verifier passed** accounts/cookie policies, isolation, saved preferences, multi-item and repeated follow-ups, budgets/dates/version failures, private exact manager approval, simulated confirmation/idempotency/verification/recovery, real OCR/Whisper and actual Lightning/Valio reads. Default shared spend remained unchanged. A subsequent 13-check stopped-writer restart verified the same 30-day cookie, password login, preferences, synthetic spend and three receipts/approval records after redeployment, with a protected integrity-checked backup and no new orders. Uploaded clip recognition took 1,800 ms backend time and OCR 444 ms in this run; HTTP/network/queue time is additional. Live NVIDIA/Valio quotation was read-only.

Local browser interaction verified the full mixed-input cart and receipt/reload, private manager handoff, expired quote recovery, explicit overlap and exact dated meal-plan bridge. Desktop/mobile and keyboard checks passed within the recorded scope; the owner confirmed actual public-site microphone transcription. See [acceptance](ACCEPTANCE_RECORD.md) and [extended checks](EXTENDED_ACCEPTANCE.md).

```bash
.venv/bin/python scripts/extended_smoke.py --url https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site --live
```

The command creates/reuses isolated QA accounts with private ignored credentials and commits only simulated orders within their synthetic caps. It does not reset or consume the shared Aurora ledger. Reports omit credentials and media/transcript contents. Sessions last eight hours, or 30 days with Remember Me; authentication throttles/revocations persist. Broader multi-user load, distributed scale and a real supplier checkout are not claimed.
