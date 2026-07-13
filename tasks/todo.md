# Issue #195 — [P2.3] Notification preference toggles persist but drive no notifications

**Branch**: `fix/195-gate-notification-toggles`
**Plan source**: CodeRabbit comment (2026-07-04), verified against codebase 2026-07-12. Approved autonomously — no architectural fork (both design choices already resolved with rationale: gate all 5 toggles; disable-in-place with "Coming soon" badge, tab stays visible).

## Problem
The Notifications settings tab renders 5 toggles promising delivery (email, marketing, writing reminders, progress updates, backup notifications). They persist to `UserPreferences` but no delivery infrastructure exists — nothing reads the flags. Beta users are promised alerts that never arrive.

## Approach (frontend-only)
Gate the whole Notifications section as disabled "coming soon": switches render current stored values but are hard-disabled; a `Badge` next to the CardTitle says "Coming soon"; the description states delivery isn't available yet and preferences will apply once notifications launch. Stored contract preserved — values still round-trip unchanged through the shared save flow.

### Adaptations from the CodeRabbit plan
- **Skip the optional Tooltip** — Radix tooltips don't fire pointer events on disabled elements without wrapper hacks; the CardDescription copy communicates the same thing. (YAGNI)
- **Remove the `disabled` prop** from `NotificationSettingsForm` instead of keeping it as dead API — the switches are unconditionally disabled now, so the prop is meaningless; page callsite updated (one line).

## Tasks
- [x] RED: update `frontend/src/__tests__/SettingsPageSave.test.tsx` "shows all five notification toggles" — keep checked-state assertions (disabled switches still show stored state), add: all 5 switches disabled + "Coming soon" badge + delivery-unavailable copy. Verify failures against current code.
- [x] RED: update `frontend/src/e2e/settings.spec.ts` first test — remove the `#notification-writing_reminders` click; assert the Notifications tab shows disabled switches + "Coming soon"; assert `writing_reminders` round-trips **unchanged** (false) in the merged PATCH payload (untouched-values-survive already asserted for export/marketing).
- [x] GREEN: `NotificationSettingsForm.tsx` — hard-disable all switches, add Badge + copy, drop `disabled` prop; `page.tsx` — drop `disabled={!isLoaded}` from this form.
- [x] Round-trip persistence unchanged: existing "preserves unexposed preference fields" unit test still passes (notification flags in merged payload).
- [x] Quality gate: jest suite + coverage, lint, typecheck; e2e settings spec.
- [x] Third-party review (opencode GLM primary, codex fallback) pre-PR + post-PR.
- [x] PR, demo (branch vs main: main shows interactive false-promise toggles; branch shows disabled + Coming soon; values still persist when saving other tabs), CI, merge.

## Acceptance criteria mapping
- "Gate the undeliverable toggles behind a coming-soon/disabled state" → all 5 switches disabled + visible "Coming soon" badge + honest copy; stored values preserved and round-trip unchanged.
