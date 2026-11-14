> **Procurement deployment update — 14 November 2026.** The historical release record below is superseded where it describes milk-only scope, in-memory sessions or blocked hosting. Smart order now supports persisted multi-product carts, structured interpretation, editable constraints, whole-basket approval and simulated checkout. The meal planner transfers saved recipes into that cart. Modal HTTPS deployment is live; the deployed API exercised core cart/confirmation/retry/recovery and real NVIDIA + Valio reads. Current architecture, limitations and setup: [implementation plan](IMPLEMENTATION_PLAN.md), [deployment](DEPLOYMENT.md), and [project status](../PROJECT_STATUS.md). No final competition submission or real purchase occurred.

# Sponsor integrations and evidence

Review date: 14 November 2026, Europe/Helsinki. This file distinguishes earlier account observations, fresh verification, implemented adapters and demonstrated behaviour. No sponsor entries have been submitted. Never publish secrets, raw response dumps or restricted datasets with this file.

## Integration roles

| Service | Intended useful role | Evidence boundary |
| --- | --- | --- |
| Valio Aimo | Static catalog plus authenticated customer/date-specific price and availability sandbox | No published order/reservation endpoint; our order is explicitly simulated |
| NVIDIA Nemotron | External buyer planning through typed tools | Actual tool responses are evidence; a plain "OK" inference alone is not agent reliability |
| Aiven PostgreSQL | Offers, approvals, factual audit records and atomic cumulative spending/idempotent orders | A run must actually use PostgreSQL to count; SQLite is a labelled local fallback |
| Codex | Implementation, integration, debugging, test design and delivery preparation | Development use; no OpenAI runtime API-credit claim |
| Modal | Conditional CPU hosting for the gateway/agent infrastructure | A manifest alone is not deployment; credits, controls and access must be freshly verified first |

## Fresh account and runtime observations

- **GitHub:** the main build session rechecked `gh repo view` and observed `isPrivate: true` for the configured repository, with no initial commits at that point. Do not make it public. Before any private push, inspect staged files/diff and scan for secrets and restricted content.
- **Modal:** the main build session's computer-use inventory exposed no browser or app surface. Attempts to use Chrome and the in-app browser reported unavailable. Consequently the previously signed-in promotional balance, expiry and controls could not be freshly inspected from this session. Do not treat the earlier observation below as current deployment authorization.
- **Core runtime smoke tests:** `.venv/bin/python scripts/backend_smoke.py` completed at **14 November 2026, 04:57 Helsinki** (`2026-11-14T02:57:27Z`). Aiven, both Valio business endpoints and NVIDIA typed function output were exercised. Details follow below. This is actual request evidence, not inference from `.env` variable presence.

## Credit ledger

No payment card, subscription, paid upgrade, auto-top-up or purchase was authorized. Promotional face value is not spendable proof.

| Resource | Previously observed | Fresh spend/coverage status | Usage decision |
| --- | --- | --- | --- |
| Modal Junction grant | $100 of $100; activated 13 Nov 2026; expiry 30 Nov 2027; $101 usage cap; $0 used; no payment method added | Current account balance/eligible usage/control state not freshly inspectable; CLI access also needs verification | No consumption until all gates pass |
| Aiven PostgreSQL | Free European service; 1 GB; 20-connection limit; development-IP-only allowlist | Use the existing free service with bounded connections and verified-full TLS; do not add a paid plan | No new paid resources |
| Aiven signup trial | $50 displayed, 30 days remaining in earlier setup | Runtime product eligibility/pricing and current balance unverified | Do not consume on an assumed Runtime plan |
| NVIDIA Build | Configured key; earlier hosted inference succeeded | Fresh typed function call succeeded at 04:57 Helsinki. Remaining account quota is not established by a response | Small bounded inference tests and runtime calls only |
| Codex Hackerpack | Earlier official detail described 2,500 personal usage credits valid for 30 days, excluding API credits/subscription | Development use only | Do not budget as model API funding |
| Anthropic | Earlier signed-in console showed $20; runtime key absent | Not used | Optional provider omitted |
| Google / ElevenLabs / Verda / Vultr | Browser/account observations or advertised offers only | Runtime keys, coverage or terms not fully verified | Not used; no logo-only integration claim |

