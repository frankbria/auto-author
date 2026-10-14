# Issue #935: a half-finished account deletion is finished automatically

*2026-10-14T19:06:58Z by Showboat 0.6.1*
<!-- showboat-id: 14607620-e350-4565-b6d0-d8f6f5566159 -->

Real MongoDB. The test makes the identity erasure fail right after the tombstone is written (as a crash or failover would), checks that the better-auth user, account, session and 2FA documents are all still there, then runs the sweep.

```bash
cd backend && TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo935 ENVIRONMENT=test uv run pytest tests/test_db/test_stranded_identity_sweep.py tests/test_startup_indexes.py -k "sweep or stranded or half_way or password_left or idempotent" -q -p no:cacheprovider -v 2>&1 | grep -E "PASSED|FAILED|passed|failed" | sed -E "s/ +\[ *[0-9]+%\]//; s/^tests\///"
```

```output
test_db/test_stranded_identity_sweep.py::test_a_deletion_that_died_after_the_tombstone_is_finished_by_the_sweep PASSED
test_db/test_stranded_identity_sweep.py::test_the_sweep_is_idempotent PASSED
test_db/test_stranded_identity_sweep.py::test_a_password_left_without_its_user_is_found_too PASSED
test_startup_indexes.py::test_create_all_indexes_is_idempotent PASSED
test_startup_indexes.py::test_lifespan_finishes_a_deletion_that_died_half_way PASSED
======================= 5 passed, 11 deselected in 4.88s =======================
```

Mutation check (scratch script, each reverted and asserted clean), each caught by name: the sweep finding the strand but erasing nothing; the sweep looking at no tombstone; the sweep erasing live accounts too; the housekeeping task not running it.
