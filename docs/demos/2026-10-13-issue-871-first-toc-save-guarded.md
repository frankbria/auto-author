# Issue #871: the first save of a book's TOC is guarded like every later one

*2026-10-14T06:08:47Z by Showboat 0.6.1*
<!-- showboat-id: 307b5978-5571-413c-8e61-e55d37d8bbcf -->

Three parts to the definition of done: GET and PUT agree on the version of a book with no TOC; the Edit TOC page and the wizard always send `expected_version`; a real-Mongo test where two first saves with the same expected version end in one 409.

`test_demo_871.py` is copied into `backend/tests/` of the checkout it is run in, against a real MongoDB. It reads a TOC-less book through the API and saves twice from that one read. Then two first saves of another book are made to both read the book before either writes, which is the race the version exists for.

## Before: main

GET says 0. Sending that back makes the first save a 409, which is why the Edit TOC page sent nothing on a first save. And when both writers read before either writes, both land: the second silently replaces the first.

```bash
cp /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo871/test_demo_871.py /home/frankbria/projects/worktrees/main871/backend/tests/ && cd /home/frankbria/projects/worktrees/main871/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo871 uv run pytest -p no:cacheprovider --no-cov -q -s tests/test_demo_871.py 2>&1 | grep -E '^  |passed|failed' | sed -e 's/^=* //' -e 's/ in [0-9.]*s.*//'; rm -f /home/frankbria/projects/worktrees/main871/backend/tests/test_demo_871.py
```

```output
 GET /toc on a book with no TOC: status 'not_generated', version 0
 first save, sending that version back: 409
 a second save from the same read: 409
 two first saves that both read before either writes: 2 landed, 0 refused; stored version 2, chapter 'From the first tab'
1 passed
```

## After: this branch

GET says 1, the first save with it lands, the second from the same read is a 409. Of two racing first saves, one lands.

```bash
cp /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo871/test_demo_871.py /home/frankbria/projects/worktrees/issue-871-first-toc-save-guarded/backend/tests/ && cd /home/frankbria/projects/worktrees/issue-871-first-toc-save-guarded/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo871 uv run pytest -p no:cacheprovider --no-cov -q -s tests/test_demo_871.py 2>&1 | grep -E '^  |passed|failed' | sed -e 's/^=* //' -e 's/ in [0-9.]*s.*//'; rm -f /home/frankbria/projects/worktrees/issue-871-first-toc-save-guarded/backend/tests/test_demo_871.py
```

```output
 GET /toc on a book with no TOC: status 'not_generated', version 1
 first save, sending that version back: 200
 a second save from the same read: 409
 two first saves that both read before either writes: 1 landed, 1 refused; stored version 2, chapter 'From the second tab'
1 passed
```

## The clients

The wizard already sent `base_version`, which generate-toc computes as PUT does. The Edit TOC page now sends the version it read on every save, the first included.

```bash
cd /home/frankbria/projects/worktrees/issue-871-first-toc-save-guarded && grep -n 'setTocVersion(response' 'frontend/src/app/dashboard/books/[bookId]/edit-toc/page.tsx'; grep -n 'expected_version: wizardState' frontend/src/components/toc/TocGenerationWizard.tsx; grep -n 'base_version = ' backend/app/api/endpoints/books.py
```

```output
173:        setTocVersion(response.version);
196:        expected_version: wizardState.generatedToc.base_version,
1134:        base_version = stored_toc.get("version", 1)
```

## Tests

```bash
cd /home/frankbria/projects/worktrees/issue-871-first-toc-save-guarded/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo871 uv run pytest tests/test_db/test_first_toc_save_guarded.py -p no:cacheprovider --no-cov -q -rA 2>&1 | grep -E '^PASSED|passed|failed' | sed -e 's#tests/test_db/test_first_toc_save_guarded.py::##' -e 's/^=* //' -e 's/ in [0-9.]*s.*//'; cd ../frontend && npx jest 'src/app/dashboard/books/\[bookId\]/__tests__/edit-toc' --coverage=false -t 'first save' --verbose 2>&1 | grep -E '✓|✕|Tests:' | sed 's/  */ /g'
```

```output
PASSED test_two_first_saves_that_both_read_before_either_writes_do_not_both_land
PASSED test_a_second_first_save_with_the_same_expected_version_is_a_conflict
PASSED test_get_and_put_agree_on_the_version_of_a_book_with_no_toc
3 passed
Tests: 9 skipped, 1 passed, 10 total
```
