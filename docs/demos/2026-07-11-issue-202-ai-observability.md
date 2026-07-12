# Issue 202: AI integration observability - autospec OpenAI boundary, no silent question fallback

*2026-07-12T05:57:49Z*

PR #275 fixes issue #202: (1) AC1 — unit mocks of the OpenAI boundary now validate kwargs against the real openai 1.97.1 SDK signature via an autospec helper, so request-shape drift can no longer sail through green; (2) AC2 — unparseable AI output for clarifying questions now surfaces as a structured retryable error instead of 4 silent hard-coded questions indistinguishable from AI output. Setup: the branch repo at fix/202-ai-observability-autospec and a pristine main worktree, driven identically. The AC2 section runs two REAL uvicorn servers (main vs branch) on a REAL local MongoDB, with the GENUINE openai SDK pointed at a local wire stub via OPENAI_BASE_URL — no test doubles inside the app.

AC1 design note: the issue suggests create_autospec(OpenAI). That literally cannot work — the client reaches chat.completions through cached_property descriptors, which autospec cannot traverse. The helper instead autospecs the real BOUND chat.completions.create method, which does enforce the genuine SDK signature. Proof, run against the installed openai 1.97.1:

```bash
cd /home/frankbria/projects/auto-author/backend && uv run python - <<'EOF'
from unittest.mock import create_autospec
from openai import OpenAI

# The AC-literal approach: breaks before it can validate anything
c = create_autospec(OpenAI, instance=True)
try:
    c.chat.completions.create(model="gpt-4")
except AttributeError as e:
    print(f"create_autospec(OpenAI): AttributeError: {e}")

# The helper approach: autospec the real bound method -> signature enforced
real = OpenAI(api_key="test-key")
m = create_autospec(real.chat.completions.create, return_value="ok")
try:
    m(model="gpt-4", messages=[{"role": "user", "content": "hi"}], bogus_kwarg=True)
except TypeError as e:
    print(f"bound-method autospec, unknown kwarg: TypeError: {e}")
try:
    m(model="gpt-4")
except TypeError as e:
    print(f"bound-method autospec, missing kwarg: TypeError: {e}")
print("bound-method autospec, production kwargs:", m(model="gpt-4", messages=[{"role": "user", "content": "hi"}], temperature=0.4, max_tokens=800))
EOF
```

```output
create_autospec(OpenAI): AttributeError: Mock object has no attribute 'completions'
bound-method autospec, unknown kwarg: TypeError: got an unexpected keyword argument 'bogus_kwarg'
bound-method autospec, missing kwarg: TypeError: missing a required keyword-only argument: 'messages'
bound-method autospec, production kwargs: ok
```

The drift differential. We inject the SAME request-shape drift into both checkouts: a bogus kwarg added to the production chat.completions.create call in _sync_request (the single choke point every AI method funnels through). This simulates the class of bug the issue describes — a renamed/invalid kwarg or a dead integration. First, main: its bare-Mock tests accept ANY kwargs, so the broken request sails through green.

```bash
WT=/tmp/claude-1000/-home-frankbria-projects-auto-author/e7d7f34d-1b51-4a44-9a50-e997c0cf1345/scratchpad/main-wt/backend && cd "$WT" && sed -i "s/max_tokens=max_tokens,/max_tokens=max_tokens, bogus_drifted_kwarg=True,/" app/services/ai_service.py && grep -n "bogus_drifted_kwarg" app/services/ai_service.py && uv run pytest tests/test_services/test_ai_service_style_transformation.py -q 2>&1 | tail -1 | sed -E "s/ in [0-9.]+s//" ; git checkout -- app/services/ai_service.py
```

```output
221:                max_tokens=max_tokens, bogus_drifted_kwarg=True,
============================== 6 passed ===============================
```

Same mutation on the branch: the autospec boundary validates every call against the real SDK signature, so the identical drift now fails loudly — 7 failures across the rewritten style-transformation suite and the new request-shape suite.

```bash
cd /home/frankbria/projects/auto-author/backend && sed -i "s/max_tokens=max_tokens,/max_tokens=max_tokens, bogus_drifted_kwarg=True,/" app/services/ai_service.py && grep -n "bogus_drifted_kwarg" app/services/ai_service.py && uv run pytest tests/test_services/test_ai_service_style_transformation.py tests/test_services/test_openai_request_shape.py -q 2>&1 | grep -E "^FAILED|passed|failed" | sed -E "s/ in [0-9.]+s//" ; git checkout -- app/services/ai_service.py && echo "(mutation reverted)"
```

