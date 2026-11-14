# Sponsor hosting assessment — 14 November 2026

User preference: host the application with a tech sponsor using redeemed credits. Do not submit the Junction project as FINAL. Do not enable paid top-ups or rely on unverified credits.

## Proposed choice

Use Modal for the application/agent API if its redeemed credits are confirmed, with existing Aiven PostgreSQL and NVIDIA inference. Modal supports full ASGI applications, HTTP web servers, secrets, and enforced workspace budgets. This is a proposed architecture; no app has been deployed and Modal account credits are now verified: active $100 Junction Hackathon grant, all remaining; expiry 30 November 2027. Dashboard shows $0 usage and a Modal-set $101 workspace cap, including $1 monthly free credit; increasing it requires adding a payment method. None was added. CLI setup and deployment still remain.

Aiven Runtime is a strong alternative because the existing Aiven account has $50 trial credits displayed and PostgreSQL already runs there. Its console exposes Deploy from GitHub, but GitHub account abbasovhasan is now connected; selected repository permissions still need checking. Runtime-specific pricing and trial-credit coverage remain unverified. Limit any eventual GitHub authorization to the private project repository.

Verda is an alternative for container/model hosting. Its documentation says redeemed credits apply to a selected project and can cover serverless containers and inference. Personal balance and account access remain unverified. NVIDIA hosted inference already works, so renting a GPU solely for this project is not currently necessary.

Vultr remains a fallback if the user's redeemed credits are there. Do not provision a server before checking its credit conditions and total cost.

## Deployment prerequisites

- Verify selected sponsor account, credit balance, expiry, eligible products, and billing cap.
- Prepare a runnable application and its container/provider manifest before deployment.
- Store credentials in provider secrets; keep source repository private and raw challenge files out of Git.
- Retain PostgreSQL TLS hostname and CA verification. Current Aiven IP allowlist permits only the development machine; add the selected host's approved egress addresses or suitable network path before deploying. Do not broadly open the database to fix connectivity.
- Make authenticated user approval and spending controls work before making the demo reachable.
- Prepare deployment for review before any final publish/deploy action.

## Account observations

- Claude Platform dashboard is signed in and displays $20 organization credits. API key not configured.
- Google AI Studio was signed in earlier. Google Cloud appeared at a project welcome URL after user verification, but its tab was closed before dashboard inspection; billing/deployment eligibility not verified.
- Modal signed in; $100 Junction Hackathon grant verified, expires 30 November 2027; $101 workspace usage cap and $0 usage displayed. No payment method added.
- Aiven Runtime deployment setup shows connected GitHub account abbasovhasan and repository selection. Aiven still displays $50 trial credits with 30 days left; existing PostgreSQL is on its free plan.

## Official documentation

- Aiven Runtime: https://aiven.io/docs/products/runtime
- Aiven deployment: https://aiven.io/docs/products/runtime/deploy-apps
- Modal web functions / full ASGI applications: https://modal.com/docs/guide/webhooks
- Modal workspace budgets: https://modal.com/docs/guide/budgets
- Verda credit redemption and eligible services: https://docs.verda.com/resources/obtaining-free-credits/how-to-redeem-credits/
