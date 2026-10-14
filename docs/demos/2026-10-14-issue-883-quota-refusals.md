# Issue #883: refused AI requests cost no quota

*2026-10-14T16:00:03Z by Showboat 0.6.1*
<!-- showboat-id: ba8aaf2a-4572-4a31-b9d8-27e0a86992fb -->

#798 already refunds a request refused before any model call; #883 asked for proof that N rate-limited requests leave the counter unchanged, and that a refusal from the entitlement gate (which runs after the quota charged) is refunded too. Real routes and real MongoDB counters; only the model call is stubbed.

```bash
cd backend && TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo883 ENVIRONMENT=test uv run pytest tests/test_api/test_ai_quota_charging.py -q -p no:cacheprovider -k "many_requests or entitlement_gate" -v 2>&1 | grep -E "PASSED|FAILED|passed|failed" | sed "s/ *\[.*%\]//"
```

```output
tests/test_api/test_ai_quota_charging.py::TestQuotaIsChargedOnlyForARequestThatMayHaveReachedTheModel::test_many_requests_the_rate_limiter_refuses_cost_nothing PASSED
tests/test_api/test_ai_quota_charging.py::TestQuotaIsChargedOnlyForARequestThatMayHaveReachedTheModel::test_a_request_the_entitlement_gate_refuses_costs_nothing PASSED
======================= 2 passed, 12 deselected in 0.39s =======================
```

Mutation check (scratch script, the refund in `get_ai_usage_quota` changed, run against the whole file, reverted and asserted clean after each): removing the refund fails both new tests; refunding only a 429 fails the entitlement-gate test (402) while every rate-limit test still passes, so that test covers a refusal nothing else did.
