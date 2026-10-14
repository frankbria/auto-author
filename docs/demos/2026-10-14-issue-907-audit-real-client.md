# Issue #907: the audit row names the real client

*2026-10-14T17:57:22Z by Showboat 0.6.1*
<!-- showboat-id: 128930eb-2039-46b3-b079-ed5b7a861860 -->

Real routes, real MongoDB, uvicorn's own ProxyHeadersMiddleware with the FORWARDED_ALLOW_IPS that docker-compose.yml gives it. A PATCH /users/me sends what nginx sends: X-Forwarded-For '203.0.113.7, 198.51.100.9' (the caller's claim, then the address nginx saw).

```bash
cd backend && TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo907 ENVIRONMENT=test uv run pytest tests/test_api/test_proxy_headers.py -q -p no:cacheprovider -v 2>&1 | grep -E "PASSED|FAILED|passed|failed" | sed -E "s/ +\[ *[0-9]+%\]//; s/^tests\/test_api\/test_proxy_headers.py:://"
```

```output
test_the_redirect_to_the_trailing_slash_stays_on_https[172.17.0.1] PASSED
test_the_redirect_to_the_trailing_slash_stays_on_https[172.22.0.1] PASSED
test_the_redirect_to_the_trailing_slash_stays_on_https[172.31.0.1] PASSED
test_the_redirect_to_the_trailing_slash_stays_on_https[192.168.0.1] PASSED
test_the_client_is_the_address_nginx_added_not_one_the_caller_sent PASSED
test_a_peer_that_is_not_the_proxy_is_not_believed PASSED
test_every_answer_tells_the_browser_to_keep_using_https PASSED
test_the_audit_row_records_the_client_the_proxy_named[through the proxy] PASSED
test_the_audit_row_records_the_client_the_proxy_named[straight from an untrusted peer] PASSED
============================== 9 passed in 0.24s ===============================
```

Mutation check (scratch script, each reverted and asserted clean): the audit taking the X-Forwarded-For header itself, a top-level ip_address: null coming back, and FORWARDED_ALLOW_IPS set to '*' were each caught by the new test.
