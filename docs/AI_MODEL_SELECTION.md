# A4TB · Valio Aimo — AI selection and measured inputs

Reviewed 14 November 2026, Europe/Helsinki. The model choice follows small application-specific measurements and available access, not a provider ranking. The project remains a controlled challenge/evaluation application with simulated orders. No model owns financial or authorization truth.

## Selected architecture

| Responsibility | Selected implementation | Reason and boundary |
| --- | --- | --- |
| Text ordering, predictable rehearsal | Existing local structured parser | Fast, explicit and usable offline; bounded English grammar and supported recipe planning. It does not claim general multilingual understanding. |
| Opt-in richer language/semantic queries | `nvidia/nemotron-3.5-lightning-30b-a3b` through the existing NVIDIA key | Completed all seven authored first-pass cases in the tested pipeline. Strict schema/constraint guards still reject invalid output. Selected as the simpler measured NLP option; not an automatic model cascade. |
| Default image text | NVIDIA Nemotron 3.5 Super VL, selected server-side | Automatic image reading was requested by the owner to remove provider choices and per-image checkboxes. Sanitized nonconfidential demo images go to NVIDIA; editable text returns. This UX choice does not establish accuracy superiority over local OCR. |
| Default speech text | Local pretrained Whisper **base**, CTranslate2 CPU int8 | Recognized the authored request correctly where tiny misheard a product; no audio is sent to an external AI service. |
| Image-service recovery / offline rehearsal | Local Tesseract, English + Finnish | A failed NVIDIA service call falls back to local OCR with honest response provenance and a review warning. Explicit API `provider=local` remains available for offline rehearsal; the customer has no provider selector. |
| Prices, stock, quantities, tax, approval, totals | Catalog/sandbox facts plus deterministic gateway code | No model or OCR/transcription output can set these purchasing facts or approve/confirm a cart. |

Speech/image endpoints return only `{text, uncertainties, source, elapsed_ms, review_required:true}`. The customer edits the preview and explicitly adds it to the composer. Building a cart is a later, separate action. Upload processing does not write an order, preference, cart or transcript record. If the customer subsequently submits the corrected text, normal scoped purchasing history is stored.

## Current official alternatives and observed access

