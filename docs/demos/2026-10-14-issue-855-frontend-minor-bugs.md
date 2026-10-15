# Issue #855: frontend minor bugs

*2026-10-15T01:48:29Z by Showboat 0.6.1*
<!-- showboat-id: fed57553-2be9-4339-8b67-2a5b0b5b8085 -->

Both #855 tests run inside the whole editor-formatting spec. The stale count shows reliably when the other tests run first, and a run of only the two can miss it.

main:

```bash
cd "$MAIN855/frontend" && npx playwright test src/e2e/editor-formatting.spec.ts --project=chromium --reporter=line 2>&1 | grep -oE "^ +[0-9]+ (passed|failed)|Received: \"[0-9]+ characters\"|\[tiptap warn\]: Duplicate extension names found[^.]*" | sort -u
```

```output
  2 failed
  4 passed
Received: "1 characters"
[tiptap warn]: Duplicate extension names found: ['underline']
```

this branch:

```bash
cd frontend && npx playwright test src/e2e/editor-formatting.spec.ts --project=chromium --reporter=line 2>&1 | grep -oE "^ +[0-9]+ (passed|failed)|Received: \"[0-9]+ characters\"|\[tiptap warn\]: Duplicate extension names found[^.]*" | sort -u
```

```output
  6 passed
```

The other fixes are proven in jest, each by a test that failed first and by a mutation check that undid each fix in turn and saw a named test fail (14 of 14): the stray 0 in the TOC review; one tab save per change; the reset-password and dashboard redirect timers cleared on unmount; the autosave backoff, its 30s cap, its reset after any save that works, and the backup kept current while it backs off; no Retry after a refusal a retry cannot change; a retry on the rewrite dialogs' rate-limit notice; and account deletion clearing the user's writing from the browser.
