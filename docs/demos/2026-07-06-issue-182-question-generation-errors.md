# Issue #182: AI question-generation failures surface as structured errors; template fallbacks tagged

*2026-07-07T00:08:16Z*

Issue #182: `generate_chapter_questions` swallowed every OpenAI failure into `return []`, and the service layer substituted generic template questions — so a real outage (bad key, removed model, network error) returned **HTTP 200 with plausible-looking fake questions** and no error surfaced anywhere. This demo runs the REAL backend three ways against real MongoDB: the `main` code (port 8125) and the fix branch (port 8126) both talk to the **real OpenAI endpoint with the genuinely stale local key** (a true 401 outage, no simulation), and a third server (port 8127, fix branch) talks to a local protocol-compatible OpenAI stub for the responds-but-unusable cases. **Disclosure**: only the wire endpoint on 8127 is stubbed (`OPENAI_BASE_URL`); HTTP, routing, auth deps, Mongo, and SDK parsing are the real stack throughout.

```bash
curl -s http://127.0.0.1:8125/api/v1/health && echo " <- old app (main @ c857886, real OpenAI + stale key)" && curl -s http://127.0.0.1:8126/api/v1/health && echo " <- new app (fix/182, real OpenAI + stale key)" && curl -s http://127.0.0.1:8127/api/v1/health && echo " <- new app (fix/182, wire stub)"
```

```output
{"status":"healthy"} <- old app (main @ c857886, real OpenAI + stale key)
{"status":"healthy"} <- new app (fix/182, real OpenAI + stale key)
{"status":"healthy"} <- new app (fix/182, wire stub)
```

**Act 1 — the bug, reproduced on `main`.** Book `6a4c4324aee81980c0e901cf` ("The Craft of Memoir") is seeded with chapter `ch-voice`. We ask the old app to generate interview questions while OpenAI is genuinely rejecting the key (401). It returns **HTTP 200** with generic template questions — presented exactly like AI output, with nothing marking them as canned and no error surfaced:

```bash
curl -s -w '\nHTTP %{http_code}\n' -X POST http://127.0.0.1:8125/api/v1/books/6a4c4324aee81980c0e901cf/chapters/ch-voice/generate-questions -H 'Content-Type: application/json' -d '{"count":5}' | python3 -c 'import json,sys
raw=sys.stdin.read(); body,code=raw.rsplit("HTTP",1); d=json.loads(body)
print("HTTP", code.strip()); print("total :", d["total"])
for q in d["questions"][:3]: print(" -", q["question_text"][:70])
print("fields marking these as fallback:", [k for k in d["questions"][0] if "fallback" in k] or "NONE")'
```

```output
HTTP 200
total : 5
 - Who are the main characters in this chapter and what are their key tra
 - How does this chapter advance the overall story?
 - What sensory details (sights, sounds, smells) bring the setting to lif
fields marking these as fallback: NONE
```

The old app **did** see the OpenAI failure — its own log shows the 401 being swallowed at the moment it returned that 200 (note the fiction-oriented "main characters" template served for a non-fiction memoir book):

```bash
grep -o 'Error generating chapter questions: AI_UNEXPECTED_ERROR.\{0,60\}' /tmp/claude-1000/-home-frankbria-projects-auto-author/d8c40812-7588-4f0f-a998-85424d982219/scratchpad/old-app.log | head -1
```

```output
Error generating chapter questions: AI_UNEXPECTED_ERROR: Unexpected AI service error: Error code: 401 - {'error': {
```

**Act 2 — the fix.** The identical request against the new app, same genuinely-failing OpenAI key. The failure now propagates as a **structured error** (`QUESTION_GENERATION_FAILED`, the TOC-path pattern) instead of masquerading as success — a 401 is classified non-retryable, so it maps to HTTP 500; transient outages (rate limits, timeouts, 5xx) map to 503 with `Retry-After` semantics:

