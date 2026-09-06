# Demo — #539 Post-#517 Dependabot sweeps, verified

**Date:** 2026-09-05 · **Branch:** `feature/539-verify-dependabot-sweep` · **Verifies:** #517 (PR #538)

#517 predicted grouping's behaviour from a local `dependabot/cli` harness. This closes the
loop with **observation**: four real weekly sweeps against the merged config, 2026-08-26 →
2026-09-05, 24 Dependabot PRs. The first sweep was recorded in [#539's 2026-08-27
comment](https://github.com/frankbria/auto-author/issues/539#issuecomment-1); this document
covers all four and settles the two ACs that comment left open.

Every figure below comes from the GitHub API, not from a harness.

---

## The window

```bash
gh pr list --author "app/dependabot" --state all --limit 80 \
  --json number,title,createdAt,closedAt,mergedAt,headRefName
```

| Sweep | Date | `npm` | `uv` | `github-actions` |
|---|---|---|---|---|
| 1 | 2026-08-26 | #543 `frontend-prod` (26) | #541 `backend` (10), #542 `openai` 2→3 solo | #540 `actions` |
| 2 | 2026-08-28 | #567 `frontend-build` (2), #568 `frontend-dev` (10), #569 `frontend-prod` (2), #562 solo¹ | #564 `backend` (3), #565 `pytest-cov` 6→7 solo | #563 `actions` |
| 3 | 2026-09-04 | #572 `frontend-dev` (12), #573 `frontend-prod` (13), #574 `better-auth` solo, #578 solo² | #575 `backend` (8) | — |
| 4 | 2026-09-05 | #580/#588 `frontend-dev` (14→10), #581 `frontend-prod` (14), #586 solo², #587 `frontend-prod` (1) | — | — |

¹ `@hugeicons/core-free-icons`, opened solo then folded into the `frontend-prod` group on reroll.
² security update on an **indirect** dependency — see AC4.

Also in-window and outside any sweep: #548 (sweep-1 `frontend-dev` reroll), #570 (`fast-uri`
security), #579 (`backend` reroll), #565.

**The shape held every sweep.** Three npm groups, one `uv` group, one `actions` group; every
production major alone (`openai` 2.45.0 → 3.0.0, `pytest` 8.4.1 → 9.1.1, `pytest-cov` 6.2.1 →
7.1.0); `better-auth` 1.7.1 → 1.7.2 alone as #556 requires. No PR ever mixed a major into a
group.

---

## AC — the post-batch self-close audit

`docs/references/quality-standards.md` → **Dependency Batches** → *After every batch*.

```bash
gh pr list --state closed --author "app/dependabot" --limit 30 \
  --json number,title,closedAt,mergedAt \
  --jq '.[] | select(.mergedAt == null) | "#\(.number) \(.closedAt)  \(.title)"'
```

Nine PRs closed unmerged in the window: **#548 #562 #564 #568 #569 #572 #573 #575 #580.**
Eight carry the supersession message —

> Looks like these dependencies are updatable in another way, so this is no longer needed.

— and #548 carries a different one, *"no longer being updated by Dependabot"*: that is #555
adding `typescript` and `tailwindcss` to `ignore`, i.e. our own config change retiring the PR.
Neither is the pathological *"up-to-date now"* close that motivated #517.

The claim that matters is not the message, it is whether the bump survived. Every `Updates \`x\`
from A to B` line was extracted from all nine bodies and checked against `origin/main`:

