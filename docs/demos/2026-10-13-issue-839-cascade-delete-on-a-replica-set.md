# Issue #839: delete_book's transaction branch runs in CI, on a replica set

*2026-10-14T02:44:30Z by Showboat 0.6.1*
<!-- showboat-id: a84ee853-b7ab-4eb1-9f36-68e0f5999d64 -->

Two acceptance criteria: a CI job runs a single-node replica set; the cascade tests assert a non-None session.

`delete_book` deletes a book and everything under it. On a replica set it does so in a transaction, and that is the branch Atlas runs. A single-node replica set is running in a container on port 27027, started the way the CI step starts its own. The standalone server every other test uses is on 27017. `cascade.sh` runs the cascade test file and prints each test and the first line of each failure.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo839/servers.sh
```

```output
27027: replica set rs0, primary: true
27017: replica set none (standalone)
```

## Before: main, on the replica set

The new tests are copied into a checkout of main and run against the replica set. Even there, the cascade is handed no session: `book.py` binds its client when it is imported, the test fixture never rebound it, the probe for a replica set raised on a client from another event loop, and the error was swallowed. A failure part-way leaves the access logs deleted.

```bash
cp /home/frankbria/projects/worktrees/issue-839-replica-set-ci/backend/tests/test_db/test_cascade_delete_atomic.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main839/backend/tests/test_db/ && cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main839/backend && ENVIRONMENT=test REQUIRE_REPLICA_SET=1 TEST_MONGO_URI='mongodb://localhost:27027/auto-author-test-demo839?replicaSet=rs0' bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo839/cascade.sh; git -C /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main839 checkout -q HEAD -- backend/tests/test_db/test_cascade_delete_atomic.py
```

```output
E   assert None is not None
E   assert [False] == [True]
PASSED test_delete_book_removes_all_related_data
PASSED test_delete_book_not_owned_removes_nothing
PASSED test_delete_all_user_books_only_touches_owner
PASSED test_delete_all_user_books_failure_leaves_every_book
PASSED test_delete_all_user_books_commands_do_not_grow_with_books[3]
PASSED test_delete_all_user_books_commands_do_not_grow_with_books[250]
PASSED test_delete_all_user_books_chunks_question_ids
PASSED test_delete_all_user_books_writes_one_audit_row
PASSED test_delete_book_failure_is_contained_and_logged
FAILED test_the_cascade_uses_the_test_runs_own_client
FAILED test_on_a_replica_set_the_cascade_runs_in_a_transaction
FAILED test_on_a_replica_set_a_failure_puts_back_what_was_already_deleted
3 failed, 9 passed
```

## After: this branch, on the replica set

The cascade is given a session with a transaction open, and a failure part-way puts back what had been deleted.

```bash
cd /home/frankbria/projects/worktrees/issue-839-replica-set-ci/backend && ENVIRONMENT=test REQUIRE_REPLICA_SET=1 TEST_MONGO_URI='mongodb://localhost:27027/auto-author-test-demo839?replicaSet=rs0' bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo839/cascade.sh
```

```output
PASSED test_delete_book_removes_all_related_data
PASSED test_delete_book_not_owned_removes_nothing
PASSED test_delete_all_user_books_only_touches_owner
PASSED test_delete_all_user_books_failure_leaves_every_book
PASSED test_delete_all_user_books_commands_do_not_grow_with_books[3]
PASSED test_delete_all_user_books_commands_do_not_grow_with_books[250]
PASSED test_delete_all_user_books_chunks_question_ids
PASSED test_delete_all_user_books_writes_one_audit_row
PASSED test_delete_book_failure_is_contained_and_logged
PASSED test_the_cascade_uses_the_test_runs_own_client
PASSED test_on_a_replica_set_the_cascade_runs_in_a_transaction
PASSED test_on_a_replica_set_a_failure_puts_back_what_was_already_deleted
12 passed
```

## On a standalone server

A developer's machine. The two tests that need a replica set are skipped and say why.

```bash
cd /home/frankbria/projects/worktrees/issue-839-replica-set-ci/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo839 bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo839/cascade.sh | grep -v '^PASSED'
```

```output
SKIPPED [1] needs a replica set: transactions do not exist on a standalone server
SKIPPED [1] needs a replica set: transactions do not exist on a standalone server
10 passed, 2 skipped
```

## A run that is told it has a replica set, and has not

`REQUIRE_REPLICA_SET` is what the CI step sets. With it, a standalone server is a failure and not a skip, so the step cannot go green by running nothing.

```bash
cd /home/frankbria/projects/worktrees/issue-839-replica-set-ci/backend && REQUIRE_REPLICA_SET=1 ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo839 bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo839/cascade.sh | grep -v '^PASSED' | sort -u
```

```output
10 passed, 2 errors
E   Failed: REQUIRE_REPLICA_SET is set, and the test database is not a replica set
ERROR test_on_a_replica_set_a_failure_puts_back_what_was_already_deleted
ERROR test_on_a_replica_set_the_cascade_runs_in_a_transaction
```

## The CI step, as written

The step's own script, taken out of the workflow file and run here: it starts a container on port 27018, makes it a replica set, waits for a primary and runs the cascade tests.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo839/step.sh
```

```output
the step's environment: REQUIRE_REPLICA_SET=1, TEST_MONGO_URI=mongodb://localhost:27018/auto-author-test?replicaSet=rs0
test_the_cascade_uses_the_test_runs_own_client PASSED
test_on_a_replica_set_the_cascade_runs_in_a_transaction PASSED
test_on_a_replica_set_a_failure_puts_back_what_was_already_deleted PASSED
12 passed
the step's script exited 0
```
