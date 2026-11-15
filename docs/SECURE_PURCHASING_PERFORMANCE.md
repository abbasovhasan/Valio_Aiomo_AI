# Secure purchasing: measured performance

15 November 2026, Europe/Helsinki. Baseline source `d52cf2d`, public Bj9 frontend, one Modal physical CPU requested/1,536MiB, one container/input, minimum zero, 120-second scale-down window. Measurements use nonconfidential authored input, actual restricted catalog locally, temporary SQLite and bounded authorized provider reads. They are small observations, not capacity or recognition guarantees. Read/media probes submitted no orders; separate explicitly authorized private journeys produced the €836 exception simulation/idempotent retry and a browser-created €77.40 simulation; shared spend was untouched. No policy, dietary, freshness or persistence check was removed.

## What caused delay

The cold process must parse the 17,546-product catalog and build its lexical index. Warm broad dietary filters still inspect verified source facts to preserve safety and accurate facets. External model response time is substantially larger than local parsing. `max_inputs=1` intentionally serializes hosted operations, so another request can queue behind model/Whisper work. Every acknowledged mutation also waits for the private volume commit. Existing catalog loading, lexical indexing and Whisper model reuse already worked; media already executes outside the event loop. Additional CPUs do not directly remove external-provider wait or a single-input queue.

| Measured sample | Observation |
| --- | --- |
| Public first HTTP request after CLI verified zero tasks | **6,584.826ms**; TCP51.569ms/TLS32.211ms/header wait6,498.181ms. Warm HTML **374.545–1,111.017ms**; health505.891ms; 420,559-byte JS146.399ms. This is cold-versus-warm total latency, not isolated container startup or browser rendering. |
| Local raw catalog /first lexical search | **1,261.864ms /1,735.887ms**, mostly CPU. Warm milk discovery **80.100–81.468ms**. |
| Local broad lactose-free /hosted first and warm milk | Local **1,191.725–1,201.486ms**; hosted first milk **3,094.439ms**, warm **776.658/1,041.546ms**; hosted broad lactose-free2,881.187ms. No date/model/supplier lookup. |
| Local three-item fixture quotation | **409.739–416.806ms**: interpretation80–86ms, discovery281–284ms, SQLite transactions29ms, fixture lookup3.6ms. |
| Local review /queue /decision | Saved review GET **2.876–4.120ms**; approval queue10.423ms; exact approval22.423ms. |
| Local isolated simulated submission /same-key replay | **36.071ms /14.405ms**; exactly one temporary €7.80 simulation. Temporary database removed; no hosted/shared spend. |
| Hosted private reads/authentication | Existing cart GET **275.707–306.013ms**; workspace264.026–491.611ms; password login5,563.568ms/logout2,169.965ms. App/persistence/proxy contributions were not separately available in this baseline. |
| Local printed OCR /Whisper | OCR **159.459–199.785ms**. Whisper load390.683ms, audio decode5.286–6.287ms, cached inference **1,154.487–1,209.337ms** for **4.861 seconds** of synthetic audio. Complete catalog/media process peak892.61MiB. |

The hosted read probe preserved the private QA buyer's preferences/spend and made zero model/supplier/order calls. Twenty-product responses contained approximately 150–193KB of decoded JSON, and one saved cart 86KB. A separate actual baseline wire check (`.local/secure-json-wire-before.json`) requested gzip and observed **7,554 wire bytes /150,337 decoded bytes**, `Content-Encoding: gzip`, HTTP200 in **1,431.931ms**: approximately **95% compression already working** at the hosted boundary. No new compression middleware was needed or added. Payload size alone therefore does not establish a network bottleneck or justify removing useful evidence. A CUA reload plus accessibility snapshot took 6.515s, but browser Performance API timing was unavailable; it is not a pure navigation/render measurement.

## Implemented safe changes

