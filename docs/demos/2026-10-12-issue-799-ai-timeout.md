# Issue #799: AI requests have a time budget, and a refused credential is an outage

*2026-10-12T03:56:50Z by Showboat 0.6.1*
<!-- showboat-id: d7ddfb40-384c-4e53-841a-7624f2aec6fb -->

The AI client was built with no timeout, so the SDK's 600 seconds applied, and a provider that rejected the API key was retried and then reported as an unexpected error. This demo runs the branch's real backend on $API against a stand-in provider on a local port, whose behaviour is switched between requests: stay silent, reject the key, or refuse for billing. The backend is started with `AI_REQUEST_TIMEOUT_SECONDS=2` and `AI_MAX_RETRIES=2`. `ask <mode>` sets the provider's behaviour, sends one summary-analysis request to the backend, and reports the status, the time taken and how many requests the provider received. Nothing here touches a real provider or staging.

**Criterion: a provider that never responds fails within the budget.** Two attempts of two seconds each, with one second between them.

```bash
ask silent
```

```output
silent: HTTP 503 after 5.0 seconds; the provider received 2 request(s)
  the user is told: Summary analysis is temporarily unavailable. Please try again.
```

**Criterion: insufficient_quota and auth errors are non-retryable and logged CRITICAL.** The provider now answers 401 for the key, then 429 `insufficient_quota`. Each is sent once, the user gets a 503 with no mention of keys or billing, and the backend log carries one CRITICAL line for each.

```bash
ask key
ask billing
grep -o "CRITICAL:[^\[]*" "$BACKEND_LOG" | sed "s/ *$//"
```

```output
key: HTTP 503 after 0.0 seconds; the provider received 1 request(s)
  the user is told: Summary analysis is temporarily unavailable. Please try again.
billing: HTTP 503 after 0.0 seconds; the provider received 1 request(s)
  the user is told: Summary analysis is temporarily unavailable. Please try again.
CRITICAL:app.services.ai_service:AI provider rejected our credential (401)
CRITICAL:app.services.ai_service:OpenAI refused for billing (insufficient_quota)
```

**Tests.** The named tests, including one that talks to a real socket that never answers:

```bash
cd "$WT/backend" && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-s799demo uv run pytest -p no:cacheprovider --no-cov -o addopts="" -v tests/test_services/test_ai_request_timeout.py tests/test_error_handlers.py -k "test_ai_request_timeout or rejecting_our_key" 2>&1 | grep -E "PASSED|FAILED|ERROR" | sed "s/ *\[ *[0-9]*%\]//; s/^tests\/[a-z_\/]*\.py:://" | sort
```

```output
TestQuestionGenerationErrorHandler::test_provider_rejecting_our_key_is_503_though_not_retryable PASSED
test_a_billing_refusal_is_logged_critical[402] PASSED
test_a_billing_refusal_is_logged_critical[insufficient_quota] PASSED
test_a_provider_that_never_answers_fails_within_the_budget PASSED
test_a_refused_credential_is_an_outage_not_something_to_retry[key not allowed] PASSED
test_a_refused_credential_is_an_outage_not_something_to_retry[rejected key] PASSED
test_the_timeout_is_a_setting_with_a_sane_default PASSED
```

Not shown: a real provider. The default budget is 120 seconds per attempt, chosen to leave room for a long draft; whether that is the right number for production traffic has not been measured.
