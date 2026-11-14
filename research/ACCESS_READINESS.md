# Access readiness — 14 November 2026

## User constraints

- Never submit the final project or change its submission status. Junction currently shows Aimo Order Desk as Draft.
- Keep project source private when publishing to GitHub.
- Keep credentials out of all source repositories, including private repositories. Use ignored local environment files and service secret storage.
- Keep challenge datasets out of Git; data/raw/ is already ignored.

## Verified access and remaining work

| Service | Verified state | Remaining work |
| --- | --- | --- |
| Aiven | Signed in; console displays $50 trial credits and service creation screen | Free European PostgreSQL service aimo-order-desk created; Running; SELECT 1 succeeded with TLS confirmed in pg_stat_ssl. Credentials and CA saved in ignored local files; TLS verify-full configured; network access restricted to the development machine current IP |
| Google AI Studio | Signed in; playground showed no API key selected | Configure a runtime API key and verify a minimal model request |
| Junction | Signed in; Aimo Order Desk is Draft | Read-only access / prepare artifacts only; never finalize |
| Valio Aimo | Signed into resource portal | API key saved in ignored .env; authenticated /api/ping returns HTTP 200 with User-Agent AimoOrderDesk/0.1 |
| GitHub | CLI signed in as abbasovhasan; private repository created | origin configured as https://github.com/abbasovhasan/Valio_Aiomo_AI; GitHub isPrivate=true confirmed; no files pushed |
| ElevenLabs | Signed-in Home page observed | Optional voice provider; runtime API key not configured |
| NVIDIA Build | Sign-in modal opened; next step accepts developer-program terms | API key saved in ignored .env; model list HTTP 200 and actual nvidia/nemotron-3.5-super-vl-120b-a12b inference HTTP 200 with response OK. NVIDIA is now the configured runtime model |
| Application hosting | No deployment configuration in repository | Sponsor-hosting assessment in HOSTING_PLAN.md. Modal selected as proposed host: $100 active Junction grant verified, expiry 30 November 2027, $101 workspace cap, $0 usage. CLI/deployment pending. Aiven GitHub account connected; Runtime pricing/credit coverage remains unverified. |

Browser sessions do not establish programmatic API access. A free Aiven database was created during follow-up setup. No paid services, source uploads, or final submissions were created.

Updated implementation direction is Codex + Aiven + NVIDIA Nemotron. Gemini remains an optional alternative. ElevenLabs is optional after the core purchasing workflow. NVIDIA is an alternative model path; do not add providers merely to list sponsors. Verda/Modal are conditional hosting choices rather than current prerequisites.
