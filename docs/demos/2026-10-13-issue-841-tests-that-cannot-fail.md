# Issue #841: four backend tests that could not fail can

*2026-10-14T04:12:37Z by Showboat 0.6.1*
<!-- showboat-id: 0eacf233-0a92-44c8-b440-b875f2e97f05 -->

Four acceptance criteria: the skip is dropped from the mocked workflow test; the anchored `^\s*pass\s*$` pattern replaces the bare one, with a guard test; the swallowing script is deleted; the export assertions use text extraction, not compressed bytes.

Each is shown on main first, then on this branch. Main's files are read from the commit this branch started from.

## 1. The coverage pattern

Coverage itself is asked which lines of `app/core/config.py` it leaves out of the count, under main's `.coveragerc` and then under this branch's. The bare `pass` matched "bypass", and a matching `def` takes its whole body with it.

```bash
cd /home/frankbria/projects/worktrees/issue-841-tests-that-cannot-fail/backend && git show 0e256887:backend/.coveragerc > /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo841/coveragerc-main && ENVIRONMENT=test uv run python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo841/left_out.py /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo841/coveragerc-main main && ENVIRONMENT=test uv run python /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo841/left_out.py .coveragerc 'this branch'
```

```output
main: 35 lines of config.py left out; 29 of them in the BYPASS_AUTH validator (lines 395 to 423)
this branch: 0 lines of config.py left out; 0 of them in the BYPASS_AUTH validator
```

```bash
cd /home/frankbria/projects/worktrees/issue-841-tests-that-cannot-fail/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo841 uv run pytest tests/test_coverage_config.py -p no:cacheprovider --no-cov -q -rA 2>&1 | grep -E '^PASSED|passed|failed' | sed -e 's#tests/test_coverage_config.py::##' -e 's/^=* //' -e 's/ in [0-9.]*s.*//'
```

```output
PASSED test_no_line_about_the_auth_bypass_is_left_out
PASSED test_the_bypass_validator_is_measured
PASSED test_a_line_that_says_only_pass_is_still_left_out
3 passed
```

## 2. The script that swallowed its own failures

Main's `tests/test_file_upload_service.py`, run as pytest runs it, unchanged. Four of its five checks fail before reaching the service at all (`UploadFile` no longer takes `content_type`); each failure is caught and printed, and the test passes. On this branch the file is gone; the real tests are in `tests/test_services/test_file_upload_service.py`.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo841/swallow.sh /home/frankbria/projects/worktrees/issue-841-tests-that-cannot-fail 0e256887
```

```output
  ❌ Valid image test failed: UploadFile.__init__() got an unexpected keyword argument 'content_type'
  ❌ Invalid file type test failed: UploadFile.__init__() got an unexpected keyword argument 'content_type'
  ❌ File size test failed: UploadFile.__init__() got an unexpected keyword argument 'content_type'
  ❌ Image processing test failed: UploadFile.__init__() got an unexpected keyword argument 'content_type'
  ✅ Statistics test passed
1 passed
(the copy is removed)
```

```bash
cd /home/frankbria/projects/worktrees/issue-841-tests-that-cannot-fail/backend && ls tests/test_file_upload_service.py 2>&1 | sed 's/^ls: //'; ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo841 uv run pytest tests/test_services/test_file_upload_service.py -p no:cacheprovider --no-cov -q 2>&1 | tail -1 | sed -e 's/^=* //' -e 's/ in [0-9.]*s.*//' -e 's/^/tests\/test_services\/test_file_upload_service.py: /'
```

```output
cannot access 'tests/test_file_upload_service.py': No such file or directory
tests/test_services/test_file_upload_service.py: 20 passed
```

## 3. The workflow test that was skipped

With no `OPENAI_API_KEY` in the environment, as in CI. Main's version of the test is skipped. This branch's runs, and it stands in for the provider for every call it does not stub by name: un-skipped, it was found to draft its chapter through the real provider, and it failed in the full suite.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo841/workflow.sh /home/frankbria/projects/worktrees/issue-841-tests-that-cannot-fail 0e256887
```

```output
main:        SKIPPED [1] Requires OpenAI API key - skipping in CI/CD without key
this branch: PASSED test_complete_system_workflow
```

## 4. The export checks

`mutate841.py` makes the export keep empty chapters even when told not to, and runs this branch's export tests and then main's. Main's EPUB and PDF checks looked for the empty chapter's title in compressed bytes, where it is never found, and pass. This branch's unpack the EPUB and decode the PDF's page streams, and fail. The second mutation is the coverage pattern put back.

```bash
python3 /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/mutate841.py /home/frankbria/projects/worktrees/issue-841-tests-that-cannot-fail 0e256887
```

```output
baseline -> 60 passed
export keeps empty chapters even when told not to -> this branch's tests: 4 failed, 56 passed (test_export_book_epub, test_export_book_markdown, test_export_exclude_empty_chapters, test_export_empty_chapters_rejected_unless_included)
export keeps empty chapters even when told not to -> main's export tests: 2 failed, 55 passed (test_export_book_markdown, test_export_empty_chapters_rejected_unless_included)
the coverage pattern is the bare `pass` again -> this branch's tests: 2 failed, 58 passed (test_no_line_about_the_auth_bypass_is_left_out, test_the_bypass_validator_is_measured)
mutations done
```
