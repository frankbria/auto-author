# Issue #181: chapter drafts no longer silently truncated to ~750 words

*2026-07-06T04:51:10Z*

Issue #181: `generate_chapter_draft` used the OpenAI default `max_tokens=1000` (~750 words) with no `finish_reason` guard — every draft request over ~750 words returned a truncated draft marked `success:true`. This demo runs the REAL backend twice — the `main` code (port 8123) and the fix branch (port 8124) — as real uvicorn servers against real MongoDB, through the real OpenAI SDK. **Disclosure**: the local OpenAI API key is stale (401), so the OpenAI *wire endpoint* is a local protocol-compatible stub that logs each request's `max_tokens` and returns genuine `finish_reason` values (`length` when the old 1000-token budget is used or when the TRUNCATE-DEMO chapter forces budget exhaustion; `stop` otherwise). Everything else — HTTP, routing, auth deps, Mongo, SDK response parsing — is the real stack.

```bash
curl -s http://127.0.0.1:8123/api/v1/health && echo " <- old app (main @ af6265e)" && curl -s http://127.0.0.1:8124/api/v1/health && echo " <- new app (fix/181-draft-truncation)"
```

```output
{"status":"healthy"} <- old app (main @ af6265e)
{"status":"healthy"} <- new app (fix/181-draft-truncation)
```

**Act 1 — the bug, reproduced on `main`.** A book (`6a4b35b724ac66ac49d6f436`) with chapter `ch-keepers` is seeded in Mongo. We request a **2000-word** draft from the old app. It asks OpenAI for only the default 1000 tokens, gets back a response truncated mid-sentence (`finish_reason=length`), and still returns `success:true` with ~750 words:

```bash
curl -s -X POST http://127.0.0.1:8123/api/v1/books/6a4b35b724ac66ac49d6f436/chapters/ch-keepers/generate-draft -H 'Content-Type: application/json' -d '{"question_responses":[{"question":"What draws people to lighthouses?","answer":"They are solitary, purposeful structures."}],"writing_style":"conversational","target_length":2000}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print("success    :", d["success"]); print("word_count :", d["metadata"]["word_count"], "(requested 2000)"); print("draft tail :", repr(d["draft"][-70:]))'
```

```output
success    : True
word_count : 752 (requested 2000)
draft tail : 'steadier with the years. The keepers climbed the spiral stairs and the'
```

**Act 2 — the fix.** The same request against the new app. `max_tokens` is now sized from `target_length` (2000 × 1.6 = 3200, clamped to [500, 4000]), so the model finishes with `finish_reason=stop` and the full draft comes back complete:

```bash
curl -s -X POST http://127.0.0.1:8124/api/v1/books/6a4b35b724ac66ac49d6f436/chapters/ch-keepers/generate-draft -H 'Content-Type: application/json' -d '{"question_responses":[{"question":"What draws people to lighthouses?","answer":"They are solitary, purposeful structures."}],"writing_style":"conversational","target_length":2000}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print("success    :", d["success"]); print("word_count :", d["metadata"]["word_count"], "(requested 2000)"); print("draft tail :", repr(d["draft"][-70:]))'
```

```output
success    : True
word_count : 1811 (requested 2000)
draft tail : ' with the years. And that, in the end, is why the lights still matter.'
```

**Act 3 — the truncation guard fails loudly.** Chapter `ch-trunc` forces the wire to return `finish_reason=length` (budget genuinely exhausted). The old app would have saved this as a success; the new stack refuses the truncated draft and the endpoint surfaces a **503** with the service message (no more swallowed generic 500):

```bash
curl -s -w '\nHTTP %{http_code}\n' -X POST http://127.0.0.1:8124/api/v1/books/6a4b35b724ac66ac49d6f436/chapters/ch-trunc/generate-draft -H 'Content-Type: application/json' -d '{"question_responses":[{"question":"Q","answer":"A"}],"target_length":2000}'
```

```output
{"detail":"Failed to generate draft: The generated draft was cut off before it finished. Try a shorter target length."}
HTTP 503
```

**The wire evidence.** The stub logged the `max_tokens` each app actually sent for the identical 2000-word request — the old app asked for 1000 tokens, the new app for 3200:

```bash
cat /tmp/claude-1000/-home-frankbria-projects-auto-author/7b5245af-5cab-4173-9299-f5017fdc8bcc/scratchpad/stub-requests.log
```

```output
model=gpt-4 max_tokens=1000
model=gpt-4 max_tokens=3200
model=gpt-4 max_tokens=3200
```

**The regression tests.** The AC test suite: budget scaling (2000→3200), clamping (10000→4000), the 500-token floor (100→500), the truncation rejection, and the endpoint 503 pass-through:

```bash
cd backend && BYPASS_AUTH=false uv run pytest tests/test_services/test_ai_service_draft_generation.py tests/test_api/test_routes/test_books_draft_style_coverage.py -q --no-cov -k "max_tokens or truncated or failure_503" 2>/dev/null | tail -3
```

```output
tests/test_api/test_routes/test_books_draft_style_coverage.py ..         [100%]

======================= 6 passed, 30 deselected in 0.29s =======================
```

**Acceptance criteria → evidence**: (1) *max_tokens sized to target_length (~×1.6, clamped)* — wire log shows 3200 for a 2000-word request vs the old 1000; tests pin 3200/4000/500. (2) *Truncated output fails loudly* — Act 3: HTTP 503 with the explicit message instead of `success:true`. (3) *Test asserts large targets are not silently shortened* — `test_truncated_output_is_rejected_not_saved` + the 6 tests above. Known limitation (follow-up #232): gpt-4's 4000-token output cap yields ~2500–3000 words max, below the UI's 5,000-word option — such requests now either succeed shorter (model stops naturally) or fail loudly, never silently.
