# A4TB · Valio Aimo — access readiness

14 November 2026, Europe/Helsinki. Customer entry point: **[A4TB · Valio Aimo](https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site)**. The public Sites frontdoor proxies the private-code-gated application on Modal. Source, restricted catalog and runtime secrets remain private.

## User constraints

- Never perform the final Junction project submission or change its submission status. The last observed entry was Draft.
- Keep the GitHub source repository private.
- Keep credentials outside all source repositories, including private repositories. Use ignored local environment files and service secret storage.
- Keep the restricted challenge datasets outside Git and public frontend assets. Hosted data belongs in the private runtime volume.
- All confirmations must remain simulated; no real supplier order, invoice, reservation or payment is created.

## Verified access and remaining work

| Service | Verified state | Remaining work / boundary |
| --- | --- | --- |
| Aiven | Existing European PostgreSQL integration previously passed TLS connectivity and concurrency checks; local credentials and CA remain ignored | Local option remains available. Hosted runtime uses persistent SQLite; the Aiven allowlist was not widened. Current service/credit state requires the account dashboard. |
| Google AI Studio | Earlier browser sign-in observed; no runtime key selected during that inspection | Optional alternative; not required by the selected NVIDIA integration. |
| Junction | Authenticated resource access previously verified; last observed competition entry Draft | Read-only research and preparation only. Owner performs any final submission. |
| Valio Aimo | Authorized catalog present; authenticated sandbox price/availability reads tested through the deployed application | Demo webshop was explored read-only. No supported supplier cart/order integration is claimed; lookup does not reserve stock. |
| GitHub | Private repository [Valio_Aiomo_AI](https://github.com/abbasovhasan/Valio_Aiomo_AI), branch codex/aimo-order-desk; earlier source push and privacy check recorded | The release source is reviewed and prepared for the private branch; the final commit record is available in Git history. Restricted data, credentials and raw runtime evidence stay ignored. |
| ElevenLabs | Earlier signed-in Home page observed | Optional voice path; not part of the delivered purchasing workflow. |
| NVIDIA Build | Configured Nemotron runtime; actual typed interpretation and Valio-backed basket quotation tested through the deployed public URL | Provider outages remain visible. Local parsing is explicitly selectable; no fabricated model output or silent fixture substitution. |
| Application hosting | Public Sites frontdoor serves A4TB · Valio Aimo and proxies Modal. Private volumes persist restricted data and single-writer SQLite; separate buyer/approver codes remain required | Final public A4TB title, navigation branding and footer verified after redeployment. Identity federation, horizontal scaling and distributed limits are not delivered. |

Browser sessions alone do not establish programmatic API access. Runtime access above was verified separately. Modal uses the existing sponsored grant with account spending controls checked before deployment; read its dashboard for current usage and remaining credits. No current balance is asserted here. No payment method, paid top-up or subscription was added during this work.

Worker-interview follow-up: authorized demo webshop credentials authenticated through the normal Valio Aimo sign-in redirect. Read-only inspection observed product search, delivery-date selection, pack/tax pricing, availability and an existing shared basket. The shared basket, customer account and supplier ordering state were not changed. UI access does not establish a supported cart/order API contract.

Latest verification: 89 backend tests passed, frontend production build passed, and 14 real HTTP checks through the new public URL passed, including authentication, multi-product follow-up/budget changes, stale-version protection, simulated receipt replay/verification/recovery, live NVIDIA typed interpretation and live Valio sandbox reads. The public page and browser title were observed. See [deployment details](../docs/DEPLOYMENT.md) and [project status](../PROJECT_STATUS.md) for the release state and operating limits.
