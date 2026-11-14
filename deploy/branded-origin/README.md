# A4TB · Valio Aimo public origin

Public address: https://a4tb-valio-aimo.cozyhawthorn4.chatgpt.site

Sites hosts this small Worker. Modal runs the FastAPI service and serves the
React build. Authentication, private catalog data and the persistent simulated
ledger remain on Modal; this proxy does not contain provider credentials.
Buyer and approver codes are still required. Browser changes from another
origin are rejected. API responses are not cached.

The exact published Worker source is `worker.js`; the original Sites project ID
is recorded in `hosting.json`. Its separate publishing checkout is ignored at
`branded-web-a4tb/`. Reuse that project; do not create another site for updates.
Read the Sites skill before publishing. Copy any reviewed Worker edit to
`worker.js` and `dist/server/index.js` in the publishing checkout; push and save
the exact source version using the Sites workflow helper, then deploy that saved
version with the existing public access setting. Never store the temporary
source credential in a file. The initial published commit is
`61fbde241e0cfa5543577601b7186ae9d8ba06dd`.

App/backend updates use the normal Modal deployment described in
`docs/DEPLOYMENT.md`; they do not require republishing this unchanged proxy.
The direct Modal service address remains available for operational checks.