| Candidate | Documented capability/context | Pricing/access facts and actual evaluation |
| --- | --- | --- |
| Gemini 4 Carbon / Argon | Both accept text/image/audio/video/PDF, support function calling and structured outputs, and have a 1,048,576-token unified input/output window. Default synchronous output is 65,536; long decode is available within the window. | Both are paid-only. Standard input/output rates are $2/$10 per million tokens through 30 November 2026, then $4/$20 from 1 December. No runtime key, verified quota or sponsored Google coverage is configured here, so neither was benchmarked. [Carbon](https://aistudio.google.com/docs/models/gemini-4-carbon), [Argon](https://aistudio.google.com/docs/models/gemini-4-argon), [current pricing](https://aistudio.google.com/docs/pricing#gemini-4-carbon). |
| Gemini 4 Hydrogen | Text/image/audio/video/PDF input, function calling and structured outputs; the same 1,048,576-token unified window and 65,536 default synchronous output, with long decode available | Official standard pricing lists a free tier and paid input/output rates of $1.50/$7.50 per million tokens. Listed free availability does not establish this project's entitlement or limits; no runtime key/quota is configured and no measured result is claimed. Free/paid data handling differs. [Model](https://aistudio.google.com/docs/models/gemini-4-hydrogen), [pricing](https://aistudio.google.com/docs/pricing#gemini-4-hydrogen). |
| Gemini 3.8 Flash | Text/image/audio/video/PDF input, function calling and structured output; 1,048,576 input and 65,536 output tokens | Official standard paid pricing through 31 December 2026: $0.75 input/$3.75 output per million tokens; listed free tier has limits and different data handling. No Gemini runtime key or verified project quota is configured, so no latency/accuracy result is claimed. [Model](https://aistudio.google.com/docs/models/gemini-3.8-flash), [pricing](https://aistudio.google.com/docs/pricing#gemini-3.8-flash), [JSON schema support](https://ai.google.dev/gemini-api/docs/structured-output). |
| Gemma 4 31B IT via NVIDIA | Text/image/video and function-calling workflows, 256K context according to the hosted model card | Actual authenticated `/v1/models` listed `google/gemma-4-31b-it`; one forced-tool probe did not satisfy this application's structured-output interface. Not selected or scored as a general model-quality failure. [Official hosted model](https://docs.api.nvidia.com/nim/reference/google-gemma-4-31b-it). |
| Older Gemma 3 27B endpoint | Text/image model, 128K documented context | Actual hosted probe returned HTTP 410 despite documentation remaining available. Do not rely on a documentation page as endpoint availability. [Official model](https://docs.api.nvidia.com/nim/reference/google-gemma-3-27b-it). |
| Nemotron 3.5 Super VL | Text/image/video, document understanding and tool use; up to 1M model context, with deployment-dependent limits | Existing project access actually worked for text and vision. First-pass extraction failures were rejected, including an extra misplaced item-level date in a fresh Finnish reproduction. Selected for automatic image reading after the owner’s UX request; it remains separate from the chosen NLP model. [Model card](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3_5-super-vl-120b-a12b). |
| Nemotron 3.5 Lightning | Actual catalog lists the model; typed `extract_order` output worked in the authored benchmark | Selected on measured pipeline results. A current independent context/rate guarantee was not established; requests are deliberately bounded. No invented USD-per-request price or unlimited quota claim. |
| NVIDIA Riva Parakeet CTC 1.1B | English ASR, hosted HTTP/gRPC; official PCM/audio formats | Existing key actually transcribed the synthetic 4.86-second clip correctly in 9.83 seconds. Local base was chosen for privacy and responsiveness; no hosted Riva dependency is deployed. [API](https://build.nvidia.com/nvidia/parakeet-ctc-1_1b-asr/api), [model card](https://build.nvidia.com/nvidia/parakeet-ctc-1_1b-asr/modelcard). |
| Whisper base / faster-whisper | Pretrained multilingual ASR, CTranslate2 CPU int8 support; model weights retain MIT license | Public model downloaded and pinned; no inference API key or per-call model-service fee. Hosting compute still consumes resources. [Original model](https://github.com/openai/whisper), [converted model](https://huggingface.co/Systran/faster-whisper-base), [runtime](https://github.com/SYSTRAN/faster-whisper). |
| Tesseract | Local printed-text OCR with language data | Official OS packages; no cloud-model account. [Command documentation](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html). |

The current Google catalog includes Gemini 4 Carbon, Argon and Hydrogen; 3.8 Flash remains a supported earlier option. These and open Gemma weights were researched without assuming a free allowance, hosted GPU entitlement or personal paid subscription. The selected available model can change after a better representative benchmark without changing the financial gateway.

## Application benchmark

Reproducible source: `scripts/benchmark_ai.py`. Inputs are authored procurement examples, not customer/private data. Text cases cover basic extraction, multi-product budget, recipe ambiguity, missing quantity, follow-up preservation, schema/authority injection and one Finnish request. Speech and image cover the directive's remaining two categories. The supported bolognese case deliberately routes to the labelled deterministic recipe planner even when NVIDIA is selected; it is not counted as a model-generated recipe.

Initial report: ignored `.local/ai-benchmark.json`. One run per text case, seven pipeline cases per strategy; six actual model calls per NVIDIA strategy because the recipe routes locally. These are small engineering observations, not statistically established superiority.

| Initial strategy | Valid pipeline outputs | All case checks passed | Authored extraction checks | Median pipeline ms | Slowest observed ms | Text-provider tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Local parser | 7/7 | 5/7 | 14/18 | 752 | 2,410 | 0 |
| Super VL | 4/7 | 4/7 | 11/18 | 9,693 | 43,328 | 16,330 |
| Lightning | 7/7 | 7/7 | 18/18 | 7,864 | 19,344 | 15,749 |

“Valid” includes schema validation and production guards. Failed outputs receive no passing extraction credit. Latency includes the interpreter and bounded catalog-result checks, not only network inference. The initial deadline metric checked presence; the final harness checks the correct next Monday. Initial local ambiguity omitted the NLP question although the downstream gateway still blocked an empty cart. The missing-quantity question and pending-context follow-up were subsequently fixed and retested below; local Finnish extraction remains unsupported.

**Final selected-model rerun:** `.local/ai-benchmark-final.json` preserved the initial report and repeated the selected Lightning/local strategies after the missing-quantity/context fixes. Local: 7/7 valid, 6/7 full cases, 15/18 checks, median 147 ms, slowest 2,747 ms; only the Finnish case remained unsupported. Lightning: 7/7 valid/full cases, 18/18 checks, median 6,119 ms, slowest 10,680 ms, six actual provider calls and 15,187 reported tokens. Both now check the correct next Monday. The separate actual procurement API probe asked for missing quantity on “I need milk by Monday”, then retained milk/date when the answer was “20 litres”; no order or synthetic spend was created. These observations remain small authored tests, not a broad accuracy/reliability guarantee.

| Media observation | Correctness scope | Elapsed |
| --- | --- | ---: |
| Local Tesseract | One clear, authored English printed list; normalized word error rate 0 | 160 ms in media rerun |
| Local Whisper base | One 4.86-second eSpeak purchasing clip; normalized word error rate 0 | 1,767 ms in media rerun |
| Optional Super VL OCR | Same authored list; normalized word error rate 0; 1,256 reported tokens | 2,254 ms in media rerun |
| Tiny ASR preliminary | Misheard “butter” as unrelated words on that clip | 1,379 ms; rejected for selected default |

The word metric normalizes case, number words and equivalent litre/kg spellings; it is not raw verbatim accuracy. Reports are `.local/ai-benchmark-media.json` and the preliminary ASR probes. These benchmark fixtures use no actual microphone, real person's recording or customer image. Separately, after deployment the owner reported that the public site's microphone correctly transcribed their speech and accent. That is one qualitative user check, not a measured accent corpus. Noisy kitchens, handwriting, Finnish speech and multilingual images remain unestablished. Catalog-result presence is recorded separately and is not asserted as human-rated semantic precision. Cost per request remains unknown where the provider/account does not expose a charge; token usage is not silently converted to a dollar estimate.

## Resource inventory

| Provider/resource | Available access and coverage | Intended use / status |
| --- | --- | --- |
| NVIDIA trial APIs | Existing key; actual model catalog/text/vision/Riva requests succeeded. Remaining quota/expiry and per-call monetary charge not visible through these responses | Bounded synthetic challenge evaluation; optional text and automatic image reading integrated. No new plan or top-up. |
| Modal | Existing CLI authentication; predeployment $100 Junction grant, 30 November 2027 expiry and $101 no-card usage cap verified; last recorded rounded usage snapshot $0.01 | CPU host/private volumes; 1 CPU/1,536 MiB selected from measured memory use. The C67 public release passed actual local OCR/ASR, persistence and live provider checks below. No GPU provisioned. |
| Aiven | Existing free European PostgreSQL service and prior TLS/concurrency proof; no new paid service | Local database option; hosted runtime stays single-writer SQLite. |
| Google AI Studio/Gemini | Prior browser access observed; current Gemini 4 Carbon/Argon are paid-only, Hydrogen lists a free tier, and 3.8 Flash remains supported. No runtime key, project quota or applicable Google credit balance is verified here | Current official models/pricing researched, no model integrated or benchmarked. No activation or billing change; a listed free tier is not proof of this team's access. |
| Hugging Face/SYSTRAN + OpenAI Whisper | Public pretrained model download and MIT license | Pinned local CPU speech model, bundled ahead of requests. No OpenAI runtime API is used. |
| Ubuntu/Debian packages | Official configured OS repository | Local Tesseract language/runtime packages; no paid OCR provider. |
| Codex/GitHub/Sites | Existing development tooling, private source and branded frontdoor | Implementation/review/publishing roles; no assumption that personal Codex credits fund model API calls. |
| Anthropic/ElevenLabs/Verda/Vultr/other sponsors | Earlier account/offer observations, no corresponding configured runtime keys or verified additional coverage here | Evaluated in existing sponsor research; no speculative paid/GPU/training deployment or extra model stack. |

## Performance and packaging

A real local process loaded the actual FastAPI app, 17,546-record catalog, local OCR and Whisper base: peak RSS **882.4 MiB**, OCR **159 ms**, speech **2,290 ms** for the authored clip. This justified memory headroom above the original 1 GiB host. On the public C67 release, a separate authored-media check measured server-reported OCR **444 ms** and speech **1,800 ms**; complete HTTP calls took **901 ms** and **2,651 ms**, respectively. These are single observations, not cold/warm distributions, concurrent capacity or a hosted latency guarantee.

Speech uses one process-cached int8 model, two CPU threads, one recognition worker and a nonblocking recognition lock. Audio decoding stops at 30 seconds and uses an allowlist of demuxers, disabled nested protocols, disabled MOV external tracks and a PyAV `io_open` callback that rejects every external file/network reference. Only the primary in-memory bytes may be read; a disguised playlist cannot open another resource. Normal WAV, WebM/Opus and MP4/AAC decoding is covered by actual decoder tests. [FFmpeg format controls](https://ffmpeg.org/ffmpeg-formats.html#mov_002fmp4_002f3gp), [protocol controls](https://ffmpeg.org/ffmpeg-protocols.html#Protocol-Options). Static weights are prepared before deployment. Customer JPEG/PNG files must be nonempty and at most 5 MiB before browser decoding. Ordinary higher-resolution photos are proportionally resized without upscaling to at most 1,600 pixels per side and reencoded without metadata before upload. The server independently retains its 5 MiB/12-megapixel decoder defense for direct API input and strips metadata again. OCR uses stdin/stdout with a 20-second subprocess limit; uploaded images and text are not placed in temporary files. Both paths require a buyer session and rate limits.

```bash
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python scripts/prepare_multimodal.py --local-ocr
# On the prepared machine, verify/rebuild only from the local pinned cache:
.venv/bin/python scripts/prepare_multimodal.py --offline
# Selected bounded final comparison; results remain ignored:
.venv/bin/python scripts/benchmark_ai.py --live --model nvidia/nemotron-3.5-lightning-30b-a3b --skip-cloud-ocr --output .local/ai-benchmark-final.json
```

`prepare_multimodal.py` pins `Systran/faster-whisper-base` revision `ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66`, copies four real files into ignored `.local/model-bundle/whisper-base`, and includes a checksum-verified MIT `LICENSE` plus `MODEL_PROVENANCE.json`. Set `AIMO_WHISPER_MODEL_PATH` to the absolute bundle path; the prepared local bundle is also automatically discovered. Runtime then uses local files only. The optional rootless OCR preparation extracts official OS packages into ignored `.local/tesseract`; no sudo/global install is needed. Modal can install `tesseract-ocr`, `tesseract-ocr-eng`, `tesseract-ocr-fin` and copy the public speech bundle into the image. The restricted challenge catalog remains in its private volume, not that model bundle.

## Privacy and authority

Local OCR and ASR keep media on the application server. NVIDIA text interpretation and automatic image reading are for nonconfidential challenge/evaluation content only. The [trial terms](https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf) restrict confidential/sensitive/personal inputs except where expressly permitted and describe logging/data use; they do not establish a production subscription. The selected [VLM playground disclosure](https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b/playground) repeats that boundary. The owner explicitly requested automatic NVIDIA image reading with no customer provider menu or per-image checkbox. The interface retains a plain privacy/demo-data disclosure. API callers that explicitly set `cloud_consent=false` cannot invoke the external reader; an explicit local route remains available. Backend image authentication, origin checks, bounds and editable review are unchanged. Registration identity and credentials are never sent to OCR/transcription.

These are material provider limits, not a reason to add a paid plan. A confidential production deployment needs an appropriate provider contract or self-hosted model with validated safeguards. The project never trains on uploaded media or private customer records. The Google free and paid tiers also differ in data handling; an advertised free tier is not a project entitlement.

## Training decision and release evidence

No model training/fine-tuning is justified now: seven authored text cases and one example per media modality are an evaluation seed, not a representative licensed training/held-out dataset. Prompt/schema improvements and deterministic validation address observed failures with less deployment complexity. No GPU or training job was provisioned and no private challenge/customer data was used for training.

Historical C67 release: the release coordinator recorded **171 passing backend tests** and a passing production frontend build. The public release serving `index-C67pl32K.js` passed **47 extended deployed checks** in ignored `.local/extended-deployed-report.json`: scoped accounts/preferences, exact separate-manager approval, simulated confirmation/retry/verification/recovery, actual local OCR/ASR, missing cloud consent rejection, upload origin protection and actual Lightning/Valio sandbox reads. Media extraction left the saved cart and receipt unchanged. `.local/extended-migration-report.json` also records recovery of an old receipt and preserved shared spending. Local interactive checks covered registration, Remember Me, preferences and editable media previews; the owner separately confirmed real public-site microphone transcription.

The [acceptance record](ACCEPTANCE_RECORD.md) distinguishes these completed checks from final browser/release handoff gates. Representative consented speech/image evaluation, latency/error distributions and appropriate confidential-production provider coverage remain improvements rather than claims established by this small release sample.


The latest catalog/history/camera continuation and automatic-image-reader release are recorded in [FINAL_QA_REPORT.md](FINAL_QA_REPORT.md). Historical media measurements above remain observations of the named engines and builds; they must not be presented as final-release or physical-camera proof.
