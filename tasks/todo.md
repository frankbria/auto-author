# Issue #204 — [P2.12] Profile-page save silently wipes all Settings-page preferences

**Plan source**: CodeRabbit plan on the issue (2026-07-04), design choice 1 pre-resolved → Option 2 (merge + load-state guard). Verified against current code 2026-07-13 — no drift; `profile/page.tsx:120-124` still sends a 3-field `preferences` object.
**Branch**: fix/204-profile-save-preserves-preferences

**Scope**: frontend-only. Backend `$set`-replace semantics intentional and unchanged.

## Adaptations to the plan (verified in code)
- `ProfilePage.test.tsx` mocks `useProfileApi` WITHOUT `getUserProfile` and mocks react-hook-form entirely. The page already guards `if (!getUserProfile) return;`. → The absent-hook path must set `loadState='loaded'` (test-only path; production always has the hook), else every legacy submit test breaks.
- Hydration effect currently early-returns on `form.formState.isDirty` BEFORE anything else. Preferences capture + loadState must happen BEFORE the dirty check — capturing server prefs never clobbers user input, and skipping it would leave the wipe bug alive whenever the user starts typing before the fetch resolves.
- `useUserPreferences` is globally jest-mocked (jest.setup.ts:507) → importing `invalidateUserPreferencesCache` in page.tsx is safe for the legacy suite.
- New test goes in a new file `ProfilePageSave.test.tsx` (real react-hook-form + real components, mock `useAuthFetch`) modeled on `SettingsPageSave.test.tsx` — the legacy `ProfilePage.test.tsx` mocks react-hook-form so it can't express the merge contract.

## Todo
- [x] Branch `fix/204-profile-save-preserves-preferences`
- [x] RED: `frontend/src/__tests__/ProfilePageSave.test.tsx` (4 tests, all RED on old code)
  - preservation: GET returns prefs incl. `default_writing_style`, `auto_save_interval`, `future_flag`; change theme; save; PATCH body `preferences` contains ALL fields + edit
  - `invalidateUserPreferencesCache` called after successful save
  - load failure (GET rejects) → Save disabled (wipe-on-failure path closed)
  - dirty-before-fetch-resolves: user edits before hydration completes → save still sends full merged prefs
- [x] GREEN: `frontend/src/app/profile/page.tsx` (+ fixed pre-existing broken dirty-guard: RHF lazy proxy never computed isDirty — subscribe during render)
  - `preferences` state (`Partial<UserPreferences>`) + `loadState` `'loading'|'loaded'|'error'`
  - hydrate: capture `p.preferences ?? {}` + `setLoadState('loaded')` before dirty check; catch → `'error'`; absent hook → `'loaded'`
  - `onSubmit`: spread retained prefs, override the 3 editable fields; on success update state from response + `invalidateUserPreferencesCache(updated?.preferences ?? null)`
  - Save button disabled unless `loaded`; error notice when `'error'` (Settings copy pattern)
- [x] Legacy `ProfilePage.test.tsx` stays green (10/10)
- [x] Deslop scan, lint (0 errors), typecheck clean, full suite 117 suites / 2122 passed / 5 skipped, coverage gates green
- [x] Mutation checks: merge-spread removal → 2 preservation tests RED; isDirty-subscription removal → dirty-path test RED
- [x] Pre-PR third-party review: opencode occupied by foreign-cwd delegation → codex fallback; 1 P2 fixed (keepDirtyValues hydration for backend-only fields on the dirty path)
- [x] PR #288; post-PR fresh codex session: 1 P2 fixed (re-arm save guard on user switch) — both posted as PR comment
- [x] Demo (hard gate): `docs/demos/2026-07-13-issue-204-profile-save-preserves-prefs.md` — real backend + local Mongo + real better-auth signup; main wipes 11→3 pref fields on a bio-only save, branch preserves 11/11 + bio; dead-backend load → alert + disabled Save
- [ ] CI green + final feedback triage
- [ ] Docs sync (CLAUDE.md changelog), merge, close issue
