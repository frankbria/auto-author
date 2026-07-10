# Issue #188: OpenAI retries happen at exactly one layer

*2026-07-10T06:31:56Z*

Issue #188 feared that nested `_retry_with_backoff` wrappers in `generate_clarifying_questions` / `generate_toc_from_summary_and_responses` could multiply OpenAI calls to `AI_MAX_RETRIES^2`. This demo drives the REAL `AIService` (genuine `openai` SDK, no mocks) against a wire-logging stub OpenAI server that returns a persistent 429 and counts every real HTTP request. We compare `main` against the `fix/188-single-retry-layer` branch. `AI_MAX_RETRIES` is 3.

The stub: every POST is counted and answered 429. The driver calls `generate_clarifying_questions` once and reports (a) real HTTP requests seen on the wire, (b) app-level "Attempting API call" log lines, (c) distinct correlation ids across those lines.

## Act 1 — main (the bug)

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/d4b5d52a-3301-46ae-8127-a774543eb5c9/scratchpad/demo188/act.sh /tmp/claude-1000/-home-frankbria-projects-auto-author/d4b5d52a-3301-46ae-8127-a774543eb5c9/scratchpad/demo188/main-wt/backend main
```

```output
raised: AIRateLimitError (AI_RATE_LIMIT)
real HTTP requests on the wire: 9
'Attempting API call' log lines: 4
  Attempting API call (attempt 1/3) [correlation_id=ba310538-785e-4ca4-8090-99c9ffb6ce9a]
  Attempting API call (attempt 1/3) [correlation_id=49c97638-879c-49e0-9e8b-c3123292738d]
  Attempting API call (attempt 2/3) [correlation_id=49c97638-879c-49e0-9e8b-c3123292738d]
  Attempting API call (attempt 3/3) [correlation_id=49c97638-879c-49e0-9e8b-c3123292738d]
distinct correlation ids across attempt logs: 2
```

On `main`, one user action produced **9 real HTTP requests** for a persistent failure — `AI_MAX_RETRIES` (3) at the app layer **times** the openai SDK's own silent internal retries (default `max_retries=2` → 3 wire tries per attempt). This is genuine `3×3` call multiplication, at a retry layer the issue had not named (the SDK), stacked under the two `_retry_with_backoff` layers. The nested `_retry_with_backoff` itself shows as **4** "Attempting API call" lines for 3 attempts (the outer wrapper logs a spurious extra one) and **2 distinct correlation ids** — the retry/backoff trace is decoupled from the calling request. Also note the total stall: the app backoff slept 1+2+4s while each attempt itself burned SDK-internal retry time.

## Act 2 — fix/188-single-retry-layer

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/d4b5d52a-3301-46ae-8127-a774543eb5c9/scratchpad/demo188/act.sh /home/frankbria/projects/auto-author/backend branch
```

```output
raised: AIRateLimitError (AI_RATE_LIMIT)
real HTTP requests on the wire: 3
'Attempting API call' log lines: 3
  Attempting API call (attempt 1/3) [correlation_id=8f5aaecc-8786-4884-b96a-eef89398a5c1]
  Attempting API call (attempt 2/3) [correlation_id=8f5aaecc-8786-4884-b96a-eef89398a5c1]
  Attempting API call (attempt 3/3) [correlation_id=8f5aaecc-8786-4884-b96a-eef89398a5c1]
distinct correlation ids across attempt logs: 1
```

Same persistent failure on the branch: **3 real HTTP requests** — exactly `AI_MAX_RETRIES` — one attempt log per real request, one correlation id across the whole retry trace, and the caller still gets the structured `AIRateLimitError`. Two changes produced this: the outer `_retry_with_backoff` wrappers were removed (retry now lives only inside `_make_openai_request`), and the openai client is constructed with `max_retries=0` so the SDK cannot silently stack its own retries underneath.

The second site the issue names, `generate_toc_from_summary_and_responses`, on the branch:

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/d4b5d52a-3301-46ae-8127-a774543eb5c9/scratchpad/demo188/act_toc.sh
```

```output
raised: AIRateLimitError (AI_RATE_LIMIT)
real HTTP requests on the wire: 3
'Attempting API call' log lines: 3
  Attempting API call (attempt 1/3) [correlation_id=abadabdd-5f43-4829-baa9-ca9c6142af7b]
  Attempting API call (attempt 2/3) [correlation_id=abadabdd-5f43-4829-baa9-ca9c6142af7b]
  Attempting API call (attempt 3/3) [correlation_id=abadabdd-5f43-4829-baa9-ca9c6142af7b]
distinct correlation ids across attempt logs: 1
```

## Verdict

| Acceptance criterion | Evidence |
|---|---|
| Retry happens at exactly one layer | Branch: one attempt log per real request (3/3) and a single correlation id per request trace, for both `generate_clarifying_questions` and `generate_toc_from_summary_and_responses`; on main the same action logged 4 attempt lines under 2 correlation ids |
| Persistently-failing call makes at most `AI_MAX_RETRIES` requests | Wire-counted by the stub: **main 9 → branch 3** real HTTP requests (`AI_MAX_RETRIES` = 3); pinned by `TestSingleRetryLayer` (call counts, log counts, correlation ids) and `test_sdk_internal_retries_disabled` |

Everything above ran the real `AIService` with the genuine `openai` 1.97.1 SDK against a live HTTP stub — no mocks anywhere in the call path. Backend suite: 1149 passed / 13 skipped, 92.21% coverage.
