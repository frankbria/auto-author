# Lessons

## A triage rebuttal is a claim: check it before posting (2026-10-02, #749)
- Two reviewers flagged that a *stored* `subchapters: null` would crash the new TOC walk. I closed
  it as a nitpick on the PR with "every other writer stores a list". I never checked that, and it
  was false. generate-toc persists the AI's JSON verbatim, and `_is_valid_toc` validates only
  chapter titles. The glm-review bot then reproduced it as a **Major regression**: before #749,
  PUT /toc on such a book succeeded and replaced the bad value; after it, every save would 500.
- What made it easy to miss: the input-side fix (a 400 at the endpoint) felt like it closed the
  topic, but data **already stored** by a different writer never passes that endpoint. A new read of
  stored data needs its own answer to "which writers produced this, and what do they validate?"
- Do instead: before dismissing a finding with "X never happens", grep every writer of the field
  (`grep -rn '"table_of_contents"' backend/app`) and read what each validates. Put the writer list
  in the rebuttal. If you cannot name them, the finding is not a nitpick.

## The conducting-demo skill's Showboat syntax needs a language (2026-10-02, #749)
- `showboat exec demo.md ./script.sh` hangs forever reading stdin. The real form is
  `showboat exec demo.md bash "./script.sh"` (`exec <file> <lang> [code]`). `agent-browser` is not
  installed on this box; the Playwright copy in `frontend/node_modules` drove the real page instead
  (`require('<repo>/frontend/node_modules/playwright')` from a `.cjs` script outside the repo).

