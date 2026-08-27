# Lessons

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
