# Issue #828: the table of contents travels without chapter bodies, and an oversize save is a 413

*2026-10-13T19:42:12Z by Showboat 0.6.1*
<!-- showboat-id: 3efd47fe-ff98-4579-a0e1-66ebf0ac2347 -->

Two acceptance criteria: the answers of `GET /toc` and `PUT /toc` carry no `content`; an oversize chapter or table of contents is answered 413, with tests.

`test_demo_828.py` is copied into `backend/tests/` of the checkout it is run in. Through the API it reads and saves the table of contents of a book with ten chapters of about fifty kilobytes each, one with a subchapter; reads one chapter from its own route; saves a 600,000-byte chapter and a 1,200,000-byte table of contents; saves a table of contents with a new chapter that carries a 600,000-byte body; and then, with the book's document filled to just under the database's sixteen megabytes, saves a chapter that would take it over.

## Before: main

The table of contents is 551 kilobytes each way, with all eleven bodies in it. The oversize chapter and the oversize table of contents are saved, and so is the body that came in with the table of contents. At the database's limit the save is answered 500.

```bash
cp /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo828/test_demo_828.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main828/backend/tests/ && cd /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main828/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo828 uv run pytest -p no:cacheprovider --no-cov tests/test_demo_828.py -s -q 2>&1 | grep -E '^  (GET|PUT|PATCH|bodies)|^=+ [0-9]+ (passed|failed)|^[0-9]+ (passed|failed)' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'; rm -f /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/main828/backend/tests/test_demo_828.py
```

```output
 GET /toc -> 200, 551,700 bytes, chapters with a body in the answer: 11 of 11
 PUT /toc -> 200, 551,736 bytes, chapters with a body in the answer: 11 of 11
 bodies still in the database after that save: 11 of 11; chapter 2 is now called 'Chapter 2, renamed'
 GET /chapters/c1a/content -> 200, 50,007 characters of body
 PATCH a 600,000-byte chapter -> 200
 PUT a 1,200,000-byte table of contents -> 200
 PUT a new chapter with a 600,000-byte body in the table of contents -> 200, bytes of it stored: 600,000
 PATCH 450,000 bytes into a book at the database's limit -> 500 An unexpected error occurred
1 passed
```

## After: this branch

The table of contents is under three kilobytes, with no body in it. Saving it erased none: all eleven are still in the database, and the rename landed. A chapter's body still comes from its own route. The oversize chapter, the oversize table of contents and the save past the database's limit are each answered 413, saying which limit and what to do. The new chapter is added and the body sent with it is not stored: a body comes in through the chapter's own route, where its size is checked.

```bash
cp /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo828/test_demo_828.py /home/frankbria/projects/worktrees/issue-828-toc-content-and-size-caps/backend/tests/ && cd /home/frankbria/projects/worktrees/issue-828-toc-content-and-size-caps/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo828 uv run pytest -p no:cacheprovider --no-cov tests/test_demo_828.py -s -q 2>&1 | grep -E '^  (GET|PUT|PATCH|bodies)|^=+ [0-9]+ (passed|failed)|^[0-9]+ (passed|failed)' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'; rm -f /home/frankbria/projects/worktrees/issue-828-toc-content-and-size-caps/backend/tests/test_demo_828.py
```

```output
 GET /toc -> 200, 1,480 bytes, chapters with a body in the answer: 0 of 11
 PUT /toc -> 200, 1,516 bytes, chapters with a body in the answer: 0 of 11
 bodies still in the database after that save: 11 of 11; chapter 2 is now called 'Chapter 2, renamed'
 GET /chapters/c1a/content -> 200, 50,007 characters of body
 PATCH a 600,000-byte chapter -> 413 This chapter is too long to save: the limit is 500,000 bytes. Split it into two chapters.
 PUT a 1,200,000-byte table of contents -> 413 The table of contents is too large to save: the limit is 1,000,000 bytes.
 PUT a new chapter with a 600,000-byte body in the table of contents -> 200, bytes of it stored: 0
 PATCH 450,000 bytes into a book at the database's limit -> 413 This book has reached the largest size it can be stored at. Shorten a chapter to save more.
1 passed
```

## Tests

The new tests by name, then the tests that were already there for the table of contents, for chapter content, and for a save keeping the bodies it was not sent.

```bash
cd /home/frankbria/projects/worktrees/issue-828-toc-content-and-size-caps/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo828 uv run pytest -p no:cacheprovider --no-cov tests/test_api/test_routes/test_toc_and_content_size.py -v 2>&1 | grep -E 'PASSED|FAILED|passed|failed' | sed 's/^tests.test_api.test_routes.test_toc_and_content_size.py:://' | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
TestTheTableOfContentsHasNoBodies::test_reading_it_returns_no_content_at_any_depth PASSED
TestTheTableOfContentsHasNoBodies::test_saving_it_returns_no_content_and_loses_none PASSED
TestTheTableOfContentsHasNoBodies::test_a_chapters_body_is_still_read_from_its_own_route PASSED
TestABodyDoesNotComeInThroughTheTableOfContents::test_content_sent_with_a_new_chapter_is_not_stored PASSED
TestABodyDoesNotComeInThroughTheTableOfContents::test_content_sent_for_a_chapter_that_has_a_body_does_not_replace_it PASSED
TestAChapterHasALargestSize::test_content_over_the_limit_is_refused_and_what_was_there_is_kept PASSED
TestAChapterHasALargestSize::test_content_at_the_limit_is_saved PASSED
TestAChapterHasALargestSize::test_the_limit_is_in_bytes_which_is_what_the_database_counts PASSED
TestABookAtTheDatabasesLimit::test_a_save_that_would_cross_it_is_refused_as_too_large PASSED
TestABookAtTheDatabasesLimit::test_a_small_save_to_the_same_book_still_lands PASSED
TestABookAtTheDatabasesLimit::test_so_is_a_table_of_contents_that_would_cross_it PASSED
TestATableOfContentsBodyHasALargestSize::test_one_over_the_limit_is_refused_and_what_was_there_is_kept PASSED
TestATableOfContentsBodyHasALargestSize::test_an_ordinary_one_is_saved PASSED
TestATableOfContentsBodyHasALargestSize::test_text_that_is_not_ascii_is_counted_as_the_bytes_it_is PASSED
TestOnlyTheSizeRefusalIsCalledAFullBook::test_another_database_error_is_left_as_it_is PASSED
TestOnlyTheSizeRefusalIsCalledAFullBook::test_both_ways_the_database_says_it PASSED
16 passed
```

```bash
cd /home/frankbria/projects/worktrees/issue-828-toc-content-and-size-caps/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo828 uv run pytest -p no:cacheprovider --no-cov tests/test_api/test_routes/test_books_toc_coverage.py tests/test_api/test_routes/test_books_chapter_content_coverage.py tests/test_db/test_toc_preserves_chapter_fields.py tests/test_api/test_routes/test_toc_unique_chapter_ids.py -q 2>&1 | tail -1 | sed -e 's/ *\[ *[0-9]*%\]//' -e 's/^=* //' -e 's/ =*$//' -e 's/, [0-9]* warnings//' -e 's/ in [0-9.]*s//'
```

```output
88 passed
```
