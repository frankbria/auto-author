# Issue #840: every route under a book refuses someone who does not own it

*2026-10-14T03:17:36Z by Showboat 0.6.1*
<!-- showboat-id: 63c3863e-9b2f-440c-83e3-0de135c95a99 -->

Two acceptance criteria: a parametrized sweep over every `{book_id}` route asserts non-owners are refused; a drift assertion fails when a new `{book_id}` route is not covered.

This is a change to tests, so the demo is the tests, and what they say when the thing they guard is taken away. `sweep.sh` runs the sweep file and prints failures and totals.

## The routes

Read from the application's own route table, which is where the sweep reads them.

```bash
cd /home/frankbria/projects/worktrees/issue-840-ownership-sweep/backend && PYTHONPATH=. ENVIRONMENT=test uv run python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo840/routes.py 2>&1 | grep -E '^(routes|by method|requests)'
```

```output
routes with a book id in their path: 48
by method: DELETE 2, GET 20, PATCH 4, POST 16, PUT 6
requests in the sweep's table: 48
```

## The sweep

Three kinds of test. Two about the table itself. Then, for each route: another signed-in user sends a request the owner could have sent, and must get 403 or 404, leave the book's content as it was, and not reach the model. And the owner sends the same request and must get through, so that a refusal cannot be for a missing chapter or a bad body. Real session cookies; nothing stands in for the sign-in check.

```bash
cd /home/frankbria/projects/worktrees/issue-840-ownership-sweep/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo840 bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo840/sweep.sh
```

```output
98 passed
```

The two the issue names, which had no test of this before, by name:

```bash
cd /home/frankbria/projects/worktrees/issue-840-ownership-sweep/backend && SHOW=1 ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo840 bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo840/sweep.sh 'export/docx or export/formats'
```

```output
PASSED test_someone_who_does_not_own_the_book_is_refused[GET-/export/docx]
PASSED test_someone_who_does_not_own_the_book_is_refused[GET-/export/formats]
PASSED test_the_owner_is_not_refused_the_same_request[GET-/export/docx]
PASSED test_the_owner_is_not_refused_the_same_request[GET-/export/formats]
4 passed
```

## A route that loses its check

In a scratch checkout, the ownership check is taken out of `export/formats`, then out of `export/docx`, and the sweep is run for that route. The stranger is answered 200 with the owner's data, and the sweep says so.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo840/unguard.sh export.py 472 'export/formats'
```

```output
export.py:472 was:    if book.get("owner_id") != current_user.get("auth_id"):
export.py:472  is:    if False:
E   AssertionError: 200: {"formats":[{"format":"pdf","name":"PDF Document","description":"Portable Document Format - ideal for reading and printing","mime_type":"applicat
FAILED test_someone_who_does_not_own_the_book_is_refused[GET-/export/formats]
1 failed, 1 passed
the file is as it was
```

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo840/unguard.sh export.py 221 'export/docx'
```

```output
export.py:221 was:    if book.get("owner_id") != current_user.get("auth_id"):
export.py:221  is:    if False:
E   AssertionError: 200: PKEM]R[Content_Types].xmlMO@/> {Cp(p,D8Y/L:UP.}=|&[CD]]W"|.f7E!IH|60:_BZX'VR=7#pTR'+hPvw"CE.&Vk
FAILED test_someone_who_does_not_own_the_book_is_refused[GET-/export/docx]
1 failed, 1 passed
the file is as it was
```

A route that calls the model. Without its check, a stranger's request for a draft of someone else's chapter is answered.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo840/unguard.sh books.py 2545 'generate-draft'
```

```output
books.py:2545 was:    if book.get("owner_id") != current_user.get("auth_id"):
books.py:2545  is:    if False:
E   AssertionError: 200: {"success":true,"book_id":"6acef474a1bb0c2becc7bd4e","chapter_id":"ch-1","draft":"stub response","metadata":{"word_count":2,"estimated_reading_ti
FAILED test_someone_who_does_not_own_the_book_is_refused[POST-/chapters/{chapter_id}/generate-draft]
1 failed, 1 passed
the file is as it was
```

## A new route nobody added to the sweep

A route with a book id in its path is added to the scratch checkout and given no request in the table. The drift test fails and names it.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo840/newroute.sh
```

```output
added to books.py: GET /api/v1/books/{book_id}/peek
E   AssertionError: a route under a book has no request in REQUESTS, so nothing checks who may use it
E   assert [('GET', '/peek')] == []
E    
E     Left contains one more item: ('GET', '/peek')
E     Use -v to get more diff
1 failed, 1 passed
the file is as it was
```
