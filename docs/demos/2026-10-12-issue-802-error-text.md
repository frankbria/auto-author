# An error tells the client a fixed message; what the provider or the database said stays in the log (#802)

*2026-10-12T09:30:04Z by Showboat 0.6.1*
<!-- showboat-id: 10d813b7-99b2-4654-b8bf-d0cbfd00b7bd -->

A provider error body and a database driver error name things a client should not see: an organisation id, request ids, hostnames, index names. This demo runs two real backends, main and this branch, against a stand-in provider that refuses every request with an error body of the kind a real provider sends. Then it hands a real driver error to the shared error handlers of each code tree.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo802/env.sh; echo "main:   $(git -C $MAIN log --oneline -1 | cut -c1-7)  $(curl -s localhost:8101/api/v1/health | cut -c1-60)"; echo "branch: $(git -C $WT rev-parse --abbrev-ref HEAD)  $(curl -s localhost:8100/api/v1/health | cut -c1-60)"; grep -A4 '^REFUSALS' $D/provider.py | cut -c1-175
```

```output
main:   7abdefb  {"status":"healthy","checks":{"mongodb":"ok","config":"ok"}}
branch: feature/issue-802-error-text  {"status":"healthy","checks":{"mongodb":"ok","config":"ok"}}
REFUSALS = {
    "limit": (429, "rate_limit_exceeded", "Rate limit reached for gpt-4o in organization org-Zx81kQp on tokens per min (TPM): Limit 30000, Used 29874. Request req_7f3a2c."),
    "reject": (400, "context_length_exceeded", "This model's maximum context length is 128000 tokens. However, your messages resulted in 131072 tokens (organization org-Zx81kQ
    "down": (500, "server_error", "The server had an error while processing your request (cluster us-east-4b, request req_7f3a2c)."),
}
```

A rate limit. The provider answers 429. On main the transform route reports a 503 with the error flattened into one string, so the client cannot tell a rate limit from an outage and gets no Retry-After. On this branch it is a 429 with Retry-After, in the same shape the other AI routes use.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo802/env.sh; echo limit > $D/provider-mode; ask 8101 aa_demo_802_before 'main' chapters/ch1/transform-style '{"content": "A short paragraph to rewrite.", "target_style": "professional"}'; ask 8100 aa_demo_802 'branch' chapters/ch1/transform-style '{"content": "A short paragraph to rewrite.", "target_style": "professional"}'
```

```output
main -> HTTP 503
  {"detail":"Failed to transform style: AI_RATE_LIMIT: AI service rate limit exceeded | retry_after=4s | correlation_id=<id>"}
branch -> HTTP 429, retry-after: 4
  {"detail":{"message":"AI service rate limit exceeded","error_code":"AI_RATE_LIMIT","retry_after":4,"retryable":true,"cached_content_available":false,"correlation_id":"<id>"}}
```

A request the provider rejects. Its error body names the organisation and a request id. On main that text reaches the client, inside a 503 on the transform route and inside a 400 on the draft route, which already re-raised but built its message from the provider text. On this branch both answer 400 with a fixed message and a correlation id.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo802/env.sh; echo reject > $D/provider-mode; ask 8101 aa_demo_802_before 'main, transform' chapters/ch1/transform-style '{"content": "A short paragraph to rewrite.", "target_style": "professional"}'; ask 8101 aa_demo_802_before 'main, draft' chapters/ch1/generate-draft '{"question_responses": [{"question": "What is this chapter about?", "answer": "Getting started."}]}'; ask 8100 aa_demo_802 'branch, transform' chapters/ch1/transform-style '{"content": "A short paragraph to rewrite.", "target_style": "professional"}'; ask 8100 aa_demo_802 'branch, draft' chapters/ch1/generate-draft '{"question_responses": [{"question": "What is this chapter about?", "answer": "Getting started."}]}'
```

```output
main, transform -> HTTP 503
  {"detail":"Failed to transform style: AI_INVALID_REQUEST: Invalid request: Error code: 400 - {'error': {'message': \"This model's maximum context length is 128000 tokens. However, your messages resulted in 131072 tokens (organization org-Zx81kQp, request req_7f3a2c).\", 'type': 'context_length_exceeded', 'param': None, 'code': '
main, draft -> HTTP 400
  {"detail":{"message":"Invalid request: Error code: 400 - {'error': {'message': \"This model's maximum context length is 128000 tokens. However, your messages resulted in 131072 tokens (organization org-Zx81kQp, request req_7f3a2c).\", 'type': 'context_length_exceeded', 'param': None, 'code': 'context_length_exceeded'}}","error_c
branch, transform -> HTTP 400
  {"detail":{"message":"Invalid request to AI service","error_code":"AI_INVALID_REQUEST","retry_after":null,"retryable":false,"cached_content_available":false,"correlation_id":"<id>"}}
branch, draft -> HTTP 400
  {"detail":{"message":"Invalid request to AI service","error_code":"AI_INVALID_REQUEST","retry_after":null,"retryable":false,"cached_content_available":false,"correlation_id":"<id>"}}
```

The text is not lost. It is in the backend log of this branch, with the correlation id the client was given, so a support request that quotes the id finds it.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo802/env.sh; id=$(python3 -c "import json; print(json.load(open('$D/last-body'))['detail']['correlation_id'])"); echo "log lines for the id the client received: $(grep -c "$id" $D/backend-8100.log)"; grep "$id" $D/backend-8100.log | grep -o 'Invalid request to AI service.*' | sed -E 's/[0-9a-f]{8}-[0-9a-f-]{27}/<id>/' | cut -c1-260 | head -1; echo "responses from this branch that contain the organisation id: $(grep -c 'org-Zx81kQp' $D/last-body)"
```

```output
log lines for the id the client received: 2
Invalid request to AI service: Error code: 400 - {'error': {'message': "This model's maximum context length is 128000 tokens. However, your messages resulted in 131072 tokens (organization org-Zx81kQp, request req_7f3a2c).", 'type': 'context_length_exceeded', 
responses from this branch that contain the organisation id: 0
```

An outage. The provider answers 500 three times. Both report a 503; main puts its internal error string into the detail, the branch gives the structured body with the time to retry.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo802/env.sh; echo down > $D/provider-mode; ask 8101 aa_demo_802_before 'main' chapters/ch1/enhance-text '{"content": "A short paragraph.", "enhancement_type": "clarity"}'; ask 8100 aa_demo_802 'branch' chapters/ch1/enhance-text '{"content": "A short paragraph.", "enhancement_type": "clarity"}'
```

```output
main -> HTTP 503
  {"detail":"Failed to enhance text: AI_SERVICE_UNAVAILABLE: AI service temporarily unavailable | retry_after=4s | correlation_id=<id>"}
branch -> HTTP 503, retry-after: 4
  {"detail":{"message":"AI service temporarily unavailable","error_code":"AI_SERVICE_UNAVAILABLE","retry_after":4,"retryable":true,"cached_content_available":false,"correlation_id":"<id>"}}
```

The database. A real duplicate-key error from the driver, made in a scratch database, is handed to the shared handlers of each code tree. Main puts the driver text, with the collection and index names, into the response. This branch answers with a fixed message and the request id.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo802/env.sh; echo '--- main'; PYTHONPATH= ENVIRONMENT=test $WT/backend/.venv/bin/python $D/handlers.py $MAIN 2>&1 | grep -v -e Warning -e error=E11000 | cut -c1-330; echo '--- branch'; ENVIRONMENT=test $WT/backend/.venv/bin/python $D/handlers.py $WT 2>&1 | grep -v -e Warning -e error=E11000 | cut -c1-330
```

```output
--- main
the driver said: E11000 duplicate key error collection: aa_demo_802_driver.books index: owner_id_1_title_1 dup key: { owner_id: "a1", title: "Writing" }, full error: {...
handle_generic_error: HTTP 500
  message: Error during saving the chapter | request_id: req_demo
  details: ["Operation failed: E11000 duplicate key error collection: aa_demo_802_driver.books index: owner_id_1_title_1 dup key: { owner_id: \"a1\", title: \"Writing\" }, full error: {'index': 0, 'code': 11000, 'errmsg': 'E11000 duplicate key error collection: aa_demo_802_driver.books index: owner_id_1_title_1 dup key: { owner_
handle_response_save_error: HTTP 500
  message: Failed to save question response | request_id: req_demo
  details: ["Error saving response: E11000 duplicate key error collection: aa_demo_802_driver.books index: owner_id_1_title_1 dup key: { owner_id: \"a1\", title: \"Writing\" }, full error: {'index': 0, 'code': 11000, 'errmsg': 'E11000 duplicate key error collection: aa_demo_802_driver.books index: owner_id_1_title_1 dup key: { o
--- branch
the driver said: E11000 duplicate key error collection: aa_demo_802_driver.books index: owner_id_1_title_1 dup key: { owner_id: "a1", title: "Writing" }, full error: {...
handle_generic_error: HTTP 500
  message: Error during saving the chapter | request_id: req_demo
  details: ["Operation failed"]
handle_response_save_error: HTTP 500
  message: Failed to save question response | request_id: req_demo
  details: ["Error saving response"]
```

The same behaviour as tests: real routes with the provider stubbed at the wire, and the handlers given a driver error.

```bash
cd /home/frankbria/projects/worktrees/issue-802-error-text/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo802 uv run pytest tests/test_api/test_error_text_stays_server_side.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1 | sed 's/ in [0-9.]*s//'
```

```output
============================== 24 passed ==============================
```
