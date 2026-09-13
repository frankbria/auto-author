---
description: Static theme/contrast guards — what makes one real instead of decorative
globs: ["frontend/src/__tests__/theme/**", "frontend/*baseline*.json", "frontend/src/app/globals.css", "frontend/tailwind.config.js"]
priority: 65
---
Every rule here is a defect this repo actually shipped, not a style preference.

**Build the sweep first and let it produce the count.** Never trust a count from an issue body or a
hand-written list. #632's issue title said 19, its own table summed to 14, the sweep found 18;
#637's said 27, the sweep found 30. The misses are systematic: a hand-written grep for an
"unprefixed" class cannot match `group-[.toast]:` or `hover:`, and an import walk silently omits the
file nobody registered.

**Measure the ratio; never quote one.** A contrast figure without the surface it was taken against is
not a measurement. Re-derive it from `globals.css` tokens and the palette using
`__tests__/theme/helpers/contrast.ts`. Two wrong numbers shipped by copying them out of an issue.

**Confirm which declaration the utility actually resolves to.** `text-primary` is `tailwind.config.js`'s
brand indigo plus a `.dark .text-primary` override in `globals.css` — not the `--primary` token, which
feeds only the v4-only `@theme` block that v3 ignores. #634 published 16.39/1.15 for a colour that
never renders. Check `tailwind.config.js` and any `@layer utilities` before pricing a class.

**Ledger per distinct value, never a per-file total.** A single total lets a net-zero swap through:
drop one `text-gray-500`, add one `text-gray-300`, count unchanged. Pair it with a stale-row assertion
so a burned-down row fails instead of silently pre-authorising the class, and an explicit vacuity
assertion on the sweep's input set (`sources.length > 150`).

**A guard scans the tree, and must exclude itself.** Once tracked, a repo-scanning guard matches the
pattern literal in its own doc comment — passing its first run while untracked, then going vacuous.

**Mutation-check in both directions.** A guard that only fails when broken proves nothing about what it
accepts. Show it failing on the regression *and* passing on the correct idiom. Scope the predicate to
the smallest unit that can't pool: same property, same hue, same state, same class run — asking "is
there *a* dark class nearby?" instead of "does one replace *this* one, where it paints" produced three
separate false greens in #637 alone.

**axe is not evidence here.** Its `color-contrast` rule does not evaluate non-text elements at all, so
icons, rings, dots and borders come back clean while failing 1.4.11.

`npm run typecheck` never sees any of this — `tsconfig` excludes `**/__tests__/**` and `**/e2e/**`.
Run `tsc` directly on a test file before citing it as green (#625).
