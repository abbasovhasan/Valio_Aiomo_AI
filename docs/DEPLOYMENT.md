# Sponsor hosting: prepared; not deployed

No Modal compute, secret, volume or proxy was created. The application is fully runnable locally with `./start.sh`.

The current session has no connected browser (CUA inventory empty; Chrome and IAB unavailable), no `modal` executable, and no Modal token configuration at the usual local paths. This prevents fresh account-level verification and deployment authentication. Earlier account observations are preserved in `research/HOSTING_PLAN.md`; they are not a current balance assertion.

Before consuming any resource, the account owner must verify in Modal workspace `hasan-abbasov`:

1. The Junction grant's **remaining** balance, expiry and eligible CPU/ASGI usage. Prior observation: $100 grant, expiry 30 November 2027, no payment method, $101 hard workspace usage cap.
2. The currently enforced **hard usage budget**, its response when exhausted, and net spend limit of $0 where supported. A notification threshold is insufficient. No card, top-up, subscription, or uncovered charges.
3. CLI authentication and the permitted deploy workflow. Creating persistent credentials in browser requires account-owner involvement under the browser tool's confirmation policy; none was attempted here.
4. A restricted Aiven network path with explicit static egress. The current database permits the development machine only. Never widen this to the Internet. Modal proxy/static egress eligibility and costs have not been verified.

`deploy_modal.py` is a **reviewable adapter, not a validated deployment**. It uses CPU 0.5, 1 GiB, one container, four in-flight inputs, scale-to-zero and a 120 s timeout. It needs a private mounted catalog/CA volume, Modal runtime secret, approved network proxy and a confirmed spending cap before deployment. A GPU is unnecessary: inference uses NVIDIA's hosted endpoint. Its safeguards deliberately refuse to serve if the catalog, CA or persistent database is unavailable. No source or restricted dataset has been published to Modal.

A production deployment also needs shared persistent sessions and distributed rate limits. The current single-process demo keeps sessions and rate counters in memory; restarting ends sessions. Do not silently run several replicas or call this production-ready.

After preparation, the owner can review `modal deploy deploy_modal.py`. Verify HTTPS health, authenticated API, separate-role approval, one receipt on retry, and stale/cumulative rejection on the deployed host. Record actual URL and usage here only after those checks pass.
