# Issue #853: unimported frontend modules, inert mocks and orphaned Playwright suites are gone

*2026-10-14T23:29:24Z by Showboat 0.6.1*
<!-- showboat-id: 7931d336-c17e-41f9-a791-b38b45c8ea31 -->

`$DEMO/check.sh` reads one checkout's frontend. For each module this issue removes, it reports whether the file exists, and how many shipped (non-test, non-Markdown) files and test files import or mock it. Then whether date-fns is a dependency, and how many Playwright specs sit under tests/e2e outside the staging suite, next to the testDir of each Playwright config.

main:

```bash
"$DEMO/check.sh" "$MAIN"
```

```output
ChapterQuestions       file: yes imported by shipped code: 0  by tests: 2
DataRecoveryModal      file: yes imported by shipped code: 0  by tests: 1
use-toast              file: yes imported by shipped code: 0  by tests: 8
chapter-content-cache  file: yes imported by shipped code: 0  by tests: 0
form-components        file: yes imported by shipped code: 0  by tests: 0
styled-avatar          file: yes imported by shipped code: 0  by tests: 0
date-fns in package.json: 1
spec files under tests/e2e outside staging: 8
Playwright testDirs: testDir: './src/e2e' testDir: './src/e2e/real-auth' testDir: '.' 
```

this branch:

```bash
"$DEMO/check.sh" "$PWD"
```

```output
ChapterQuestions       file: no  imported by shipped code: 0  by tests: 0
DataRecoveryModal      file: no  imported by shipped code: 0  by tests: 0
use-toast              file: no  imported by shipped code: 0  by tests: 0
chapter-content-cache  file: no  imported by shipped code: 0  by tests: 0
form-components        file: no  imported by shipped code: 0  by tests: 0
styled-avatar          file: no  imported by shipped code: 0  by tests: 0
date-fns in package.json: 0
spec files under tests/e2e outside staging: 0
Playwright testDirs: testDir: './src/e2e' testDir: './src/e2e/real-auth' testDir: '.' 
```

On main nothing shipped imported any of the six. Their only importers were tests, and use-toast's were jest.mock blocks for a module nothing those tests rendered used. The 8 specs under tests/e2e sat outside every config's testDir: ./src/e2e, ./src/e2e/real-auth, and . for tests/e2e/staging's own config. The full jest suite passes on this branch (3158 tests) with coverage above every threshold, after the busy-button guard's floor dropped by the one busy button that left with DataRecoveryModal.