The current [Modal budgets documentation](https://modal.com/docs/guide/budgets) says a workspace usage budget is a hard pre-credit cap, while a separate spend limit controls net out-of-pocket charges. Its default can equal usage limit minus credits. The [billing documentation](https://modal.com/docs/guide/billing) generically requires a payment method; promotional no-card access must be empirically established without adding one. Prefer a verified $0 net spend limit and a conservative usage cap covered by applicable, unexpired credits. Workspace/environment caps and credit eligibility are separate checks.

## Eligibility and review gaps

Earlier authenticated research in `research/CHALLENGE_RESEARCH.md` records the following. Fresh authenticated challenge-page reads failed during this build; these details are not re-certified eligibility.

- **NVIDIA / Nemotron:** the brief names Nemotron 3.5 Super VL and asks for meaningful use and output improvements. Its example API model string was inconsistent with that name. The configured default is `nvidia/nemotron-3.5-super-vl-120b-a12b`. Successful use should be shown with actual tool call evidence; owner/mentor confirmation of challenge eligibility remains useful. No one has been contacted.
- **Aiven:** recorded judging weights are meaningful use 40%, implementation 30%, impact 20%, creativity 10%. Evidence should show the database's transactional role, not just a connectivity badge.
- **Modal:** recorded weights are use 40%, ambition 25%, impact 20%, deployed demo 15%; infrastructure should be central. A local adapter or an unused account is insufficient to claim deployment.
- **Codex:** explain concrete implementation/debugging contributions and redacted development evidence. Runtime inference may use NVIDIA. Personal Codex credits are not OpenAI API credits.
- **Main challenge:** published core requires structured lookup, inquiry-to-order interaction and permissions/human approval. Published sandbox does not expose search, approval or order placement. The documented simulator fills that interface gap honestly.

Official references: [Nemotron](https://hackjunction.app/participate/45/tech-challenges/46), [Aiven](https://hackjunction.app/participate/45/tech-challenges/43), [Modal](https://hackjunction.app/participate/45/tech-challenges/40), [Codex](https://hackjunction.app/participate/45/tech-challenges/49), [Valio Aimo](https://hackjunction.app/participate/45/challenges/327). Deadline was freshly verified through the [public event schedule](https://hackjunction.app/hackathons/junction-2026): 15 November 2026 at 10:00 Helsinki.

## Deployment boundary

The current Aiven allowlist permits the development machine only. A cloud host needs a deliberate restricted egress route. Never open PostgreSQL broadly to make a demo work. Protect hosted access and privileged endpoints, use provider secrets, HTTPS, bounded CPU/concurrency and request limits, and verify the health endpoint plus full deployed flow before claiming deployment. Preserve a one-command local fallback even if hosting succeeds.

## Verification addendum

Command executed from the project root: `.venv/bin/python scripts/backend_smoke.py`.

| Check | Observed result at 04:57 Helsinki | Limit of the evidence |
| --- | --- | --- |
| Aiven PostgreSQL | Connected; schema creation succeeded; `pg_stat_ssl` reported TLS active; client uses `sslmode=verify-full` and the preserved CA | No broad allowlist change; max two concurrent application connections. This is not a production resilience/load test |
| Valio `/api/price` | Authenticated POST succeeded for three shortlist product IDs; tax-inclusive sales-unit prices returned | Synthetic customer/date-specific sandbox evidence, not a real commercial offer or reservation |
| Valio `/api/availability` | Authenticated POST succeeded for the same shortlist and 16 November delivery date; date-specific schedules returned | The Terminal candidate's sentinel quantity/cutoff is blocked, not presented as confirmed stock |
| NVIDIA Nemotron | `nvidia/nemotron-3.5-super-vl-120b-a12b` returned a valid `propose_candidates` typed function call with allowed catalog IDs | Candidate proposal only; model has no approve/commit tool. One successful call does not establish reliability or unlimited quota |

The ignored local evidence is `.local/integration-report.json`; latest supplier response records are also under ignored `.local/`. Do not commit those raw responses. Sanitized evidence above is enough to establish which operations were exercised.

### Complete external-agent flow

The main build session executed:

```bash
.venv/bin/python scripts/agent_client.py --mode live --model --commit --output .local/external-live-proof.json
```

The first run completed at approximately **05:03 Helsinki**; a later release smoke repeated it successfully. In these runs, the independent process called NVIDIA and received `live_tool_call`, sent selected IDs through the real HTTP gateway, obtained live Valio sandbox evidence, and persisted a **simulated** order through Aiven PostgreSQL. Repeating commitment returned the same receipt (`duplicate_returned_same_receipt: true`). The scoped verification endpoint reported record integrity and scope valid. This is gateway record consistency, not a digital signature, independent product truth, stock reservation or delivered goods.

The gateway agent separately exercised the same client against an isolated server on port 8001 with `--base-url http://127.0.0.1:8001`; it also completed the live/model/simulated-order path. The local evidence file may contain the latest of these runs. Do not publish the raw product/evidence content.

### Invariant and real database verification

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/backend_postgres_check.py
```

The latest gateway test invocation reported **31 passed in 4.08 seconds**, with one upstream Starlette/httpx deprecation warning. Covered behaviour includes autonomous commitment, independent receipt verification, separate exact-offer approval, invalid dietary choices, quantity/role bypasses, unknown and late availability, staleness, changed prices, missing prices, cumulative cap concurrency, duplicate concurrency, prompt injection, upstream/model failure, foreign-origin mutation rejection, security headers, unknown dietary facts, and dimensionally valid pack/lot arithmetic. The final adversarial checks also reject supplier cutoff, price-validity or freshness expiry after acquiring the database row lock, and reject changing the idempotency key of an already committed offer. These are synthetic prototype tests, not production certification.

The PostgreSQL check used a temporary isolated namespace on the real Aiven service: PostgreSQL **18.7**, active **TLSv1.3**, two-connection application bound. Six concurrent distinct €1,150 simulated commitments against a €6,000 cap resulted in **five successes and one cap rejection**, with €5,750 spent. Four duplicate retries returned the same receipt. The temporary tables were removed. The ignored summary is `.local/postgres-check.json`; the reproducible source is `scripts/backend_postgres_check.py`.

The main session prepared a conditional Modal adapter and deployment instructions. **No Modal resources were consumed and no deployed URL is claimed.** Browser account access and CLI authentication remain unavailable; the current promotional account coverage and controls cannot be freshly verified. Final UI/browser checks and release results belong in DELIVERY.
