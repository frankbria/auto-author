# Issue #201: CI-runnable core authoring journey E2E (un-skip journey/autosave/error-recovery)

*2026-07-13T17:23:46Z*

Issue #201: the core authoring journey — auto-save, retry-with-backoff, and the end-to-end book→TOC→questions→draft flow, all listed Production Ready — had zero executing E2E coverage. The journey spec was test.skip (needed a live OpenAI key), the autosave/error-recovery suites were describe.skip ("NEEDS TEST IDS"), and interview-prompts carried a stale "NOT IMPLEMENTED" banner for a feature that shipped in #105/#110. This demo runs the real Playwright suites against a real backend + local MongoDB, exactly like the CI e2e job (BYPASS_AUTH=true, chromium, no OpenAI key). First, proof that CI genuinely has no OpenAI key — the workflow never sets one:

```bash
grep -ci "openai" /home/frankbria/projects/auto-author/.github/workflows/tests.yml || echo "0 OPENAI references in the CI workflow"
```

```output
0
0 OPENAI references in the CI workflow
```

THE PROBLEM ON MAIN. Restore the four spec files exactly as they exist on main and run them: every one of them is skipped — Playwright executes zero tests from the entire core-journey surface.

```bash
git -C /home/frankbria/projects/auto-author checkout main -- frontend/src/e2e/complete-authoring-journey.spec.ts frontend/src/e2e/editing-autosave-flow.spec.ts frontend/src/e2e/error-recovery-flow.spec.ts frontend/src/e2e/interview-prompts.spec.ts && grep -n 'test.skip\|describe.skip' /home/frankbria/projects/auto-author/frontend/src/e2e/complete-authoring-journey.spec.ts /home/frankbria/projects/auto-author/frontend/src/e2e/editing-autosave-flow.spec.ts /home/frankbria/projects/auto-author/frontend/src/e2e/error-recovery-flow.spec.ts /home/frankbria/projects/auto-author/frontend/src/e2e/interview-prompts.spec.ts | sed "s|/home/frankbria/projects/auto-author/||" | head -8
```

```output
frontend/src/e2e/complete-authoring-journey.spec.ts:57:  test.skip('user can create book, generate TOC, add chapters, answer questions, and generate draft', async ({ page }) => {
frontend/src/e2e/complete-authoring-journey.spec.ts:462:    test.skip();
frontend/src/e2e/complete-authoring-journey.spec.ts:468:    test.skip();
frontend/src/e2e/editing-autosave-flow.spec.ts:135:test.describe.skip('Editing & Auto-save Flow (NEEDS TEST IDS)', () => {
frontend/src/e2e/error-recovery-flow.spec.ts:137:test.describe.skip('Error Recovery Flow - Automatic Retry with Exponential Backoff (NEEDS TEST IDS)', () => {
frontend/src/e2e/interview-prompts.spec.ts:20:test.describe.skip('Interview-Style Prompts Cross-Browser Tests (NOT IMPLEMENTED)', () => {
frontend/src/e2e/interview-prompts.spec.ts:106:      test.skip('This test is only for mobile devices');
```

```bash
cd /home/frankbria/projects/auto-author/frontend && npx playwright test complete-authoring-journey editing-autosave-flow error-recovery-flow interview-prompts --project=chromium --reporter=line 2>&1 | grep -E "passed|skipped|failed" | sed -E "s/ \([0-9.]+m?s\)//" | tail -2
```

```output
[1A[2K  26 skipped
```

26 tests collected, 26 skipped, zero executed. That is the entire E2E coverage of the core authoring journey on main. THE BRANCH: restore this branch's specs (interview-prompts is deleted — its "NOT IMPLEMENTED" premise has been false since #105/#110 and real questions coverage lives in chapter-questions-tabs.spec.ts) and run the same command:

