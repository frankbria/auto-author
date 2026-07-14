# Issue #206 — BookCard + EmptyBookState hardcode dark theme (P2.14)

## Plan (CodeRabbit 2026-07-04, design choice pre-resolved: migrate gray-* AND dark-tinted indigo)
Verified against live code — no drift. Both files unchanged since the plan.
- `primary`/`destructive` are fixed RGB in tailwind.config.js (brand, theme-independent) ✓
- `card/muted/secondary/border/foreground` are CSS-var tokens with :root + .dark values ✓
- `ui/card.tsx` Card base already applies `bg-card text-card-foreground border` — BookCard overrides it with grays ✓
- **Adaptation**: no global `* { @apply border-border }` rule exists in globals.css, so bare
  `border` = Tailwind default gray-200 → use explicit `border-border`.

## Mapping
BookCard: container `bg-card border-border hover:border-primary`; title `text-card-foreground`;
muted text `text-muted-foreground`; "New" + callout `text-primary bg-primary/10 border-primary/50`;
progress track `bg-muted`, fill `bg-primary`; Open Project `bg-secondary text-secondary-foreground
hover:bg-primary hover:text-primary-foreground`; delete `bg-secondary text-secondary-foreground
hover:bg-destructive hover:text-destructive-foreground` (ChapterTab precedent).
EmptyBookState: container `bg-card/50 border-border`; heading/labels `text-foreground`;
body `text-muted-foreground`; step cards `bg-muted/40`; CTA `bg-primary hover:bg-primary/90
text-primary-foreground`.

## Review outcome (pre-PR)
opencode (GLM) hung 10 min with zero output (documented condition) → codex fallback.
**codex Major (real, fixed)**: `text-primary` on the "New" label + callout text was a
dark-mode contrast regression (~2.3:1) because `primary` is FIXED indigo-600 in this
repo (not a .dark CSS var). Fixed with the repo's two-tone precedent
(`text-indigo-600 dark:text-indigo-400/300`, per PasswordRequirements/sign-in/TwoFactorSetup);
fills/borders keep `primary` tokens. Literal-sweep tests refined: a literal is allowed
only on elements carrying a `dark:` variant (theme-responsive pair). Mutation-verified:
dropping the dark: variant fails exactly the 2 intended tests.

## Tasks
- [x] Branch `fix/issue-206-theme-tokens`
- [x] RED: BookCard.test.tsx token-class pins (10 new tests RED on old code);
      new EmptyBookState.test.tsx token pins
- [x] GREEN: migrate both components per mapping
- [x] Quality gate: jest 117 suites / 2134 passed, lint 0 errors, typecheck clean;
      codex pre-PR review (1 Major fixed, 1 Minor noted)
- [ ] PR
- [ ] Demo: light + dark dashboard with books + empty state, branch vs main differential
- [ ] Post-PR review + CI green
- [ ] Docs sync + merge
