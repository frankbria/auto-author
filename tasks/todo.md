# Issue #202 — [P2.10] AI integration is unobservable in CI (fallback masks outages; mocks lack autospec)

**Plan source**: self-authored (no plan comment on issue). Branch: `fix/202-ai-observability-autospec`.

## Key design decisions (autonomous, precedent-backed)

1. **AC1 OR-branch: autospec mocks, NOT a nightly real-key job.** The AC explicitly offers either. A scheduled real-key job means recurring OpenAI spend, a required signal keyed on a secret whose validity can't be verified from the repo, and a flaky external dependency in CI. Rejected; documented in PR.
2. **The AC's literal `create_autospec(OpenAI)` is unusable** — verified empirically: the client reaches `chat.completions` through `cached_property` descriptors, so `create_autospec(OpenAI, instance=True).chat.completions` raises `AttributeError`. Instead, autospec the **real bound method** `OpenAI(api_key="test").chat.completions.create`, which enforces the real SDK signature (verified: rejects bogus/missing kwargs, accepts production kwargs). A meta-test pins that the helper has teeth.
3. **AC2: the one remaining silent fallback is `_parse_questions_response`** (ai_service.py:507-514) substituting 4 hard-coded clarifying questions when AI output is unparseable — indistinguishable from AI output. Fix: raise `AIServiceError(error_code="AI_INVALID_RESPONSE", retryable=True)`, consistent with the #48 TOC precedent (ai_service.py:765-776). Endpoint maps base AIServiceError to a structured 500 with error_code/retryable/correlation_id (429/503 reserved for rate-limit/network/unavailable subclasses). Chapter-question fallback observability already shipped in #182 (`is_fallback`, asserted in 3 test files) — no code needed, cited in PR.

## Steps

- [x] 1. **Autospec helper + meta-tests** — new helper `backend/tests/test_services/openai_autospec.py`: `autospec_openai_client(content, finish_reason="stop")` returning a client mock whose `chat.completions.create` is `create_autospec` of the real bound method, returning a real typed `ChatCompletion`. Meta-tests: bogus kwarg → TypeError; missing required kwarg → TypeError; production kwargs accepted.
- [x] 2. **Request-shape regression tests** — `backend/tests/test_services/test_openai_request_shape.py`: real `AIService` with autospec'd client; drive `_make_openai_request` (the single choke point all 8 AI methods funnel through — verified) and one full public method; pin the exact kwarg set {model, messages, temperature, max_tokens}. Rewrite `test_ai_service_style_transformation.py` fixtures onto the helper (drops the bare `Mock(spec=OpenAI)` that validated nothing).
- [x] 3. **Kill silent clarifying-question substitution (AC2)** — `_parse_questions_response` raises `AIServiceError` AI_INVALID_RESPONSE when no questions are parseable; tests: parse-failure raises; endpoint structured-500 pass-through (established base-AIServiceError convention); happy path unchanged; fix/remove any tests characterizing the old default substitution.
- [x] 4. Full backend suite + coverage gate + ruff; deslop scan.
- [x] 5. opencode (GLM) pre-PR review of branch diff (codex fallback per hang memory).
- [x] 6. PR with Known Limitations (nightly-job branch rejected rationale; TOC text-extraction recovery + analyze-summary error dict deliberately untouched).
- [x] 7. Post-PR opencode review posted as PR comment.
- [x] 8. Demo (showboat): main-vs-branch differential — (a) bogus kwarg injected into `_sync_request` sails through bare-Mock tests on main but fails autospec tests on branch; (b) unparseable AI output returns 200 + 4 canned questions on main vs structured 500 AI_INVALID_RESPONSE on branch.
- [x] 9. CI green + final feedback triage.
- [x] 10. Docs sync (CLAUDE.md changelog) + merge + close issue.

## Acceptance criteria

- [x] AC1: unit mocks validate kwargs against the real SDK signature (autospec branch of the OR; meta-test proves enforcement).
- [x] AC2: fallback output observable — chapter questions via `is_fallback` (#182, already asserted); clarifying-questions silent substitution eliminated (structured retryable error); mocked tests can assert the AI path was taken.

## Non-goals (documented)

- Nightly real-key CI job (AC1 OR-branch rejected — spend + unverifiable secret + flake).
- TOC text-extraction recovery marker (`_create_fallback_toc` recovers real AI content; unrecoverable case already raises — #48).
- `analyze_summary_for_toc` error dict (already observable: `error` key + `is_ready_for_toc: False`, never persisted — #105).
- Autospec'ing high-level `ai_service` method patches in endpoint tests (own-method signatures, not SDK boundary).
