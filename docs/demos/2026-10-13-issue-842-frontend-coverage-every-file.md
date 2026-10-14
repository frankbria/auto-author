# Issue #842: frontend coverage counts every source file

*2026-10-14T04:36:56Z by Showboat 0.6.1*
<!-- showboat-id: edb3c9d3-ec02-4829-a656-d051169d9800 -->

Two acceptance criteria: `collectCoverageFrom` is set; the thresholds hold, or are re-baselined with the real number.

`coverage.sh` runs the frontend tests with the coverage gate exactly as CI does (`--coverageThreshold` lines 85, statements 85, branches 75, functions 85), in the checkout it is given, writing its summary to a scratch directory. It prints the totals, how many files were counted, and the gate's verdict.

## Before: main

173 files counted: only those a test happened to import.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo842/coverage.sh /home/frankbria/projects/auto-author/frontend main
```

```output
Statements   : 90.72% ( 6066/6686 )
Branches     : 83.98% ( 3439/4095 )
Functions    : 89.07% ( 1182/1327 )
Lines        : 91.76% ( 5704/6216 )
files counted: 173
Tests: 4 skipped, 3191 passed, 3195 total
the gate: passed
```

## Every file, with nothing removed

This branch's `collectCoverageFrom`, on main's files. Functions fall to 84.35%, under the gate: the files no test imports have 75 functions and none of them is run.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo842/coverage.sh /home/frankbria/projects/auto-author/frontend all-files 'src/**/*.{ts,tsx}' '!src/**/*.d.ts' '!src/**/__tests__/**' '!src/**/*.{test,spec}.{ts,tsx}' '!src/__mocks__/**' '!src/e2e/**' '!src/jest.setup.ts'
```

```output
Statements   : 87.07% ( 6061/6961 )
Branches     : 81.95% ( 3439/4196 )
Functions    : 84.35% ( 1181/1400 )
Lines        : 87.99% ( 5700/6478 )
files counted: 192
Tests: 4 skipped, 3191 passed, 3195 total
the gate: FAILED
```

```bash
python3 /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo842/newly_counted.py main all-files
```

```output
20 files counted that were not: 267 lines, 75 functions, 0 of them run
    68 lines   8 functions  src/components/examples/ai-error-handling-example.tsx
    25 lines   3 functions  src/app/api/auth/[...all]/route.ts
    24 lines   6 functions  src/types/api.ts
    20 lines   7 functions  src/app/dashboard/books/[bookId]/chapters/[chapterId]/page.tsx
    16 lines   8 functions  src/lib/api/chapter-tabs-old.ts
    15 lines  11 functions  src/components/ui/alert-dialog.tsx
    15 lines  10 functions  src/components/ui/select.tsx
    13 lines   5 functions  src/components/ui/form-components.tsx
    13 lines   1 functions  src/app/layout.tsx
    12 lines   2 functions  src/components/ui/use-toast.ts
    11 lines   3 functions  src/lib/cache/chapter-content-cache.ts
     9 lines   1 functions  src/components/ui/styled-avatar.tsx
     7 lines   2 functions  src/components/performance/WebVitalsInit.tsx
     7 lines   1 functions  src/components/ui/sonner.tsx
     4 lines   1 functions  src/app/dashboard/books/[bookId]/generate-toc/page.tsx
     3 lines   2 functions  src/components/ui/refresh-button.tsx
     2 lines   1 functions  src/app/dashboard/not-found.tsx
     1 lines   1 functions  src/components/toc/ReadinessChecker.tsx
     1 lines   1 functions  src/components/chapters/ChapterPreview.tsx
     1 lines   1 functions  src/app/auth/layout.tsx
```

## After: this branch

The two of those files that nothing imports and #853 names for removal are gone: the AI error-handling example component and `lib/api/chapter-tabs-old.ts`. Every threshold holds as it was; none is lowered.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo842/coverage.sh /home/frankbria/projects/worktrees/issue-842-frontend-coverage-from/frontend branch
```

```output
Statements   : 88.13% ( 6060/6876 )
Branches     : 82.83% ( 3445/4159 )
Functions    : 85.33% ( 1181/1384 )
Lines        : 89.14% ( 5700/6394 )
files counted: 190
Tests: 4 skipped, 3189 passed, 3193 total
the gate: passed
```