```output
221:                max_tokens=max_tokens, bogus_drifted_kwarg=True,
FAILED tests/test_services/test_ai_service_style_transformation.py::TestAIServiceStyleTransformation::test_transform_success
FAILED tests/test_services/test_ai_service_style_transformation.py::TestAIServiceStyleTransformation::test_openai_error_handled
FAILED tests/test_services/test_ai_service_style_transformation.py::TestAIServiceStyleTransformation::test_truncated_output_is_rejected_not_saved
FAILED tests/test_services/test_ai_service_style_transformation.py::TestAIServiceStyleTransformation::test_each_style_sends_distinct_prompt
FAILED tests/test_services/test_openai_request_shape.py::TestRequestShapeThroughService::test_make_openai_request_sends_valid_sdk_kwargs
FAILED tests/test_services/test_openai_request_shape.py::TestRequestShapeThroughService::test_generate_clarifying_questions_through_real_sdk_shape
FAILED tests/test_services/test_openai_request_shape.py::TestUnparseableQuestionsRaise::test_unparseable_ai_output_raises_instead_of_canned_questions
========================= 7 failed, 5 passed ==========================
(mutation reverted)
```

AC2: silent fallback vs structured error, end to end. Stack: an OpenAI wire stub on :9797 (logs every request body; serves whatever stub_content.txt holds), the MAIN worktree server on :8031 and the BRANCH server on :8030 — both real uvicorn + real MongoDB, genuine openai SDK reaching the stub via OPENAI_BASE_URL (the SDK reads it when the client is constructed without an explicit base_url). BYPASS_AUTH=true is the documented local-dev auth path; everything downstream of auth is production code. The stub starts loaded with UNPARSEABLE prose: "I cannot help with that request."

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/e7d7f34d-1b51-4a44-9a50-e997c0cf1345/scratchpad/start_demo_stack.sh
```

```output
branch /health: {"status":"healthy"}
main   /health: {"status":"healthy"}
```

Seed one book per server (identical title + summary) through the real API. Book ids are random; they are stored in scratch files and masked in output.

```bash
SB=/tmp/claude-1000/-home-frankbria-projects-auto-author/e7d7f34d-1b51-4a44-9a50-e997c0cf1345/scratchpad
SUMMARY="A practical guide to observable AI integrations: how request-shape drift, silent fallbacks, and mocked tests hide real outages, and what disciplined test boundaries look like in production systems."
for pair in "main 8031" "branch 8030"; do
  set -- $pair
  BID=$(curl -s -X POST http://127.0.0.1:$2/api/v1/books/ -H "Content-Type: application/json" -d "{\"title\":\"Observable AI ($1)\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)[\"id\"])")
  echo "$BID" > "$SB/bid_$1"
  CODE=$(curl -s -o /dev/null -w "%{http_code}" -X PUT http://127.0.0.1:$2/api/v1/books/$BID/summary -H "Content-Type: application/json" -d "{\"summary\":\"$SUMMARY\"}")
  echo "$1: book created, summary saved (HTTP $CODE)"
done
```

```output
main: book created, summary saved (HTTP 200)
branch: book created, summary saved (HTTP 200)
```

The differential. Both servers call generate-questions while the AI returns the refusal prose (no extractable questions). MAIN answers HTTP 200 with 4 questions that came from NOWHERE — they are the hard-coded defaults in _parse_questions_response, indistinguishable from AI output. The BRANCH answers a structured HTTP 500 with error_code AI_INVALID_RESPONSE and retryable:true (the established convention for base AIServiceError — #48/#182; 429/503 are reserved for rate-limit/network/unavailable subclasses). Nondeterministic fields (book_id, generated_at, correlation_id) are masked.

```bash
SB=/tmp/claude-1000/-home-frankbria-projects-auto-author/e7d7f34d-1b51-4a44-9a50-e997c0cf1345/scratchpad
echo "--- stub content served to both servers ---"
cat "$SB/stub_content.txt"
echo "--- MAIN (:8031) ---"
CODE=$(curl -s -o "$SB/r_main.json" -w "%{http_code}" -X POST http://127.0.0.1:8031/api/v1/books/$(cat "$SB/bid_main")/generate-questions -H "Content-Type: application/json" -d "{}")
echo "HTTP $CODE"
python3 -c "import json;b=json.load(open(\"$SB/r_main.json\"));print(json.dumps({\"questions\":b[\"questions\"],\"total_questions\":b[\"total_questions\"]},indent=2))"
echo "--- BRANCH (:8030) ---"
CODE=$(curl -s -o "$SB/r_branch.json" -w "%{http_code}" -X POST http://127.0.0.1:8030/api/v1/books/$(cat "$SB/bid_branch")/generate-questions -H "Content-Type: application/json" -d "{}")
echo "HTTP $CODE"
python3 -c "import json;b=json.load(open(\"$SB/r_branch.json\"));b[\"detail\"].pop(\"correlation_id\",None);print(json.dumps(b,indent=2))"
```

```output
--- stub content served to both servers ---
I cannot help with that request.
--- MAIN (:8031) ---
HTTP 200
{
  "questions": [
    "What is the main problem your book solves?",
    "Who is your target audience?",
    "What are the key topics you want to cover?",
    "What should readers be able to do after reading your book?"
  ],
  "total_questions": 4
}
--- BRANCH (:8030) ---
HTTP 500
{
  "detail": {
    "message": "The AI returned unusable clarifying questions. Please try again.",
    "error_code": "AI_INVALID_RESPONSE",
    "retryable": true
  }
}
```

Wire evidence that both servers made a GENUINE openai-SDK HTTP request (not a test double): the stub logged each request body. The kwarg set on the wire is exactly what the new request-shape tests pin — model, messages, temperature, max_tokens.

```bash
tail -2 /tmp/claude-1000/-home-frankbria-projects-auto-author/e7d7f34d-1b51-4a44-9a50-e997c0cf1345/scratchpad/stub_requests.log
```

```output
{"path": "/v1/chat/completions", "wire_kwargs": ["max_tokens", "messages", "model", "temperature"], "model": "gpt-4", "temperature": 0.4, "max_tokens": 800, "n_messages": 2}
{"path": "/v1/chat/completions", "wire_kwargs": ["max_tokens", "messages", "model", "temperature"], "model": "gpt-4", "temperature": 0.4, "max_tokens": 800, "n_messages": 2}
```

Happy path intact: flip the stub to well-formed questions and the BRANCH returns 200 with the parsed AI content (three questions, none of them the canned defaults) — proving tests and users can now tell the AI path from a fallback.

```bash
SB=/tmp/claude-1000/-home-frankbria-projects-auto-author/e7d7f34d-1b51-4a44-9a50-e997c0cf1345/scratchpad
printf "1. What outcome should readers achieve?\n2. Which chapters need case studies?\n3. What is your unique angle?\n" > "$SB/stub_content.txt"
CODE=$(curl -s -o "$SB/r_happy.json" -w "%{http_code}" -X POST http://127.0.0.1:8030/api/v1/books/$(cat "$SB/bid_branch")/generate-questions -H "Content-Type: application/json" -d "{}")
echo "HTTP $CODE"
python3 -c "import json;b=json.load(open(\"$SB/r_happy.json\"));print(json.dumps({\"questions\":b[\"questions\"],\"total_questions\":b[\"total_questions\"]},indent=2))"
```

```output
HTTP 200
{
  "questions": [
    "What outcome should readers achieve?",
    "Which chapters need case studies?",
    "What is your unique angle?"
  ],
  "total_questions": 3
}
```

```bash
SB=/tmp/claude-1000/-home-frankbria-projects-auto-author/e7d7f34d-1b51-4a44-9a50-e997c0cf1345/scratchpad
for p in stub branch main; do kill "$(cat "$SB/$p.pid")" 2>/dev/null && echo "stopped $p"; done
mongosh --quiet --eval "db.getSiblingDB(\"aa_demo202_branch\").dropDatabase(); db.getSiblingDB(\"aa_demo202_main\").dropDatabase();" > /dev/null && echo "demo DBs dropped"
```

```output
stopped stub
stopped branch
stopped main
demo DBs dropped
```

Acceptance criteria map. AC1 (autospec branch of the issue OR): the identical bogus-kwarg drift passed 6/6 bare-Mock tests on main but failed 7 tests on the branch — mocked calls are now validated against the real openai 1.97.1 signature, with meta-tests pinning that the helper rejects unknown/missing kwargs (guarding silent degradation, which is exactly what the AC-literal create_autospec(OpenAI) would do). AC2 (fallback observable): the same unparseable AI output produced HTTP 200 + 4 hard-coded questions on main vs a structured retryable AI_INVALID_RESPONSE error on the branch, while well-formed AI output still parses to 200 — the AI path and the failure path are now distinguishable by tests and users alike. Chapter-question template fallback was already observable via is_fallback (#182). The nightly real-key job branch of AC1 was rejected (recurring spend, unverifiable secret, CI flake); rationale in PR #275.
