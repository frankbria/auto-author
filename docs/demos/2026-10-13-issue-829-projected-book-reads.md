# Issue #829: a handler reads the part of the book it uses

*2026-10-13T20:30:33Z by Showboat 0.6.1*
<!-- showboat-id: 62cd77c1-16e9-405c-95b1-1a894e43049e -->

Two acceptance criteria: each listed handler reads with a projection of only the fields it uses; the existing endpoint tests pass.

`test_demo_829.py` is copied into `backend/tests/` of the checkout it is run in, with the table of routes from the new test file. For each route it builds a book whose chapter bodies are 700 kilobytes, whose summary history is 200 and whose interview answers are 100, turns on MongoDB's profiler, calls the route, and prints how many bytes the route's reads of the `books` collection brought back.

## Before: main

Every route reads the whole megabyte, whatever it wants from it. Saving the summary reads it twice. The refused save reads it once and the book without its bodies once.

```bash
cp /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo829/test_demo_829.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main829/backend/tests/ && cp /home/frankbria/projects/worktrees/issue-829-projected-book-reads/backend/tests/test_api/test_routes/test_book_reads_are_projected.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main829/backend/tests/test_api/test_routes/test_book_reads_are_projected.py && cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main829/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo829 uv run pytest -p no:cacheprovider --no-cov tests/test_demo_829.py -s -q 2>&1 | grep -E '^  [a-z].* bytes in|^=+ [0-9]+ (passed|failed)|^[0-9]+ (passed|failed)' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'; rm -f /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main829/backend/tests/test_demo_829.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main829/backend/tests/test_api/test_routes/test_book_reads_are_projected.py
```

```output
 the book                                   200  1,002,506 bytes in 1 read
 the summary                                200  1,002,506 bytes in 1 read
 saving the summary                         200  2,005,012 bytes in 2 reads
 patching the summary                       200  1,002,506 bytes in 1 read
 the interview answers                      200  1,002,506 bytes in 1 read
 readiness for a table of contents          200  1,002,506 bytes in 1 read
 the table of contents                      200  1,002,506 bytes in 1 read
 the chapters' metadata                     200  1,002,506 bytes in 1 read
 enhancing text, refused for having none    400  1,002,506 bytes in 1 read
 saving the interview answers               200  1,002,506 bytes in 1 read
 cleaning up a transcription, refused for having none 400  1,002,506 bytes in 1 read
 deleting the book                          204  1,002,691 bytes in 2 reads
 one chapter's content                      200  1,002,506 bytes in 1 read
 several chapters' content                  200  1,002,506 bytes in 1 read
 a save refused as out of date              409  1,304,865 bytes in 2 reads
1 passed
```

## After: this branch

Each route reads what it uses. Readiness, deleting, and the two saves read the owner and a field or two: a few hundred bytes. The summary routes read the summary and its history. The routes that walk the chapter list read the book without its bodies. The routes that return a chapter's body read the table of contents, and not the 300 kilobytes beside it.

```bash
cp /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo829/test_demo_829.py /home/frankbria/projects/worktrees/issue-829-projected-book-reads/backend/tests/ && cd /home/frankbria/projects/worktrees/issue-829-projected-book-reads/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo829 uv run pytest -p no:cacheprovider --no-cov tests/test_demo_829.py -s -q 2>&1 | grep -E '^  [a-z].* bytes in|^=+ [0-9]+ (passed|failed)|^[0-9]+ (passed|failed)' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'; rm -f /home/frankbria/projects/worktrees/issue-829-projected-book-reads/backend/tests/test_demo_829.py
```

```output
 the book                                   200    302,359 bytes in 1 read
 the summary                                200    200,763 bytes in 1 read
 saving the summary                         200        175 bytes in 1 read
 patching the summary                       200    200,763 bytes in 1 read
 the interview answers                      200    100,608 bytes in 1 read
 readiness for a table of contents          200        509 bytes in 1 read
 the table of contents                      200    302,359 bytes in 1 read
 the chapters' metadata                     200    302,359 bytes in 1 read
 enhancing text, refused for having none    400    302,359 bytes in 1 read
 saving the interview answers               200        175 bytes in 1 read
 cleaning up a transcription, refused for having none 400    302,359 bytes in 1 read
 deleting the book                          204        360 bytes in 2 reads
 one chapter's content                      200    701,282 bytes in 1 read
 several chapters' content                  200    701,282 bytes in 1 read
 a save refused as out of date              409  1,003,610 bytes in 2 reads
1 passed
```

## Tests

The new tests: the same measurement with a limit for each route, two more for draft generation and the cover upload, and one that the routes answer what they answered before. Then every existing test of the book, chapter, summary, table of contents and export routes.

```bash
cd /home/frankbria/projects/worktrees/issue-829-projected-book-reads/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo829 uv run pytest -p no:cacheprovider --no-cov tests/test_api/test_routes/test_book_reads_are_projected.py -v 2>&1 | grep -E 'PASSED|FAILED|passed|failed' | sed 's/^tests.test_api.test_routes.test_book_reads_are_projected.py:://' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
test_the_read_brings_back_no_more_than_the_route_uses[the book] PASSED
test_the_read_brings_back_no_more_than_the_route_uses[the summary] PASSED
test_the_read_brings_back_no_more_than_the_route_uses[saving the summary] PASSED
test_the_read_brings_back_no_more_than_the_route_uses[patching the summary] PASSED
test_the_read_brings_back_no_more_than_the_route_uses[the interview answers] PASSED
test_the_read_brings_back_no_more_than_the_route_uses[readiness for a table of contents] PASSED
test_the_read_brings_back_no_more_than_the_route_uses[the table of contents] PASSED
test_the_read_brings_back_no_more_than_the_route_uses[the chapters' metadata] PASSED
test_the_read_brings_back_no_more_than_the_route_uses[enhancing text, refused for having none] PASSED
test_the_read_brings_back_no_more_than_the_route_uses[saving the interview answers] PASSED
test_the_read_brings_back_no_more_than_the_route_uses[cleaning up a transcription, refused for having none] PASSED
test_the_read_brings_back_no_more_than_the_route_uses[deleting the book] PASSED
test_the_read_brings_back_no_more_than_the_route_uses[one chapter's content] PASSED
test_the_read_brings_back_no_more_than_the_route_uses[several chapters' content] PASSED
test_the_read_brings_back_no_more_than_the_route_uses[a save refused as out of date] PASSED
test_generating_a_draft_reads_no_bodies PASSED
test_uploading_a_cover_reads_the_owner_and_the_cover_it_replaces PASSED
test_one_measurement_does_not_count_the_one_before PASSED
test_the_book_in_these_tests_is_as_large_as_they_say PASSED
test_what_the_routes_answer_is_what_they_answered_before PASSED
20 passed
```

```bash
cd /home/frankbria/projects/worktrees/issue-829-projected-book-reads/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo829 uv run pytest -p no:cacheprovider --no-cov tests/test_api -q 2>&1 | tail -1 | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
990 passed, 6 skipped (0:02:33)
```
