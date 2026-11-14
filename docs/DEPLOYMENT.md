# A4TB · Valio Aimo — deployment

14 November 2026: open **[A4TB · Valio Aimo](https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site)**. This public Sites frontdoor proxies the existing code-gated React/FastAPI application on Modal. The repository, runtime secrets and restricted catalog remain private. The application still requires a private buyer or separate approver code.

Technical backend origin: `https://hasan-abbasov--aimo-order-desk-web.us-east.modal.run`. Keep the Sites address as the customer-facing entry point. Deployment is separate from the Junction competition entry; all orders are simulated and no final submission is performed.

## Runtime

- The Sites frontdoor proxies the React production assets and FastAPI routes through one customer-facing HTTPS origin. Modal runs the existing Python application; Sites does not contain the restricted catalog or supplier credentials.
- CPU 0.5, 1 GiB, zero warm containers, at most one container and one in-flight request; 120-second idle scale-down.
- All four original checksum-verified restricted data files are in a private Modal volume, outside Git and public assets.
- Runtime API keys and buyer/approver access codes use a named Modal Secret. Nothing secret is bundled into frontend assets.
- Persistent SQLite in a separate private volume stores hashed expiring login sessions, carts, approvals, receipts and shared synthetic spend. Volume persistence completes before a mutation response is acknowledged.
- This is deliberately a single-writer demonstration. Stop the previous deployment before deploying a revision. Do not increase replicas or in-flight inputs. Horizontal scaling requires PostgreSQL and distributed rate limits.
- The existing Aiven PostgreSQL integration remains available locally with verified TLS. Its network allowlist was not widened. Modal does not receive the Aiven password or bypass the allowlist.

Modal was selected because it runs the existing Python ASGI application directly. Sites supplies the public entry point and proxy; implementing the Python application inside Workers would require a backend replacement. Persistent single-instance SQLite removes the need to buy static database egress for this small demonstration. [Modal ASGI hosting](https://modal.com/docs/guide/webhooks), [volume consistency](https://modal.com/docs/guide/volumes).

## Financial controls verified in account

Predeployment account verification recorded a $100 Junction Hackathon grant, expiry 30 November 2027, a Modal-set $101 workspace usage cap and no payment method. The cap could not be raised without adding a payment method. No card, paid top-up or subscription was added. Deployment and verification consume resources: read the dashboard for actual usage and remaining credits; the last observed dashboard snapshot during this release showed $0.01 total usage (rounded). That is an observation, not a forecast or final bill; this document makes no current balance assertion. [Budget behavior](https://modal.com/docs/guide/budgets).

## Reproduce deployment

First verify remaining credits and enforced hard cap. Authenticate using `uv run --with modal modal setup`; keep the resulting local credential private.

```bash
npm run build --prefix frontend
uv run --with modal --with python-dotenv python scripts/deploy_sponsored.py
# For a revision, stop the previous writer first:
uv run --with modal modal app stop aimo-order-desk --yes
uv run --with modal modal deploy deploy_modal.py
```

The preparation script verifies source file hashes, uploads only the four authorized datasets, and creates/updates the private runtime secret without printing values. It does not upload `.env`, local access files, database credentials or unrelated local files. Dataset usage remains subject to the challenge restrictions.

## Verification and operating limits

The latest verification passed 89 backend tests and the frontend production build. All 14 real HTTP checks through the new Sites URL passed: HTTPS health, buyer authentication, two-product catalog matching, follow-up quantity changes, preservation of the other product, stale-version rejection, hard-budget blocking/correction, fresh simulated confirmation, same-key receipt replay, read-only integrity verification and saved-state recovery. Actual deployed NVIDIA typed interpretation and Valio price/availability reads succeeded after an earlier visible NVIDIA HTTP503; no fixture was substituted for that failure. The public landing page and browser title were observed; the final A4TB footer and navigation branding were verified after redeployment.

Exact basket approval requires the separately authenticated manager and binds the current basket fingerprint. It cannot waive a hard dietary, stock or delivery failure. Local tests cover that authority boundary. A separate hosted check also rejected buyer self-approval, approved the exact €1,725 fixture basket as approver, confirmed it as buyer, and verified the simulated receipt. That prior receipt survived the final redeployment and remained readable through the branded address.

```bash
.venv/bin/python scripts/procurement_smoke.py --url https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site --live
```

This command commits a small **simulated** test basket and consumes the shared synthetic spending cap. It never sends a supplier order or payment. Local tests should use a temporary SQLite ledger instead of consuming demonstration spend. Reports remain in ignored `.local/`.

Cold starts and sequential request queueing are expected. Sessions persist across restarts and expire after eight hours. Rate counters remain process-local; full identity federation, load hardening and distributed limits are not delivered. The hosted service is a restricted synthetic purchasing demonstration, not a production wholesaler checkout.
