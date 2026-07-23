# Demo — #331: core authoring pages visible in the light theme

**Claim:** Book-detail, summary, and TOC-wizard headings/body/cards hardcoded
near-white `text-gray-*` on the theme-aware `bg-background`, so they were
invisible in the shipped light theme. This migrates them to the design tokens so
they render with proper contrast in light mode, and adds a guard so it can't
recur.

For a contrast regression, the outcome evidence is the **actual light-mode WCAG
contrast** each cited element renders at, before vs after — computed from the
project's own token values (`globals.css` `:root`) and Tailwind's default gray
palette. No stack needed; the visual result is fully determined by these values
(the same shared light/dark palette #64/#206 already ship).

## AC1 — replace hardcoded grays with the token vocabulary

Gray literals remaining on the three pages:

```
main  (book page.tsx):                                    48
branch page.tsx:                                           0
branch summary/page.tsx:                                   0
branch TocGenerationWizard.tsx:                            0
```

`bg-gray-800`→`bg-card`, `bg-gray-900`(input)→`bg-background`,
`bg-gray-700`→`bg-secondary`(buttons)/`bg-muted`(tracks & disabled),
`border-gray-*`→`border-border`, `text-gray-100/200`→`text-foreground`,
`text-gray-300/400/500`→`text-muted-foreground`; paired `text-white`/`text-gray-100`
on now-`bg-secondary` buttons→`text-secondary-foreground`. Brand accents
(indigo/green/red) stay theme-fixed, as #206 did.

### Outcome — real light-mode contrast (invisible → visible)

`LIGHT THEME (:root) — on --background (white, Y=1.000)`

| Element | BEFORE | | AFTER | |
|---|---|---|---|---|
| Book title (`page.tsx:428`) | `text-gray-100` | **1.10:1 — invisible** | `text-foreground` | **19.79:1 — PASS AA** |
| "Provide a Summary" (`summary:157`) | `text-gray-100` | **1.10:1 — invisible** | `text-foreground` | **19.79:1 — PASS AA** |
| "Generate Table of Contents" (`wizard:313`) | `text-gray-100` | **1.10:1 — invisible** | `text-foreground` | **19.79:1 — PASS AA** |
| Stepper description (`page.tsx:454`) | `text-gray-400` | **2.54:1 — fail** | `text-muted-foreground` | **4.73:1 — PASS AA** |

The 1.10:1 matches the issue's reported "~1.1:1 (invisible)" exactly. The core
authoring flow's headings go from unreadable to WCAG-AA-passing in light mode.
(Dark mode is unchanged: the `.dark` token values equal the old hardcoded RGBs,
per #206.)

## AC2 — a guard so the regression can't recur silently

`src/__tests__/theme/core-authoring-pages-tokens.test.ts` source-sweeps all three
files for any `gray-*` utility; render assertions pin each cited heading to
`text-foreground`. Mutation check — reintroduce the exact bug on the summary
heading (`text-foreground` → `text-gray-100`):

```
-- bug reintroduced --
Tests:       2 failed, 10 passed, 12 total
   ✕ source sweep: summary/page.tsx contains no gray literals   → ["text-gray-100"]
   ✕ renders the page heading with the theme foreground token   → had class "text-gray-100"

-- restored --
Test Suites: 2 passed, 2 total
Tests:       12 passed, 12 total
```

Both the sweep and the render assertion turn RED on the reintroduced bug and
GREEN when restored — the guard fires.

## Review

Cross-family `codex` (opencode occupied by a concurrent foreign-cwd session):
**"No substantive defects found."** Its non-blocking note (broaden the sweep past
`text/bg/border-gray-*`) was adopted — it now bans any `*gray-N` utility.
