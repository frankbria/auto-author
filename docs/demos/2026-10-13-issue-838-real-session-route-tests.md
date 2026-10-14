# Issue #838: routes are tested with real session cookies, and the stand-in for sign-in is strict

*2026-10-14T01:48:46Z by Showboat 0.6.1*
<!-- showboat-id: 025466f7-e80f-4a35-8b5e-ba2611cbd5f0 -->

Three acceptance criteria: a real-session test module covers valid, expired, revoked and cross-user cookies with no override; the first-user fallback is removed and the user is re-read per call; `_sync_sessions` uses the correct collection name.

This is a change to tests, so the demo is tests. The second and third criteria are about `tests/conftest.py`, and `test_auth_client_factories.py` says what the stand-in for the sign-in check must do. It is run first against main's conftest and then against this branch's.

## Before: main's conftest

The new test file is copied into main and run there. A client made without sign-in, and a cookie no client was given, are both signed in as the first user. A change to the user in the database is not seen. With the second factory, two clients are one user: its stand-in had an untyped `request` parameter, which FastAPI never fills, so it had always answered with the first user.

```bash
cp /home/frankbria/projects/worktrees/issue-838-real-session-route-tests/backend/tests/test_auth_client_factories.py /home/frankbria/projects/auto-author/backend/tests/ && cd /home/frankbria/projects/auto-author/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo838 uv run pytest -p no:cacheprovider --no-cov -q -rA tests/test_auth_client_factories.py 2>&1 | grep -E '^(PASSED|FAILED)|passed|failed' | sed -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s.*//' -e 's/ - .*//' -e 's#tests/[a-z_/]*\.py::##'; rm -f /home/frankbria/projects/auto-author/backend/tests/test_auth_client_factories.py
```

```output
PASSED test_each_client_is_its_own_user[auth_client_factory]
FAILED test_a_client_made_without_sign_in_is_not_signed_in_as_the_first_user[auth_client_factory]
FAILED test_a_client_made_without_sign_in_is_not_signed_in_as_the_first_user[async_client_factory]
FAILED test_a_cookie_no_client_was_given_is_not_signed_in_as_the_first_user[auth_client_factory]
FAILED test_a_cookie_no_client_was_given_is_not_signed_in_as_the_first_user[async_client_factory]
FAILED test_each_client_is_its_own_user[async_client_factory]
FAILED test_the_user_is_read_again_on_every_request[auth_client_factory]
FAILED test_the_user_is_read_again_on_every_request[async_client_factory]
FAILED test_a_user_who_is_no_longer_in_the_database_is_not_signed_in[auth_client_factory]
FAILED test_a_user_who_is_no_longer_in_the_database_is_not_signed_in[async_client_factory]
FAILED test_the_sessions_handle_is_better_auths_collection
10 failed, 1 passed
```

## After: this branch's conftest

```bash
cd /home/frankbria/projects/worktrees/issue-838-real-session-route-tests/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo838 uv run pytest -p no:cacheprovider --no-cov -q -rA tests/test_auth_client_factories.py 2>&1 | grep -E '^(PASSED|FAILED)|passed|failed' | sed -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s.*//' -e 's/ - .*//' -e 's#tests/[a-z_/]*\.py::##'
```

```output
PASSED test_a_client_made_without_sign_in_is_not_signed_in_as_the_first_user[auth_client_factory]
PASSED test_a_client_made_without_sign_in_is_not_signed_in_as_the_first_user[async_client_factory]
PASSED test_a_cookie_no_client_was_given_is_not_signed_in_as_the_first_user[auth_client_factory]
PASSED test_a_cookie_no_client_was_given_is_not_signed_in_as_the_first_user[async_client_factory]
PASSED test_each_client_is_its_own_user[auth_client_factory]
PASSED test_each_client_is_its_own_user[async_client_factory]
PASSED test_the_user_is_read_again_on_every_request[auth_client_factory]
PASSED test_the_user_is_read_again_on_every_request[async_client_factory]
PASSED test_a_user_who_is_no_longer_in_the_database_is_not_signed_in[auth_client_factory]
PASSED test_a_user_who_is_no_longer_in_the_database_is_not_signed_in[async_client_factory]
PASSED test_the_sessions_handle_is_better_auths_collection
11 passed
```

## Routes with real session cookies

`test_real_session_routes.py`: signed cookies, the `session` and `user` documents better-auth writes, and no dependency overridden (a fixture refuses to run the tests if one is). The application already behaved this way; these tests are what would say so if it stopped.

```bash
cd /home/frankbria/projects/worktrees/issue-838-real-session-route-tests/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo838 uv run pytest -p no:cacheprovider --no-cov -q -rA tests/test_api/test_routes/test_real_session_routes.py 2>&1 | grep -E '^(PASSED|FAILED)|passed|failed' | sed -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s.*//' -e 's/ - .*//' -e 's#tests/[a-z_/]*\.py::##'
```

```output
PASSED test_a_valid_cookie_reaches_the_routes_as_its_own_user
PASSED test_an_expired_cookie_is_refused_and_its_session_removed
PASSED test_a_revoked_cookie_is_refused_on_the_very_next_request
PASSED test_one_users_cookie_does_not_open_another_users_book
PASSED test_two_cookies_are_two_users_whatever_order_they_signed_in
PASSED test_a_cookie_that_is_not_a_live_session_is_refused[none]
PASSED test_a_cookie_that_is_not_a_live_session_is_refused[unsigned]
PASSED test_a_cookie_that_is_not_a_live_session_is_refused[signed for a session that does not exist]
PASSED test_a_cookie_that_is_not_a_live_session_is_refused[another token's signature]
9 passed
```

## Nothing leaned on the fallback

The whole backend suite with the strict stand-in. No existing test needed changing.

```bash
cd /home/frankbria/projects/worktrees/issue-838-real-session-route-tests/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo838 uv run pytest tests -p no:cacheprovider --no-cov -q 2>&1 | tail -1 | sed -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s.*//'
```

```output
1987 passed, 10 skipped
```
