# Issue #826: a signed-in request asks the database two things, not five

*2026-10-13T18:10:03Z by Showboat 0.6.1*
<!-- showboat-id: 661e4abd-30e4-46fe-b0ae-49250821169a -->

Three acceptance criteria: a steady-state authenticated GET makes at most two reads and no write; `explain()` on the remaining lookup shows an index scan on `_id`; the user read on the sign-in path leaves `book_ids` out.

`test_demo_826.py` is copied into `backend/tests/` of the checkout it is run in. It fills a database in the shape better-auth writes (200 users and 200 sessions besides the one signing in, whose application record lists 500 books), runs the index step start-up runs, turns on MongoDB's profiler, makes one `GET /api/v1/users/me` with a signed session cookie, and prints what the profiler recorded: each command, the plan it ran, how many documents it examined, and how many bytes came back.

## Before: main

Four reads and a write. The session is found by scanning every session. The user is first looked for by an `id` field that better-auth does not write: all 201 users are examined and none is returned. The application's record comes back with its 500 book ids, 17 kilobytes.

```bash
cp /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo826/test_demo_826.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main826/backend/tests/ && cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main826/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo826 uv run pytest -p no:cacheprovider --no-cov tests/test_demo_826.py -s -q 2>&1 | grep -E '^  |passed|failed' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'; rm -f /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main826/backend/tests/test_demo_826.py
```

```output
 GET /api/v1/users/me -> 200, book_ids in the answer: True
 4 reads, 1 writes
 query     session  COLLSCAN                                   examined 201 documents, answered   244 bytes
 update    session  EXPRESS_IXSCAN { _id: 1 },EXPRESS_UPDATE   examined   1 documents, answered     0 bytes
 query     user     COLLSCAN                                   examined 201 documents, answered   118 bytes
 query     user     EXPRESS_IXSCAN { _id: 1 }                  examined   1 documents, answered   208 bytes
 query     users    EXPRESS_IXSCAN { auth_id: 1 }              examined   1 documents, answered 17129 bytes
1 passed
```

## After: this branch

Two reads and no write. The session is found through an index on its token and its user comes with it, joined on `_id`. The application's record is 224 bytes. Then `explain()` for that one read of session and user: the join used the index on `_id`, scanned no collection, and examined one document.

```bash
cp /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo826/test_demo_826.py /home/frankbria/projects/worktrees/issue-826-auth-path-queries/backend/tests/ && cd /home/frankbria/projects/worktrees/issue-826-auth-path-queries/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo826 uv run pytest -p no:cacheprovider --no-cov tests/test_demo_826.py -s -q 2>&1 | grep -E '^  |passed|failed' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'; rm -f /home/frankbria/projects/worktrees/issue-826-auth-path-queries/backend/tests/test_demo_826.py
```

```output
 GET /api/v1/users/me -> 200, book_ids in the answer: False
 2 reads, 0 writes
 aggregate session  EXPRESS_IXSCAN { token: 1 }                examined   2 documents, answered   345 bytes
 query     users    IXSCAN { auth_id: 1 }                      examined   1 documents, answered   224 bytes
 explain() of the one read of session and user:
   session by token: ['EXPRESS_IXSCAN'] on index ['token_1']
   user joined on _id: indexes used ['_id_'], collection scans 0, documents examined 1
1 passed
```

## What had to keep working

A session whose better-auth user is gone is refused (#763). The application's email still follows better-auth's (#765). A session that holds its user id as text still signs in. And "Last active" in Settings, which is the session's `updatedAt`: it is written once it is out of date, and not before.

```bash
cd /home/frankbria/projects/worktrees/issue-826-auth-path-queries/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo826 uv run pytest -p no:cacheprovider --no-cov tests/test_core/test_auth_path_queries.py -v 2>&1 | grep -E 'PASSED|FAILED|passed|failed' | sed 's/^tests.test_core.test_auth_path_queries.py:://' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
test_a_signed_in_request_reads_twice_and_writes_nothing PASSED
test_nothing_it_asks_scans_a_collection PASSED
test_the_user_is_found_through_the_index_on_its_id PASSED
test_a_lookup_of_the_user_on_its_own_goes_by_id_too PASSED
test_the_user_it_returns_does_not_carry_every_book_id PASSED
test_last_active_is_written_once_it_is_out_of_date PASSED
test_a_session_whose_user_is_gone_is_refused PASSED
test_a_session_holding_its_user_id_as_text_still_signs_in PASSED
test_the_better_auth_email_is_still_mirrored PASSED
test_sessions_are_indexed_by_token PASSED
10 passed
```

```bash
cd /home/frankbria/projects/worktrees/issue-826-auth-path-queries/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo826 uv run pytest -p no:cacheprovider --no-cov tests/test_core/test_better_auth_session.py -v -k 'active' 2>&1 | grep -E 'PASSED|FAILED|passed|failed' | sed 's/^tests.test_core.test_better_auth_session.py:://' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
TestValidateBetterAuthSession::test_a_session_active_a_moment_ago_is_not_written PASSED
1 passed, 37 deselected
```

## The rest of the sign-in tests

Including the ones for a database that cannot be reached, for email ownership, whose fixture now seeds users as better-auth stores them, and for account deletion with a real session.

```bash
cd /home/frankbria/projects/worktrees/issue-826-auth-path-queries/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo826 uv run pytest -p no:cacheprovider --no-cov tests/test_core tests/test_api/test_routes/test_email_verification.py tests/test_api/test_routes/test_account_deletion_real_session.py -q 2>&1 | tail -1 | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
200 passed
```
