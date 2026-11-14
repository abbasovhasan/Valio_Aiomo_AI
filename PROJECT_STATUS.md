# Project status — delivered locally

14 November 2026, Europe/Helsinki. Aimo Order Desk / Rewind & Repair is implemented, running locally was verified, and review assets are prepared. No Junction/sponsor entry or status change; last observed entry Draft. Source remains private. No real orders, payments or messages.

- React/TypeScript workbench + FastAPI gateway complete: explicit three-way authority, scoped buyer/approver sessions, exact approval/resume, server revalidation, simulated receipts, evidence recorder and stale-offer repair comparison.
- Real NVIDIA typed shortlist → independent HTTP buyer → live Valio price/availability → Aiven PostgreSQL simulated receipt completed; retry returned same receipt.
- **31 backend tests passed** (4.08 s; one upstream deprecation warning). Real Aiven concurrency check passed, including cap and duplicate protection; temporary test tables removed.
- **11 Chromium desktop/mobile checks passed**, zero JavaScript errors; mobile 390 px no overflow. Explicit offline SQLite smoke passed. Production frontend build and Python compilation passed.
- Real local captioned fixture demo recorded 87.48 s; local draft seven-slide PDF/editable PPTX, pitches, submission copy, sponsor ledger and wake-up review docs ready.
- Hosting blocked: no browser account connections, Modal CLI credentials or current credit/control verification. Conditional adapter prepared. No Modal resources consumed; Aiven allowlist unchanged.
- QA server stopped at handoff; run `./start.sh` then http://127.0.0.1:8000. Generated buyer/approver codes are ignored in `.local/access.json`. Synthetic ledger reset to €0 after preserving evidence.
- Original four raw datasets retain their recorded SHA-256 hashes; .env remains 0600. Credentials, CA and raw evidence remain ignored.

Read `docs/DELIVERY.md` for reviewer steps, exact executed checks, deployment prerequisites and limitations. Official public schedule freshly confirmed: 15 November 2026 10:00 Helsinki; authenticated challenge-rule reread unavailable. Never finalize automatically.

Release verified: private-source scan passed for all 52 staged files (including extracted pitch text); all four dataset checksums match. Source pushed to origin/codex/aimo-order-desk; GitHub privacy rechecked true. Working tree clean at release.
