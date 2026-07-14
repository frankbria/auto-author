# Issue #216 — [P2.15] Type-to-confirm safeguard for account deletion

**Plan source**: self-authored (no plan comment on the issue).
**Approval**: autonomous — no architectural fork. AC allows "account email or a literal
confirmation phrase"; email is chosen for consistency with `DeleteBookModal`'s
type-the-specific-thing pattern and is available from both the session and the
hydrated profile.

## Problem
`frontend/src/app/profile/page.tsx` guards the irreversible account deletion (account +
all books) with a plain Cancel/Delete dialog, while the less destructive single-book
delete requires typing the exact book title (`DeleteBookModal`).

## Design decisions (resolved, no fork)
- **Confirmation phrase = the account email**, sourced `session.user.email ?? profile.email`
  (profile email captured during the existing `getUserProfile` hydration — needed because
  route-mocked E2E has no real session). If neither is available the button stays
  disabled (fail-closed; unreachable in production where the session always has email).
- **Inline in the existing profile-page dialog** — no new shared component. Extracting a
  generic TypeToConfirmModal is YAGNI for two call sites with different copy/props.
- Mirror `DeleteBookModal` semantics: exact case-sensitive match, mismatch hint with
  `role="alert"` + `aria-invalid`, form wrapper so Enter submits when confirmed,
  input reset when the dialog opens/closes, guard in the handler
  (`if (!confirmed) return`).

## Steps (TDD)
1. **RED**: new `frontend/src/__tests__/ProfilePageDelete.test.tsx` (ProfilePageSave idiom:
   real RHF + real UI components incl. Radix Dialog + real `useProfileApi` over mocked
   `useAuthFetch`, mocked `useSession`):
   - dialog opens with Delete disabled; wrong text keeps it disabled + shows the
     mismatch alert; DELETE never sent
   - typing the exact email enables the button; click sends `DELETE /users/me` and
     `router.push('/')`
   - cancel + reopen resets the input (disabled again)
   - Enter in the input submits when confirmed
2. **GREEN**: implement in `profile/page.tsx` (state `deleteConfirmText`, `profileEmail`;
   Input + Label + hint inside the dialog; disable Delete until match; reset on
   open-change; form wrapper; handler guard).
3. E2E: extend `frontend/src/e2e/profile-editing.spec.ts` with a delete-guard test
   (route-mocked): disabled → wrong text disabled → exact email enabled → click →
   DELETE observed.
4. Verify legacy `ProfilePage.test.tsx` still green (it mocks Dialog/Input crudely but
   doesn't index inputs or assert dialog internals).
5. Deslop, lint, typecheck, full frontend suite, third-party review (opencode → codex
   fallback), PR, demo (branch vs pristine main worktree), CI, docs sync, merge.

## Acceptance criteria mapping
- "Require typing the account email … before enabling the Delete-account button,
  consistent with the book-deletion safeguard" → unit tests (disabled/enabled + alert),
  E2E pin, live demo differential vs main.
