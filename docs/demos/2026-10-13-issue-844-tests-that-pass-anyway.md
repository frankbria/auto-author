# Issue #844: sanitizing AI output is tested, unexpected requests fail, placeholder specs are gone

*2026-10-14T05:03:42Z by Showboat 0.6.1*
<!-- showboat-id: f4bc2b07-e4ad-4405-8660-6c39be1ce257 -->

Three acceptance criteria: a hostile-payload test per renderer fails under the sanitize-removal mutation; the default fetch mock rejects unexpected calls; no assertion-free or body-only `test.skip()` specs remain.

## 1. Five renderers without DOMPurify

`DOMPurify.sanitize` is taken out of all five components that put AI output into the page as HTML. The tests those components had before this change all pass that way. The new test, which sends each the same hostile payload (a script, an `onerror` handler, a `javascript:` link, and a sentence worth keeping), fails for all five.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo844/unsanitized_old_tests.sh /home/frankbria/projects/worktrees/issue-844-tests-that-pass-anyway
```

```output
DOMPurify.sanitize calls left in the five renderers: 0
the tests the renderers had before #844: Tests: 51 passed, 51 total
AIOutputIsSanitized.test.tsx: Tests: 5 failed, 5 total
the renderers are as they were
```

One component at a time, each failing only its own case:

```bash
python3 /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/mutate844.py /home/frankbria/projects/worktrees/issue-844-tests-that-pass-anyway
```

```output
baseline -> 0 failed, 5 passed
StyleTransformer renders unsanitized (2 calls removed) -> 1 failed, 0 passed (StyleTransformer)
ContentEnhancer renders unsanitized (2 calls removed) -> 1 failed, 0 passed (ContentEnhancer)
VoiceEnhancer renders unsanitized (2 calls removed) -> 1 failed, 0 passed (VoiceEnhancer)
DraftGenerator renders unsanitized (1 call removed) -> 1 failed, 0 passed (DraftGenerator)
DraftGenerationButton renders unsanitized (1 call removed) -> 1 failed, 0 passed (DraftGenerationButton)
mutations done
```

## 2. A request nothing stands in for

A test that fetches a URL nobody stood in for and swallows whatever comes back. Under main's setup the global stand-in answers `200 {}` and the test passes. Under this branch's the request is refused and the test fails afterwards, swallowed or not.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo844/fetch.sh /home/frankbria/projects/auto-author/frontend main; bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo844/fetch.sh /home/frankbria/projects/worktrees/issue-844-tests-that-pass-anyway/frontend 'this branch'
```

```output
main: Tests: 1 passed, 1 total 
this branch:  Requests nothing stands in for (#844): http://localhost:8000/api/v1/books/someone-elses-book  > 52 | throw new Error(`Requests nothing stands in for (#844): ${made.join(', ')}`); Tests: 1 failed, 1 total 
```

## 3. Skipped specs

Main, then this branch. What is left is two `test.skip` calls with a condition, which skip a flaky webkit route-mock and run on chromium, the browser CI gates on. The skipped protected-route test was turned back on: it passes.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo844/skips.sh /home/frankbria/projects/auto-author/frontend main; bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo844/skips.sh /home/frankbria/projects/worktrees/issue-844-tests-that-pass-anyway/frontend 'this branch'
```

```output
main: skipped with a title 8, test.skip() in a body 3, skipped on a condition (webkit) 2
this branch: skipped with a title 0, test.skip() in a body 0, skipped on a condition (webkit) 2
```