**Static catalog brand-name index.** Previously each intent clause rebuilt/sorted brands by scanning all17,546 rows. Only immutable brand names are indexed; replacing/reloading the source object rebuilds it. Product eligibility, dietary declarations, prices, stock, budgets, authority and preferences remain freshly evaluated. Warm brand lookup changed from7.5–8.6ms to0.18–0.23ms; the same three-item local intent median changed **63.664→2.008ms**. Alternating old/new scanners in the **same current app/process** gave fixture-cart medians **410.555→334.822ms** (about18.4% for this sample), with all six projected constraints/status/selected quantities/prices/totals equal. This isolates the index change despite concurrent purchasing-feature development.

**Reusable provider connections.** Separate bounded HTTPX pools for Valio and NVIDIA retain connections, not answers. Current credentials, customer/date/products and each original timeout are supplied per request. Redirects remain disabled; response cookies are discarded and cookie headers never forwarded. Existing bounded retries and explicit failures remain. Every commercial lookup still reaches the provider; there is no quote/result or permission cache. Pools close at process exit.

The bounded transport A/B executed exactly **two text and two image** service invocations, with **9,077 reported tokens for those four only** and no full catalog or customer media. Root later executed one additional text and one automatic-image invocation, making **six service invocations across these performance probes**; root's token usage was not reported. Text HTTP changed **6,890.727→10,238.442ms**, with response-header wait6,747.528→10,128.297ms and completion tokens1,264→1,590: **no total text-model speedup is claimed**. Vision HTTP changed **2,165.655→1,815.924ms**; before it spent222.363ms in TCP/TLS setup, while the reused connection recorded neither phase. Provider header wait also varied1,941.903→1,814.614ms, so the whole difference cannot be attributed to pooling. Header wait combines provider/network/queue/inference; it is not pure model execution. The first text interpretation also paid approximately1.2s for cold local catalog loading.

Focused validation: **11 new hotpath tests plus interpretation/media suites: 68 passed in 3.06s**. Tests verify scoped keys/timeouts, fresh customer payloads on every lookup, cookie isolation, no auth forwarding on redirects, bounded failures without cached/fixture substitution, missing-key behavior, separate/thread-safe pools, closure and source-index rebuild. The final current combined backend suite passed **414 tests in 127.46s**, exit 0 without warnings/failures, including the current-review and authority fixes. The deployed bounded read probe below also passed.

## CPU and hosting decision

A separate local affinity experiment used the same4.861s synthetic clip/model/decoding and three runs each: one logical CPU/one inference thread median **1,934ms**; one CPU/two threads **2,147ms**; two distinct-core logical CPUs/two threads **1,825ms**, all preserving the expected quantities. This is not a Modal resource benchmark or a mapping of logical affinity to Modal physical-core requests. The modest improvement over the best one-CPU setup and observed memory below1,536MiB do not alone establish a need for2CPU/2GiB. Existing model reuse remains; no resource/concurrency change was applied by this audit.

Root verified the live account: **$100.76** credit balance, **$0.24** applied credits/$0 charges this cycle, active Junction grant **$100 remaining**, expiry **30 November2027**, enforced **$101** workspace cap and a payment-method requirement to raise it. This supersedes old grant/balance observations. No payment method, top-up or paid commitment was added. Root owns any resource adjustment.