| Package | Target | On `main` |
|---|---|---|
| `@axe-core/react` | 4.13.0 | `^4.13.0` ✅ |
| `@playwright/test` | 1.62.1 | `^1.62.1` ✅ |
| `@testing-library/jest-dom` | 7.0.1 | `^7.0.1` ✅ |
| `@testing-library/react` | 16.3.3 | `^16.3.3` ✅ |
| `@testing-library/user-event` | 14.6.6 | `^14.6.6` ✅ |
| `@types/react` | 19.2.18 | lock `19.2.18` ✅ |
| `@types/react-dom` | 19.2.5 | lock `19.2.5` ✅ |
| `autoprefixer` | 10.5.4 | `^10.5.4` ✅ |
| `@hugeicons/core-free-icons` | 4.3.0 | `^4.3.0` ✅ |
| `@hugeicons/react` | 1.1.10 | `^1.1.10` ✅ |
| `@sentry/nextjs` | 10.71.0 | `^10.72.0` ✅ (ahead) |
| `@tiptap/*` (6 pkgs) | 3.30.5 | `^3.30.5` ✅ |
| `mongodb` | 7.6.0 | `^7.6.0` ✅ |
| `next` | 16.3.3 | `^16.3.3` ✅ |
| `react-hook-form` | 7.86.0 | `^7.86.0` ✅ |
| `web-vitals` | 6.2.1 | `^6.2.1` ✅ |
| `boto3` | 1.43.77 | `==1.43.78` ✅ (ahead) |
| `cloudinary` | 1.46.0 | `==1.46.0` ✅ |
| `openai` | 3.3.1 | `==3.3.1` ✅ |
| `python-dotenv` | 1.2.3 | `==1.2.3` ✅ |
| `reportlab` | 5.0.1 | `==5.0.1` ✅ |
| `sentry-sdk[fastapi]` | 2.68.0 | `==2.68.0` ✅ |
| `stripe` | 15.5.1 | `==15.5.1` ✅ |
| `uvicorn` | 0.52.4 | `==0.52.4` ✅ |
| `eslint` | 10.9.0 | `^9.39.5` — **capped on purpose** (#583) |
| `@typescript-eslint/{parser,eslint-plugin}` | 8.67.0 | **absent on purpose** — dropped as direct deps by the ESLint 9 flat-config migration (#585); `eslint-config-next` 16 bundles them |

**Nothing was lost.** Two of the three non-matches are deliberate, and both are recorded in
`dependabot.yml`'s `ignore` block or in #585. Zero self-closes with a false claim across four
sweeps — grouping did remove the collision at its source.

---

## AC — `gh pr merge --auto` on a mergeable grouped PR

Closed in production, three times over: **#540** (`actions`, sweep 1), **#581**
(`frontend-prod`, 14 updates), **#588** (`frontend-dev`, 10 updates) all landed via
auto-merge after their required checks went green. #517's AC2 no longer rests on the
arm/disarm test.

---

## AC — the indirect residue: the recorded claim was incomplete

`dependabot.yml` and `quality-standards.md` both said the "indirect residue" predicted by the
harness was an artefact of `allowed-updates: all`, and that the live sweep produced none. That
is **true for version updates and false as a general statement.**

Three solo PRs in this window bump packages that appear in neither `frontend/package.json`
section:

| PR | Package | Direct? | Driven by |
|---|---|---|---|
| #570 | `fast-uri` 3.1.5 → 3.1.7 | no | GHSA-qw65-cvwx-89v3 + GHSA-58mr-gqgx-xq4g (high) |
| #578 | `postcss-selector-parser` 6.1.2 → 6.1.4 | no | GHSA-w9m9-85wc-3x92 (low) |
| #586 | `minimatch` 3.1.2 → 3.1.5 | no | GHSA-7r86-cg39-jmmj / GHSA-23c5-xmqv-rm74 (high) |

```bash
gh api repos/frankbria/auto-author/automated-security-fixes
# {"enabled":true,"paused":false}
```

These are **security** updates, a different lane from everything `dependabot.yml` configures:
advisory-driven, reaching indirect dependencies, and — because `applies-to` defaults to
version-updates — unreachable by any group above. That default is the one we want: an advisory
patch lands alone and fast. It also means these PRs sit outside `open-pull-requests-limit`
entirely, which matters for the section below.

`#578` is worth one line on its own: `main`'s top-level `postcss-selector-parser` is still
6.0.10 and did not move. That is correct, not a miss — the advisory range is `>= 6.1.0, <
6.1.3`, so 6.0.10 was never affected; the two consumers that were (`postcss-nested`,
`tailwindcss`) are both at 6.1.4 in the lockfile.

---

## AC — `open-pull-requests-limit: 5`: not reached, and the naive reading is wrong

Left explicitly unresolved in the sweep-1 comment ("npm opened 1 PR against a limit of 5, so
the cap was never approached"). Recomputed as a peak-concurrency sweep over every PR's
`createdAt`/`closedAt` in the window, the raw counts look alarming:

| Ecosystem | PRs | Peak concurrent open | Limit |
|---|---:|---:|---:|
| `npm` | 16 | 5 | 5 |
| `uv` | 6 | 2 | 5 |
| `github-actions` | 2 | 1 | 5 |

**That 5-of-5 is not a cap hit.** From GitHub's Dependabot options reference, on
`open-pull-requests-limit`:

> Security update pull requests are not subject to this limit and do not count toward it.
> There is no limit on the number of open pull requests for security updates.

The five open at 2026-09-04T22:28Z were #567, #572, #573, #574 and **#578** — and #578 is
`postcss-selector-parser`, one of the three advisory-driven PRs from the section above. It
neither counts toward the limit nor is bounded by one. Excluding all three security PRs
(#570, #578, #586), the real figure is:

| Ecosystem | version-update PRs | Peak concurrent | Limit |
|---|---:|---:|---:|
| `npm` | 13 | **4** | 5 |
| `uv` | 6 | 2 | 5 |
| `github-actions` | 2 | 1 | 5 |

npm peaked at **4 of 5** at 2026-09-04T07:34:40Z: #567 `frontend-build`, #572 `frontend-dev`,
#573 `frontend-prod` — the three groups — plus #574 `better-auth`. **Nothing was truncated in
this window.** The AC is answered in the negative, and the earlier suspicion that the
`minimatch` bump had been queued behind a full slot list is unfounded: as a security update it
could never have been queued behind one.

**The limit is still raised to 10, as headroom rather than as a fix.** The three npm groups
are fixed overhead in every sweep, so 5 leaves exactly two slots for everything this config
deliberately forces solo — `better-auth`, production majors, build-toolchain majors. One sweep
where a prod major coincides with a `better-auth` bump and a `postcss`/`autoprefixer` major
exhausts them, and Dependabot does not announce a PR it declined to open: a suppressed bump is
indistinguishable from no bump being available, which is #504's *"up-to-date now"* ambiguity
arriving as silence instead of a false claim. Grouping already caps the volume this limit was
originally protecting against, so the extra slots cost nothing. `uv` and `github-actions` stay
at 5; neither exceeded 2.

---

## Not done, and why

- **No guard test for the new limit.** `assert limit >= 10` restates the config file it reads
  from. `scripts/test_dependabot_config.py` pins *structural* invariants — a production major
  swallowed by a group, `better-auth` losing its exclusion — where the regression is silent and
  the blast radius is a user-facing outage. A number that only changes when someone edits that
  line, in a diff a reviewer reads, needs a comment rather than a test, and it has one.
- **#536's premise is void, not verified.** It expected a grouped backend PR to need the
  `requirements.txt` regen once per group instead of once per PR. #534 deleted the export
  outright, so there is no regen at all; sweeps 1–4 landed five `backend` group PRs with no
  manual step. Noted on #536 rather than silently absorbed here.
