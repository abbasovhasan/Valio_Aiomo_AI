# A4TB · Valio Aimo — services, credits and evidence

Reviewed 14 November 2026, Europe/Helsinki. This record distinguishes an implemented integration, an executed check and unverified eligibility. No sponsor entry or final Junction submission was performed. Credentials, raw responses and restricted datasets remain outside source and public artifacts.

## Services actually used

| Service | Concrete role | Executed evidence and boundary |
| --- | --- | --- |
| Valio Aimo | Restricted static catalog and authenticated customer/date-specific price/availability reads | The current 47-check hosted extension run exercised actual sandbox reads. Registered private workspaces use the configured demonstration supplier account, not a newly established customer contract. No published order/reservation contract is used; confirmations belong to our simulator. |
| NVIDIA Nemotron | Optional typed purchasing interpretation/grounded queries and the owner-requested automatic image reader | Hosted text interpretation succeeded with `nvidia/nemotron-3.5-lightning-30b-a3b`. Sanitized images now try separately configured `nvidia/nemotron-3.5-super-vl-120b-a12b` automatically, without a provider selector/checkbox; failed provider reads fall back to local OCR with honest API provenance. Trial inputs remain nonconfidential demonstration content under the plain privacy notice. No approve/commit tool is available to either model. |
| Tesseract and Whisper | Local image fallback/explicit offline OCR and default speech recognition | Actual hosted checks returned local Tesseract OCR and pretrained Whisper base CPU int8 transcription. Speech remains local; ordinary images now attempt NVIDIA first. Editable text requires customer review and never directly changes a cart. Explicit API `provider=local` avoids external image processing; explicit cloud denial is respected. |
| Modal | CPU ASGI hosting for the Python service and private catalog/state volumes | Final B4 is live with 1 CPU, 1,536 MiB memory, maximum one container/input. Persistent SQLite commits before acknowledgement. Public asset/health/policy, 12 fresh B4 continuity checks and the actual automatic NVIDIA image probe passed without new orders or lost shared/private records. |
| Sites | Public branded HTTPS frontdoor, proxying the existing Modal service | The owner explicitly chose public reachability while retaining authenticated buyer/manager access, including private registration and existing code login. Sites contains the proxy, not provider keys or the restricted catalog. |
| Aiven PostgreSQL | Existing local option for transactional offers, approval, audit, spending and idempotency | Real TLS and isolated concurrency tests were previously executed. Hosted operation uses persistent SQLite; no hosted Aiven use or widened allowlist is claimed. |
| Codex | Repository research, implementation, integration, test design, review and delivery | Development use. Personal Codex usage credits are not OpenAI runtime API credits. |
| GitHub | Existing private source repository and reviewed branch history | Prior release `ff0384c` was pushed to `codex/aimo-order-desk`; privacy and staged private-source scan were checked. Current release identity belongs to the Git history and final handoff; no public source release is claimed. |

Text ordering defaults to the local structured parser; speech uses local Whisper base. Image reading automatically attempts NVIDIA and falls back to Tesseract on provider failure; images are resized/sanitized and output stays editable. A single hosted transactional store owns purchasing truth. Google/Gemini, Anthropic, ElevenLabs, Verda, Vultr, MongoDB and other evaluated offers were not integrated merely for a sponsor claim. Browser sign-in or an advertised offer does not establish runtime access or credit coverage. Measurements and provider limits remain in [AI_MODEL_SELECTION.md](AI_MODEL_SELECTION.md).

## Credit and spending observations

| Resource | Verified observation | Use boundary |
| --- | --- | --- |
| Modal Junction grant | Previously verified: $100 grant, expiry 30 November 2027; Modal-set $101 workspace usage cap; no payment method. The later November preparation CSV observed $0.06505835 total, after the earlier $0.04369075 release observation. | Reports can lag/include other workspace activity; neither observation is a final bill or remaining balance. Check actual usage/coverage before further provisioning; no card, top-up or paid upgrade was added. |
| Aiven | Existing free European PostgreSQL service; bounded connections and verified-full TLS | No new paid plan. The development-machine allowlist was preserved. The earlier $50 signup-trial display does not establish eligibility for another Runtime product. |
| NVIDIA Build | Configured project key and actual bounded typed inference succeeded | Successful requests do not prove unlimited remaining quota. Use bounded inference/runtime calls; record failures honestly. No full-catalog embedding job or new paid subscription is claimed. |
| Codex Hackerpack | Earlier official offer described personal usage credits, excluding API credits/subscription | Development only; do not budget these as runtime model funding. |
| Other offers | Earlier account observations or advertised grants only | No consumption or paid commitment based on assumed eligibility. |

Modal controls and deployment configuration are detailed in [DEPLOYMENT.md](DEPLOYMENT.md). The last usage observation is historical evidence; the live dashboard owns current spending. No personal purchase, payment card, paid subscription, auto-top-up or uncovered financial commitment was initiated.

## Current verification

The prior A4TB release passed 89 backend tests, the production build and 14 hosted checks covering authentication, cart edits, budget/version failures, simulated confirmation/replay/verification/recovery and live NVIDIA/Valio. A separate hosted exact-approval check also passed and its simulated receipt survived redeployment.

Final `index-B4p90PsT.js` is deployed with **285 backend tests**, **12 fresh continuity checks** and **3 hosted long-name checks**. Bk repeated-choice/layout and unchanged CFF media evidence remain valid: actual no-query NVIDIA vision, cloud-denial handling, preserved purchasing state and the owner's phone-photo success. Catalog/history and live text/Valio checks remain separately scoped. Only private commit/push remains pending; no universal accuracy, eligibility or production certification is implied. See [ACCEPTANCE_RECORD.md](ACCEPTANCE_RECORD.md).

## Historical external-agent and database proof

The original milk release actually executed:

```bash
.venv/bin/python scripts/backend_smoke.py
.venv/bin/python scripts/agent_client.py --mode live --model --commit --output .local/external-live-proof.json
.venv/bin/python scripts/backend_postgres_check.py
```

The separate HTTP client obtained NVIDIA `propose_candidates` output, called the real gateway, read live Valio sandbox facts and committed a simulated receipt through Aiven; retry returned the same receipt and scoped verification passed. The model received a small normalized shortlist, not credentials or the full catalog.

The isolated PostgreSQL check reported PostgreSQL 18.7/TLS1.3, at most two concurrent application connections, five successful €1,150 commitments and one cap rejection under €6,000, and same-receipt duplicate retries. Temporary tables were removed. These are observed prototype transaction checks, not load/failover certification or supplier purchases. Raw local evidence remains ignored.

The historical milk browser/video/pitch artifacts are secondary demonstrations of authority and recovery. They should not be presented as footage of the final generic-cart workflow.

## Eligibility limits

Earlier authenticated research records meaningful-use requirements for [NVIDIA](https://hackjunction.app/participate/45/tech-challenges/46), [Aiven](https://hackjunction.app/participate/45/tech-challenges/43), [Modal](https://hackjunction.app/participate/45/tech-challenges/40) and [Codex](https://hackjunction.app/participate/45/tech-challenges/49). Later authenticated rereads were unavailable, as recorded in [rule checks](evidence/RULES_RECHECK.md). Implemented use is not a guarantee of eligibility or an award. No organizer/mentor message or sponsor entry has been sent.

The text and automatic image model names are recorded above; the earlier sponsor example string was inconsistent, so owner/mentor eligibility review remains useful. Trial input restrictions and unknown remaining quota still apply; automatic image routing is not a production subscription or consent to send confidential material. Source remains private. Organizer access/licensing and restricted-data terms require separate owner review before submission. Deployment is not submission.
