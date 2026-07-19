# Demo — #211: Guard test-DB teardown against non-test/remote URIs

**Type:** backend test-infrastructure change (no web/runtime surface) → main-vs-branch differential with outcome evidence (same pattern as #196/#199).

**Acceptance criterion:** _"at import time, assert the resolved DB host is local and/or the name matches `*test*` before any drop; raise otherwise."_

**The dangerous input (both sides):**
```
TEST_MONGO_URI="mongodb+srv://appuser:s3cret@cluster0.abcde.mongodb.net/auto-author"
```
An accidental Atlas URI with the real, non-test DB name `auto-author`.

---

## BEFORE — `main` (no guard): data-loss path is OPEN

`conftest.py` goes straight from resolving the DB name to connecting and dropping it, with nothing in between:

```
$ grep -n '_TEST_DB_NAME =|MongoClient|drop_database|assert_safe' backend/tests/conftest.py
29:_TEST_DB_NAME = TEST_MONGO_URI.rsplit("/", 1)[-1].split("?")[0]
30:_sync_client = pymongo.MongoClient(TEST_MONGO_URI)
167:    _sync_client.drop_database(_TEST_DB_NAME)
193:    _sync_client.drop_database(_TEST_DB_NAME)

$ ls backend/tests/db_guard.py
db_guard.py: DOES NOT EXIST on main
```

With the Atlas URI, main resolves the drop target and proceeds — no error:

```
resolved DB name to drop: 'auto-author'
main has no guard -> drop_database('auto-author') would target the REAL Atlas DB
RESULT: NO RuntimeError raised -> data-loss path OPEN
```

## AFTER — branch (guard in place): collection aborts before any drop

The guard sits at line 36 — **after** the DB name is resolved (29), **before** the client connects (38) and long before the drop sites (175/201):

```
$ grep -n '_TEST_DB_NAME =|assert_safe_test_db|MongoClient|drop_database' backend/tests/conftest.py
29:_TEST_DB_NAME = TEST_MONGO_URI.rsplit("/", 1)[-1].split("?")[0]
34:from tests.db_guard import assert_safe_test_db
36:assert_safe_test_db(TEST_MONGO_URI, _TEST_DB_NAME)
38:_sync_client = pymongo.MongoClient(TEST_MONGO_URI)
175:    _sync_client.drop_database(_TEST_DB_NAME)
201:    _sync_client.drop_database(_TEST_DB_NAME)
```

Same Atlas URI → pytest aborts at collection; no fixture, and no drop, ever runs:

```
$ TEST_MONGO_URI="mongodb+srv://.../auto-author" pytest --collect-only
E   RuntimeError: Refusing to run destructive test teardown against database
    'auto-author' at a non-local host (URI scheme 'mongodb+srv'). conftest DROPS
    this database. Point TEST_MONGO_URI at a local Mongo or a database whose name
    contains 'test'. (#211)
```

## No over-blocking — the safe default still runs

```
$ TEST_MONGO_URI="mongodb://localhost:27017/auto-author-test" pytest --collect-only
========================= 13 tests collected in 0.08s ==========================
```

Full-suite regression: `--collect-only` → **1158 collected** (guard breaks no import); `tests/test_db/` + `tests/test_api/test_routes/` + guard tests → **442 passed / 9 skipped** (every drop site exercised).

---

## The single variable

The ONLY difference between the two sides is the presence of the import-time guard. Same URI, same conftest structure, same drop sites — main lets `drop_database('auto-author')` reach the real Atlas DB; the branch raises before the sync client even connects.
