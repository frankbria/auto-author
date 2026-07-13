# Issue #205 — Remove orphaned /dashboard/new-book route (P2.13)

## Decision (plan's Design Choice 1, kept): DELETE the page
Unreachable in-app, drops required genre/target_audience (data loss), duplicate taxonomy.
Canonical flow = BookCreationWizard modal.

## Plan drift found (CodeRabbit plan is 2026-07-04, pre-#201)
1. **PR #287 (#201, merged 2026-07-13) pointed CI-run E2E at the orphaned page**:
   `src/e2e/error-recovery-flow.spec.ts` (create-book error tests) and
   `src/e2e/complete-authoring-journey.spec.ts` step 1 both `goto('/dashboard/new-book')`.
   Deleting the page without retargeting breaks CI.
2. **The wizard's error path is WEAKER than the orphaned page's**: generic
   `toast.error('Failed to create book...')`, no classification, no Retry action.
   #201's E2E pins classified toast + Retry recovery (currently only the orphaned
   page has that, via #46's classifyError + showErrorNotification). The delete
   branch must port that handling into the wizard or the E2E pins are unsatisfiable.
3. Wizard `target_audience` is a fixed-option Radix select; journey spec filled
   free text — spec adapts to select 'general'.

## Tasks
- [x] Branch `fix/issue-205-orphaned-new-book`
- [x] RED: BookCreationWizard.test.tsx error-path tests → expect classified
      showErrorNotification (not generic toast.error)
- [x] GREEN: wizard catch → classifyError + showErrorNotification(classified, {onRetry});
      dialog stays open, form intact (already true)
- [x] RED: pin canonical taxonomy — BookMetadataForm renders 'Historical' (absent
      from its old 7-item list, present in canonical 11-item list)
- [x] GREEN: `src/lib/constants/book-metadata.ts` (GENRE_OPTIONS = wizard's list,
      TARGET_AUDIENCE_OPTIONS); refactor BookCreationWizard + BookMetadataForm onto it
- [x] Delete `src/app/dashboard/new-book/` + `src/__tests__/NewBookPage.test.tsx`
      (its 2 assertions now live in the wizard suite)
- [x] Retarget CI E2E: error-recovery-flow fillNewBookForm → open wizard from
      /dashboard; URL assertions → dialog-still-open; journey step 1 → modal
- [x] Page objects: book-form gotoNewBook → open modal from dashboard; Radix
      select helpers; dashboard.page.ts drop unused clickNewBook; 04-security-
      performance perf block → measure modal open
- [x] DEPLOYMENT-TESTING-CHECKLIST.md line 143 route mention
- [x] Verify: jest suite, lint, typecheck, chromium E2E (both retargeted specs)
      against real backend; mutation-check RED evidence
- [ ] opencode/codex pre-PR review → PR → post-PR review → demo → CI → merge