```bash
curl -s -w '\nHTTP %{http_code}\n' -X POST http://127.0.0.1:8126/api/v1/books/6a4c4324aee81980c0e901cf/chapters/ch-voice/generate-questions -H 'Content-Type: application/json' -d '{"count":5}' | python3 -c 'import json,sys
raw=sys.stdin.read(); body,code=raw.rsplit("HTTP",1); d=json.loads(body)["detail"]
print("HTTP", code.strip()); print("error_code :", d["error_code"])
print("retryable  :", [x["message"] for x in d["details"] if x.get("field")=="retryable"][0])'
```

```output
HTTP 500
error_code : QUESTION_GENERATION_FAILED
retryable  : This error is not retryable
```

**Act 3 — the legitimate fallback, now tagged.** Templates are still the right answer when the AI *responds* but produces nothing usable. The third server talks to a wire stub that returns a valid completion whose content contains no questions (chapter `EMPTY-DEMO`). The app still degrades gracefully to templates — but every one is now tagged `is_fallback: true` so the client and tests can tell canned from real:

```bash
curl -s -w '\nHTTP %{http_code}\n' -X POST http://127.0.0.1:8127/api/v1/books/6a4c4324aee81980c0e901cf/chapters/ch-empty/generate-questions -H 'Content-Type: application/json' -d '{"count":5}' | python3 -c 'import json,sys
raw=sys.stdin.read(); body,code=raw.rsplit("HTTP",1); d=json.loads(body)
print("HTTP", code.strip()); print("total :", d["total"])
print("is_fallback flags:", [q["is_fallback"] for q in d["questions"]])'
```

```output
HTTP 200
total : 5
is_fallback flags: [True, True, True, True, True]
```

**Act 4 — real AI output stays untagged.** Same server, chapter `ch-momentum`, stub now returns a valid 5-question completion — the response carries `is_fallback: false` on every question:

```bash
curl -s -w '\nHTTP %{http_code}\n' -X POST http://127.0.0.1:8127/api/v1/books/6a4c4324aee81980c0e901cf/chapters/ch-momentum/generate-questions -H 'Content-Type: application/json' -d '{"count":5}' | python3 -c 'import json,sys
raw=sys.stdin.read(); body,code=raw.rsplit("HTTP",1); d=json.loads(body)
print("HTTP", code.strip()); print("total :", d["total"])
print("is_fallback flags:", [q["is_fallback"] for q in d["questions"]])
print("sample:", d["questions"][0]["question_text"])'
```

```output
HTTP 200
total : 5
is_fallback flags: [False, False, False, False, False]
sample: What real-world experience shaped your thinking on topic 1?
```

**The regression tests.** The AC test patches `_make_openai_request` to raise and asserts no masquerade; route tests pin the structured error through the full stack for generate, bulk regenerate, and single-question regenerate, plus the tagged-fallback contracts:

```bash
cd backend && BYPASS_AUTH=false uv run pytest tests/test_services/test_ai_service_core.py tests/test_services/test_question_generation_service.py tests/test_api/test_routes/test_books_chapter_questions_coverage.py tests/test_api/test_question_regeneration.py -q --no-cov -k 'reraises or propagates or outage or fallback or tagged or mixed' 2>/dev/null | tail -2
```

```output

====================== 15 passed, 89 deselected in 0.68s =======================
```

**Acceptance criteria → evidence.** (1) *AI failure surfaces a structured error (like the TOC path)* — Act 2: a genuine OpenAI 401 returns HTTP 500 `QUESTION_GENERATION_FAILED` with retryability info (transient failures → 503), where `main` returned a fake 200 (Act 1); the same mapping is test-pinned for bulk and single-question regeneration. (2) *Response tagged `is_fallback` so clients/tests can tell real from fallback* — Act 3 vs Act 4: identical 200 responses, templates tagged `true`, AI output `false`; `main` had no such field (Act 1: "NONE"). (3) *Test patches `_make_openai_request` to raise and asserts no masquerade* — `test_generate_chapter_questions_reraises_ai_service_error` + `test_generate_questions_openai_outage_503_not_200`, in the 15-test run above. Backend suite: **1101 passed / 13 skipped, 91.92% coverage**. Known limitations: bulk regenerate still deletes before generating (pre-existing ordering; honest 503 now, follow-up #234); template questions persisted during pre-fix outages read back as `is_fallback: false` (forward-looking tag, no backfill).
