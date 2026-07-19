# Demo — #210: Delete debug scratch tests committed under `backend/tests`

**PR:** #316 · **Type:** backend test-hygiene, pure deletion (−1604 lines, 0 additions)

The acceptance criterion is a single line: *"delete these files (or move genuine cases
into properly-named asserting tests)."* This demo shows the **outcome** — the false-green
and collection-poison the scratch files caused (BEFORE), and that removing them lost no
importer and no unique coverage (AFTER).

`BEFORE` = the parent commit (`HEAD~1`, == `main` for this branch). `AFTER` = the branch tip.

---

## AC — the seven scratch files are gone

```
$ git show --stat HEAD | tail -9
 backend/tests/test_api/run_test_api.py                        |  74 ---
 backend/tests/test_api/test_routes/run_test_authenticated_endpoints.py | 216 ---
 backend/tests/test_api/test_routes/test_debug_loop.py         | 681 --------
 backend/tests/test_services/run_test_question_responses.py    | 155 ---
 backend/tests/test_services/run_test_toc_flow.py              | 163 ---
 backend/tests/test_services/simple_endpoint_test.py           | 102 ---
 backend/tests/test_services_summary.py                        | 213 ---
 7 files changed, 1604 deletions(-)
```

The issue names the `run_test_*` **class**; deleting only the literally-cited files would
leave `run_test_toc_flow.py` + `run_test_authenticated_endpoints.py` (same class) behind,
so all seven go — root-cause, not symptom.

---

## Outcome 1 — false-green removed (a test file that barely asserts, run in CI)

`test_debug_loop.py` matched pytest's `python_files = test_*.py` glob, so CI collected and
ran it — **15 test functions across 681 lines with only 4 real asserts** (all the same
`status_code == 201` book/chapter-creation smoke check):

```
# BEFORE (HEAD~1)
$ git show HEAD~1:backend/tests/test_api/test_routes/test_debug_loop.py | grep -cE '^\s*(async )?def test_'
15
$ git show HEAD~1:backend/tests/test_api/test_routes/test_debug_loop.py | grep -cE '\bassert\b'
4
$ git show HEAD~1:backend/tests/test_api/test_routes/test_debug_loop.py | grep -cE '\bprint\('
176
```

Those `201` assertions are **redundant** — the same creation paths are asserted in 8 real
route suites that all pass green:

```
$ grep -rln 'status_code == 201' backend/tests/test_api/test_routes/
test_books_crud_coverage.py
test_books_chapters_crud_coverage.py
test_books_metadata.py
test_books_toc_coverage.py
test_books_pretoc_coverage.py
test_books_chapter_content_coverage.py
test_toc_generation.py
test_chapters_error_handling.py
```

## Outcome 2 — collection-poison removed (env mutated at import, zero asserts)

`test_services_summary.py` had **0 asserts** but mutated six process-wide env vars at
**module import time** — merely collecting it rewrote `DATABASE_URL`, the OpenAI key, and
the Better-Auth secret for whatever ran next (a collection-order poison vector):

```
# BEFORE (HEAD~1) — top-level, executes on import
$ git show HEAD~1:backend/tests/test_services_summary.py | grep -nE "os\.environ\["
10:os.environ['DATABASE_URL'] = 'mongodb://localhost:27017'
11:os.environ['DATABASE_NAME'] = 'auto_author_test'
12:os.environ['OPENAI_AUTOAUTHOR_API_KEY'] = 'test-key'
13:os.environ['BETTER_AUTH_SECRET'] = 'test-secret-for-ci-minimum-32-characters-long-safe-for-testing'
14:os.environ['BETTER_AUTH_URL'] = 'http://localhost:3000'
15:os.environ['BETTER_AUTH_ISSUER'] = 'better-auth'
$ git show HEAD~1:backend/tests/test_services_summary.py | grep -cE '\bassert\b'
0
```

## Outcome 3 — hygiene / security smell removed (hardcoded token, Windows path)

The uncollected `run_test_*` scripts carried a hardcoded auth-token placeholder and a
developer's absolute Windows path:

```
# BEFORE (HEAD~1)
$ git show HEAD~1:backend/tests/test_api/run_test_api.py | sed -n '12p'
    load_dotenv("d:\Projects\auto-author\backend\.env")
$ git show HEAD~1:backend/tests/test_services/run_test_question_responses.py | sed -n '18,20p'
# Test authentication token - you'll need to get this from your browser
...
AUTH_TOKEN = "your_auth_token_here"
```

---

## Invariant — nothing of value lost

**No remaining importer** of any of the 7 modules anywhere in `backend/`
(imports, conftest, pytest plugins/markers, dynamic/string refs, fixtures):

```
$ for m in test_debug_loop test_services_summary run_test_api \
           run_test_authenticated_endpoints run_test_question_responses \
           run_test_toc_flow simple_endpoint_test; do
    printf '%-32s -> %s\n' "$m" "$(grep -rn "$m" backend/ --include='*.py' --include='*.ini' \
      --include='*.cfg' --include='*.toml' || echo CLEAN)"
  done
test_debug_loop                  -> CLEAN
test_services_summary            -> CLEAN
run_test_api                     -> CLEAN
run_test_authenticated_endpoints -> CLEAN
run_test_question_responses      -> CLEAN
run_test_toc_flow                -> CLEAN
simple_endpoint_test             -> CLEAN
```

**Collection stays clean** — no import error introduced by the deletions:

```
# AFTER (branch)
$ cd backend && uv run pytest --collect-only -q tests/ | tail -1
======================== 1145 tests collected in 1.00s =========================
```

**Every deletion site passes green** — a full-suite run (on tmpfs mongod) was green through
all of `test_api/test_routes/`, `test_api/`, `test_services/`, and the tests root before it
reached the pre-existing network-bound slow tests (`test_ai_service.py`, `test_e2e_no_mocks.py`,
untouched here). Representative `test_api/test_routes/` slice (deletion site of
`test_debug_loop.py` + `run_test_authenticated_endpoints.py`):

```
tests/test_api/test_routes/test_books_crud_coverage.py .................
tests/test_api/test_routes/test_books_chapters_crud_coverage.py ........
tests/test_api/test_routes/test_chapters_characterization.py ....
... (all green, zero failures)
```

The authoritative full-suite + 85% coverage gate runs in CI's branch-protected
**Backend Tests** job.
