# Demo — #280: Legacy export page surfaces the backend's `userMessage`

**PR:** #326 · **Type:** frontend-only · **Method:** main-vs-branch differential against the real `ExportBookPage` component.

## What was broken

`frontend/src/app/dashboard/books/[bookId]/export/page.tsx`'s `handleExport`
catch showed a generic `"Failed to export book. Please try again."` toast for
every failure, discarding the `userMessage` (backend `detail` — e.g. a 504
timeout or 503 exporter-unavailable message) that `bookClient.exportError`
already attaches to the thrown error.

## Acceptance criteria → outcome evidence

Both runs render the **real** page component and assert the actual toast title a
user would see. The only variable is the catch block.

### AC1 — surface `userMessage` when present, fall back otherwise

Same rejected export carrying `{ statusCode: 504, userMessage: 'The export timed
out. Please try again shortly.' }`:

| | toast the user sees |
|---|---|
| **main** (generic-only catch) | `Failed to export book. Please try again.` — userMessage discarded ❌ |
| **branch** (this PR) | `The export timed out. Please try again shortly.` — backend message surfaced ✅ |

Fallback clause — an error with **no** `userMessage` (`new Error('boom')`):
generic copy on **both** main and branch ✅ (the fix never regresses the
no-message path).

Differential run output:

```
>>> MAIN behavior (generic-only catch): userMessage DISCARDED
    ✕ surfaces the backend's userMessage when the export fails
    ✓ falls back to the generic message when no userMessage is present

>>> BRANCH behavior (this PR): userMessage SURFACED
    ✓ surfaces the backend's userMessage when the export fails
    ✓ falls back to the generic message when no userMessage is present
```

The `✕ → ✓` flip on the userMessage test **is** the mutation evidence: the
retargeted assertion is RED against main's behavior, GREEN on the branch.

### AC2 — the error-toast unit test asserts the backend-derived message

`export/__tests__/page.test.tsx` → `"surfaces the backend's userMessage when the
export fails"` asserts `toast.error` was called with the exact backend title,
not the generic copy.

## Known limitations

None — frontend-only, reuses the existing `userMessage` contract from
`bookClient.exportError`. Mirrors the ExportOptionsModal path's intent (surface
the backend's classified message) without its heavier `showErrorNotification`
retry pipeline, which a legacy one-shot toast doesn't need.
