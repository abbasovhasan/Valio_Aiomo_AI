# Critical rule recheck - 14 November 2026

All timestamps use Europe/Helsinki (UTC+02:00 on these dates). No submission, sponsor entry or organizer communication was made.

## Fresh public observations

- The official [Junction 2026 public event page](https://hackjunction.app/hackathons/junction-2026) was successfully read during this build session. Its schedule lists submissions starting **14 November 2026 at 12:00** and final submissions at **15 November 2026 at 10:00**, UTC+02:00. It lists teams of 1-4. At the initial 04:49 Helsinki build check, the deadline was still about 29 hours 11 minutes away.
- Public event "registration closed" refers to the 25 October application deadline. It does not establish that project submissions have closed.
- The authenticated [guide](https://hackjunction.app/participate/45/guide), [Valio challenge](https://hackjunction.app/participate/45/challenges/327), and [Nemotron](https://hackjunction.app/participate/45/tech-challenges/46), [Aiven](https://hackjunction.app/participate/45/tech-challenges/43), [Modal](https://hackjunction.app/participate/45/tech-challenges/40) pages were attempted through the web tool. Each returned an access/internal error. Direct unauthenticated guide/challenge HTTP reads returned 404. This does not prove a rule change. Scoring and sponsor eligibility details remain based on the earlier authenticated research in `research/CHALLENGE_RESEARCH.md`.
- Unauthenticated `https://junction26.valioaimo.fi/openapi.json` returned a sign-in HTML page, not an API contract. Backend verification uses the configured authenticated connection; a sign-in response must never be mistaken for valid OpenAPI JSON.
- Browser inventory in the main build session exposed no available Chrome or in-app-browser connection. Signed-in Modal billing could therefore not yet be freshly inspected. Previously recorded promotional account observations are not a fresh balance check.

## Fresh Modal documentation

The official [budgets documentation](https://modal.com/docs/guide/budgets) was read successfully. A workspace budget is a hard usage cap for the current billing cycle **before** credits. A separate spend limit caps net out-of-pocket charges. Without a custom spend limit, the documented default is usage limit minus credits. Environment budgets do not cover all workspace charges and are available on Team/Enterprise plans.

The official [billing documentation](https://modal.com/docs/guide/billing) describes monthly and incremental charges and generically says a payment method is required. That generic statement does not establish whether this particular promotional workspace can deploy without one. No card should be added to resolve that ambiguity. The account's real remaining applicable grant, expiry, enforced cap/net limit and deploy access must all be verified before consuming resources.

## User review boundary

The standing instruction overrides any guide instruction to finalize: **never change the Junction submission status or submit a sponsor entry**. Prepare materials locally. Keep Aimo Order Desk Draft. The user's review buffer is intentional.

Earlier research records an event MIT/source-access requirement. The source repository must remain private under the user's instruction. The user should resolve organizer access and any licensing/publicity tension before deciding what to submit; no privacy setting should be weakened automatically. Challenge datasets have separate restricted-use terms and must not be published under a code license.