[Modal pricing](https://modal.com/pricing) lists Functions CPU **$0.0000131/physical-core-second**, memory **$0.00000222/GiB-second**; load and warm-idle time are billable, scaled-to-zero time is not. [Resource billing](https://modal.com/docs/guide/resources) uses the greater of requested or actual usage. At reservation levels, 1CPU/1.5GiB is approximately **$0.059148/active hour**, versus 2CPU/2GiB **$0.110304**; these exclude any regional factor or higher actual usage. The published compute allowance excludes Modal Model APIs; grant-specific Model API coverage was not proven. This app uses Functions and the existing NVIDIA Build service separately, with no Modal Model API calls planned.

Root selected only the reversible **120→300-second idle window**, based on the measured6.585s cold versus0.4–1.1s warm responses. **CPU1, memory1,536MiB, minimum zero, one container and one input remain unchanged.** The extra180s idle reservation is approximately **$0.0029574 per cycle** at listed base rates before any regional multiplier, not a verified billed amount or continuously warm service; no region override is configured. Deployment and the coordinated idle/zero-task recovery checks passed as recorded below; the300s setting is not an exact shutdown-time guarantee. No CPU/memory increase was selected. [Modal volume consistency](https://modal.com/docs/guide/volumes) permits last-write-wins conflicts on a shared file, and [input concurrency](https://modal.com/docs/guide/concurrent-inputs) requires appropriate application semantics. This implementation retains its single-writer constraints.

## Deployed measurements and evidence

After deployment of **index-D7lX2GlZ.js**, the same private-QA-B read probe passed **15/15 HTTP200 responses**. Its saved preferences and spend remained identical; mandatory-restriction count was zero in both samples. No order, model or supplier request occurred. Root ran browser journeys concurrently, so the single-input queue/transport conditions differ; these totals cannot establish a general end-to-end speedup.

| Same hosted operation | Baseline total ms | After total ms | After measured app /persistence ms |
| --- | --- | --- | --- |
| Private password login | 5,563.568 | 5,402.159 | 4,600.714 /523.068 |
| First measured milk search | 3,094.439 | 1,757.949 | 1,442.116 /none |
| Two subsequent milk searches | 776.658–1,041.546 | 687.627–2,303.775 | 185.450–193.049 /none |
| Broad lactose-free | 2,881.187 | 2,736.577 | 2,216.655 /none |
| Category 17300 | 741.699 | 380.477 | 65.412 /none |
| Saved cart review GET, three samples | 275.707–306.013 | 299.049–307.604 | 29.930–34.426 /none |
| History GET | 532.510 | 218.305 | 18.947 /none |
| Logout of probe's own session | 2,169.965 | 1,432.966 | 385.691 /729.310 |

The slow after milk sample spent **193.049ms inside the app** and had **2,110.726ms unattributed** outside measured app time. That residual includes network/proxy/hosting queue/body delivery; it does not isolate which one caused the wait. Login's measured app time also remains large and is not explained away as provider latency; that operation made no provider call. No authentication/persistence checks were weakened. Read-only GETs had no volume-persistence duration; authentication mutations measured it explicitly. After milk responses remained compressed at **7,476–7,572 wire bytes /150,338 decoded bytes**, and saved-cart responses were 8,122 wire bytes /86,955 decoded bytes. Existing hosted compression was preserved.

### Hosted media, complete cart and exact decisions

Root's additional media report passed **20/20 HTTP200 responses**, cancelled/hid only its two new fixture drafts, and preserved the existing €836 receipt, spending and preferences. Actual automatic-image provenance was NVIDIA Super VL; speech and explicit local OCR remained local. The following processing durations are the API's whole extraction/transcription helper time, including decoding and any model loading, **not isolated inference**. “First” means the first sample of the recorded pair.

| Named operation | HTTP ms | App ms | Persistence ms | Reported media processing ms |
| --- | --- | --- | --- | --- |
| Printed local OCR | 659.294 | 413.255 | 5.108 | 395 |
| Automatic NVIDIA image | 1,947.589 | 1,589.493 | 5.067 | 1,574 |
| Local Whisper first sample | 2,653.767 | 1,891.247 | 5.044 | 1,408 |
| Local Whisper cached sample | 2,460.292 | 1,527.198 | 5.800 | 1,348 |
| Two-item fixture cart, local interpretation | 2,912.230 | 1,729.899 | 792.487 | — |
| Two-item fixture cart, NVIDIA interpretation | 8,736.026 | 7,889.050 | 503.743 | — |

The last two rows include the **whole two-item cart operation**—interpretation, discovery, validation and persistence. They are not pure parser/model measurements, and differ from the earlier isolated **three-item** brand-index A/B. No speedup percentage is inferred between them.

| Successful private exception/manager operation | HTTP ms | App ms | Persistence ms |
| --- | --- | --- | --- |
| Explicit €36 exception request for €836 basket/€800 budget | 1,759.708 | 1,075.142 | 487.412 |
| Buyer resubmits a fresh exact revision | 1,981.000 | 1,046.014 | 704.268 |
| Explicit buyer simulated submission | 2,160.913 | 1,492.365 | 455.036 |
| Same-key submission retry | 1,414.203 | 727.977 | 427.046 |
| Receipt consistency verification | 306.691 | 10.341 | none |
| Independent manager read-only review of browser's €77.40 request | 445.762 | 27.535 | none |
| Independent exact manager approval of that request | 2,236.084 | 1,391.994 | 430.414 |

The €836 report passed eight functional checks: original €800 budget/exact €36 preserved, direct premature submission blocked, exact independent approval, one private simulation, identical retry receipt, scoped consistency verification and unchanged preferences. The separate €77.40/€70 request's manager approval created **zero orders** and did not submit automatically. These named samples establish neither an overall hosted latency guarantee nor an isolated hosted queue-discovery timing.

The later private no-order transition audit passed22checks in43.46s, preserving its€913.40spend/preferences/history/two receipts. Its three queue samples had median293.15ms HTTP /35.557ms app (no persistence); exact approval1,863.14/1,000.775/559.273ms HTTP/app/persistence; rejection2,438.86/1,371.395/841.885ms; request changes1,950.86/1,041.616/491.427ms. These are small later samples under possible concurrent UI traffic, not an isolated latency comparison or new orders. Protected evidence: `.local/private-hosted-transition-report.json`.

Private reports: `.local/secure-hosted-before-navigation.json`, `secure-performance-hosted-reads-before.json`/`-after.json`, `secure-json-wire-before.json`, `secure-performance-journeys-before.json`, `secure-performance-components-before.json`/`-after.json`, `secure-performance-brand-quote-ab.json`, `secure-performance-provider-before.json`/`-after.json`, three `secure-performance-whisper-*.json` files, `secure-hosted-media-performance.json`, `secure-hosted-exception-report.json` and `secure-hosted-ui-manager-report.json`. They omit credentials, uploaded customer media and private response bodies.

Separate `Server-Timing` app and volume-persistence fields were observed in the new deployment; baseline headers had neither. Root's CUA owns frontend rendering/loading feedback, review/approval/media journeys and physical-device checks; no new broad hardware or recognition claim follows from these measurements.

### Coordinated inactivity and cold recovery

No agent app requests occurred during the coordinated gaps. The bounded probe observed **one task after201.161s idle**, followed by a661.207ms root response (app3.560ms). After another gap, app-list reportedzero tasks at423.146s and independent function statistics showedzero runners/backlog/running inputs before the next HTTP. An earlier349s app-list sample still showed1task, followed by an empty container inventory; control-plane counts and shutdown observations have granularity. The configured300s window is not a guaranteed precise shutdown deadline or billed duration. No continuously warm instance was introduced.

| Public navigation | Before120s config, total ms | After300s config, total ms | After app ms |
| --- | --- | --- | --- |
| First root after verifiedzero tasks | 6,584.826 | 4,970.343 | 7.035 |
| Three subsequent warm roots | 374.545–1,111.017 | 193.746–202.221 | 2.630–3.049 |
| Warm health | 505.891 | 505.724 | 1.685 |
| JavaScript download, decoded420,559→440,709bytes | 146.399 | 105.293 | 4.403 |

This is HTTP from the same workstation/public origin, not browser paint or isolated container startup. Network/provider/proxy conditions differ; no universal before/after speedup is inferred. The300s window avoids a cold handoff in the observed201s gap but does not eliminate first-visit cold starts. The new JavaScript includes review/approval functionality; its decoded size increased, while compression remains working.

The same remembered cookie recovered its private buyer/workspace/actor/principal after actualscale-down. Both new receipts recovered and verified; spend/preferences were unchanged. The probe revoked only its own session and createdzero orders. Actual protected report: `.local/secure-hosted-after-navigation.json`.