```bash
git -C /home/frankbria/projects/auto-author reset -q HEAD -- frontend/src/e2e/ && git -C /home/frankbria/projects/auto-author checkout HEAD -- frontend/src/e2e/ && rm -f /home/frankbria/projects/auto-author/frontend/src/e2e/interview-prompts.spec.ts && ls /home/frankbria/projects/auto-author/frontend/src/e2e/interview-prompts.spec.ts 2>&1 | tail -1; cd /home/frankbria/projects/auto-author/frontend && npx playwright test complete-authoring-journey editing-autosave-flow error-recovery-flow --project=chromium --reporter=line 2>&1 | grep -E 'passed|skipped|failed' | sed -E 's/ \([0-9.]+m?s\)//' | tail -2
```

```output
ls: cannot access '/home/frankbria/projects/auto-author/frontend/src/e2e/interview-prompts.spec.ts': No such file or directory
[1A[2K[10/10] [chromium] › src/e2e/error-recovery-flow.spec.ts:137:9 › Error Recovery Flow › question-response save (retry with backoff) › failed save retries exactly 3 times with backoff, then manual Retry recovers
[1A[2K  10 passed
```

10 executing tests, 10 passed, against a real backend and real MongoDB with no OpenAI key — the AI endpoints are page.route-mocked, everything deterministic (book create, summary save, the wizard Accept's PUT /toc, chapter content autosave) hits the real API, and the journey re-reads the persisted TOC and draft from the backend rather than trusting the DOM. WOULD THEY CATCH A REGRESSION? Mutation 1: break the retry budget — QuestionDisplay's ErrorHandler maxRetries 3→1. The retry-with-backoff test must go RED naming the exact contract:

```bash
sed -i 's/maxRetries: 3,/maxRetries: 1,/' /home/frankbria/projects/auto-author/frontend/src/components/chapters/questions/QuestionDisplay.tsx && cd /home/frankbria/projects/auto-author/frontend && npx playwright test error-recovery-flow --project=chromium --reporter=line -g 'retries exactly 3 times' 2>&1 | grep -E 'passed|failed|Expected|Received' | sed -E 's/ \([0-9.]+m?s\)//' | head -4; git -C /home/frankbria/projects/auto-author checkout -- frontend/src/components/chapters/questions/QuestionDisplay.tsx && echo '--- mutation reverted ---'
```

```output
[1A[2K[1/1] [chromium] › src/e2e/error-recovery-flow.spec.ts:137:9 › Error Recovery Flow › question-response save (retry with backoff) › failed save retries exactly 3 times with backoff, then manual Retry recovers
[1A[2K  1) [chromium] › src/e2e/error-recovery-flow.spec.ts:137:9 › Error Recovery Flow › question-response save (retry with backoff) › failed save retries exactly 3 times with backoff, then manual Retry recovers 
    Expected: [32m3[39m
    Received: [31m1[39m
--- mutation reverted ---
```

RED: "Expected: 3, Received: 1" — the test counts actual wire requests, so a broken retry budget fails by number. Mutation 2: silently drop persistence — make the TOC wizard's Accept skip the real PUT /toc (the UI still navigates as if it saved). The journey's backend re-read must catch the lie:

```bash
sed -i 's|await bookClient.updateToc(bookId, wizardState.generatedToc.toc);|/* mutation: skip persist */|' /home/frankbria/projects/auto-author/frontend/src/components/toc/TocGenerationWizard.tsx && cd /home/frankbria/projects/auto-author/frontend && npx playwright test complete-authoring-journey --project=chromium --reporter=line 2>&1 | grep -E 'passed|failed|Expected|Received|toEqual' | sed -E 's/ \([0-9.]+m?s\)//' | head -5; git -C /home/frankbria/projects/auto-author checkout -- frontend/src/components/toc/TocGenerationWizard.tsx && echo '--- mutation reverted ---'
```

```output
    Error: [2mexpect([22m[31mreceived[39m[2m).[22mtoEqual[2m([22m[32mexpected[39m[2m) // deep equality[22m
    [32m- Expected  - 5[39m
    [31m+ Received  + 1[39m
    > 312 |       expect(titles).toEqual(TOC_CHAPTERS.map((c) => c.title));
    test-results/complete-authoring-journey-1feef-d-an-AI-draft-in-the-editor-chromium/test-failed-1.png
--- mutation reverted ---
```

RED: the journey re-reads GET /books/{id}/toc after Accept and the deep-equality on chapter titles fails — a wizard that only pretends to save cannot pass. Mutation 3: break the localStorage backup path — write the network-failure backup under the wrong key. The autosave failure test must go RED:

```bash
sed -i 's/const backupKey = `chapter-backup-${bookId}-${chapterId}`;/const backupKey = `chapter-bak-${bookId}-${chapterId}`;/' /home/frankbria/projects/auto-author/frontend/src/components/chapters/ChapterEditor.tsx && cd /home/frankbria/projects/auto-author/frontend && npx playwright test editing-autosave-flow --project=chromium --reporter=line -g 'failed auto-save' 2>&1 | grep -E 'passed|failed|not.toBeNull|Received' | sed -E 's/ \([0-9.]+m?s\)//' | head -4; git -C /home/frankbria/projects/auto-author checkout -- frontend/src/components/chapters/ChapterEditor.tsx && echo '--- mutation reverted ---'
```

```output
[1A[2K[1/1] [chromium] › src/e2e/editing-autosave-flow.spec.ts:119:7 › Editing & Auto-save Flow › failed auto-save shows an error and backs content up to localStorage
[1A[2K  1) [chromium] › src/e2e/editing-autosave-flow.spec.ts:119:7 › Editing & Auto-save Flow › failed auto-save shows an error and backs content up to localStorage 
    Received: [31mnull[39m
    > 129 |     expect(backup).not.toBeNull();
--- mutation reverted ---
```

RED: the backup lands under the wrong key and the localStorage assertion fails. All three mutations reverted — final state check: no skip markers remain in the three suites, the new save-status testid is in place, and the working tree is clean:

```bash
grep -c 'test.skip\|describe.skip' /home/frankbria/projects/auto-author/frontend/src/e2e/complete-authoring-journey.spec.ts /home/frankbria/projects/auto-author/frontend/src/e2e/editing-autosave-flow.spec.ts /home/frankbria/projects/auto-author/frontend/src/e2e/error-recovery-flow.spec.ts | sed "s|/home/frankbria/projects/auto-author/||"; grep -n 'data-testid="save-status-indicator"' /home/frankbria/projects/auto-author/frontend/src/components/chapters/ChapterEditor.tsx | sed "s|/home/frankbria/projects/auto-author/||"; git -C /home/frankbria/projects/auto-author status -s -- frontend/src | wc -l
```

```output
frontend/src/e2e/complete-authoring-journey.spec.ts:0
frontend/src/e2e/editing-autosave-flow.spec.ts:0
frontend/src/e2e/error-recovery-flow.spec.ts:0
800:            data-testid="save-status-indicator"
0
```

Acceptance criteria → evidence: (AC1) the full-journey spec executes and passes with zero OpenAI references in the CI workflow env — create book → summary → clarifying questions → TOC accept (real PUT /toc, verified by backend re-read) → interview questions → draft in the TipTap editor → draft autosaved and re-read from GET /chapters/{id}/content. (AC2) the missing data-testid (save-status-indicator + data-save-status) is added and both the autosave and error-recovery suites run un-skipped — 10 executing tests vs 0 on main — with each suite mutation-verified RED. (AC3) the stale "NOT IMPLEMENTED" interview-prompts suite is deleted. The error-recovery suite was deliberately retargeted to shipped behavior: bookClient.createBook has no retry code (plain fetch), so the old exponential-backoff-on-create premise was fiction; real retry-with-backoff lives in the question-response save path and is now pinned at exactly 3 wire attempts.
