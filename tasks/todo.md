# Issue #65 — Migrate UI to shadcn nova template (residual cleanup)

## Context
Core migration **already merged in PR #73** (Dec 24): `components.json` is nova/gray/hugeicons,
Nunito Sans font applied, 37 files already use hugeicons. Issue is still OPEN because the
literal acceptance criteria ("no lucide-react imports", "no zinc colors") aren't fully met.

## Remaining drift (the actual work)
### A. zinc-* → gray-* (20 files) — mechanical className swap, safe
dashboard pages (export/page, [bookId]/page, summary/page, new-book), app/page, ChapterTab,
ai-error-handling-example, LoadingStateManager, ProgressIndicator, ChapterBreadcrumb,
toc/{ClarifyingQuestions,ErrorDisplay,NotReadyMessage,ReadinessChecker,TocGenerating,
TocGenerationWizard,TocReview,TocSidebar}, ui/{avatar,toaster}

### B. lucide-react → hugeicons (14 source files) — per-usage refactor + icon mapping
Feature code: auth/{sign-in,sign-up,reset-password,forgot-password}, PasswordRequirements,
SessionWarning.
Stock shadcn ui/* primitives: sheet, checkbox, sonner, breadcrumb, dialog, radio-group,
dropdown-menu, select.  <- scope decision (see question)
Icon map (lucide -> @hugeicons/core-free-icons): Eye->ViewIcon, EyeOff->ViewOffIcon,
AlertCircle->Alert02Icon, CheckCircle->CheckmarkCircle01Icon, ArrowLeft->ArrowLeft01Icon,
Mail->Mail01Icon, Check/CheckIcon->Tick02Icon, X/XIcon->Cancel01Icon, Circle->CircleIcon,
ChevronRight->ArrowRight01Icon, ChevronDown->ArrowDown01Icon, ChevronUp->ArrowUp01Icon,
MoreHorizontal->MoreHorizontalIcon, Clock->Clock01Icon, Shield->ShieldIcon
(verify each name exists in v3 before use)

### C. Remove `lucide-react` from package.json once imports hit zero; clean test/e2e/md refs
### D. Tests stay green + >=85% coverage; typecheck + lint + build pass
### E. Docs: short CLAUDE.md note; verify grep shows 0 lucide / 0 zinc

## Approach
Mechanical/visual swaps. Rely on existing component tests + build + typecheck as the
regression net; add/adjust tests only where a swap touches asserted markup.

## DONE
- 0 lucide / 0 zinc remaining; lucide-react removed from package.json + lockfile.
- Removed obsolete frontend/backup-pre-nova/ migration backup.
- typecheck clean, lint 0 errors, build green, 89/89 suites + 1853 tests pass,
  coverage stmt 92 / lines 93 / func 90 / branch 83.