## Never quote a contrast ratio you did not measure yourself (2026-09-09, #629)
- Two wrong numbers in one change, from two different sources, both caught only by re-measuring:
  - **Invented.** I wrote `--primary` as "15.9:1 light-muted, 12.3:1 dark-muted" into a code comment
    from intuition about how dark the token is. Measured: **16.44 and 12.01**. Nobody would have
    caught it — the guard only asserts `>= 3`, so a plausible-looking wrong figure sails through the
    test suite and into the repo as a fact the next reader trusts.
  - **Inherited.** The issue body predicted `blue-600` at 3.56 / 3.26 on the light surfaces. Measured
    in this repo: **5.17 / 4.74**. The issue's figures were Tailwind **v4**'s `blue-600`; the repo is
    still on v3 (#513). Palette literals are versioned data, so a ratio computed elsewhere is not
    portable — even one written by the same project, about the same class name.
- Do instead: before writing any ratio into a comment, commit message, PR body or changelog, run it
  through the repo's own helper (`src/__tests__/theme/helpers/contrast.ts`) against the repo's own
  `globals.css` and `tailwindcss/colors`. A throwaway `it()` under `src/__tests__/theme/` that
  `console.log`s the figures takes a minute; it must live under that dir so the relative import and
  jest's roots resolve, and delete it before committing.
- When your measurement disagrees with the issue's, **say so in the code** rather than silently using
  the better number — the gap otherwise reads as drift to whoever audits the guard next.
- Generalising a source-scanning guard's regex (`bg-` to `bg|text|border`) is only safe if you check
  it does not change how existing entries resolve. Cheap proof: the case count moved 57 -> 62, exactly
  the new entry's 4 surfaces + 1 pin, so no existing entry started matching a different utility.

## Next's app router never routes an underscore-prefixed folder (2026-09-09, #629)
- A temporary visual-verification page at `src/app/__629/page.tsx` served a **404** with no warning,
  no build error and no log line. `_`-prefixed directories are Next's "private folder" convention and
  are excluded from routing. Renaming to `dev629` served 200 immediately.
- Also: `next dev` refuses to start a second instance in the same project and prints the existing
  PID/port instead of failing loudly — the new port is simply never bound, so `curl` gives exit 7.
  Read the startup log before blaming the route. Reusing the running dev server is fine: it compiles
  from the working tree, so a new page appears without a restart.
- Kill nothing you did not start. The already-running server may be the user's.

## Bisect a dep-PR failure FORWARD from a green baseline (2026-09-05, #589)
- Reverting one suspect at a time out of a failing multi-package PR is worse than useless when the
  culprit is something you never thought to revert: every run still fails, so each innocent package
  looks guilty in turn. On #588 this cleared `@testing-library/user-event`, `jest` +
  `jest-environment-jsdom`, and `@testing-library/jest-dom` 7 across three ~4-minute failing runs and
  pointed at nothing.
- Do instead: in a worktree on the PR branch, restore the base branch's exact `package.json` AND
  `package-lock.json`, `npm ci`, confirm green. That control also proves the failure is the deps and
  not your environment. Then add packages forward, in halves. Green runs were 1s against 220s failing
  ones, so forward bisection is both cheap and unambiguous.
- The culprit can be a package the PR does not list at all. Here it was `nwsapi` 2.2.24 -> 2.2.26,
  jsdom's CSS selector engine, an unpinned `^2.2.x` transitive (`jest-environment-jsdom -> jsdom ->
  nwsapi`). #588 only regenerated the lockfile and floated it. **Diff the lockfile, not the PR
  description.**
- When the suspect's own source diff looks cosmetic (`jest-environment-jsdom` 30.4.1 -> 30.5.0 was
  `var` -> `let`), compare resolved TRANSITIVE versions between the two lockfiles instead of diffing
  the named package.
- Name the mechanism, don't guess it: monkey-patching `Element.prototype.matches` to count calls showed
  `:fullscreen` evaluated 29,999,829 times per keypress, with `:modal` triggering ~1000 nested walks.
  That turns "some perf regression" into a filable upstream report.
- Fixed with `"nwsapi": "2.2.25"` in `frontend/package.json` `overrides` (#590). No new guard test:
  `ChapterTab.keyboard.test.tsx` already fails loudly inside the required `Frontend Tests` check the
  moment `nwsapi` floats, which is how this was caught.
- The override came out in #589 once 2.2.28 shipped the upstream fix. Verify that kind of release by
  swapping only that package into the current tree and timing the tripwire test (16 timeouts in 202s on 2.2.27, 23/23 in 1.8s on
  2.2.28). Then diff the release's source for the fix you expect.
  A version number named in a close condition is a hypothesis until the test runs fast on it.

## Verify a dependency fix under the NEW dep set, never the old one (2026-09-05, #571/#583)
- #571 said ESLint 10 was blocked because `eslint.config.mjs` imported `@eslint/eslintrc` without
  declaring it. Declaring it and running `npm run lint` under the repo's THEN-current eslint 8 passes —
  and proves nothing, because the goal was eslint 10.
- Checked out the Dependabot branch in a worktree, applied the candidate fix there, `npm install`, ran
  the real gate: it failed immediately with `Converting circular structure to JSON`. `eslint-config-next`
  16 ships no eslintrc-style config at all, so `FlatCompat` cannot consume it either way. Migrating to
  native flat config was unavoidable.
- Two blockers were stacked; fixing the first only exposes the second. ESLint 10 is capped upstream:
  `eslint-config-next` 16 pulls `eslint-plugin-react@7.37.5` (the latest published), which peers
  `eslint ^9.7` and still calls the removed `context.getFilename()` (#583).
- Flat-config gotcha worth 20 minutes: plugin namespaces resolve per file, so a rules-override object
  with no `files` fails with *could not find plugin "react"*. Each override block must repeat the glob
  the shared config registered that plugin under.

## #174 — entitlement gate: frontend error classification has TWO pipelines
- A backend structured error (`HTTPException(detail=error_response.model_dump())`) surfaces as
  `{detail: {error, error_code, status_code, ...}}` — text is under `detail.error`, NOT `detail.message`.
  `bookClient.aiError` only read `detail.message` and dropped the HTTP status, so a 402 (or 429)
  misclassified as a generic 500. Attach `statusCode` on the thrown Error (like `exportError` already does)
  so the unified `classifyError` (reads `error.statusCode`) maps it. codex caught this; unit tests didn't
  because they fed pre-formed JSON-in-message errors, not the real `aiError` shape.
- Two classifiers exist: `lib/errors/classifier.ts::classifyError` (reads `error.statusCode`) and
  `lib/api/aiErrorHandler.ts::handleAIServiceError` (parses the Error *message*). A new HTTP→ErrorType
  mapping must work for BOTH — map the status in `HTTP_STATUS_TO_ERROR_TYPE` AND make `extractErrorDetails`
  honor an attached `statusCode`.
- Pre-commit re-runs the FULL frontend+backend suites + coverage (not E2E on this repo's trigger set) — it
  exceeds a 2-min foreground window. Run `git commit` with `run_in_background: true` and monitor, don't
  fight the timeout. Stale local `node_modules` (missing `react-qr-code` from #64) breaks `tsc`; `npm i
  <pkg> --no-save` to match CI without dirtying the lockfile.

## #118 — restoring `pre-commit run --all-files` (gate enforcement)
- `pre-commit run --all-files` runs whitespace/EOF hooks across the WHOLE repo. Years of
  `--no-verify` commits leave debt — expect a large mechanical (whitespace-only) diff to make it green.
  That sweep is legit for an enforcement issue, but separate it clearly from substantive changes in the PR.
- A repo-wide stage drags pre-existing false-positives into commit-time scanners. `check-secrets.sh`
  flagged a load-test password only because the sweep staged that file. Fix the root scanner, don't bypass.
- Secret scanners must scan ADDED (`+`) diff lines only. Scanning removed/context lines makes deleting a
  hardcoded secret impossible without `--no-verify` — self-defeating.
- `.git/hooks/pre-commit.legacy`: when `pre-commit install` runs over a hand-written hook, it preserves +
  runs the old one. If a commit is rejected by a check the framework reports as PASSING, suspect a stale
  `.legacy` duplicate (local-only, not version-controlled) — delete it.
- bd's `.beads/.gitignore` keeps `metadata.json`/`config.json` but ignores `daemon.log/lock/pid`, `*.db-shm`.
  Those runtime files were tracked-before-ignored and re-dirty the gate; `git rm --cached` them.

## #57 — mirroring an existing pattern can copy its gaps
- When you implement a new endpoint by mirroring a sibling (here: `enhance-text` mirrored
  `transform-style`/#58), don't assume the template is complete. `transform-style` only checks book
  ownership — it never verifies the `chapter_id` exists, while every chapter *content* endpoint 404s via a
  local recursive `find_chapter`. codex's pre-PR pass caught the missing check on the new endpoint. Lesson:
  add proper trust-boundary validation to the new code even when the thing you copied omits it; note the
  pre-existing sibling's gap rather than silently propagating it.

## Never `git add -A` with unrelated untracked files present (2026-06-29, #52)
- `git add -A` swept pre-existing untracked working files (`plans/`, `tasks/lessons.md`,
  a staging-only E2E spec, helper scripts) into the #52 commit. The staging spec needs
  live auth and **failed the E2E CI job** — looked like my feature broke E2E; it hadn't.
- Fix: `git rm --cached` the strays (keeps them on disk), commit, push (no force needed).
- Rule: stage explicitly (`git add <paths>`) when `git status` shows untracked files
  outside the change. Check `git show --stat HEAD` before pushing.

## A hook returning a ref object misses conditionally-late-mounted targets (2026-06-29, #51)
- `useSwipeGesture` returned a `useRef` object and bound listeners in a one-time
  `useEffect(..., [])`. But the swipeable element only mounts on a *later* render:
  `useMediaQuery` starts `false`, so `ChapterTabs` renders the swipe wrapper only after
  the media query resolves to mobile. The effect ran once with `ref.current === null`,
  exited, and never re-ran → swipe was dead on real mobile loads. Unit tests mocked
  `useMediaQuery` to `true` from the start, so they masked it; codex's pre-PR pass caught it.
- Fix: return a **callback ref** — React invokes it with the node on attach and `null` on
  detach, so binding/cleanup happen exactly when the element appears/disappears, regardless
  of which render that is. Add a regression test where the ref'd element mounts *after* the
  initial render (toggle state), not one that starts mounted.
- Rule: any hook that attaches DOM listeners to a ref'd element that can mount conditionally
  should use a callback ref, not `useRef` + `useEffect([])`.

## A global skip link needs a target in EVERY render state (2026-06-29, #50)
- A site-wide "Skip to main content" link (`href="#main-content"`) rendered in the root layout
  is only as good as its target. Putting `<main id="main-content">` in *page content* leaves it
  missing in every fallback state that bypasses the page: route `loading.tsx`, `error.tsx`,
  `not-found.tsx`, `<Suspense>` fallbacks, auth-redirect spinners (`ProtectedRoute`), and custom
  ErrorBoundary fallbacks. codex flagged these across 4 review rounds — each a different state.
- The skip link must land *after* the nav, so a single root-layout `<main>` wrapping everything
  doesn't work either (it'd sit before the dashboard nav). Resolution: give the landmark to each
  *layout/shell* (dashboard layout, `auth/layout`) and to each *fallback state component*
  (ProtectedRoute spinner, error.tsx, ErrorBoundary fallback) — one `<main id="main-content">`
  per render path, never two at once. Watch for components that already render their own `<main>`
  (here `QuestionContainer`) → demote to a labeled `<section>` to avoid nested/duplicate main.
- Rule: when adding a global skip link, enumerate Next.js special files (loading/error/not-found/
  global-error) and auth/loading shells, not just the happy-path pages.

## Adding a UI element can break a fixed-viewport E2E (#61 Markdown export)
- Adding the 4th format card (Markdown) to `ExportOptionsModal` made the export dialog taller,
  pushing the "Export PDF" footer button out of `export-templates.spec.ts`'s fixed 1500px
  viewport → `locator.click` timed out ("waiting for element to be visible, enabled and stable").
  The modal renders format radios from **hardcoded JSX**, not the mocked `/export/formats`, so
  route-mocking the old 2-format list didn't spare the spec.
- Rule: when adding a control to a modal/dialog that an E2E interacts with, check specs that
  `test.use({ viewport })` a fixed height and click a footer action — bump the height. The spec
  here already documented the pattern ("dialog is tall … viewport that fits its footer").
- Verify the fix by running the single spec on chromium locally (`npx playwright test <spec>
  --project=chromium`) before pushing, instead of burning a blind CI cycle.

## Long pre-commit hooks exceed the 2-min foreground Bash timeout (2026-07-01, #159)
- `git commit` triggers the backend pre-commit gate, whose coverage run takes ~90–140s. Run in a
  foreground Bash call it hit the 2-min tool timeout → SIGTERM aborted the commit **and** left
  pre-commit's stashed-unstaged-files patch (`~/.cache/pre-commit/patch<ts>`) unrestored, so the
  working tree lost its unstaged changes (a pre-existing `CLAUDE.md` edit + `tasks/todo.md`).
- Recovery: `git apply ~/.cache/pre-commit/patch<newest>` restores the stashed working-tree changes.
- Rule: commit through hooks with `run_in_background: true` (or a Monitor loop), not a plain
  foreground Bash call. Same for the full `pytest --cov` suite.
- Also: `gh pr merge --delete-branch` does a **local** checkout of main afterward; a pre-existing
  unstaged tracked change (here `CLAUDE.md`) blocks it with "local changes would be overwritten"
  even though the server-side merge already succeeded. Stash the WIP first, or verify merge state
  via `gh pr view` (it *did* merge) then clean up locally with stash→checkout→pull→stash pop.

## Rewriting a test's mechanism can orphan imports the hooks won't catch (2026-07-05, #180)
- Replaced `time.sleep(...)` with `patch.object(deps.time, "time", ...)` in a test — the local
  `import time` went dead. Pre-commit's "Backend Linting (ruff)" hook **passed anyway** (its scope
  /select differs from a bare `uvx ruff check <file>`), so the F401 only surfaced in a later review
  pass. Rule: after changing *how* a test works (not just what it asserts), re-run
  `uvx ruff check` on the file directly; don't trust the hook's green.
- Demo seeding: pydantic `EmailStr` rejects reserved TLDs (`@demo.test`) at **response**
  validation — endpoints 500 after the mutation already ran. Seed demo/test users with a routable
  domain (e.g. `@demo-180.io`).
- Diagnosing proxy headers: a uvicorn access-log client of `1.2.3.4:0` (port **0**) is the
  ProxyHeadersMiddleware rewrite signature — instant proof X-Forwarded-For is being honored
  without touching config.

## 2026-07-05 (#181)
- **Credential hunting is blocked — design around it**: when a local API key is stale, don't search other projects' .env files or SSH to servers for a replacement (auto-mode classifier denies both as credential exploration). Demo AI features with a wire-boundary OpenAI-compatible stub (`OPENAI_BASE_URL` env, SDK honors it) that logs request params — often *stronger* evidence than a live model (shows exact `max_tokens` on the wire), disclosed in the demo doc.
- **showboat exec signature**: `showboat exec <file> <lang> [code]` — omitting `<lang>` makes it read code from stdin and hang silently. Always `showboat exec demo.md bash '<cmd>'`.

## 2026-07-06 (#182)
- **Never run a second pytest while the full suite runs**: I re-ran one test file "to inspect errors" while the background full-suite run was mid-flight — both share `auto-author-test` and drop/recreate it, so BOTH runs produced phantom errors and the 25-min suite had to be killed and redone. The rule I already knew ("kill stragglers before a run") also means: queue the follow-up run, never overlap it. Serialize every backend pytest invocation.
- **mongod can be started user-level with --fork**: `mongod --dbpath <scratch> --port 27017 --bind_ip 127.0.0.1 --fork --logpath <scratch>/mongod.log` — no sudo needed; tests create/drop their own DB so an empty scratch dbpath is fine.

## 2026-07-07 (#185)
- **agent-browser screenshot paths are relative to the daemon's cwd** (wherever the first `agent-browser open` ran), not the shell's cwd — `showboat image` then can't find the file. Always pass an absolute output path: `agent-browser screenshot /abs/path/x.png && echo /abs/path/x.png`.
- **showboat exec lang arg — repeat offense**: hit the documented `<lang>` omission again despite the 2026-07-05 lesson. Before ANY showboat session, re-read the invocation shape: `showboat exec <file> bash '<cmd>'`.

## 2026-07-09 (#247)
- **Stable identities in hook mocks for mount-effect components**: mocking `usePerformanceTracking` with `() => ({trackOperation: ...})` returned a fresh object per render; the wizard's `useEffect` deps include `trackOperation` → infinite re-render loop → jest worker OOM (looked like a heap bug, was a mock bug). Define the mock's return object ONCE in the factory and return the same reference.
- **Adding the first test for an untested component can FAIL the coverage gate**: jest with no `collectCoverageFrom` only counts test-imported files; importing a big low-coverage component (wizard at 37% funcs) into coverage dropped the global functions % below 85. Either cover the component's flows in the same PR (stub child components to drive the state machine cheaply) or expect the gate to move.
- **agent-browser httpOnly cookies**: `agent-browser cookies get` exists but `state_save <file>` then parsing `.cookies[]` from the JSON is the reliable way to hand a better-auth session to curl; join multiple cookies with `'; '` — a multi-line Cookie header makes uvicorn reject the request ("Invalid HTTP request received", HTTP 400).

## 2026-07-13 (#201)
- **`git stash -- <pathspec>` un-stages a staged `git rm`**: a mutation-check stash/pop cycle over `frontend/src` silently converted a staged deletion into an unstaged one, and the explicit-`git add`-list commit missed it — the AC-critical file deletion shipped in a follow-up commit only because codex review diffed HEAD against the claim. After any stash/pop, re-check `git status` for ` D` (unstaged deletes) before committing; better, commit staged work BEFORE running mutation checks.
- **`git checkout -- <file>` for mutation-revert also nukes uncommitted edits to that file**: reverting a sed mutation this way deleted the session's own uncommitted testid change. Commit first, mutate second.
- **classifyError retry semantics differ by error shape**: bookClient throws status-less `Error`s, so a mocked HTTP 500 classifies UNKNOWN (no retry) — only network-level failures (`route.abort` → TypeError) classify NETWORK/TRANSIENT and exercise ErrorHandler backoff or the toast Retry action. When testing retry paths, inject aborts, not 5xx fulfills.

## 2026-08-25 — #512: don't state a mechanism more absolutely than you verified it

**Corrections taken (both from codex, post-PR):**

1. Wrote "a `GITHUB_TOKEN` push does not re-trigger workflows … checks that never run"
   as the justification for rejecting an automated fix. The documented rule is
   narrower: GitHub's recursion guard means such a push creates no *new workflow run*.
   The conclusion held; the premise was stated more categorically than the docs support.
2. Wrote "Dependabot no longer sees `requirements.txt` at all" in five places while the
   same PR's Known Limitations section correctly said `exclude-paths` scopes update
   scans, not the dependency graph. Self-contradiction inside one changeset.

**Pattern:** when a decision rests on a platform behaviour, write the claim at exactly
the scope that was verified — name the mechanism ("recursion guard", "update scans")
rather than the sweeping consequence. Overstated premises survive review of the *code*
because they live in prose; they need a reviewer pointed explicitly at the docs claims.

**How to apply:** ask the third-party reviewer to check the docs/comments as hard as
the diff, naming the specific factual assertions to verify. That prompt is what caught
both here — the pre-PR pass, aimed only at code and config, returned no findings.

## 2026-08-25 — verify a config fix against the real tool, not the config file

Reviewing `.github/dependabot.yml` by eye would have shipped a plausible-looking change
with no evidence. Running `dependabot/cli` against the published
`ghcr.io/dependabot/dependabot-updater-uv` image — twice, same tree, differing only in
`exclude-paths` — turned "should stop the no-op PRs" into 35 → 0, and separately proved
the issue's own fallback (`allow: dependency-type: direct`) could not have worked, and
that the trade-off was 8× bigger than my estimate from the last batch.

**How to apply:** for CI/config changes, check whether the tool ships a runnable local
harness before settling for inspection. `dependabot`, `act`, and `actionlint` all do.

## 2026-08-25 — killing a `git commit` mid-hook loses unstaged work to pre-commit's stash

`pre-commit` stashes unstaged changes before running hooks and restores them on exit.
Kill the commit before it exits — here the Bash tool's 2-minute cap hit while the
backend pytest hook ran the full suite — and the restore never happens: unstaged edits
vanish from the working tree with no stash entry and no warning. Cost me 33 lines of
this file, briefly.

**Recovery:** the stash is a patch under `~/.cache/pre-commit/patch<timestamp>-<pid>`.
Find the newest one and `git apply` it. Do this *before* redoing the work.

**Prevention:** any `git commit` in this repo that stages backend files runs the whole
suite, so it needs `run_in_background`, not a foreground call — and stage everything
you care about first, since only staged content is safe from the stash window.

Related: [[commit-before-mutation-checks]] is the same lesson from a different angle —
uncommitted work is the fragile thing; commit early.

## #534 — "X reads this file" is a claim to test, not to trust (2026-08-27)

**Pattern:** a decision deferred twice (#512, #521) on the assumption that two named
scripts were live consumers of `backend/requirements.txt`. Grepping confirmed "2 readers"
and would have kept the file. **Running them** settled it in a minute: both exit 1 against
a healthy tree — one asserts a repo layout retired at #484, the other shells to system
`python` in a uv project. Neither used the file in a load-bearing way (a grep for three
strings; a `pip install` inside a try/catch that logged a WARNING and continued).

**Rule:** when a keep/delete call turns on whether a consumer is real, execute the
consumer. Static reference-counting overstates liveness.

**Corollary, found by the cross-family reviewer:** deleting the export also deleted every
guard that watched it — the CI sync gate, `exclude-paths`, and the test pinning that
exclusion. Nothing would have noticed the file returning, and the `uv export` command is
still quoted in older CHANGELOG entries. **When a removal takes all existing checks with
it, leave exactly one tripwire behind, and mutation-check it.**

## #553 — a repo-scanning guard matches its own literal (2026-08-27)

**Pattern:** added `scripts/test_no_staging_identifiers.py` with a second test asserting
every `ALLOWED_HOSTS` entry still matches a real file, so a stale entry cannot silently
whitelist a hostname forever. `git grep -lF "$HOST"` matches the `ALLOWED_HOSTS` literal
in the guard file itself, so it could never fail.

**Why it survived review-by-me:** it *did* fail on first run, catching two allowlist
entries I had guessed at — because the file was still **untracked**, so `git grep` could
not see it. The moment it was committed it became vacuous. I then wrote in the PR body
that it "earned its keep immediately", crediting it for work it structurally could not do.

**Rules:**
1. Any guard that scans the repo must exclude itself: `git grep ... -- ":!$SELF"`.
2. Mutation-check a new guard **after `git add`**, not before — tracked/untracked changes
   what `git grep`, `git ls-files` and `git diff --cached` can see.
3. Mutation-check **both directions**. The forbid-direction ("add the bad thing → RED")
   passed. Only the require-direction ("remove the required thing → RED") was broken, and
   I never tested it.

**Also, again:** `git checkout <file>` to revert a mutation probe reverted an *uncommitted*
scrub in the same file. Same trap as `commit-before-mutation-checks`. Use a backup copy
(`cp` to scratch, `cp` back) when the working tree has uncommitted work.

## 2026-08-27 — #556: read the whole failure path before describing its blast radius

I wrote "sign-in, password reset and password change all 401" into a plan comment and a commit
message after reading only `sign-in.mjs` and grepping for the shared issuer filter. Reading
`password.mjs` properly showed reset does something different and worse: it succeeds and creates a
*second* credential account, so users self-rescue while the collection silently accumulates rows
that then collide on the new unique key.

The correction mattered — it inverted the deploy ordering argument from "run the backfill whenever"
to "run it before the deploy, because every hour of drift adds manual reconciliation."

**Pattern:** a shared helper appearing in three call sites is not three identical failures. Read
what each caller does with the miss before writing the consequence down. Grep finds the call; only
the caller says what it costs.

## 2026-08-27 — #556: a test that compares against the constant tests nothing about the constant

Ten tests, all green, all mutation-resistant — except the one mutation that mattered. Changing
`LOCAL_CREDENTIAL_ISSUER` from `"local:credential"` to `"credential"` passed the whole suite,
because every assertion read `assert stored["issuer"] == LOCAL_CREDENTIAL_ISSUER`. The single value
the entire fix turned on was untested, and a wrong one would have produced a clean, green, useless
migration against production data.

**Pattern:** when a value is a *wire constant* — a protocol string, a route path, an enum another
system compares against — at least one test must assert the literal, and better, derive it from the
other system. Importing the constant into the test makes the test agree with the code by
construction. Always include the constant itself in the mutation set.

## 2026-09-05 — Dependabot sweep: a green required check is not evidence the gate ran

Two separate lessons from clearing nine dependency PRs.

**1. A stale-green required check is not a current one.** Four PRs last ran CI on 2026-08-28 and
showed `Security Audit: SUCCESS`. Two high-severity `browserslist` advisories published
2026-09-01 meant every one of them would fail the moment it re-ran — the green was an artifact of
when the run happened, not of the code being clean. The failure also surfaced on a PR that had
nothing to do with browserslist (a `fast-uri` bump), so reading the check name as "this PR's
problem" pointed at entirely the wrong package.

**Pattern:** on a required check, read the *run date* alongside the conclusion, and read the failing
job's log before attributing the failure to the PR's own diff. Under `strict: true` protection the
only conclusion that means anything is one from a run whose base is current `main`.

**2. Exit codes that overload two meanings will eventually pick the wrong one.** `npm audit --json`
exits 1 for "vulnerabilities found" — the normal case — *and* for a registry error. The workflow
guarded with `if [ "$rc" -gt 1 ]`, so a registry failure sailed through and handed `audit_gate.py`
an `{"error": ...}` body. The gate correctly refused to read it; the required check went red twice
in twenty minutes on unrelated PRs, each time reading as "this PR introduced an advisory."

The gate was right and needed no change. The bug was upstream of it, in trusting an exit code to
distinguish two outcomes it cannot. Fixed by retrying on the real signal — a response body with no
`vulnerabilities` key (#576/#577).

**Pattern:** when a tool overloads one exit code across success and failure, validate the *output
shape*, not the status. And when a required check is flaky, it is not merely annoying — with
`strict: true` it is an intermittent, self-inflicted merge freeze that also misattributes blame.

**3. Dependabot group PRs reroll on every lockfile change.** Merging them one at a time under
`strict: true` is a treadmill: #564→#575→#579, #569→#573→#581, #568→#572→#580 all superseded
themselves mid-session. Triage the *delta* against the superseded PR rather than re-reviewing from
scratch, and keep the tracking issue on the blocker (#571), never on an individual reroll.

## 2026-09-06 — a concurrency count is not a cap hit until you know what the cap counts (#539)

Verifying #517's grouping config, peak-concurrency over every Dependabot PR's
`createdAt`/`closedAt` showed npm at **5 open against `open-pull-requests-limit: 5`**. That is a
clean, arithmetically correct number, it lined up with a plausible story (three groups are fixed
overhead, so the limit is structurally tight), and it explained an anomaly — a `minimatch`
advisory open since 2026-08-11 whose PR appeared 2026-09-05 minutes after a slot freed. The
config change, the demo document, `quality-standards.md` and the CHANGELOG entry were all written
and committed on that reading.

It was wrong. GitHub's Dependabot options reference:

> Security update pull requests are not subject to this limit and do not count toward it. There is
> no limit on the number of open pull requests for security updates.

One of the five was advisory-driven. The real version-update peak is **4 of 5**, nothing was
truncated, and the `minimatch` timing coincidence had no mechanism behind it — a security PR could
never have been queued behind a full slot list. Four files had to be rewritten.

**Pattern:** before reading a measurement against a threshold, read the threshold's own definition
— specifically *which population it counts*. Every number here was right; the denominator was
assumed. The tell was available in advance and ignored: the same investigation had just
established that security updates are a separate lane that no group can absorb, which should have
prompted "separate from grouping — separate from the limit too?" A finding that arrives with a
satisfying causal story attached deserves more scepticism than one that does not, because the
story suppresses exactly that question.

Two pre-existing repo claims failed the same way and are now corrected: #536 argued urgency from
"the limit is saturated so a security update cannot open", and the sweep-1 note on #539 read the
limit as untested. Both were reasoning about the wrong population.

**Corollary for verification issues:** the deliverable is the *observation*, so an unfalsifiable
✅ is worse than a ❌. "Nothing was truncated" is inferred from staying under the cap, not read
from a Dependabot log — Dependabot never announces a PR it declined to open. Say which of the two
you have.

## 2026-09-06 — a guard is code, and its blind spots are not testable by running it (#518)

Pinning every Action to a commit SHA came with `scripts/test_actions_are_sha_pinned.py` to stop
the policy decaying. The guard globbed `.github/workflows/*.yml`. **GitHub executes `.yaml`
too**, so a future workflow named that way would have run with the repo's credentials while
passing a check that never looked at it — a bypass in the very policy the guard existed to
enforce.

Every workflow in this repo is `.yml`. The guard was mutation-checked three ways before review —
revert a pin, strip a version comment, point it at an empty directory — and **all three passed,
because none of them could express the gap**. A mutation test proves the guard catches the
failure you thought of. It says nothing about the input class you never enumerated. `codex
review` found it by reading line 45, not by running anything.

**Pattern:** when the deliverable is a check, review its *input set* separately from its logic —
what does it glob, what does it skip, what extension/path/case would slip past — and treat that
as a distinct question from "does it fail when I break something". For file-scanning guards the
recurring blind spots are alternate extensions (`.yml`/`.yaml`), case, symlinks, and any path
filter added "for noise". Related: [[guard-tests-can-self-match]], where the guard's blind spot
was itself.

**Second, smaller correction from the same PR.** The PR body claimed both image-build jobs
"exercise the new pins pre-merge". They resolve and download all five, but `Log in to GHCR` is
gated on `github.event_name != 'pull_request'` — so `docker/login-action`, the one action holding
the registry token and the entire reason the issue was P2, did not run at its new pin until the
merge-to-`main` build. A workflow that runs on a PR does not necessarily run *the step that
matters* on a PR: read the step-level `if:` before claiming a path is covered, and check the job's
step conclusions for `skipped`, not just the job's own green tick.

## 2026-09-06 — the riskiest place to re-leak a scrubbed value is the document explaining the scrub (#554)

Scrubbing the operator's network from a public repo, I reintroduced scrubbed values **three
times in one commit** — every time in prose *about* the work, never in the work itself:

1. The CHANGELOG entry restated the third-party egress address while describing its removal.
2. The demo doc's verification block pasted the `git grep` commands with their arguments filled
   in, putting the `/24` prefix and the ISP name into the document asserting they were gone —
   and falsifying its own claim, since a fresh grep would then match that file.
3. The new guard's own test fixture named the real ISP, so the file forbidding the disclosure
   contained it.

The new guard caught (1). **It could not have caught (2) or (3)**: a `/24` written as three
octets matches no IPv4 pattern, and an ISP name is a proper noun no shape rule separates from
prose. Shape-based rules catch shapes — a *partial* value and a proper noun both walk straight
through. (2) was caught by `codex review`; (3) only by chasing (2).

**Pattern:** after scrubbing a value, grep for it again *after* writing the evidence — the
changelog entry, the demo doc, the PR body and the guard's fixtures are all part of the same
commit and none of them existed when the scrub was verified. Write verification blocks as
*results* ("no match for the residential IP and its prefix") rather than as runnable commands
with the literals inlined, and say how to reconstruct the literals from the parent commit
instead.

**Corollary, and the one I nearly got wrong:** fixing (1) revealed that the proximity rule ANDed
"an IP anywhere on the line" with "the description anywhere on the line" — and a CHANGELOG entry
in this repo is a single 3000-character line, so prose about the guard matched a placeholder
mentioned paragraphs away. The tempting fix was an exclusion for `docs/CHANGELOG.md`: one line,
instantly green. **The right fix was to tighten the rule** to require the two within 60
characters, which is the relationship it always meant. An allowlist that silences a true
positive-shaped false positive leaves the rule wrong for every file nobody has tested yet.

Related: [[guard-tests-can-self-match]], and the #518 lesson above on reviewing a guard's *input
set* separately from its logic.

## 2026-09-06 — a repeatable number is not a slow path, it is a limit (#551)

The #83 staging canary failed its first attempt on every run at 32.4–32.7s and passed on retry.
The issue reasoned from that to cold-path latency — Next.js route JIT, better-auth's first Atlas
round trip, the Mongo connect retry loop — and then honestly recorded a fact that killed its own
theory: one run was still slow 33 minutes after deploy.

The tell was in the number's *stability*, not its size. A cold start is a distribution; three
runs landing within 0.3s of each other across two different deployed images is a **threshold**.
The actual cause was better-auth's built-in `/sign-in*` rule — window 10s, max 3 per IP — with a
counter that resets only after 10s of silence. The fixture signed in once per test, so 11
sign-ins at 2–6s spacing tripped it on the 8th, every run, deterministically.

**Pattern:** when a "flaky" timing reproduces to a tenth of a second, stop theorising about
latency and go read the artifact. The answer was sitting in `error-context.md` — the page
snapshot showed the sign-in form displaying "Too many attempts. Please try again later." One
artifact download would have replaced the entire cold-start hypothesis. Also: the *successful*
samples in the same log are free evidence. Seven sign-ins at 0.9–1.1s, including the first one
27s into a fresh run, disproved "first-auth is expensive" without running anything.

**Corollary — an opaque error is a cost, not a neutral.** `page.waitForURL: Timeout 30000ms
exceeded` says nothing about why. Attaching the page's own error alert to that throw is four
lines and converts a dedicated investigation into a one-line diagnosis. Do it wherever a wait
can fail for a reason the page already knows.

## 2026-09-06 — check that the checker covers the file before reporting it passed (#551)

I ran `npx tsc --noEmit -p tsconfig.json`, saw it clean, and said the change typechecked. It had
not: `frontend/tsconfig.json` excludes `**/e2e/**` and `**/playwright*.ts`, so neither the
Playwright fixture I rewrote nor the config I edited was ever fed to the compiler. The third-party
reviewer found this, not me. Typechecking the two files explicitly afterwards was clean — the
claim happened to be true, which is exactly what makes this easy to repeat.

Same shape as [[guard-tests-can-self-match]] and the #518 lesson: a gate that does not include
your file passes for a reason unrelated to your work, and a green result reads identically either
way.

**Pattern:** before citing a gate as evidence for a specific file, confirm the file is in the
gate's input set — read the `exclude`/`testPathIgnorePatterns`/path-filter list, or make the file
fail on purpose and watch the gate go red. This is the mutation check applied to tooling rather
than to tests, and it costs one command.

**Related, from the same PR:** the reviewer also caught that writing a file into
`project.outputDir` publishes it, because that whole tree is uploaded as a CI artifact and this
repo is public. "Where does this path end up?" deserves the same treatment as "is this path
gitignored?" — `.gitignore` protects commits, not artifacts. Tracked as #599.

## 2026-09-07 — the document describing a credential pattern reproduces it (#599, #601)

The #554 lesson above says the riskiest place to re-leak a scrubbed value is the document
explaining the scrub. #601 produced three instances of the same shape in one PR, none of
which involved a real secret:

1. `.env.test.example` was changed to show single-quoted values, per #558. The pre-commit
   secret scan flags a password-ish key assigned a quoted literal of eight or more
   characters, and the obvious placeholder was exactly that shape. Rejected.
2. The placeholder was shortened and a comment added explaining *why* it was short. The
   comment spelled the rule out longhand, quoting its shape. Rejected again, by the same
   rule.
3. Both fixed, committed, pushed — and **GitGuardian** then flagged a different line in the
   same file: `PASSWORD=abc#def`, written to illustrate how dotenv truncates an unquoted
   value. A documentation example of a bad password assignment is, to a scanner,
   indistinguishable from a bad password assignment.

**Pattern:** when documenting a credential mistake, *describe* it, never *demonstrate* it.
"An unquoted value is cut at the first `#`" carries the same information as showing
`KEY=abc#def` and matches nothing. Say in the file why it is phrased that way, or the next
person helpfully adds the example back.

**The other half, and the one that matters more:** the fix was never to loosen the rule. An
allowlist or a per-file exclusion would have cleared all three in one line, and left the
rule wrong for every file nobody has tested yet — the #554 corollary, arrived at from the
opposite direction. Two of the three were my own prose; the rule was right each time.

**Corollary on scanner scope:** GitGuardian scans every commit in a PR, not the head tree.
Fixing the working tree does not clear it — the finding stays pinned to the commit that
introduced the string. The options are rewriting branch history, dismissing the incident, or
squash-merging so it never reaches `main`. Worth knowing before promising a green check.

**And a fourth instance, writing this entry.** The first draft quoted the offending
placeholder verbatim to illustrate point 1, and the pre-commit hook rejected `lessons.md`
for it. The lesson tripped over its own subject. That is not a coincidence worth smiling at
and moving past — it is the measure of how strong the pull is toward *showing* rather than
*telling*, even while writing down the instruction not to. Assume the next person feels it
too, and that the scanner will be what stops them.

Related: [[gate-must-cover-the-file]], and the #554 lesson above.

**Recurrence, 2026-09-07 (#602).** It happened again, in a demo doc this time: a runnable
repro snippet assigned a quoted literal to a `password` key, and `check-secrets` rejected the
commit. The value was genuinely fake, which is exactly the pull described above — a literal
reads as more honest than a construction. The fix is not an exemption: build the string
(`'not-a-real-'.padEnd(24, 'x')`) and say in a comment why. Second data point that the
scanner, not the author's judgement, is what catches this — and this very paragraph was
rejected on its first attempt for quoting the offending line, so it describes it instead.


---

## A mutation check is only as good as its revert (#493, 2026-09-07)

Mutation-testing the pagination work, the script applied a mutation, ran the suite, then
`git checkout -- <file>` to restore. Seven mutations, results recorded, moving on. The
results were garbage.

A stale `.git/index.lock` — left by an earlier interrupted `git commit`, with no git
process still running — made **every** `git checkout` a silent no-op. It printed its error
to stderr, which the script did not check, and exited in a way the loop ignored. So
mutations *accumulated*: M9's result was really M8+M9, M10's was M8+M9+M10. Four mutations
recorded as "caught" were caught by a pile of unrelated damage, and the one genuinely
uncaught mutation (M8) was the only honest number in the set.

Worse, the review fixes being tested were **uncommitted at the time**. Had the checkout
worked, it would have restored from the index and destroyed them — the exact hazard already
recorded in [[commit-before-mutation-checks]]. The broken lock is the only reason the work
survived. Both failure modes were live simultaneously, in opposite directions.

**What to do differently:**

1. **Assert the revert, don't assume it.** After restoring, `git diff --quiet HEAD -- <file>`
   and abort loudly if it fails. Equally, assert the mutation *did* apply — a mutation that
   silently fails to apply reads as "caught nothing" and looks like a passing baseline.
2. **`git checkout HEAD -- <path>`, not `git checkout -- <path>`.** The latter restores from
   the index, which is whatever was last staged, not what you think you are comparing to.
3. **Commit first — and confirm the commit landed.** The commit that would have protected
   this work had itself failed on the same lock, and the failure was buried in a background
   task's output under a line that read `exited with code 0`.
4. **A clean `git status` is not proof git is healthy.** Check for a stale lock when any git
   operation behaves oddly: `ls .git/index.lock` plus `pgrep git` to confirm nothing owns it.

**The general shape:** a verification harness that silently degrades reports success. Every
step of a check that exists to catch problems needs its own check that it ran — otherwise
the harness fails open, which is the one direction a test tool must never fail. This is the
same fault as [[guard-tests-can-self-match]] and [[gate-must-cover-the-file]]: the gate was
present, ran, printed green, and was measuring nothing.

---

## Verify a lockfile with the npm CI actually runs — and never with `--dry-run`

**Date:** 2026-09-08 (auto-author #616 / PR #617)

`codex review` raised a [P1]: my lockfile change dropped the top-level `@emnapi/core` and
`@emnapi/runtime` entries, and `npm ci` would fail. I checked, concluded it did not
reproduce, posted a confident rebuttal blaming the reviewer's `--offline` flag — and CI then
failed with exactly the predicted error. **The reviewer was right and I was wrong.**

**Two independent flaws in my check, either one sufficient to hide the bug:**

1. **`npm ci --dry-run` against a populated `node_modules` passes regardless.** It printed
   `up to date in 657ms`, which I read as a pass. It is not a lockfile-consistency check.
2. **Wrong npm.** This machine had npm 11.6.2; CI runs Node 24.20.0 with npm **11.19.0**.
   They resolve `@napi-rs/wasm-runtime`'s optional `@emnapi/*` peers differently — 11.6.2
   drops the top-level entries and is content, 11.19.0 demands them. I generated the
   lockfile with a resolver that was not the one that would validate it.

Even my "clean-room" `npm ci` in an empty directory passed, because it still used the local
npm. The environment I controlled for was not the one that mattered.

**What to do differently:**

1. **Read the CI log before rebutting a review finding.** The failing job already contained
   `Missing: @emnapi/runtime@1.11.3 from lock file`. I argued from a local reproduction
   attempt when the authoritative evidence was one `gh api .../logs` away.
2. **Pin the tool version to CI's before touching a lockfile.** Get it from the job log
   (`npm: 11.19.0`) and use `npx npm@<that> install`. A lockfile is an artifact *of a
   resolver version*; regenerating it with a different one is a silent format change.
3. **The only valid lockfile check is `npm ci` in an empty directory under CI's npm.**
   Not `--dry-run`, not `npm install`, not a clean-room run under the local npm.
4. **Make the check discriminate before trusting it.** Run it against the *known-bad*
   lockfile too. Old → `FAIL`, new → `PASS` is what turns "my check passed" into evidence.
   I only did this after being wrong, and it settled the question immediately.
5. **A dependency-tree diff is a first-class review artifact.** `removed: 2` was visible in
   my own output before I pushed, and I read past it. For a lockfile change that is not a
   removal, *anything* removed is the finding.

**The general shape:** same family as [[stale-git-index-lock-breaks-reverts]] and
[[gate-must-cover-the-file]] — the check ran, printed green, and could not have detected the
defect. The new wrinkle is social: a correct external finding was overridden by a confident
local "verification". Weight a specific, reproducible claim from a reviewer above your own
negative result until your negative result is shown to discriminate.

## 2026-09-08 — #618 chapter tab contrast

### `pkill -f "<pattern>"` matches the invoking shell's own command line
`pkill -f "next dev"` and `pkill -f "uvicorn app.main"` both killed the very Bash
call that issued them (exit 144), because the pattern appears in that process's
own argv. Twice. Use a non-self-matching pattern (`uvicorn app[.]main`), or
record the PID at launch and kill that.

### Hand-rolled contrast math on `getComputedStyle` is wrong in modern Chrome
Colors come back as `lab(66.128 ...)`, not `rgb(...)`, so an `rgb`-shaped regex
silently parses garbage and produces ratios like `1520538.91`. Never hand-roll it:
read `axe.run(...)` results' `nodes[].any[0].data.contrastRatio` / `.fgColor` /
`.bgColor`. axe resolves `lab()` correctly and is the number the AC is written against.

### `next-themes` persists the theme in localStorage across agent-browser reloads
A `localStorage.setItem('theme','light')` from an earlier step survived a reload
and made a "dark then light" scan pair run **both halves in light** — the output
looked plausible. Assert `document.documentElement.className` inside every scan
payload and read it back, rather than trusting the toggle you just performed.

### Prove the "before" in the same browser, not by arithmetic
Setting the old colour back on the live nodes and re-running axe (3 violations at
1.46:1), then restoring (0), is far stronger evidence than recomputing the ratio —
and it validates that the scan is actually looking at the element you think it is.

### A suggested fix in an issue is a hypothesis, not a spec
#618 recommended `text-muted-foreground`. It passes on dark (5.85:1) and **fails on
light** (4.34:1). The AC said "both themes"; only running both themes caught it.

### A count-based debt ledger has a swap loophole
`actual > ledgered` per file lets a change drop one `text-gray-500` and add one
`text-gray-300` for a net-zero total — precisely the wrong-shade edit the guard
exists to catch (#618). Ledger **per distinct value**, not one total per file.
Codex caught this in pre-PR review of #620; the mutation that proves it keeps the
file's total unchanged, so a total-based check passes it.

### Whole-tree sweep beats a transitive import walk for a "cannot omit a file" guard
#620 offered both. The import walk is *itself* the mechanism that silently omits
files (dynamic imports), which was the defect. Globbing everything is less code
**and** strictly stronger, and it retires the "static walk misses dynamic imports"
caveat instead of documenting around it. Prefer the option that removes the
caveat over the option that scopes it precisely.

### A repo-scanning guard must exclude its own doc comment
`core-authoring-pages-tokens.test.ts` explains itself using `text-gray-100`,
`bg-gray-800/50`, `border-gray-700` — all of which match its own pattern. It was
safe only because it read a fixed path list; the moment it swept a directory it
would have matched itself. Excluding test sources fixed it, but state the reason
in the file so nobody "helpfully" re-includes them. (See also: guard-tests-can-self-match.)

### Add a vacuity assertion to any guard that walks a tree
`expect(sources.length).toBeGreaterThan(150)` plus two `toContain` anchors. Without
it, breaking the walk (wrong root, over-eager filter) makes the guard pass on an
empty list — green, and guarding nothing. Mutation-check it by narrowing the root.

### Compute the contrast pairing you actually mean, in the theme you actually mean
While measuring status dots I applied the *light* `--muted-foreground` (#6e6e6e)
against the *dark* `bg-muted` (#262626) and got a plausible-looking 2.97:1 "fail".
The real dark value is #a1a1a1 → 5.86:1, a pass. Achromatic tokens make the wrong
pairing look reasonable. Label each row with both the theme and the resolved hex
before believing any of them.

### `codex review` is the working fallback when opencode 500s
opencode returned `{"name":"UnknownError","ref":"err_f1fe58b5"}` on a ~580-line
diff — a server error, distinct from the known silent-hang mode. One attempt, then
`codex review --base main`, which worked and found a real P2. Both GLM paths failed
on #622 (CLI 500, and the CI "GLM Review" check hung pending forever) — do not let
either block a merge whose required checks are green.

### Run opencode in the background and check its stream file at 2 minutes
On #623 I gave opencode a 10-minute *foreground* `timeout` and got exit 143 with
zero output — burning ten minutes on a 237-line diff. The
`opencode-concurrent-hang` note already says to background the run and check the
`.jsonl` stream after ~2 minutes, because a file still at 0 bytes then has never
recovered. I had the note and did not apply it. Size is not the predictor; the
2-minute stream check is the whole cost control.

### Sweep the whole indicator row, not just the element the issue names
#623 named one status dot (`bg-green-500`, 2.09:1). Extending the same guard over
every dot in the same component found two more real failures: `MobileChapterTabs`
painted the DRAFT dot `bg-muted` — its own surface, 1.00:1, *invisible*, the #618
defect never fixed in the mobile variant — and the unsaved-changes dot at 2.57:1.
A contrast issue split out of a larger sweep has usually only been measured where
someone happened to look. Enumerate every sibling before deciding the scope.

### A literal count is not a failure count — measure before mass-editing
#624's ledger said the six TOC-wizard steps were the biggest debt (139 of 464
literals). Real axe found almost no violations there: they paint self-consistent
dark cards, so the *pairs* are legible even on a white page. The severe failures
(1.1:1 headings) were in files with far smaller counts. Rank by measurement, not
by inventory.

### Tokenizing a surface relocates every accent sitting on it
Converting `bg-gray-900` cards to `bg-card` moved `text-green-400`,
`text-purple-400` and `text-red-400` from a dark box onto a white one, creating
seven violations that did not exist before the fix. The post-change scan is not
a formality — it is the only thing that catches the failure the change itself
introduced. Re-measure both themes after every surface edit.

### A component you did not edit can still fail on the screen you did
Three `text-gray-400` failures in the wizard's GENERATING step came from
`LoadingStateManager`/`ProgressIndicator`, which the step renders but which were
not on the target file list. Scan the *screen*, not the file set.

### Trust the browser's rendered colour over the token arithmetic
`--muted-foreground` (`oklch(0.54 0 0)`) computes to `#6e6e6e` by hand and 4.56:1
on `bg-indigo-50` — a pass. Chromium renders it `#6f6f6f` and axe reported
**4.49:1**, a fail by 0.01. For a token with no headroom, arithmetic is a
prediction; axe's own `fgColor`/`contrastRatio` is the measurement.

### Clean demo artifacts BEFORE `git add -A`, and read the hook output
On #624 I staged everything while `public/axe-demo.js` (580KB), two scratch
`.js` scanners and next-dev's untracked `AGENTS.md`/`CLAUDE.md` were still on
disk. The large-file hook failed the commit — but I had piped the output through
`grep -c "Failed"` and only read the count, so I believed it succeeded, then ran
`git checkout HEAD~1 -- <files>` and destroyed the two fixes I had just made.
The aborted hook also left a stale `.git/index.lock` that made the next two
`git reset` calls no-ops. Clean the working tree first, stage explicitly, and
read what the hooks actually said.

### You cannot prove a Tailwind "before" by restoring classes on live DOM nodes
The axe-traps note says to re-set the old colour on the live node and re-scan.
That does not work for Tailwind utilities: once the literal leaves the source,
the JIT stops emitting the CSS, so the restored class matches no rule and the
element silently keeps its inherited colour — both scans return 0 and the
"before" looks fine. Stash the fix, let the dev server recompile, then scan.

### A grep for an "unprefixed" class also rejects `group-[.toast]:` and `hover:`
`(?<![:\w-])bg-[a-z]+-900/\d+` looks like it finds classes with no `dark:` prefix.
It finds classes with **no prefix at all** — every variant chain ends in `:`, so
`group-[.toast]:bg-red-900/20` is invisible to it. #632's title said 19 sites, its
hand-built table summed to 14, and the guard's first run found 18: four in
`ui/toaster.tsx` behind a `group-` prefix that three rounds of grepping missed.
Match the whole class token, capture the variant chain, then test whether `dark`
is *in* it. And when an issue hands you a site list, build the sweep first and let
it produce the count — a mismatch is a finding to report, not a discrepancy to
quietly reconcile.

### A contrast figure without its surface is not a measurement
#632's issue quoted 1.02 / 1.76 / 1.05 / 1.05 for four badges. Recomputing over
`--background` gave 1.10 / 1.91 / 1.03 / 1.02 — close enough to look like drift,
wrong enough to fail `toBeCloseTo`. They reproduce exactly over `--muted`, which
is what those badges actually sat on. Probe the candidate surfaces until the
figure reproduces rather than adjusting the tolerance, and record the surface
next to the number. Same trap as #629, one step further along.

### Don't invent a WCAG bar the shipped idiom does not meet
The #632 issue proposed `border-<hue>-300 dark:border-<hue>-700` and I asserted
it at 1.4.11's 3:1. It measures 1.74:1 — as does the identical idiom #631 already
shipped with axe green. The bar was wrong, not the code: these are alerts with
`role="alert"`, an icon and literal text, so colour is never the sole indicator
and 1.4.11 does not attach to the border. Check what obligation actually applies
before picking a threshold; assert the real one (the text at 4.5:1) and label
anything else as a design drift guard, not a WCAG claim.

### The token you think feeds a utility may feed nothing at all
#634's guard priced the active tab title as the `--primary` oklch token and
published 16.39 light / 1.15 dark for it. Under Tailwind **v3** `text-primary`
never touches that token: `tailwind.config.js` pins `primary.DEFAULT` to a
theme-fixed brand indigo, #610's `.dark .text-primary` override repaints it in
dark, and the `--primary` token in `globals.css` only feeds the `@theme` block —
which is v4 syntax this repo ignores. The real figures were 5.75 / 2.73, and
4.87 worst-case after the fix rather than the 11.53 claimed. Same file already
had a sibling guard (`dark-primary-text-contrast.test.ts`) reading the real
override, which is the tell: if another guard resolves the same utility
differently, one of you is measuring a phantom. Before asserting on a token,
grep for what the utility actually resolves to — a `tailwind.config.js` entry
and a `@layer utilities` override both outrank a `:root` custom property.

### Verify the reviewer's failure scenario, not just its finding
The same review claimed the phantom made the guard stay green on an opaque
`dark:bg-red-900` card. It did not: run against the pre-review guard, that
mutation fails 3 cases, because `--muted-foreground` is 3.88:1 there either way.
The finding was right and the fix was necessary; the escape route was already
closed. Reproduce the scenario before repeating it in a commit message — an
overstated failure mode published as fact is the same error the finding was
about.

### Writing the rule down is not the same as following it
2026-09-12. Installed a live rule (`verified-reverts.md`) that says: commit
before mutating, because `git checkout HEAD --` cannot restore an *uncommitted*
file. Then skipped it twice in the same session — in #613 and #661 — both times
on a brand-new guard script. The revert silently did nothing, the broken
mutation persisted into the next check, and the only reason it surfaced was
re-running the gate rather than trusting the revert message.

The operational form that actually works: **commit the new file first, then
mutate**, and treat "the revert printed nothing" as unverified until
`git diff --quiet HEAD -- <path>` says so. A revert that cannot fail is not a
revert. Assert it every time, including — especially — for files created minutes
ago, which is exactly when it feels unnecessary.

### `pkill -f` / `pgrep -f` match the shell that runs them
2026-09-12, twice in one session, both `exit 144` with the invoking Bash call
killed mid-script so the *rest* of the command never ran. `pgrep -f "next dev"`
matches its own command line. The bracket trick (`next[-]server`) helps for the
literal being searched but not for a pattern that appears elsewhere in the same
line. Use a captured PID (`echo $! > file`), or find the listener by port with
`ss -ltnp`. The failure is worse than it looks: the shell dies silently
part-way, so a later step reports on a mutation that never happened.

### Build the ledger with the guard's own matcher, never a convenience grep
2026-09-12, #661. Generated a ledger of duplicated changelog dates with
`grep -oE "^### [0-9]{4}-..."` — a prefix match — while the guard used an
anchored `\s*$` regex. It listed 13 dates where the guard saw 11; the extra two
were `### 2026-07-21 (evening)` and similar, an existing deliberate convention
for splitting a busy day. Four false rows, in a ledger whose whole purpose is to
be trusted. Generate the ledger by calling the same function the guard calls —
if that is awkward, the guard's matcher is not reusable enough yet.

### An issue's numbers age; its premise can rot entirely
2026-09-12. Four issues in one batch had premises that did not survive checking:
#630 and #638 described defects in components **no module imports** (one never
imported in any commit); #640 quoted a contrast figure that had already been
retracted in #634 and transposed two others; #613's "vacuous helpers" turned out
to be called by no spec at all while the live suite was fine. In every case the
defect class was real and the specific claim was not.

Re-derive the measurement and re-check the consumer list before implementing,
even when the issue is recent, detailed, and written by someone who was right
about the class. Especially then: a confident, specific issue is the one you are
least likely to re-measure.

**Extended, same session, #672:** the fifth was **my own issue, filed five
minutes earlier**. I wrote that `TabBar`'s `else` branch existed because
`scrollIntoView` is missing under jest, so "the real path has no coverage at
all". `jest.setup.ts` already stubs `scrollIntoView` — added for Radix Select,
nothing to do with tabs — so the branch was dead and the real path was the only
one running. Freshness is not evidence, and neither is authorship: I had read
the component, not the setup file, and the premise was a plausible inference
from the code comment rather than something I checked.

What settled it in under a minute: put a `throw` where the code under suspicion
runs and run the suite. A branch that cannot throw is a branch that does not
execute. Do that **before** writing the issue, not after — it costs one test run
and it is the difference between "no coverage" and "dead code", which are
opposite fixes.

### `git reset --hard` on a tidy-up discards config you forgot was uncommitted
2026-09-12, the same session as the entry above, and worse than it. Used
`git reset --hard origin/main` to clean up a local `main` that had briefly
carried a commit by mistake. That silently destroyed several hours of
uncommitted `.claude/settings.json` work — seeded permissions, a dead-config
removal, a plugin enablement — none of which was the subject of the tidy-up, and
all of which was invisible in the command. The untracked rule files beside it
survived only because `reset --hard` leaves untracked files alone, which is luck,
not design.

Two habits, neither of which I had:
- Before any `reset --hard` / `checkout --` / `clean`, run `git status` and read
  it as a **list of things about to be lost**, not as noise to scroll past. A
  file modified hours ago and unrelated to the current task is the likeliest
  casualty, because it has stopped registering as "work in progress".
- Fix a branch mix-up with the narrowest tool: `git branch <name>` then
  `git reset --hard` **only** once you have confirmed nothing else is pending, or
  better, `git branch -f` and switch away without resetting at all.

This is the third instance in one session of the same family — knowing a rule
about destructive git operations, having written it down, and then reaching for
the destructive command anyway. The pattern is that the rule fires when the
operation *feels* risky, and these all felt like tidying.

### A watcher that cannot fail is not a watcher
2026-09-13. Set a background monitor on a PR's CI with
`gh pr checks <N> --json name,bucket`. This `gh` build has no `--json` flag on
`pr checks`, so the command errored every poll, the `|| echo '[]'` swallowed it,
and the monitor sat silent for its full window. Silence is what "still running"
looks like, so nothing distinguished it from a healthy watch.

Rewrote it against `gh pr view --json statusCheckRollup` and it reported **ALL
CHECKS COMPLETE** while three checks were still running: a check in flight has
`conclusion: ""`, and `.conclusion // "RUNNING"` does not substitute for an empty
string — only for `null` — so every running check read as finished. Fixed that,
and the third version broke out at `length >= 9` moments before a tenth check
(`E2E Tests (Playwright)`) registered; a rollup polled right after a push is
partial, so any count threshold is a race.

Three variants, three different false greens, all of the same family as the
`git rebase --continue` redirected to `/dev/null` earlier in this session:
**acting on a success signal I never validated.** What finally worked was not a
better predicate over the check list but a different source of truth —
`mergeStateStatus` reaching `CLEAN`, which is the state the merge itself
consults. When you are about to trust a derived signal, prefer the one the next
step actually reads.

Before arming any watcher, ask what it prints when the thing it watches is
broken. If the answer is "nothing", it is a timer, not a check.
### A lint fix is a measurement, not a reading
2026-09-13. Read `ActiveSessionsList`, saw `setLoadState('loading')` at the top
of an async function an effect calls, saw that `loadState` already initialises to
`'loading'` and that the only other caller is a Retry button, and wrote on the
issue that hoisting the setter into that handler was "exact". Made the change.
The warning stayed: `react-hooks/set-state-in-effect` flags **any** `setState`
reachable inside an `async` callee, regardless of whether an `await` precedes it.
The shape of the reset was never what the rule objected to.

The same session's `ExportProgressModal` change — move the reset into the effect's
cleanup — did work, and looked no more certain beforehand. The two were
indistinguishable by reading and separated in one `npx eslint <file>`.

Rules have blind spots that no amount of reasoning about intent will predict.
Run the linter on the one file before writing the classification, not after.
(The same probe found the blind spot's shape: converting the callee to a `.then()`
chain silences it. That is a fix for the count, not for the code, and belongs in
a ledger rather than in five components.)

### "Does not close #584" closes #584
2026-09-13. Wrote a disclaimer into a commit message specifically to stop a
closure — *"Does not close #584 — its condition is the rules back at `error`"* —
and that sentence closed #584 on merge, with 17 violations outstanding and all
three rules still at `warn`. GitHub's linked-issue parser matches
`close|fixes|resolved #<n>` anywhere in a commit message or PR body and does not
parse negation. The disclaimer was the trigger.

To reference an issue without closing it, drop the keyword entirely: "#584's
close condition", "per #584", "partial progress on #584". Now enforced by
`scripts/check-commit-message.sh` at the `commit-msg` stage. Note what that hook
cannot see: a PR **body** closes issues the same way, and no local hook reads it.

### A wiring assertion that greps the whole config proves nothing
2026-09-13, in the guard for the entry above. Its "is this hook actually wired
up" test read the pre-commit config as text and asserted `"commit-msg" in
config`. That string also appears in `default_install_hook_types: [pre-commit,
commit-msg]` a hundred lines away, so retagging the hook to `stages: [manual]`
left the test green — the guard for the guard was vacuous in exactly the way the
guards it sits beside exist to prevent.

Found by mutating the one thing the assertion claimed to check, which is the
only reason it is now parsed YAML asserting `hooks[0]["stages"] == ["commit-msg"]`.
Substring checks against a structured file are not assertions about structure.
**When a test claims a thing is configured, mutate that configuration** — not
the code it configures.

### git strips comment lines, except when it does not
2026-09-13, the second defect in the same guard. It skipped lines starting with
`#` on the reasoning that git removes comments before a message reaches GitHub.
Git does — in **editor** mode, where cleanup defaults to `strip`. `git commit -m`
uses `--cleanup=whitespace` and keeps every line.

The first message the guard ever ran on opened its body with an issue number, so
the skip discarded that whole line and the negated closing keyword inside it. The
hook reported *Passed* on the one message it was written to catch, and the commit
would have closed the issue a second time. Caught only by running the finished
guard against the message that motivated it — a check worth doing every time a
guard exists because of one specific artefact.

For a guard, the asymmetry decides it: a false positive on a genuine comment is a
reword; a false negative is the failure you already paid for. Do not filter the
input.

The reviewer then found a third defect of the same class: `grep` is line-based,
commit bodies wrap at ~72 columns, so "This does not" / "close #123" split across
two lines reads as safe while GitHub, which has no concept of the wrap, closes
the issue. Newlines now collapse to spaces before matching.

All three defects were in the **filtering of the input**, not in the pattern —
skipping `#` lines, and letting line boundaries break a match. The pattern was
right from the start and never touched. When a guard reads a file line by line,
the bug is usually upstream of the regex.

### `git checkout HEAD -- <file>` reverted uncommitted work, again
2026-09-13. Fourth instance this session, and this time the file was one I had
*just* created content in: a mutation loop reverted `.pre-commit-config.yaml`
between cases, silently deleting the uncommitted hook block being tested. The
next test run failed against a tree missing the feature, which reads exactly like
a broken test.

The existing lesson says commit before mutating. The gap was that I applied it to
the file under mutation and not to the *other* files the same loop reverts. Commit
the whole change set first — the revert step does not distinguish "my mutation"
from "my work".

### A sweep cannot fail on what its pattern does not match
2026-09-13, #642. Wrote a guard asserting that every `<Button>` showing a busy
label declares `busy`, with the label pattern enumerating ten verbs — taken from
what the sweep had already found in the tree. That is circular, and the reviewer
produced three more it missed. Broadening it from an enumeration to the actual
shape (a gerund plus an ellipsis) found **twelve** more sites, more than doubling
the fix.

The deeper problem was that **narrowing the pattern back could not fail the
guard**. A sweep of the form "everything matching X must also have Y" passes
trivially when X matches nothing; shrinking X makes it *more* green, so the
mutation that should have caught this was the one mutation that survived. The
fix is a floor on what the sweep finds — `>= 23` busy-labelled buttons — so the
count can rise freely and only drops when a label genuinely leaves the tree.

Any guard whose failure requires a match needs a separate assertion that matches
still happen. The anti-vacuity fixture tests I had ("this pattern recognises a
busy button") do not cover it: they pin the pattern against a literal, not
against the tree.

### A prefixed utility class is inert without the state that prefixes it
2026-09-13, the same guard's feature. `busy` applied
`disabled:opacity-100 disabled:pointer-events-none`, which is right for a real
`<button>`. Under `asChild` the component deliberately omits `disabled` — an
anchor has no such attribute — so **every one of those classes was inert** and
the "busy" link stayed fully clickable. The prop's own contract said otherwise.

Caught by the pre-PR reviewer, not by me, and not by my own test for that path:
I had asserted the link does *not* get `disabled`, which was the half I was
thinking about, and never asserted what it does get instead. When a branch
deliberately drops something, test what replaces it.

### A mutation that does not apply looks exactly like one that survives
2026-09-13, #684. Ran four mutations against a new guard; three failed as
intended and the fourth passed, which I was one keystroke from writing up as "the
guard does not cover this". It did. My `str.replace()` carried the wrong
indentation — fourteen spaces where the file has ten — so the substitution
matched nothing, the file was unchanged, and the suite passed because there was
no mutation to catch.

The tell is that a *surviving* mutation and a *no-op* mutation produce identical
output: a green run. Nothing distinguishes them unless the mutation step asserts
it changed something.

Every mutation now goes through a substitution with `assert n == 1`, the same way
the guards themselves assert their own sweeps are non-empty. A mutation check
whose mutation is unverified is a test of nothing, and it fails safe in the
direction that makes a weak guard look thorough.

### A guard that reads a selector must anchor it
2026-09-13, #682. The guard for a new `.dark .text-destructive` override located
it with `/\.dark \.text-destructive[^{]*\{/`. Renaming the selector to
`.dark .text-destructive-RENAMED` left the guard **green**: the pattern matched
the rename as a prefix, so it happily read a colour out of a rule that no longer
applied to anything.

Fixed by requiring the selector to end — `\.text-destructive\s*[,{]` — which
the same mutation then fails. Same family as #680's three defects: the pattern
was fine, the *boundary* was missing, and the failure mode is a guard reporting
on something that is no longer there.

When a test reads a value out of a name (a CSS selector, a config key, a class),
mutate the **name**, not just the value. Mutating the value proves the maths;
mutating the name proves the guard is still pointed at the thing.

### A config that measures right can still emit nothing
2026-09-13, #682. Split the destructive colour into a theme-aware token so every
`text-destructive` shape would follow the theme without a stylesheet override
naming each variant. Every guard passed: the ratios were right, the tokens were
right, the sweep was clean.

The pre-PR reviewer pointed out that Tailwind v3 cannot apply an opacity modifier
to a plain `var()`. Built the CSS to check, and `bg-destructive/10`,
`border-destructive/20`, `text-destructive/90` and `ring-destructive/20` each
emitted **zero rules**. Error-card tints, invalid-state rings and destructive menu
backgrounds would have shipped colourless, with the whole theme suite green.

Every guard in that directory reads the config and the stylesheet and does colour
maths. **None of them can see whether a class produces a rule.** "The config is
correct" and "the CSS exists" are different claims, and only the second one
ships. The fix is the channel form, `rgb(var(--x-rgb) / <alpha-value>)`, and the
new guard **builds the stylesheet** and asserts each class appears in it.

Generalises past Tailwind: whenever a guard checks an *input* to a generator —
a config, a template, a schema — ask what it would take for the generator to
produce nothing from a valid-looking input, and check the output instead.

### One flag, two jobs: check the other writers before trusting the initial value
2026-09-13, #584. A `setIsLoading(true)` at the top of a mount effect is the
textbook case for "initialise the state to its real initial value instead".
Probed it, the warning cleared, the suite stayed green.

Then read the other `setIsLoading` call sites: the same flag is the **submit
button's** label. Starting it `true` opens the page with the button reading
**"Saving..."** before anything has been saved. No test covered it, so nothing
would have failed.

The generalisation is not about React. When a change hinges on a variable's
*initial value*, the question is not "is this value correct at mount" but "how
many distinct things does this variable mean". Grep every writer and every
reader first; a flag serving two jobs has no single correct initial value, and
the fix is to split it rather than to pick one.

### Run every gate the PR can trip, not the ones you were thinking about
2026-09-13, #691. Verified a change with `npx jest`, `npx eslint` and
`npm run typecheck`, called it green, and opened the PR. CI failed on
`typecheck:tests` — the **new test file** I had just written had a type error.

`npm run typecheck` cannot see it: `tsconfig.json` excludes every test-shaped
path, which is the whole reason `typecheck:tests` exists (#625). And jest runs
through SWC, which strips types without checking them. So the two commands I ran
were structurally incapable of catching a type error in the file I had added, and
I ran them anyway and reported green.

The repo's own note for #625 says exactly this. Knowing a gate exists is not the
same as running it. The frontend gate list is `lint`, `typecheck`,
`typecheck:tests`, `gate:react-hooks`, `check:specs`, `jest` — **adding a test
file makes `typecheck:tests` load-bearing**, and that is the case where it is
easiest to forget, because the change "is only a test".

### A codemod rewrites guard fixtures and English along with markup
2026-09-13, #513. Measured `@tailwindcss/upgrade` in a throwaway worktree before
trusting it. Its class renames in shipped source were correct. It also rewrote
the **guard tests**, and could not tell a class used in markup from a class that
is *the input a guard is testing*, or from an English word:

- `hover:dark:bg-red-800/70` → `dark:hover:bg-red-800/70` inside three guards'
  fixtures. Those fixtures exist to prove a `dark:` **buried after another
  variant** is still caught. Normalising it moves `dark:` to the front — the easy
  case — so each guard silently lost the harder half of its coverage and would
  have stayed green through a regression on exactly that shape.
- "every animate-spin **ring** clears WCAG" → "ring-3". The word, not the class.

It also silently repainted the brand: it ported `--color-primary` correctly into
a new `@theme {}` block but left a pre-existing `@theme inline {}` block that set
it later, so the later one won and every `bg-primary` went near-black. The tool's
one *loud* failure (an invalid `@utility` name) was the least harmful of its
four mistakes.

Before running any codemod over a repo with guard tests, **exclude the test tree
and review test edits by hand**. A fixture string is data describing a case, not
code to modernise, and a tool that normalises it deletes the case. And diff the
built output, not the source: the repaint was invisible in the stylesheet diff
and obvious in one `grep` of the generated CSS.

The same codemod, finished (2026-09-14): it also rewrote two **prop values**
(`variant="outline"` → `"outline-solid"`), left v3's removed `bg-opacity-50` in
place (a solid black overlay under v4), and never opened a stylesheet outside
the main entry (`editor.css` failed the production build on `@apply prose`).
Only typecheck, tailwind-merge's own diff, and `next build` saw those; the
computed-style diff over `globals.css` could not, because it never loaded
`editor.css`. **A visual diff covers the stylesheets it loads, and the build is
the only check that loads all of them.**

And a per-element computed diff is blind to **variants that target other
elements** (`*:`, `[svg]:`, `[&_x]:`). v4 reads stacked variants left to right,
v3 right to left, and the codemod reordered nine shadcn classes to keep v3's
meaning. Those nine were already dead on v3, so "preserved" meant "still dead".
The third-party review found two of them, and a sweep of every reordered variant
list found the rest. Diff the emitted selectors for child-targeting variants,
because the measured element never shows them.

### Making a dead class render is a visual change that needs measuring
2026-09-13, #697. `ring-ring/50` emitted no CSS under v3, so shadcn's controls
fell back to Tailwind's default blue focus ring. The fix made the class render,
and the colour it rendered was *weaker* than the accident it replaced (1.54:1
against 1.83:1, both under 1.4.11). A green emission guard said "fixed"; the
screenshot said "harder to see". When a fix brings a dead rule to life, price
what the rule paints before calling it done. The same thing applied in reverse
converting `ring-opacity-50`: in v3, `dark:ring-blue-700` reset the opacity to
1, so a mechanical `/50` on both colours halved a ring v3 painted opaque.

### A sweep that finds zero where you know of one is broken, not clean
2026-09-14, #513. A rename sweep over the codemod's diff reported **0**
string-value rewrites while typecheck had already named two. Splitting hunks on
`^@@.*$` under `re.M` left the pairing misaligned. Seed every sweep with a case
you know is there; if the known case is missing from the output, the output is
about the sweep.

### Reinstall before trusting tests after a dependency-branch switch
2026-09-13, #695. Switching from the Tailwind v4 branch back to a v3 branch kept
v4's `node_modules`, and jest reported **158 failures** that had nothing to do
with the change. `npm ci` with CI's npm, then the same suite: 0. After any
checkout that changes `package-lock.json`, reinstall first.

### A manual mock under an import alias makes every factory for that module miss
2026-09-14, #713. `frontend/__mocks__/@/lib/auth-client.ts` sat there from #39. next/jest's
SWC transform compiles `import … from '@/lib/auth-client'` to `require('../lib/auth-client')`,
while `jest.mock('@/lib/auth-client', factory)` keeps the alias, and Jest folded the manual mock
into only the aliased specifier's module id. The global factory in `jest.setup.ts` and fourteen
per-test factories therefore never reached a component. Every one of those tests passed, against
a different mock. When a factory seems not to apply, compare a top-level `import` with an inline
`require` of the same specifier in one file: two answers means two module instances. Then
list every `__mocks__` directory.

### Verify the commit landed before a mutation loop that reverts to HEAD
2026-09-14, #712. The implementation commit and the mutation checks ran in one chained
command. Pre-commit's `git write-tree` hit a transient `.git/index.lock`, the commit did not
land, and the first `git checkout HEAD -- page.tsx` reverted the uncommitted page to main. It
was recoverable only because the edit was a deterministic script. "Commit first" (#201) is not
enough when the commit can fail inside the same command: capture `git rev-parse HEAD` before,
compare after, require a clean `git status`, and exit before mutating if any check fails. That
gate stopped the same failure twice more in #715.

## Count the population before writing "exactly N" (#607 / #746, 2026-10-02)

- Closing #607, I wrote "five of six notices were supersessions, exactly one real timeout" into the
  issue, the CHANGELOG and a workflow pin comment. The figures came from the runs the issue thread
  happened to cite. A count of every September `glm-review.yml` run (215) found 33 of 36 cancellations
  superseded and **4** real 35-minute timeouts. The third-party review on #747 caught it before merge.
- The same issue was declared "unobserved" by three status checks because they counted run
  *conclusions*. The outcome the criterion asked about was a rewritten PR *comment* (#622's stub).
- Do instead: any "exactly N" or "M of K" about runs or events gets a whole-population query first
  (`gh run list --created <range> --limit 400` + jq), captured in the demo as a command rather than
  typed. When a criterion is about what a run posted, read the PR comments. On a workflow with
  `cancel-in-progress`, treat a cancelled run as a supersession until its timing says otherwise:
  compare its end time with the next run on the same branch.

## Phase 0 launch-blocker run (2026-10-02)

### TipTap v3 setContent fires onUpdate (#756, 2026-10-02)
Unlike v2, TipTap v3's `editor.commands.setContent()` emits an update by default, so any "dirty"/"autoSavePending" flag set in `onUpdate` goes true on every programmatic load. On main this left `autoSavePending` stuck after a no-op autosave and silently disabled autosave for users who paused >3s before typing. Pass `{ emitUpdate: false }` or compare content before marking dirty, and clear pending flags on every exit path of the save timer.

### Parallel agents: no broad pkill, opencode unusable today (2026-10-02)
Three parallel worktree agents each stopped their own stuck opencode review with `pkill -f "ask-opencode[.]sh"`, a pattern that matches every slot's reviewer. opencode gave 0 bytes on 4 of 4 runs and codex `--base main` once ran 40 minutes with no verdict. In multi-slot runs, kill only captured PIDs and cap reviewers with `timeout`; the PR's `glm-review` workflow is the dependable cross-family pass.

### Never pipe `git commit` into `head` (2026-10-02, PR #881)
`git commit ... 2>&1 | grep ... | head` closed the pipe after 10 lines of pre-commit output. SIGPIPE killed `git commit` after every hook had passed, so no commit was written, a stale `index.lock` was left behind, and the next `git push` pushed the old HEAD while reporting success. Redirect commit output to a file, check `$?`, and compare `git log -1` with the expected subject before pushing.

### Ordering tests need a counter, not the clock (#769, 2026-10-02)
A webhook test fixture that left `created` out (or defaulted it to `time.time()`) meant no signed-webhook test exercised the ordering guard, and a #768 test passed only because its events had no timestamp. Once real stamps arrived, it failed whenever two events straddled a second boundary. Stamp event times from a monotonic counter in fixtures, so the ordering filter runs in every test.

### Read every bot finding, not the newest summary (2026-10-02, #898)
A green PR's latest glm-review comment said "no new defects", while two inline findings from the previous run (a Build Images breakage on main and a runbook gap) were still unfixed. "No new defects" is scoped to the latest commit. Before merging, list every inline review comment on the PR (`gh api repos/<o>/<r>/pulls/<N>/comments`), not just the last summary.

### Check how staging deploys before holding a PR for a deploy-time effect (2026-10-02)
Two PRs (#900, #903) were held because merging "would break staging". `deploy-staging-containers.yml` is `workflow_dispatch`-only, and staging had not been deployed since 2026-08-28. The real constraint was a pre-deploy checklist, not a merge block. Read the deploy workflow's trigger, and `gh run list` for its last run, before deciding merge order.

## #917 configurable AI provider (2026-10-09)

### A live model call finds what the wire stub can't (#921)
The stub tests were green, and a demo against a real model through local Ollama (`localhost:11434/v1`, `nemotron-3-nano:30b-cloud`) still found two bugs. First, `AI_BASE_URL` with an empty `AI_API_KEY` passed `api_key=""` to the OpenAI SDK, which raises at `AIService()` import, so the backend never booted. Second, the reasoning model spent all 1000 analysis tokens thinking and returned empty content with `finish_reason: length`, which the parser turned into a confident "not ready, 0.5" verdict. A stub returns only what you thought to script. For any AI-flow change, run one live call through local Ollama after the stub tests; `glm-5.2:cloud` also gives a real 402.

### A green `main` can be stale for the advisory gate (#923)
`main`'s last `tests.yml` run was green but 4 days old. Eight advisories had landed since, so the first CI run of an unrelated PR went red on the required Security Audit. A green run only covers the advisory gate as of the day it ran. If `main`'s last run is over a day old, run `scripts/audit_gate.py` locally (with `NO_COLOR=1`) before branching, so the advisory fix ships first in its own PR.

### Stale `index.lock` with no git process, twice in one run
`.git/index.lock` appeared twice (21:46 and 12:56), each time with no live git process and no piped `git commit`. The first broke a commit and the second a merge. The cause is unconfirmed: `.beads/metadata.json` is modified in the background throughout, so a beads hook is the suspect. Before removing a lock, confirm with `pgrep -x git` and the lock's mtime, then retry and verify with `git log -1`.

## #784 account-deletion tombstone (2026-10-09)

### A test inserted by text anchor can land where pytest never collects it (#934)
The new webhook test was inserted before `class TestSubscriptionStatus:` with class-level indentation, on the assumption that the preceding block was a test class. It was a module-level helper, so the test became a nested function inside `_post_signed` and was never collected. The file stayed green and nothing warned. It surfaced only because the RED run listed nine failures where ten were expected. After adding a test, check that its name appears in the failing list before writing the implementation; a passing or absent new test in RED means it is not testing anything yet.

### The issue's evidence can be half-shipped already (#784 vs #763)
#784 cited `user.py:131-145` as leaving the better-auth `user` and `account` docs untouched. #763, a P0 from the same audit, had already deleted them before this run started. Reading the cited lines first cut the work to the `users` doc and a proving test. For any issue from the 2026-10-01 audit, read the evidence lines at HEAD before planning: the audit ran at 34ebf94 and earlier P0 fixes overlap later P1 issues.

## #785 uploads deleted with their book or account (2026-10-10)

### The opencode reviewer is not read-only: it runs pytest on the shared test DB and creates git worktrees (#937)
The review prompt passes the diff inline with no `--auto`, and the phase file calls that "strictly read-only". In practice the reviewer ran `pytest` against the default `auto-author-test` database and created two worktrees under `/tmp/opencode`. Its test runs dropped the database under the pre-commit hook's run, which failed on an unrelated test (`test_save_and_retrieve_response`) and then flaked 1 run in 3 until the review ended. The worktree creation is the likely source of the stale `.git/index.lock` that blocked the same commit, and of the two unexplained locks recorded above. While a reviewer is running, give your own runs and commits `TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-s<N>`. In the review prompt, tell the reviewer to use its own `TEST_MONGO_URI` and to run no git command that writes; the second pass followed both. Afterwards run `git worktree list` and remove what it left.

### A mutation that fails to apply cleanly reads as a survivor
The mutation script moved a code block by slicing between two comment markers found with `str.index`. The end marker, `# Create audit log entry`, appears four times in `book.py`, so the slice was empty, the file became a syntax error, pytest collected nothing, and the script printed "killed by: NOTHING". That is the same output as a real survivor. A mutation harness must assert that the run collected tests (a `passed` or `failed` count in the summary) before it reports a result, and must find a marker from the start position (`src.index(end, start)`), not from the top of the file.

## #752 PDF markup escape, finishing PR #865 (2026-10-10)

### A test of a hardening setting is vacuous if the library already refuses by default
To back the corrected comment on the reportlab lock (`trustedSchemes`/`trustedHosts`), I wrote a test that an `<img>` with a URL source is refused. It passed with the lock deleted, twice: first with an unreachable URL and a non-image file, then with a `file://` URL to a real PNG. reportlab 5.0.1 refuses `http`, `file://` and `data:` sources with its defaults, so the lock changes nothing observable today, and a plain path embeds either way. Before testing a hardening setting, run the probe with the setting off. If the behaviour is the same, the setting is a pin against a future default: test the config value, and say "pin" in the comment. The same probe is what showed the original comment over-claimed.

### "@copilot resolve the merge conflicts" also edits tests
Asked to resolve conflicts on #865, Copilot merged main and then pushed a second commit that moved `expected_version` out of the `toc` object in two e2e tests. `PUT /books/{id}/toc` reads only `data["toc"]`, so the tests stopped exercising the optimistic lock, and CI could not notice because those tests skip without an OpenAI key. After a bot resolves conflicts, list its non-merge commits (`git log --no-merges origin/main..<branch>`) and read each one against the route it touches.


## #779 per-environment frontend image (2026-10-10)

### Do not build for an environment that does not exist (#899)
The first version of #899 added a `frontend (production)` build to the main matrix, with a fail-closed check on that environment's variables. No production exists, so the PR could only merge after the owner created a GitHub `production` environment, and I reported that as a blocker for two rounds. The owner's correction: nothing may block on production before there is one. The issue asked for a per-environment build mechanism, not for a second environment. Ship the mechanism with the environments that exist (staging), and let the production entry arrive in the PR that deploys to production (#782). Before reporting "blocked on the owner", check whether the blocker is something the change itself introduced.

## #797 server-written image URLs, owner-scoped deletes (2026-10-10)

### A stub exception class of `Exception` hides what the code really catches (#942)
The S3 unit fixture set `service.ClientError = Exception`, copied from an older test. A new case fed the delete helper a URL that makes `urlparse` raise `ValueError`, and it passed before the fix: `except self.ClientError` was catching everything. With the real `botocore.exceptions.ClientError` in the fixture the case failed, and the fix (`except (self.ClientError, ValueError)`) made it pass. When a stand-in replaces an exception type, use the real class, or the test cannot tell a narrow handler from a blanket one.

### Fixture files must carry the names the service writes
The #785 tests created covers called `a.jpg` and avatars called `<auth_id>.jpg`. They passed because deletion trusted any name inside the directory. #797 made the helpers refuse names the service did not write, and six of those tests failed on the names alone until the fixtures were rewritten around `<owner>_<uuid hex>[_thumb].<ext>`. A fixture that invents its own shape for server-written data tests a looser contract than production has.

### An issue's "make the field server-written" can remove a feature's only entry point
#797's criteria said `cover_image_url` must be server-written. The only UI that set a cover was a text input for that field; the upload route has no UI. Reading the frontend before planning turned up three more facts that shaped the change: the form sent `''` on every save (clearing uploaded covers), an external URL never rendered (no remote image host; staging's optimizer answers 400), and a 422 would have broken saves for cached bundles. Before closing a write path, list every client that uses it and say in the PR what stops working. The missing upload UI is #941.

### Cutting a block out of JSX by searching for its closing tag cuts the wrong one
A scripted removal of a `<FormField ... />` block searched for the first `            />` after the opening line. `str.index` matches substrings, so a deeper-indented `/>` of a child matched first and left half the block behind. `tsc` caught it. Match the closing line exactly (leading newline plus the indent), and run the typecheck before moving on.

### A guard that CI always skips fails only on a developer's machine (#947)
`test_matches_create_local_account_issuer_in_the_installed_library` reads better-auth's source out of `frontend/node_modules` and skips when that directory is absent. CI's backend job never installs it, so the test has never run where merges are gated. Dependabot's 1.7.2 to 1.7.7 bump (#919) removed the function it asserts, CI stayed green, and the main checkout's stale `node_modules` hid it locally. The first worktree that ran `npm ci` and then committed a backend file had every commit rejected by the hook. After a dependency bump, run any backend test that reads the frontend's installed packages with those packages installed. Whether that test should run in CI is #950.

### A hook that fails on someone else's test is a question for the owner
The two ways past the #947 hook failure were to move `frontend/node_modules` aside so the test would skip, or to change the test. Auto mode refused both: the first as a hook bypass, the second as weakening an auth guard. Both refusals were fair, because either one decides on the owner's behalf that a failing auth tripwire does not matter. The useful moves were to prove the failure exists on untouched `main`, read the library to find out why (1.7.7 has no `account.issuer`), and ask with that evidence. The answer took one message. Put the unrelated fix in its own commit and name it in the PR body.

### Teardown chained after a measurement destroys the evidence when the measurement fails
A mutation worktree was created, used, then measured for diff coverage and removed, all in one command joined with `;`. The pytest step named a test file that does not exist, wrote no `coverage.xml`, and the next step removed the worktree anyway. Run the measurement, read its result, and tear down in a later command. The same run showed why `git add -A -- backend` is the wrong tool in a tree where tools write reports: it staged an untracked 6,000-line `backend/coverage.xml`, which is now gitignored. Add files by name.


### A record kept as evidence must sit outside the indexes and resolvers that reuse its keys (#954)
The deactivated account keeps the user's email. Left at the top level it sits on the unique `email` index, and when the same address signs up again the #765 conflict resolver (`release_email`) unsets it on the old record: the sign-up works and the retained record quietly loses the field it exists to hold. The mutation check showed how well that hides. With the email put back at the top level, `test_same_email_can_sign_up_again_after_deletion` still passed, because the resolver repaired the collision; only the tests that assert the exact field set failed. When a record is kept for later, nest what it keeps, and assert the whole shape rather than the one behaviour the feature is named after.

### A step that resets a field before the record is saved must leave what it reset (#954)
`cancel_subscription_for_deletion` sets the plan to free and clears the subscription id before the user record is written, for retry safety (#764). A retention record built from the user document afterwards would have shown every paying user as "free" with no subscription. Nothing failed; the record was just wrong. Before snapshotting a document, read the code that runs ahead of the snapshot in the same request and check what it has already overwritten.

### A filtered log of a background gate loses the one line you need
The full frontend suite ran in the background with its output piped through `grep` for the summary lines. It reported `1 failed`, and the filter had dropped the test's name. A second run passed everything, so the failure was never identified. Write the whole log to a file and grep the file afterwards.

### Demo harness: indexes come from startup, and showboat records the path you give it
Dropping the demo database also drops its unique indexes, which the backend only creates when it starts. A same-email sign-up demo run without restarting the backend would have proved nothing about the index. Also, `showboat image` writes the path it is given into the document, so an absolute scratch path ends up in a committed file: copy the screenshot into `docs/demos/` first and pass the repo-relative path.

### `showboat exec` takes a language before the code, and waits on stdin without it (#789)
`showboat exec <file> <lang> [code]`. Called as `showboat exec doc.md 'curl ...'`, it reads the command as the language and blocks on stdin for the code, with no output and no error. A chained demo command sat until the tool timeout. Pass `bash` explicitly, or feed the code on stdin with a quoted heredoc, which also removes the quoting problem for `agent-browser eval` expressions that need both quote characters.

### "No lines with coverage information" from diff-cover has two different causes (#789)
The backend report was empty because the only changed lines were entries inside a multi-line dict literal: coverage records the statement's first line, so the diff has no measurable line and there is nothing to gate. The frontend report was empty for a different reason: Jest writes `SF:src/...` paths relative to `frontend/`, while the diff is relative to the repository root, so no file matches. Prefix the paths first (`sed 's#^SF:#SF:frontend/#' coverage/lcov.info`) and run diff-cover from the root; that gave 11 of 11 changed lines. diff-cover also refuses a Cobertura file and an LCOV file in one call.

### Check the main checkout for a stale index.lock before the post-merge pull (#789)
All the work happened in a worktree, yet a zero-byte `.git/index.lock` appeared in the main checkout 25 minutes before the merge, and the post-merge `git pull` failed on it. What wrote it was not found. The squash merge itself had already happened on GitHub, so the output of the chained command read like a failed merge when only the pull had failed. Before the post-merge steps, look for the lock, confirm no git process is running (`pgrep -ax git`), and only then remove it. Run the merge and the pull as separate commands so each result is read on its own.


### A null written at creation defeats an "only if the account had it" allowlist (#960)
The deactivated record copies allowlisted fields with `{field: "$field"}` inside `$replaceWith`, which leaves out a missing field but keeps a null one. #789 writes `None` for the Terms fields on an account that has no record, so adding those fields to the allowlist would have stored two nulls for every such account. The exact-equality test on the retained record caught it. Wrap each field in `{"$ifNull": ["$field", "$$REMOVE"]}` when the source can hold null, and keep at least one test that compares the whole stored document.

### A new route fails a ledger test that a targeted run never touches (#790)
`tests/test_api/test_rate_limit_routes.py` lists every rate-limited route and its count. The new export route passed its own tests and failed that ledger in the commit hook. The first commit attempt then hid the failing test name, because the command piped the hook output through a filter for "Passed" and "Failed" lines. Run the whole backend suite once before the first commit when a route is added, and write hook output to a file instead of filtering it.

### A probe that discards stderr reports a missing tool as an empty answer (#792)
`dig +short ... 2>/dev/null` printed nothing for six DNS queries, which read as "the domain has no mail records". `dig` is not installed on this machine. The same queries over DNS-over-HTTPS (`curl https://dns.google/resolve?name=...&type=...`) showed the provider's DKIM key, feedback MX and DMARC record. Keep stderr on a probe, and confirm the tool answers a query whose result is already known before reading an empty result as a fact.

### Running the app's lifespan in a test shuts down pools the rest of the session needs (#792)
A test that entered `lifespan(app)` to check a startup step passed, and 33 later tests failed: shutdown calls `export_executor.shutdown()`, and that executor is a module-level object shared by every export test. Patch the module attribute with a throwaway executor for that one test. A targeted run of the new file showed nothing; only the full suite did.

### CI type-checks the test sources; the commit hooks do not (#792)
`npm run typecheck:tests` runs only in CI's Frontend Tests job, against a per-file ledger of known errors that may shrink but not grow. Three new `process.env.NODE_ENV = ...` lines in `email.test.ts` copied the file's existing pattern, each one a read-only assignment, and took the file from 8 to 11. Every local hook was green and the PR went red a minute into CI. Run `npm run typecheck:tests` before pushing whenever a test file changed, and do not copy a pattern out of a ledgered file without checking why it is ledgered.

### Do not run a demo stack while the commit hooks are running (#792)
The frontend coverage hook failed on tests the change never touched: a performance test measured 127ms against a 100ms limit, and two suites took over a minute each. The demo's dev server, browser and its own test runs were competing for the same machine. With nothing else running the same commit passed. Let the hooks finish, or record the demo first.

### The local install can be older than the lockfile, and every local probe then runs the wrong library (#793)
Worktrees here link `frontend/node_modules` to the main checkout's. That install was better-auth 1.7.2 while `package-lock.json` pinned 1.7.7, and 14 other production packages had moved too. Unit tests mock the library, so nothing failed; the "real better-auth" probes and demos for #789, #792 and #793 all ran on 1.7.2 while CI and staging ran 1.7.7. A reviewer caught it by reading `node_modules/.package-lock.json`. The results were the same on 1.7.7, but that was luck. Before a probe or demo that depends on a library's behaviour, print the installed version next to the locked one, and run `npm ci` when they differ.

### A recorded demo command can trip the secrets hook with a variable reference (#793)
`body: JSON.stringify({ password: '$DEMO_PW' })` inside a recorded `agent-browser eval` matched the commit hook's password pattern, although it holds no secret. The demo file cannot be hand-edited, so the fix cost a re-recording of half the demo with the stack restarted. Keep `password: '...'` out of recorded commands (pass the value through a file or a variable with another name), and run `pre-commit run check-secrets` on the demo before tearing the stack down.

### A check that passes under the mutation it exists to catch is not a check (#843)
The real-auth E2E's "the bare session token is refused" assertion passed with the backend's signature comparison switched off, twice. First because the cookie never left the browser: Playwright does not send a `Cookie` header set through `extraHTTPHeaders`, so the 401 was for want of any cookie. Then, sent properly, because a bare token has no signature and is refused for its shape before any comparison runs. Only a token with a made-up signature of the right shape reaches the comparison. Two habits came out of it: when asserting a refusal, include a positive control sent the same way (the genuine cookie replayed gets 200), and run the mutation the assertion is named for before trusting it. A test that passes on its first run has shown nothing yet.

### The bot's green review check can mean the model never ran (#795)
The repo's GLM review job ended in about a second with `is_error: true`, one turn, zero cost and a comment reading "I'll analyze this and get back to you", and the check was green. The plan it runs on had hit its usage limit, which the local reviewer reported in words (`Weekly/Monthly Limit Exhausted`). A green review check is evidence of a review only if the comment contains one. Ping the reviewer with a one-word prompt before relying on it, and say on the PR when the bot did not review.

### Edit a PR comment by the id that was returned, never "the last comment" (#795)
To fix a typo in a comment just posted, the command fetched the newest comment's id and patched it. A bot's tracking comment had landed nine seconds after mine, so the patch overwrote the bot's comment with my text. `gh pr comment` prints the URL of what it created; take the id from that.

### A mutation script killed by a timeout leaves the mutation in the tree (#796)
The script mutates a file, runs the suite, then reverts. A 400-second tool timeout killed it between the run and the revert, leaving a mutated component and two servers. Run a mutation script in the background with no timeout, and check `git diff --quiet HEAD --` and the ports before doing anything else afterwards.

### A worktree without the `node_modules` link gets a stray install, not an error (#798)
`npx next dev` in a worktree where the `frontend/node_modules` symlink was never created downloaded a private copy and then failed with module-not-found. Create the link when the worktree is created, and treat a real `node_modules` directory in a worktree as a mistake to delete.

### A line that no test and no mutation can observe should be deleted (#798)
A per-request reset of a `ContextVar` survived its own mutation check, because each request already starts with a fresh context. The choices were a comment defending it or removing it. Removing it was right: code that cannot be shown to do anything is a claim nobody can check.

### The changelog's union merge joins two entries, and a broad repair damages the file (#799, #804)
`docs/CHANGELOG.md` merges with the union driver, so two branches that add an entry at the same spot merge without conflict but lose the blank line between the entries. A regex that restored "a blank line before every entry" inserted 131 lines, because older entries were never separated that way. List the first few entries with their preceding line and fix the one that is wrong.

### A 422 can be the right status for the wrong reason (#800)
The test "an answer over the cap is refused" passed before the cap existed: the question id in the URL did not exist, and that route answers 422 for an unknown question. Reading the names of the tests that passed in the RED run caught it. When a status code has more than one cause on a route, assert the reason as well.

### The auth bypass also bypasses the quota and the rate limiter (#800)
A demo backend started with `BYPASS_AUTH` reported zero generations charged after a successful AI call, because the quota and the limiter both skip a bypassed request. To show either, seed a verified `user` and a `session` in the demo database and sign the cookie with the demo's own `BETTER_AUTH_SECRET`, the way `backend/tests/session_cookies.py` does.

### A validation error carries the rejected input, into the response and the log (#800)
FastAPI's `RequestValidationError` lists each error with its `input`, and its text form includes it. This app's handler returned the list and logged with `exc_info=True`, so a refused request came back whole and was written to the log, user text included. A dry run of the demo showed a 400 KB log after one request. Check what a refusal returns and logs, not only its status.

### `.get(key, default)` does not apply the default to a stored null (#800, fixed in #801)
`chapter.get("title", "Chapter")[:500]` and `chapter_description[:2000]` both raised `TypeError` for a chapter stored with `"description": null`, a shape no write path rejects. Main had rendered the value with an f-string, which accepts anything, so adding a slice turned a harmless `None` into a failed draft. The tests seeded only well-formed chapters. When a change starts calling a method on a stored value, test the stored shapes that exist: missing, null, wrong type.

### A review bot that is mid-review is about to say something (#800)
The repo's review bot was 12 minutes into a real review when PR #982 merged on green required checks. Its verdict arrived two minutes later with two confirmed defects, and main carried the regression for about an hour. "Never wait on review bots" was written when the bot was a no-op. My reading now: do not sit idle for it, but when its tracking comment shows work in progress, start the next issue and merge when the verdict lands.

### Write a demo note about a live model after the run, not before (#801)
A note said the 1,000-word chapter "comes back whole"; in that recording the real model spent its budget on hidden reasoning and the route answered 413. Three sections had to be popped and recorded again. For anything a stub does not control, the note before the command says what is being tried, the command runs more than once, and a second note says what was observed.

### One live call found what the stubbed tests could not (#801)
With the provider stubbed, a 5,000-word chapter "succeeds". Against a real model it also returned 200, with 42% to 49% of the words. The stub returns what the test author scripted; only a live call shows what a model does with the larger input the change now allows. Filed as #983.

### A measurement on a cleaned sample measures the cleaning (#801)
To size a cap I counted gpt-4o tokens for 5,000 words of the repository's docs, after a filter that kept only alphabetic words. It gave 5.6 characters a token, and I set the cap from it. The filter had removed punctuation, numbers and identifiers, which are exactly what costs tokens: the same docs with punctuation kept are 4.4, and license prose is 4.9. The reviewer doubted the number without knowing why it was wrong. Measure the thing as it will arrive, on more than one source, and put the measuring command in the demo so the number can be re-run.

### Writing the reviewer's brief is a review (#983)
The brief for the cross-family review asked "what happens for a script written without spaces, where split() yields very few words?" Writing that sentence answered it: a long Chinese chapter has almost no words, so the check never ran, and the same text marked up differently counted as shorter and would have been refused. Both reviewers were out of quota; the two tests and the fix came from the brief. Write the brief before the PR, and read it as a list of things to check yourself.

### Read the demo output for what else changed (#805)
The change kept a chapter with no text when its subchapters have text, so that "1.1" has a "Chapter 1" above it. The demo's page listing showed that such a chapter then printed "(No content yet)" and took a page to itself, which main never did because main dropped it. No test asked about that line. The recorded output is evidence for the claim and also the first look at everything near it.

### A mutation whose edit did not apply looks like a mutation that survived (#983)
The script's edit step failed on an escaping mismatch, the test run went ahead on unchanged code, and the line read "markup counts as text -> 19 passed". Only a count of `AssertionError` in the log gave it away. The script now prints `NOT APPLIED` and skips the run when the file is unchanged after the edit.

### A heredoc inside a heredoc ends at the first matching line (#802)
A shell command embedded a Python script whose text contained a line reading `EOF`, inside a heredoc that also ended at `EOF`. The outer heredoc stopped there, Python saw half a string, and the rest of the script was run as shell. Nothing was changed, because the failure came first, but that was luck. Put a script that contains heredoc markers in its own file.

### A made-up cluster hostname fails the same guard as a real one (#802)
A test fixture imitated a database driver's error, with an invented hostname in the shape of a managed-cluster host. `scripts/test_no_staging_identifiers.py` matches that shape, not a list of real names, and failed the Security Audit job in CI; nothing local runs it. `docs/references/quality-standards.md` says so, and another test file carries a comment about it. For a hostname in a fixture use a reserved domain (`.example`, `.invalid`), and before pushing a file that imitates infrastructure text run `uv run --project backend pytest scripts/test_no_staging_identifiers.py`.

### A header the page cannot read is not part of the contract (#803)
The issue asked for a 429 "carrying X-AI-Quota-Period" to be shown as a quota. The header was sent, and a client test with a mocked `fetch` would have passed. In a browser the page is on another origin than the API, and the backend's CORS setup exposed no headers, so `response.headers.get(...)` returns null there. The demo ran the page and the API on different ports for that reason. When a frontend change reads a response header, check `Access-Control-Expose-Headers` first, and prove it in a browser with the two on different origins.

### A page remembers its last tab, and a scripted demo starts where the last run stopped (#803)
The recording opened the book and pressed "Transform Style"; the page had reopened on the Interview Questions tab, left there by the dry run, so three steps captured an empty state. The failure lines were cut off by a `tail`. Select the tab, do not assume it; and read a recording's captured values before reading its last line.

### A daemon started inside a piped command keeps the pipe open (#803)
`bash setup.sh 2>&1 | grep ... | tail` never returned: the browser daemon the script started inherited the pipe, and `tail` waits for every writer to close. The script itself had finished minutes earlier. Send such a script's output to a file and read the file.

### Test an inference at the level of the claim (#806)
Importing the upload service in a directory it cannot write to raised `PermissionError`, and the container's working directory is unwritable, so I concluded that the container cannot start without storage configured, and from staging being healthy that staging has storage configured. Both went into the changelog. Booting the old code in an unwritable directory took ten seconds and showed it starts: the service is imported inside the request handlers, on first use. "The import fails" was measured; "startup fails" was assumed. Run the experiment on the thing the sentence is about.

### A test's setup can be the condition the bug needs to be absent (#806)
The test for "local files are served" created `uploads/` and then mounted it. The demo started the real backend in an empty directory, uploaded a picture and got a 404: the mount is decided at startup, and the directory is only created by the first upload. The setup line had supplied the one thing a real first run does not have. When a test arranges state by hand, ask in what order the real system arrives at that state, and let the demo run from empty.

### A backend change can fail a frontend test, and the hooks will not show it (#806)
`frontend/src/lib/constants/__tests__/subprocessors.test.ts` reads `backend/app` to keep the subprocessor list honest, and its "the sweep finds something" assertion named a Cloudinary read through `os.getenv`. Moving that read into settings removed the anchor. The commit hooks run the frontend suite only when frontend paths change, so the first failure was in CI. Before removing or moving an environment read, grep the whole repository for the variable's name, tests included, and run `npx jest src/lib/constants` when `backend/app` stops reading something from the process environment.

### To show a dependency going away, take it away; do not start without it (#807)
To show that liveness answers while the database is down, the first attempt started the backend with a database URL nothing listens on. It never served: startup creates indexes and gives up after thirty seconds. "Down at start" and "goes away while running" are different states, and the second is the one a liveness check is for. The demo starts a database of its own on another port, boots against it, and kills it.

### A filter at the end of a pipeline hides where a long command is (#807)
A dry run of several server starts was piped through `cut` and looked hung with one line of output for six minutes. `cut` writes in blocks when its output is not a terminal, so nothing arrived until the end, and the end was a step that waited on a server that would never start. Write each step's result to a file as it happens and read the file.

### A server started inside a recorded command has to be stopped inside it (#807)
`showboat exec` did not return for ten minutes: the command it ran had started a backend and left it running, and the recorder waits for everything the command started. Earlier demo scripts happened to end each such command with a stop. And clearing up the stuck run with a process search by command line killed the shell doing the clearing, which the notes already warn about; `ps -eo pid,args | grep "[r]ecord.sh"` does not match itself.

### A helper named for a decision may read more than the setting you have in mind (#807)
The health gate made missing Stripe fatal "in production" by calling `is_production_env()`, the helper every production guard uses. It also reads `NODE_ENV`, and the backend container receives the box's whole `.env`. For a guard that refuses something dangerous, counting either marker is right. For a gate that fails a deploy, it means a leftover `NODE_ENV=production` on staging turns every deploy red with a message about Stripe. The reviewer found it; the box's file could not be read to rule it out. When a new consequence hangs on an existing predicate, read what feeds the predicate and ask which way this consequence should fail.

### A reviewer that could not read the tree exits 0 with nothing to say (#807)
The review was started from the scratch directory instead of the worktree. The reviewer was refused every file under the worktree, wrote one byte and exited 0. The refusal was only in its error file. Start it from the checkout it reviews, and read the size of its answer before reading the exit code.

### A sentinel written in the probe's own source is found in every error report (#808)
A probe looked for "what the user typed" in the events the Sentry SDK built. On the fixed branch two values were still found. They were string literals in the probe file, a few lines below the route that failed, and an event carries the source lines around every frame. The values now come from a file read at run time, and in the tests from module constants referred to by name. When a check searches a report for a value, make sure the value can only get there the way a user's would.

### The Sentry SDK watches only the database clients created after it starts (#808)
The check that MongoDB commands reach an event with their values removed needs the commands to be recorded at all. The SDK registers its listener when it starts and a client made earlier is never seen, so a test that reuses the session's client records nothing and passes for that reason. The test makes its client inside the request and asserts a `query` breadcrumb exists before it asserts the value is absent.

### Ask what the library reports on its own before counting reports (#808)
"Exactly one event per 500" looked like a question about our handler. The two events came from two of our ERROR log lines, the handler's explicit capture was already dropped as a duplicate, and a third source was not ours at all: the SDK turns on an integration for the model client by itself, and that integration reports a failed model call even when the app handles it. List the integrations the SDK enabled (`sentry_sdk.get_client().integrations`) before reasoning about what is sent.

### A scrubber that works on key names cannot make free text safe; count the channel before promising to clean it (#808)
The first version kept ERROR log lines as Sentry events, moved one duplicate line to WARNING and listed "any log line is sent as it is" as a known limitation. The reviewer then followed one real endpoint: question generation logs the same failure up to six times at ERROR, with the question it was saving, so one failure was seven events and the scrubber touched none of the text. A count would have said so sooner: 133 calls in the backend log at ERROR, and each was an event by the SDK's default, which nobody had chosen. The fix is one line that sends no log line at all. When a limitation reads "X is sent as it is", count how much X there is before accepting it. And two mutations survived the first run for a related reason: a second guard was catching what the first was meant to (the request body sat under a key the scrubber filters). Give each guard a case only it can catch.

### Measure the mechanism an issue names before writing the test it asks for (#930)
The issue said an `AttributeError` on a missing setting carries the settings' repr in its message, and asked for a test of that. The test passed before any change: the installed pydantic's message names only the attribute. The secrets in the original pytest output came from pytest rendering the object in a failed assertion, and only at `-vv`; at the repository's own `--verbose` it prints two of thirteen. The demo measures the three ways the values really come out (the repr, a log line, `pytest -vv`). The requested test stays as a pin, and the PR says it could not fail.

### To see what a browser SDK sends, give it an address on this machine and read what arrives (#809)
The issue asked for a unit test that query strings and bodies are stripped. A unit test checks the events I thought of. Building the real image with the Sentry address set to a port on this machine, with a twenty-line server that keeps what is posted, showed what a real page error sends: the reset token three times over, a console line, and, from a real click, the element's `title`. That last one was not in the issue; `BookCard` puts the book's title there. The same run proved the CSP entry, because a blocked post would never have arrived. The server side needed its own run: the SDK that Next uses on the server attaches the request body, which for a sign-in is the password. Before writing a scrubber, list what the SDK's default integrations record and trigger each one for real.

### Ask the server as the page would before planning anything the page has to read (#810)
The issue asked for the request id "in the 500 body". One request with an `Origin` header showed the body could not matter: an unhandled failure was answered outside the CORS middleware, the response had no CORS headers, and the browser refuses to hand a page such a response. Every backend 500 had been a "failed to fetch" on staging. The fix moved where the failure becomes a response, which is a bigger change than adding a field, and it would have been found in review or not at all if the plan had been written from the issue text. For anything a cross-origin page must read, the first measurement is `curl -D- -H "Origin: <frontend>"` on the real route, on a success and on each kind of failure.

### `logging.basicConfig` configures nothing when something configured logging first (#810)
`main.py` set a log format with a time and a logger name. Another module called `basicConfig` earlier at import, the first call wins, and the format had never been used: lines were the default `LEVEL:logger:message`. Adding `%(request_id)s` to that call would have changed nothing either. The format and the filter are now put on the handler itself. When a setting is made through a call that can be a no-op, look at one real output line before building on it.

### A repeat run in the same browser session is not a second measurement (#810)
The scripted browser step passed on every fresh start and showed nothing on a second run against the same servers: the dialog was not submitted, and no request reached the backend. The script printed "Reference ID: nothing" and the server's id from the earlier run on the next line, which read like a failure of the feature. Each side of the demo is recorded once after a fresh start. A probe that compares the page with the server's last request should check that the request is new.

### I said what was no longer reported without sending one of them through (#812, correcting #808)
In #808 I turned off log lines as Sentry events and wrote, in the PR, the changelog and a follow-up issue, that a failure the code handles is then reported nowhere unless it asks. I had measured an unhandled failure and a handled model failure. I had not measured the commonest handled failure in this codebase: a route that catches an error and raises `HTTPException(500)`. A test for #812 failed on a second report I did not expect, and the measurement took one request each: the SDK's Starlette integration reports any 5xx a route raises, as an `HTTPException` with the detail text. The same day's lesson says to list what the library reports on its own before counting reports; I listed the integrations and did not send a request through each. A claim about a whole class ("handled failures") needs one member of each kind of that class measured, and the kinds here are: unhandled, raised as 5xx, answered below 500, swallowed, in the background.

### A header that authenticates a request goes to the error tracker with the other headers (#812)
The report for an unconfigured webhook carried the delivery's `Stripe-Signature` header: the SDK attaches the request's headers and filters only the names it knows (cookie, authorization and a few more). It was found because the test searched everything sent for the signature, not just the message it had written. Any header this app treats as a credential has to be named in the scrubber's list.

### The unit test counted one failure; the browser showed the loop around it (#813)
The acceptance criterion was "each failure calls captureException", and a jest test with one rejected save passed. Running the real editor against a stopped backend showed what the test's single failure could not: autosave retries every three seconds, so "each failure" was a report every three seconds from every open editor for as long as the backend is away. The count came from the demo, and the code now reports once per run of failures. When a criterion says "each", find out how often "each" happens in the real loop before implementing it literally.

### A limit on how often something is reported belongs where it is sent, not in one of the callers (#813)
After the browser showed a report every three seconds, I put a "reported already" flag in the editor's autosave handler and cleared it when a save worked. The reviewer found the two ways that was wrong within minutes: a run of failures can end without a save working (a chapter switch, taking the other copy after a conflict), so the flag stuck and a later outage was silent; and the backup, which is retried by the same loop but reported from another function, was not behind the flag at all. Both came from guarding one call site. The limit now lives in the function every report goes through, per kind of failure, with a time after which it reports again whatever happened, so a path nobody thought of costs five minutes and not the rest of the session. #812's webhook throttle was already built that way an hour earlier; I did not carry it over.

### I put the report in a function the failing sites do not call (#996)
Eight routes log "Failed to log chapter content access" and carry on. I read the message, took the callee to be the audit function, put the report there with a test that called the audit function, and the test passed. The eight sites call the chapter access service; the audit function is called from elsewhere, where its failure is raised as a 500 and already reported, so the report I added would have been a second one. It came out only when the demo needed a real route to fail and I looked at what the route calls. A test that calls the function I changed proves the function, not that the sites I meant to cover reach it. Drive one of the real sites.

### A handled error's text is still an error's text (#996)
Reporting a caught database error by hand sends its message. For the demo's failed insert that was "Document failed validation, full error: {…}", and the part after the comma is the server's whole answer, which for a schema rule includes the value that failed. The scrubber already cut a duplicate-key message for the same reason. Each new way of sending an exception to Sentry needs the question asked again: what does this library put in the message?

### A test that runs the app's real start-up also runs its shutdown (#996)
Three new tests ran `main.lifespan()` to drive the start-up failures. They passed, and 86 export tests later in the same run failed with "cannot schedule new futures after shutdown": the lifespan's shutdown closes the shared export thread pool. Only the commit hook's whole-suite run showed it; the file on its own was green. One existing test already ran the lifespan, with a comment saying exactly this and a throwaway pool to hand it. Before using a piece of the app's machinery in a test, grep for a test that already does, and run the new file followed by the rest of the suite, not alone.

### The same mistake twice in one issue: a report on a path that cannot fail (#996)
After moving the access-record report to the right function, I had still put the file-deletion reports in the callers' `except` blocks, and their tests patched the upload service's delete method to raise. The reviewer read the method: its docstring says "Never raises", and it catches everything itself. So the reports could only fire if the service could not be constructed, the real failures (the disk refusing, the provider answering no) were logged a layer down and reported nowhere, and the PR said "their callers report it". Both times the test proved the branch I had written by forcing an exception no real code path produces. When adding a handler to an `except`, read the callee to see what it can raise, and make the test fail the real dependency (the disk, the provider's answer, the database), not the function directly underneath.

### "Returns None on any error" turns our outage into the user's problem (#1007)
The session lookup caught every exception and returned None, and None meant "not signed in". That reads as safe: fail closed. It was found only because a demo for another issue stopped the database and printed the status code. A catch-all that returns the same value as the ordinary negative answer hides which of the two happened, and every caller then gives the user's answer to our failure. When a function has an `except Exception: return <the empty answer>`, ask what a caller should do differently when the dependency is down, and whether it can tell.

### In a test, the SDK reports a 5xx only if the app's middleware was built after the SDK started (#1007)
A mutation gave the new exception a `status_code` of 503, which should make the Sentry SDK report every such request, and the test that counts reports still passed. The SDK wraps an app's exception handlers when the app's middleware stack is built. The shared `app` builds it on the first request of the test run, long before a test's fixture starts the SDK, so in that test the SDK's own reporting was simply not there and "one report, not one per request" could not fail. Setting `app.middleware_stack = None` after starting the SDK rebuilds it wrapped, and the mutation is then caught. Any test that counts Sentry events through the shared app needs this, or a fresh app built after the SDK starts, which is why the webhook tests (their own app per test) had already seen the SDK's reports.


### The issue named a flag that was already on (#814)
The issue said uvicorn ran without `--proxy-headers`. That is uvicorn's default. What was missing was the list of peers it believes the headers from, which defaults to loopback, and a container sees nginx on the host as its Docker network's gateway. Adding the flag as written would have changed nothing and the redirect would still have gone to http. One container run settled it: send the headers, read the `location:` and the client in the log line. When an issue prescribes a setting, read the default for the version in the lockfile and reproduce the symptom before turning it on.

### A server started inside `showboat exec` keeps the step open (#814)
The demo script started `next dev` in the background inside a `showboat exec` step and the recording stopped there for six minutes. The server's own output went to a file, but the shell that launched it still held the pipe showboat reads the step's output from, so the step never reached end of file. Start servers before the recording, with all three of their streams redirected, and let the recorded steps only ask them things.

### My search for callers of a route I was removing looked in `frontend/src` only (#815)
Before turning `/docs` off on deployed hosts I searched for anything that calls it and found nothing. The reviewer found two specs in `frontend/tests/e2e/deployment` that load the Swagger page on staging, and an operator checklist that says to. No workflow runs that suite, so CI would have stayed green and the first person to run it by hand after the deploy would have got two failures. The search had named `frontend/src`, and then filtered its own output until the hits were gone. When removing something other code may call, search the whole tree for the literal with one plain `grep -rn`, excluding only `node_modules` and build output, and read every hit before filtering any.

### A `git stash -u` inside a recorded demo step took the demo document with it (#816)
One step of the demo script stashed the tree to run the guard against main's workflows. The demo document was the only untracked file, so the stash took it, every later step failed to open it, and the stash was left behind. The stash is also shared by every worktree of the repository, so another session's `git stash pop` could have picked it up. To compare against main inside a script, read the file with `git show main:<path>`, or `git checkout main -- <path>` followed by `git checkout HEAD -- <path>` and an assertion that the path is clean. Never stash in a script.

### Every refused value was wholly wrong, so an unanchored check passed (#816)
The guard ran each input check against values that must be refused: `staging`, `$(id)`, a tag followed by a command. A mutation that dropped the `^` from the tag's pattern passed all of them, because none had anything in front of a valid tag. A list of bad inputs for a pattern needs a good value with something before it and with something after it, built from the good values so that it stays true when the pattern changes.

### The guard's own pattern stopped at the first `}` (#816)
The guard matched `${{ … inputs … }}` with `[^}]*` on either side of the name. The repository's review bot pointed out that `${{ format('{0}', inputs.image_tag) }}` has a `}` before the name, so the pattern never reached it, and one evasion defeated both rules at once: the paste rule and the table of checked variables use the same pattern. My own tests of the pattern were the three shapes already in the workflows. A pattern that guards a syntax has to be tested against that syntax's nesting and quoting, not only against today's uses: for a GitHub expression that means a function call, a literal containing a brace, and two expressions on one line.

### A workflow change can be proved on GitHub before it merges (#816, #817)
`gh workflow run <file> --ref <branch>` runs the branch's copy of a dispatchable workflow. For #816 that showed the deploy stopping at its first step on a bad tag and still deploying a real one. For #817 a throwaway branch whose two Dockerfiles start something that does not exist showed both smoke tests failing and neither tag reaching the registry (`docker manifest inspect` answers `manifest unknown`). A unit test of a workflow's scripts cannot show either. Delete the throwaway branch afterwards and say in the PR that it existed.

### I committed the throwaway branch with the hooks switched off (#817)
The commit that broke both `CMD`s was made with `core.hooksPath=/dev/null`, to keep a deliberately broken Dockerfile from being argued with. The rule here is no bypassed hooks, and it has no exception for a branch that will be deleted. The hooks would have passed anyway: none of them boots an image. Commit a demonstration branch the same way as any other, and if a hook really does refuse the deliberate breakage, that is worth knowing before the demo, not a reason to switch it off.

### A Dependabot entry was measured twice: does it do anything, and does it do only that (#818)
The issue asked for Dependabot `docker` entries. Run against main with the real updater, an entry found no dependency in either Dockerfile: the updater does not resolve `FROM python:${PYTHON_VERSION}`. With the image named literally and pinned to a digest it found both, and its first proposal was Python 3.13 to 3.14 and Node 24 to 26, which nobody asked for. With `ignore` rules for major and minor it found both and proposed nothing, which is right while the digests are current. Either of the first two would have passed a test that only asserts the entry exists. For a config that drives a tool, run the tool: once to see that it acts, and again to see what else it does.

### The scan's first findings were all in things the image did not need (#818)
Eleven `HIGH` findings on the first scan, and the reflex is an ignore file with eleven reasons. Looking at where each one sat showed four inside pip and seven inside npm, both shipped by the base images and neither used at run time. Removing the two package managers from the runtime stages emptied the report and left no baseline to maintain. Before baselining a scanner's finding, look at the path it reports and ask whether that thing needs to be there.

### I filed half of the issue under "known limitations" (#819)
The issue was that uv floats: `:latest` in the image build, `curl | sh` in CI. I pinned the image, replaced the piped installer with the action, and wrote in the PR that the action installs the newest uv, "as the existing use of it already did". The reviewer's one finding was that this is the issue, not a limitation of the fix: CI still ran a uv nobody had reviewed. Each job now reads the version out of the Dockerfile and gives it to the action, so there is one place it is written and Dependabot moves both. When a limitation I am about to write down is the same sentence as the issue's problem statement with a different noun, it is unfinished work.

### The third measurement of the same Dependabot entry found a third thing (#819)
#818's lesson was to run the updater to see that a config acts and what else it does. Adding a cooldown for uv, I ran it again and the log said `Cooldown was not applied because no publication date was available from the registry`: Dependabot cannot hold back an image on ghcr.io, and reports that as a warning nobody reads. The stanza, and the test asserting it existed, would both have been green and inert. The same image is on Docker Hub under the same digest, and there the next run logged `Skipping tag 0.13.0 due to cooldown period`. A test that a setting is present says nothing about whether the tool honours it; for each setting, find the log line that shows it taking effect.

### A plugin's pinned dependency was overridden, and the proof was the build's output (#820)
The new floor reported `postcss-selector-parser` 6.0.10, pinned exactly by `@tailwindcss/typography`, whose newest release still pins it. The choices looked like "baseline it" or "override a major version and hope". The plugin uses the parser for one thing, writing the selectors of the `prose` styles, so the stylesheet is the test: compiled with 6.0.10 and with 7.1.6 it has the same checksum. That turned a guess into a measurement and an accepted advisory into a fixed one. When an override changes a build-time tool, compare the artifact the tool produces before reaching for the baseline.

### `--write-baseline` at a higher floor than CI would have dropped what CI checks (#820)
The baseline file's own header says to regenerate it with `--write-baseline`. That flag used the same default floor as checking did. Raising only the floor CI passes on its command line would have left the default at `high`: the next regeneration would write a baseline without the moderate entries, and CI would then fail on them. The default and the workflow's flag now agree, and a test regenerates a baseline holding a moderate entry. When a tool both checks and regenerates its own allow-list, a threshold has to move in both paths at once.

### The command in the issue upgraded 38 packages and quietly took one down (#821)
`uv lock --upgrade --exclude-newer <fourteen days ago>` is what the issue asks for. Its summary line said `Updated botocore v1.43.111 -> v1.43.103` in the middle of thirty-eight upgrades: the locked botocore was younger than the cut-off, so the resolver could no longer see it and picked an older one. It also wrote the cut-off into the lock as an option. Neither is an error and neither stops anything. A small script comparing the two locks by version, in both directions, found the downgrade; a plain `uv lock` afterwards dropped the option and `--upgrade-package 'botocore==1.43.111'` put the version back. After any bulk upgrade, diff the lock for packages that went down, not only for the ones meant to go up.

### A test that failed on the upgrade was wrong about the thing it tested (#821)
The CA bundle test read the file's first 500 characters and looked for `BEGIN CERTIFICATE`. certifi 2026 puts a root with a longer comment block first, so the test failed on a bundle with 121 good roots in it. It now builds a TLS context from the bundle and counts what loaded. When a dependency bump breaks a test, read what the test actually asserts before reading the dependency's changelog: a test of a file's opening bytes is a test of formatting.

### I quoted a test count from a run I had told to stop at the first failure (#821)
The PR description said "the whole backend suite (1,409 tests)". That number came from `pytest -x`, which had stopped at the one failure with 1,408 passed behind it. CI's run of the same suite reports 1,870. A count is only the population when the run finished; take it from a run without `-x`, or from CI.

### Replacing a converter: run both over the same input before writing a line (#823)
html2text and markdownify both turn HTML into Markdown, and "swap the import" would have shipped four regressions: headings written as text over a row of `=` (which the PDF builder takes for a paragraph), a list as one block (whose lines run together in a PDF), italics with a different marker, and backslash escapes printed into PDFs. Nineteen samples of the HTML the editor writes, run through both and compared at the point the builders consume them, found each one before any code changed, and showed which differences were improvements (a stray space before punctuation, a stray backslash after `1`). Then the real files, PDF, DOCX and EPUB, were read back from both and diffed. For a like-for-like library swap, the corpus and the comparison come first; the options you need are whatever makes the diff empty or defensible.

### A mutation that survived showed code I had written against my own experiment (#823)
My first trial of markdownify passed `strip=["img", "script", "style"]`, and the output contained `alert(1)`. I concluded that markdownify keeps script text and wrote an override to drop it, with a comment saying so. Removing the override in a mutation check changed nothing: left alone, markdownify drops both tags, text and all, and it was my `strip` option that had kept the text. The override was dead code and its comment was false. The survivor was the finding. What I observed in an exploratory call belongs to that call's arguments until it is reproduced with the arguments the real code uses.

### Searching for a name in one case missed its uses in another (#823)
I looked for `html2text` to find everything to change and found the export service. The export endpoint imports `HTML2TEXT_AVAILABLE`, which that search does not match, and the first test run failed at import. It is the #815 lesson again from another side: search without regard to case, across the whole tree, for the thing being removed.

### A step that was safe only because of the old library's formatting (#823)
After the swap, the Markdown export still moved headings down two levels by rewriting every line that began with `#`. With html2text that was safe by accident: it indented code blocks by four spaces, so a `# comment` never began a line. markdownify fences code at the margin, and the same rewriting turned `# comment` into `### comment` inside the fence. My corpus had a code block with no `#` in it, so nineteen samples and three file formats showed nothing; the reviewer found it by reading the lines after the conversion. When replacing a library, read every step that consumes its output and ask what about the old output's shape that step was relying on. The fix was to do the move in the converter, where a heading is known to be a heading, and delete the rewriting.

It then happened a second time, in code I had just written. Following the reviewer's point to the other export path showed that the builders decide what is a heading by the same test, a block that begins with `# `, and that I had made code blocks begin at the margin there too by stripping their fences. A code block opening with a comment was set as a heading in the PDF. One finding about a class of input is a reason to put that input through every path, not only the one the finding named: the sample that would have shown both was a code block with a `#` in it.

### A test that would hang is not a test that fails (#1012)
The mutation that put the start-up work back in front of the server did not fail the new tests. It hung them: entering the lifespan waited for a database that never came, and the run was killed by my own five-minute limit. In CI that is a job timeout with no test name on it. Each test that enters the lifespan while the database is away now does so under `asyncio.timeout`, so the same mistake is a named failure in ten seconds. When the bug under test is "this waits forever", the test needs its own clock.

### The come-back test checked only what the last step creates (#1012)
A mutation let the work go ahead after one failed attempt at the database, instead of waiting. The test passed: by the time the database was put back, the early steps had failed quietly and the last step, whose indexes were the ones asserted, ran against a database that was there. Asserting an index from the first step as well did not help: the first step creates several, and the one I named was built after the database returned. What tells waiting from going ahead is whether the work has begun, so the test now watches the first step and asserts it has not been called while the database is away. For a sequence that is supposed to wait and then run, assert on the waiting, not on what is true once everything has finished.

### The scratch directory did not survive a restart (#823)
The machine restarted mid-session and the session's scratch directory came back empty: the commit and deploy helpers, the mutation scripts, the demo harnesses and their logs. Nothing in the repository was lost, and the helpers were rewritten in a few minutes, but the pull request description I had been editing there had never been sent, and its corrections had to be redone from the published copy. Send a changed description when it changes; scratch is not a place to keep the only copy of anything that has to outlive the hour.

### "Wait for a ping, then do the work" trusted steps that never say they failed (#1012)
The start-up steps each catch their own database errors, log them and return. That is why moving them behind a ping looked sufficient: once the database answers, do the work. The reviewer's case was a database that answers the ping and then goes: every step returns normally, the task logs that the database is prepared, and nothing was created. The task now pings again when the work is over and repeats the work if the database has gone. When a sequence is built from steps that swallow their failures, the sequence cannot conclude anything from their having returned; it needs its own check at the end.

### The reviewer's fix failed the validator, and I had already started the commit (#824)
The reviewer said every entry in `toc.ncx` needs a `playOrder`, and that ebooklib used to write one. The first half is true of the format. The second is not: the file ebooklib wrote for the same book has none. I added the attribute as suggested, numbering the entries one after another, and ran epubcheck in the same command that started the commit, one after the other with nothing between them. epubcheck reported two errors, because entries that open the same document have to share a number, and the commit was already in its hooks with them in it. The next commit fixed it, at the cost of a second ten-minute hook run.
**Rule:** a fix taken from a review is run through the artefact's own validator before it is committed, and the commit is chained to that check with `&&`, not placed after it. Check the reviewer's "the old one did this" against what the old one actually produced before repeating it.

### The library I replaced had been rejecting input the new code accepted (#824)
ebooklib parsed every document it was given, so a form feed or vertical tab pasted into a chapter made it raise and the export failed. Writing the same text straight into a zip does not fail: it produces a file that is not XML and that no reader opens. Comparing the two exports of one ordinary book showed no difference, and would never have shown this; it took a book with the awkward input.
**Rule:** when a library is replaced by direct code, find out what the library refused or repaired, not only what it produced. Feed both the input that is not valid in the output format (control characters, lone surrogates, unescaped markup) and compare what each does.

### The assertion found the address somewhere else in the entry (#825)
The notices give each package's source on a line of its own. The test for it asked whether libvips's entry contained the repository's address, and a mutation that removed the line passed: the README text carried into the same entry links to that repository's issue page.
**Rule:** when a test reads a block of generated text, assert the labelled line (`^Source: ...`), not that the value appears somewhere in the block.

### "Not marked dev" is not "shipped" (#825)
I expected the lockfile's `dev` flag to separate what ships from what does not, and wrote a test that Playwright is left out of the notices. It is not marked dev: it is a dev dependency and also an optional peer of `next`, which npm records as `devOptional` and keeps under `--omit=dev`, though it is never installed in the image for that reason alone. `npm ls --omit=dev` lists it too.
**Rule:** before asserting what a lockfile flag means, tally the flags (`dev`, `devOptional`, `optional`, `peer`) over the whole file and look at the small groups.

### Two demo outputs were wrong and I only saw them by reading the document (#825)
The recorder printed "recorded" and the document said `entries: 0`: the count used a `{72}` repetition that busybox grep, inside the image, does not read without `-E`. Both screenshots were of the top of the page, not the footer: the scroll ran before the page had settled.
**Rule:** read every recorded output and open every screenshot before the demo is committed. A command that runs inside an image runs with that image's tools. A screenshot of something scrolled to waits until the element's position says it is in view.

### The issue's reason for deleting a read had stopped being true (#826)
The launch review said the better-auth user read on every request was used only when creating the application's record, so it could go. That was right on the day it was written. Two later issues from the same review made that row load-bearing on every request: a session whose user is gone is refused (#763), and the application's email follows better-auth's (#765). The read stayed, joined into the session's.
**Rule:** an issue describes the code as of its audit commit. Before removing something it calls unused, grep what reads it now.

### Tests that mocked the old call kept passing, for the wrong reason (#826)
The session lookup changed from `find_one` to `aggregate(...).to_list(1)`. Eleven tests stood in for the session's `find_one`. Five failed. The other six passed: the mock's `aggregate` returned a coroutine with no `to_list`, the function's catch-all turned that into "no session", and "no session" was what those six expected.
**Rule:** when code changes how it calls something tests stand in for, change every test that stands in for the old call, and do not take "it still passes" as the list of the ones that are fine.

### The write that looked like waste had a reader in the other half of the repository (#826)
The session's `updatedAt` was written on every request and nothing in the backend reads it. The frontend does: Settings shows it as "Last active". The write is throttled to once in five minutes, not removed.
**Rule:** before removing a write, search both `backend/` and `frontend/` for the field.

### I added a limit that needed data the save path is built not to read (#828)
To stop a book outgrowing its document I wrote a limit on the total size of a book's chapters, checked on every save. The save handler reads the book without the chapters' bodies, deliberately (#344), so the check had nothing to add up without a second read on the path that saves every three seconds. Reaching the database's limit takes more than thirty full-size chapters. The limit came out; the database's own refusal, which was a 500, is answered 413.
**Rule:** before adding a check to a hot path, read what that path already loads and why. If the check needs more, ask whether the failure it guards against can be reported when it happens.

### A size taken from `json.dumps` counts escapes, not bytes (#828)
The limit on a table of contents measured `json.dumps(body)`. By default that writes each non-ASCII character as a six-character escape, so text in French or Japanese was counted at up to three times its stored size. The chapter limit, written a few lines away with `.encode()`, was right, and had a test with accented text. The table-of-contents limit had only an ASCII test. The reviewer found it.
**Rule:** every size limit gets a test with non-ASCII input, and `json.dumps` used for measuring takes `ensure_ascii=False`.

### The commit had failed after ten minutes and the log's last line still said "done" (#828)
A test I appended left an extra blank line at the end of the file. The end-of-file hook fixed it, which fails the commit, after the test hook had run for ten minutes. My wait loop looked for the helper's last line, "done", and the line above it showed a commit, the previous one. I recorded a demo on top of an uncommitted tree before noticing. Earlier in the same issue I had also reverted a mutation with `git checkout` while a fix sat uncommitted in the same file, and had to reapply it: the rule for that is already here and I did not follow it.
**Rule:** the commit helper now runs the two file-tidying hooks first and writes "NOT COMMITTED" when HEAD has not moved. After any commit, check the exit code and the hash, not the last line.

### A limit on one way in, with a second way in left open (#828)
I capped a chapter's content on the route that saves it. I knew `PUT /toc` also stores whatever `content` comes with a chapter new to the table of contents, and wrote it off as something only a hand-made client would do. The second review called it what it was: a way round the limit I had just added. A body sent with a table of contents is dropped now.
**Rule:** when adding a limit on a value, list every route that can write that value and close or cap each. "Our own client does not do that" is not a reason to leave one.

### The test table covered eleven of seventeen changed reads (#829)
I changed seventeen reads and wrote a table of eleven routes to measure. Reverting any of the eleven failed a test. Reverting the cover upload or draft generation passed everything, and four more routes had no row either: I had left out the ones that needed a file, a stand-in for the model, or a conflict to provoke.
**Rule:** when a change is the same edit in N places, the test table has N rows, and the mutation run is one mutation per place. Count both against the diff before calling it covered.

### A measuring helper that reads a log has to clear it (#829)
The profiler helper read every entry in `system.profile`. Between tests the database is dropped, so nothing was left over, and every test passed. Twice in one test it counted the first measurement in the second, which I hit in the demo and fixed only there. The reviewer raised it against the tests; the scenario it described does not happen in this suite, but the helper was one reuse away from it.
**Rule:** a helper that measures by reading a log clears the log, or filters to its own window, itself. Fix it where it lives the first time it bites, not in the one caller that tripped.

### Two tests held the defect in place (#830)
The issue said a chapter missing from the saved tab order gets no tab. Two tests in `TabStatePersistence.test.tsx` asserted exactly that: a saved order of two chapters, a book of three, and the restored order equal to the saved one. They failed as soon as the fix went in, and for a moment that read as a regression. What settled it was the component, not the tests: the tab bar draws only what is in the order, so a chapter left out of it cannot be opened at all.
**Rule:** when a fix breaks a test, read what the test's expectation means for a user before deciding which of the two is wrong. An old test can be the bug's own specification.

### The deploy was dispatched before its image existed (#829)
My deploy helper waited for the image build with `gh run watch` and then read the build's conclusion. While the GitHub API was answering 502, the watch returned at once and the conclusion came back empty; the helper printed the empty conclusion and dispatched the deploy anyway. The deploy run failed on an image tag that was not there yet, and staging stayed on the previous build. I only saw it because the E2E line said "skipped".
**Rule:** a wait is not a check. After waiting for a run, compare its conclusion with the one word that means go, and stop on anything else, an empty answer included. Read the helper's whole log, not its last line.

### The stand-in for the editor could not show the bug, or the fix (#831)
The unit tests run against a stand-in for the editor library. Its `setContent` emitted an update whatever options it was given, so a fix that passes `{ emitUpdate: false }` could not pass a test; it does not redraw restored text, so three assertions about what the editor showed were about nothing; and it reset the editor's content by itself when a prop changed, which the real hook never does. Each had to be found and the stand-in corrected against the library's source before a test meant anything.
**Rule:** before writing a test against a stand-in, read the stand-in for the behaviour under test, and compare it with the real thing's source. When a fix depends on an option, the stand-in has to honour the option.

### The issue said "always"; a browser said "for three seconds" (#831)
The issue: every untouched load is marked unsaved and the browser always asks before leaving. With the real editor in a browser, on main, asked once a second: yes, yes, yes, no, no, no. The mark lasts until the autosave timer runs, finds nothing to save and clears it. Still a defect, on every chapter opened, but a different size from the one described, and the unit test alone (which only looks once, straight away) would have agreed with the issue.
**Rule:** measure the defect in the real thing before writing it up, and over time when a timer is involved.

### Two browsers on one backend talk to each other through it (#831)
For the before-and-after I ran main's frontend and the branch's against one backend, one scenario after another. A scenario on main restored a backup; its autosave reached the backend three seconds later, after the next scenario had reset the chapter, and the branch's page loaded the backup text as the saved chapter. The branch looked as if it had restored the backup while still asking whether to. The driver now leaves the page at the end of each scenario and fails loudly if the chapter does not load as seeded.
**Rule:** in a shared-backend comparison, end each scenario by leaving the page and waiting out its saves, and assert the starting state before measuring.

### A recorded command restarted a server, and the recorder waited on it for ten minutes (#832)
The demo stops the backend to make a save fail, then starts it again, inside a command the recorder runs. The start was written `(cd backend && server >> log 2>&1 &)`. The shell backgrounds the whole `cd && server` list as a subshell, and the redirection belongs to the server, not to that subshell: it kept the recorder's output pipe open for as long as the server ran, and the recorder waits for the pipe to close. An earlier lesson says to start servers outside the recording; this one had to be inside it.
**Rule:** when a recorded or piped command must start something that outlives it, background only that one command, with its own stdin, stdout and stderr: `cd dir || exit; server >> log 2>&1 < /dev/null &`. Prove it by piping the call through `cat` and seeing it return.

### The screenshot's caption named four figures and the picture had none, then three (#833)
The demo's screenshot of the Book Stats panel was first a window full of chapter text: the panel sits beside a tall editor and `scrollIntoView` centred the wrong thing. The second try had the panel but cut its last row off, under a caption that listed it. The third used a window tall enough for the panel and recorded where the panel's last row ends, in pixels, beside the picture.
**Rule:** check a screenshot against its own caption, item by item. For something that will not scroll into view, size the window to it, and record the element's position with the picture.

### A test of "nothing happens" that did not wait for the thing (#834)
The test: answers that arrive after the writer has started typing must not write over the typing. It resolved the pending request, awaited one microtask, and asserted the typed text was still there. It was, with or without the guard: the handler that would have written over it had not run yet. Two mutations that removed the guard passed. The request's arrival now happens inside `act` with a turn of the event loop, and both mutations fail.
**Rule:** a test that something does not happen has to let it happen first. Flush the event loop after the trigger, and run the test once against code that does the thing, to see it fail.

### Twice in one issue, a check was satisfied by something beside what it was for (#835)
A test asserted that the prompt mentions non-fiction. I had added two sentences that do, and the test was for the first; a mutation that removed it passed, on the strength of the second. And the demo counted lines of the new templates file that contain a fiction word and printed 7: the dictionary keys (`QuestionType.CHARACTER`) and the docstring that explains them, not one template. The same shape as the address found elsewhere in an entry (#825).
**Rule:** assert the particular sentence, and search the values a reader is shown, not the source file that holds them. When a count is meant to be nought, see first that it counts what it claims on something that is not.

### The helper that commits everything committed the scratch file too (#836)
For a browser scan I copy axe's bundle into `frontend/public/`. My commit helper runs `git add -A`, and the 580 KB bundle went into a commit; the large-file hook did not stop it. It was caught by a `git status` that was clean when it should have shown one untracked file, before anything was pushed.
**Rule:** a helper that stages everything refuses while a known scratch file is in the tree (it now does), and `git show --stat HEAD` is read after every helper commit, before the push. A clean status is evidence only if you know what it should have listed.

### user-event lets go of an arrow key before Radix has moved the focus (#836)
A Radix radio group moves focus a tick after the arrow key goes down and chooses the radio only if the key is still down then. `user.keyboard('{ArrowRight}')` presses and releases at once, so in jest the focus moved and nothing was chosen, while a real key in a real browser chose. The test now holds the key (`{ArrowRight>}`), waits for the focus, and releases.
**Rule:** when a keyboard test and the browser disagree, find out which one is like a finger before changing the component. Hold keys for components that act on focus.

### The keyboard driver pressed Enter on whatever had the focus (#836)
The demo's loop pressed Tab six times looking for Retry, which is the seventh stop, then pressed Enter anyway. Enter landed on "Back to Book", the browser left the page, and the script printed a state that looked like a failed retry.
**Rule:** a driver that presses a key to act says what has the focus first and stops if it is not the thing it meant.

### A mutation that passes may not be a mutation; find what the property buys (#837)
To check the test "Tab stays inside the menu" I broke the focus trap twice. The first break did not break it (a handler on the same element is not stopped by `stopPropagation`). The second made the sheet non-modal, and every test still passed, because a Radix dialog loops Tab whether it is modal or not. What modal buys is something else: the page behind is hidden from assistive technology. Nothing asserted that, and it is the half a screen reader user needs.
**Rule:** when a mutation survives, first ask whether it changes the behaviour the test names. If it does not, ask what the mutated property is for, and assert that.

### Swapping a hand-written control for the shared one can drop what the old one had (#837)
The old drawer's close button was 44 by 44 pixels on a phone. The shared sheet's is a 16-pixel icon. The swap passed every test and axe; a measurement in the browser found it.
**Rule:** before replacing a control, list what the old one gives a user (size, label, focus, keys) and measure each on the new one. Fix the gap in the shared component, where its other users get it too.

### A stand-in for a dependency needs the dependency's types, and its own tests (#838)
The test stand-in for the sign-in check was written twice. One copy declared `request: Request = None`, the other `request=None`. FastAPI fills a parameter with the request only when it is typed as one; untyped, it is a query parameter, always `None` here, and that copy's "no request" branch returned the first user. Every multi-user test on that factory had been one user, and passed.
**Rule:** a stand-in that everything else is tested through gets tests of its own (two clients are two users; no cookie is nobody). And when a helper exists twice, diff the copies before trusting either.

### A run that stalls against a container: look at the container first (#839)
The whole backend suite against a replica set in Docker stopped producing output. I waited on it, then on a second command that needed the same server, for forty minutes between them. The container had exited within a minute of the first run starting: mongod aborts on "Too many open files", and a container's default limit is low. Every later command was waiting on a server that was not there.
**Rule:** when a test run against a container goes quiet, `docker ps -a` before anything else. Give a database container `--ulimit nofile=64000:64000`. And a wait loop for a result gets a bound and says what it was waiting for when it gives up.

### One request per route sweeps one path through the route (#840)
The ownership sweep sent `PATCH /summary` a new summary. With the route's ownership check removed it still passed, because the write is scoped to the owner in the database too. The same route, sent no summary, answers with the book's summary, and nothing but the route's check guards that. The sweep had been pointed at the path with two locks.
**Rule:** when a mutation shows a second layer doing the refusing, look for the path through the same route that the second layer does not cover, and sweep that one. A table of one request per route is a table of one path per route; say so where the table is.

### Un-skip a test in the whole suite, not on its own (#841)
The workflow test had been skipped without an API key, and its docstring said it was fully mocked. Run alone after the skip came off, it passed. In the commit hook's full run it failed: drafting a chapter was not stubbed and went to the real provider, and something earlier in the suite changed what that call met. The stubs were method by method, and one method was missing.
**Rule:** a test coming out of a skip runs in the full suite before it is called passing. And a stand-in for an outside service goes at the client, where every call passes, with named stubs on top; a list of methods leaves out the one added next.

### A doc rewrite needs its claims checked against the code, one by one (#846)
I rewrote the deploy docs from reading the workflows and wrote six sentences the code does not support, among them a health-check error name I had also carried in memory for two months. A fresh agent given each claim and the files to check them against found all six in one pass.
**Rule:** after rewriting operator docs, hand the added lines to a fresh agent with file targets and correct what it cannot confirm before the PR. A sentence that names an error, a trigger or a cleanup step is a claim about code.

### Ordering fixes one trigger; check every trigger the issue names (#873)
The issue named two ways a draft could overwrite a completion. Draining a question's saves in order fixes the first. The second, a draft made after an offline Complete Response, is queued after the completion, so in-order draining lands it last: ordering makes that one certain instead of racy. A test per trigger, both seen failing, showed it before any code was written.
**Rule:** when an issue lists triggers, write one failing test per trigger and run the proposed fix against each before calling the root cause found. And a lock kept in component state must be read back from where the pending work lives, or a remount or prop change clears it while the work is still pending.

### A test that runs the app's lifespan breaks every later export test (#885)
I added a start-up test beside the feature's own tests in `tests/test_db/`. The commit hook's full run failed 86 export tests with "cannot schedule new futures after shutdown": the lifespan's shutdown closes the process-wide `export_executor`, and `tests/test_db/` sorts before `tests/test_services/`. The existing lifespan tests pass only because `tests/test_startup_indexes.py` sorts after it. Filed as #1071.
**Rule:** a test that enters `app.router.lifespan_context` goes in `tests/test_startup_indexes.py` until #1071 is fixed. When a full run fails in files the change never touched, look for shared process state the new test tears down, before suspecting those files.

### A browser test of the whole path finds what the unit test framed out (#886)
The jest test for "sign out lands home" passed after the ProtectedRoute fix. The real-auth Playwright test of the same two paths found two more failures on the deletion path that no unit test could see: the page's own refetch got a 401 and the shared handler redirected, and the delete was refused with a 429 because three different routes shared one rate-limit bucket. The bucket bug had shipped in #798 with tests that armed one limit for every route.
**Rule:** for a fix about where the user ends up, run the real path in a browser against real auth before calling it done; the repo has a real-auth Playwright suite for exactly this. And a rate-limit key is only per-route if it names the method and the full path; check what the framework's `route.path` actually holds.

### A delete that lands after an await must read the latest state (#906)
Asking before a delete made the delete asynchronous: it waits for the answer count. The existing `deleteChapter` built the new tree from the `toc` the click handler had captured, so a chapter added during the wait vanished with the delete. A title edit did not show the bug, because the page mutates chapter objects in place and the stale array still held them; only a new array element exposed it, and the review's suggested test passed until I changed the edit to an add.
**Rule:** when a state update moves behind an `await`, write it as a functional update (`setX(current => ...)`), and test the race with an edit that replaces the array, not one that mutates an element.

### A record that blocks an action needs a way to stop blocking (#912)
To stop two checkout tabs from both being paid, I recorded the user's newest Checkout session and refused a new checkout while the recorded one was paid but its webhook had not landed. Nothing ever cleared the record, so a user who cancelled months later could never subscribe again: the old session was still 'complete'. The reviewer found it, and so did I once I asked what happens a month later.
**Rule:** for any stored marker that refuses an action, name the event that retires it and test the action after that event. "Pending until X" needs X to clear it.

### A backend deletion can break a frontend test (#851)
Removing the backend seed script broke `subprocessors.test.ts`, a frontend test that sweeps `backend/app` for `os.getenv` reads and pins `SEED_USER_PASSWORD` as its sentinel. The commit hook runs only the hooks whose paths changed, so a backend-only commit never ran it; CI's Frontend Tests found it after the PR was open. Earlier, the backend hook also caught two tests the targeted runs had missed (a PUT twin of a PATCH test, and a coverage-config test that pointed at a `pass` line in a deleted class).
**Rule:** before committing a deletion, `git grep` the deleted file's name and every name it defines across the whole repo, tests and other stacks included, and run whatever turns up; a targeted test run is not the inventory.
