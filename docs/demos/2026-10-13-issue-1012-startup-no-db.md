# Issue #1012: the backend starts whether or not the database can be reached

*2026-10-13T15:16:34Z by Showboat 0.6.1*
<!-- showboat-id: 19497b98-9961-4a45-b2a9-2450d95becb6 -->

Four acceptance criteria: with the database unreachable at start, the liveness route answers within a few seconds; indexes that could not be created at start are created once the database can be reached, without a restart; `/api/v1/health` still reports the database as away meanwhile; a test starts the lifespan against a database that is not there and asserts it finishes within a bound.

`run.sh` starts the backend image in a container with a database address nothing answers at, and reports when its liveness route answers and what its health route says. Asked to, it then brings a database up at that address and reports what the backend does, without restarting it.

## Before: the image built from main

Ninety seconds after the container starts, the liveness route has not answered. Start-up is still working through its indexes, thirty seconds each, and has not finished.

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo1012/run.sh ghcr.io/frankbria/auto-author-backend:sha-d23c6dc 90
```

```output
liveness route: no answer in 90s
index creations that have failed so far, thirty seconds apart: 2
'Application startup complete' in the log: 0
```

## After: the image built from this branch

The liveness route answers in the first seconds. The health route says the database is away, as it should. The backend logs that the indexes are waiting.

Then a database is started beside it. The backend notices, creates its indexes, and its health route turns healthy. The container was not restarted.

```bash
/tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo1012/run.sh aa1012-backend 90 then-database
```

```output
liveness route: answered 2s after the container started
health route:   503 {"status":"unhealthy","checks":{"mongodb":"error: TimeoutError","confi
app.main - ERROR - [-] The database cannot be reached (ServerSelectionTimeoutError); indexes are waiting for it
a database is started beside it; the backend is not restarted
'Database prepared' logged 4s later
health route:   200 {"status":"healthy","checks":{"mongodb":"ok","co
indexes on books: _id_, owner_book_id_idx, owner_updated_idx
indexes on users: _id_, auth_id_unique_idx, email_unique_idx, stripe_customer_id_unique_idx
backend container restarts: 0
```

## Tests

Start-up does not wait for a database that is not there; the liveness route answers; the wait is reported; when the database comes back the indexes are created without a restart. And the tests that were already there for what start-up does, which now wait for the task and find it done.

```bash
cd /home/frankbria/projects/worktrees/issue-1012-startup-no-db/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo1012 uv run pytest tests/test_startup_indexes.py -p no:cacheprovider --no-cov -v 2>&1 | grep -E 'PASSED|FAILED|passed|failed' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^tests.test_startup_indexes.py:://' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//'
```

```output
test_create_all_indexes_creates_owner_and_ttl_indexes PASSED
test_create_all_indexes_is_idempotent PASSED
test_no_text_index_on_books PASSED
test_lifespan_creates_owner_and_ttl_indexes PASSED
test_lifespan_purges_expired_deactivated_accounts PASSED
test_ensure_audit_log_indexes_creates_ttl_and_actor_indexes PASSED
test_lifespan_creates_audit_log_indexes PASSED
TestStartingWhileTheDatabaseIsAway::test_start_up_does_not_wait_for_it PASSED
TestStartingWhileTheDatabaseIsAway::test_the_liveness_route_answers PASSED
TestStartingWhileTheDatabaseIsAway::test_the_indexes_are_created_when_it_comes_back_without_a_restart PASSED
10 passed in 5.38s
```

```bash
cd /home/frankbria/projects/worktrees/issue-1012-startup-no-db/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo1012 uv run pytest tests/test_handled_failure_reporting.py tests/test_api/test_routes/test_email_verification.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1 | sed -e 's/^=* //' -e 's/ =*$//'
```

```output
31 passed, 24 warnings in 4.18s
```
