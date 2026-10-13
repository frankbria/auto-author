# Issue #827: saving a chapter no longer inserts an access-log row

*2026-10-13T18:39:41Z by Showboat 0.6.1*
<!-- showboat-id: 70f7eaa2-1298-4bc9-a8b3-d0323f90dd20 -->

One acceptance criterion: an autosave makes no access-log insert, with a test.

`test_demo_827.py` is copied into `backend/tests/` of the checkout it is run in. Through the API it creates a book with one chapter, creates the indexes start-up creates, opens the chapter, saves it twenty times as the editor does (`PATCH /books/{id}/chapters/{chapter}/content`), reads it back, and prints what is in `chapter_access_logs`. Twenty saves is about a minute of typing: the editor saves three seconds after the last keystroke.

## Before: main

Twenty saves, twenty rows of type `update_content`, each entered in six indexes.

```bash
cp /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo827/test_demo_827.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main827/backend/tests/ && cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main827/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo827 uv run pytest -p no:cacheprovider --no-cov tests/test_demo_827.py -s -q 2>&1 | grep -E '^  |passed|failed' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'; rm -f /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main827/backend/tests/test_demo_827.py
```

```output
 20 saves answered: [200]; the chapter now holds 20 words
 rows in chapter_access_logs, by type: {'read_content': 2, 'update_content': 20}
 rows written by the saves: 20
 indexes each row is entered in: 6
1 passed
```

## After: this branch

The same twenty saves are answered the same way and the chapter holds what was saved. No row was written for them. The two rows that are there are from reading the chapter, before and after.

```bash
cp /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo827/test_demo_827.py /home/frankbria/projects/worktrees/issue-827-autosave-access-log/backend/tests/ && cd /home/frankbria/projects/worktrees/issue-827-autosave-access-log/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo827 uv run pytest -p no:cacheprovider --no-cov tests/test_demo_827.py -s -q 2>&1 | grep -E '^  |passed|failed' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'; rm -f /home/frankbria/projects/worktrees/issue-827-autosave-access-log/backend/tests/test_demo_827.py
```

```output
 20 saves answered: [200]; the chapter now holds 20 words
 rows in chapter_access_logs, by type: {'read_content': 2}
 rows written by the saves: 0
 indexes each row is entered in: 6
1 passed
```

## Nothing read those rows

Every place the application reads `chapter_access_logs`, with the types it asks for. Recent chapters come from `view` and `edit` rows and tab state from `tab_state` rows. The analytics query counts rows of every type; its one route is called by no page, which the second command shows: the API client mentions analytics once, in a comment, and no file in the frontend names the route.

```bash
cd /home/frankbria/projects/worktrees/issue-827-autosave-access-log/backend && grep -n 'access_type' app/services/chapter_access_service.py | grep -v 'access_type: str\|access_type=access_type'
```

```output
50:                {"user_id": user_id, "book_id": book_id, "access_type": "tab_state"}
68:                    "_id": {"chapter_id": "$chapter_id", "access_type": "$access_type"},
88:                    "access_type": {"$in": ["view", "edit"]},
126:            access_type="tab_state",
```

```bash
cd /home/frankbria/projects/worktrees/issue-827-autosave-access-log && grep -ni 'analytics' frontend/src/lib/api/*.ts | cut -c1-120; echo "files under frontend/src that name the route: $(grep -rl '/analytics' frontend/src | wc -l)"
```

```output
frontend/src/lib/api/bookClient.ts:515:   * - Analytics and access logs
files under frontend/src that name the route: 0
```

## Tests

The new test, which failed before the change with three rows for three saves, and the rest of the tests for reading and saving chapter content.

```bash
cd /home/frankbria/projects/worktrees/issue-827-autosave-access-log/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo827 uv run pytest -p no:cacheprovider --no-cov tests/test_api/test_routes/test_books_chapter_content_coverage.py -v -k 'no_access_log' 2>&1 | grep -E 'PASSED|FAILED|passed|failed' | sed 's/^tests.test_api.test_routes.test_books_chapter_content_coverage.py:://' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
test_saving_content_writes_no_access_log_row PASSED
1 passed, 34 deselected
```

```bash
cd /home/frankbria/projects/worktrees/issue-827-autosave-access-log/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo827 uv run pytest -p no:cacheprovider --no-cov tests/test_api/test_routes/test_books_chapter_content_coverage.py tests/test_services/test_chapter_access.py tests/test_handled_failure_reporting.py -q 2>&1 | tail -1 | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
64 passed
```
