# Claude Code Configuration - SPARC Development Environment

## 🚨 CRITICAL: CONCURRENT EXECUTION & FILE MANAGEMENT

**ABSOLUTE RULES**:
1. ALL operations MUST be concurrent/parallel in a single message
2. **NEVER save working files, text/mds and tests to the root folder**
3. ALWAYS organize files in appropriate subdirectories

### ⚡ GOLDEN RULE: "1 MESSAGE = ALL RELATED OPERATIONS"

**MANDATORY PATTERNS:**
- **TodoWrite**: ALWAYS batch ALL todos in ONE call (5-10+ todos minimum)
- **Task tool**: ALWAYS spawn ALL agents in ONE message with full instructions
- **File operations**: ALWAYS batch ALL reads/writes/edits in ONE message
- **Bash commands**: ALWAYS batch ALL terminal operations in ONE message
- **Memory operations**: ALWAYS batch ALL memory store/retrieve in ONE message

### 📁 File Organization Rules

**NEVER save to root folder. Use these directories:**
- `/src` - Source code files
- `/tests` - Test files
- `/docs` - Documentation and markdown files
- `/config` - Configuration files
- `/scripts` - Utility scripts
- `/examples` - Example code

---

## Recent Changes

### 2026-07-13 (latest)
- **CI-runnable core authoring journey E2E — journey/autosave/error-recovery un-skipped (#201, P2.9, test-trust)**: frontend-tests-mostly, PR #287. The core journey had **zero executing E2E**: the journey spec was `test.skip` (needed real AI), autosave/error-recovery were `describe.skip` ("NEEDS TEST IDS"), interview-prompts carried a stale "NOT IMPLEMENTED" banner (feature shipped #105/#110). **Verified premises before rewriting**: the skipped suites could never have run — route globs `**/api/books/...` never match `/api/v1/books/...`, method checks said PUT/POST for a PATCH endpoint, one assertion required a `✓` glyph that doesn't exist (SVG icon), and error-recovery pinned **exponential backoff on `createBook`, which has no retry code at all** (plain fetch). Rewrites: (1) journey spec — **hybrid mocking mirroring CI exactly** (real backend+Mongo, BYPASS_AUTH, chromium, no OpenAI key): deterministic endpoints real (book create, summary save, wizard Accept's `PUT /toc`, content autosave), only AI endpoints + a stateful chapter-question store `page.route`-mocked; outcome evidence re-read from the backend API (persisted TOC deep-equality, persisted draft); post-PR review drove **request-contract pins** — the generate-toc/generate-draft mocks 400 unless the wizard sends the clarifying answers and the draft button sends the 3 completed `{question, answer}` pairs (the #105 bug class); (2) autosave — 6 tests on the real tabbed book page with seeded books: save round-trip, debounce collapse (exactly 1 PATCH), failure → localStorage backup, reload → Restore/Dismiss banner, automatic self-recovery (failed autosave keeps `autoSavePending`, retries each cycle); (3) error-recovery **retargeted to shipped behavior**: create-book failure → classified toast + no redirect + exactly 1 request + form intact (HTTP 5xx classifies SYSTEM → resubmit; network abort classifies TRANSIENT → toast Retry action), question-response save → **exactly 3 ErrorHandler attempts** then persistent error + Retry — NB the injection must be `route.abort`, not a mocked 500: bookClient throws status-less Errors that classify UNKNOWN (non-retryable); only NETWORK errors exercise the backoff; (4) interview-prompts deleted (#200 precedent). Only app-code change: `data-testid="save-status-indicator"` + `data-save-status` on ChapterEditor's save footer. All three suites **mutation-verified RED** (maxRetries 3→1, skipped TOC persist, wrong backup key — each fails exactly its suite). Reviews: opencode (GLM) occupied by a foreign-cwd delegation → **codex fallback**: pre-PR caught 1 real Major (the `interview-prompts` `git rm` was silently un-staged by a mutation-check `git stash` cycle and missed the commit) + 2 findings rebutted with evidence (`'/generate-questions'.endsWith('/questions')` is false); post-PR fresh session's P2 adopted (the contract pins above). Demo (`docs/demos/2026-07-13-issue-201-ci-runnable-e2e.md`, **showboat verify exit 0**): main's specs = 26 collected / 26 skipped / 0 executed vs branch 10/10 passed, plus all three live mutation REDs. Full chromium run 74 passed / 7 skipped (the 1 responsive failure is the dev-mode Next.js dev-tools overlay button at 32×32 — reproduces on unmodified code, absent in CI's prod build). Frontend units 116 suites / 2118 passed; net **−1,227 lines**. Test-harness gotchas: the summary page's mount fetch can clobber a `fill()` even after `waitForResponse` (the `.json()`+setState lands later) — use the re-fill-until-navigates `toPass` loop; dev-mode's Next.js dev-tools button substring-matches `getByRole('button', {name: 'Next'})` — use `exact: true`.
  - **Status**: ✅ Complete

### 2026-07-13
- **Orphaned 'gold standard' tests removed — no test that runs nowhere or cannot fail (#200, P2.8, test-trust)**: tests-only, PR #286. Four flagship tests inflated perceived coverage while validating nothing; **premise verified with one aggravation**: `backend/tests/test_draft_generation_api.py` wasn't merely orphaned — under `asyncio_mode = auto` it was *collected and passed unconditionally* with zero assert statements (a test that cannot fail, counted green). All four took the AC's **delete** branch, evidence-driven: (1) `SystemIntegration.test.tsx` — imports nonexistent `@/lib/api/aiClient`, jest name-excluded, Clerk-era; (2) `SystemE2E.test.tsx` — Playwright API in `src/__tests__/e2e/`, outside `testDir` (`./src/e2e`), collected by no runner; real journey coverage for both is `src/e2e/complete-authoring-journey.spec.ts` + the staging suite; their three now-pointless `testPathIgnorePatterns` entries dropped from `jest.config.cjs`; (3) `TocGenerationWizard.test.tsx` **dissolved** — the headline test asserted `expect(true).toBe(true)` with the wizard import commented out (real wizard state-machine tests exist since #247 in `TocGenerationWizardEntitlement.test.tsx`); salvage: the `TocGenerating` loading test rehomed to a dedicated file **unmocked** (real `LoadingStateManager` — `findByText` for its 200ms anti-flicker delay; `getAllByText` because the current step renders twice) and two `TocReview` structure tests rehomed into `TocReview.test.tsx` with an explicit collapsed-by-default pin; dropped as valueless: a ClarifyingQuestions duplicate of the 33-test dedicated suite, a genre string-interpolation test, and a jsdom "mobile responsive" test (asserts a padding class; resize does nothing in jsdom); (4) the zero-assert backend file deleted — the endpoint's real validation is `test_books_draft_style_coverage.py` (24 route tests: happy/404/403/400/503/500) + `test_draft_generation_simple.py`; the superseded `test_draft_generation.py.disabled` deleted as the same executes-nowhere class. Rehomed tests **mutation-verified RED** (operation-text change and `isExpanded={false}` each fail exactly their tests). Reviews: opencode (GLM) pre-PR **"clean to merge"** (independently re-verified every deletion claim against the live codebase and ran the rehomed tests) + post-PR fresh session. Demo (`docs/demos/2026-07-13-issue-200-orphaned-gold-standard-tests.md`, showboat verify exit 0): main worktree runs the assertless backend test green and the `✓ renders TocGenerationWizard` vacuous pass with the import commented out; both System tests show 0 in `jest --listTests` and `playwright --list`; branch shows files gone, rehomed tests green→RED-under-mutation→green. Frontend **116 suites, 2118 passed / 5 skipped** (net −4: 7 removed, 3 rehomed); backend **1116 passed / 12 skipped, 91.81% cov** — exactly one fewer pass than main: the test that couldn't fail.
  - **Status**: ✅ Complete

- **Real rate-limit test coverage restored — limiter no longer neutered untestably (#199, P2.7, test-trust/security)**: backend-tests-only, PR #285. `conftest.py` no-ops `get_rate_limiter` suite-wide (correctly), but the fake factory returned a *fresh closure per call*, so production routes were un-overridable and deleting `Depends(get_rate_limiter(...))` from any of the 26 wired endpoints passed the entire suite green (demo proves it: mutated main runs 1111 passed / 13 skipped). Fix: the fake factory now returns ONE shared module-level `noop_rate_limiter`; new conftest fixture **`arm_real_rate_limiter`** re-arms the genuine Mongo-backed limiter on any production route via a single `dependency_overrides` entry (BYPASS_AUTH forced off; `deps.time.time` frozen 1s past a bucket start so epoch windows can't roll mid-test — closes the same flake class that made `test_two_users_do_not_share_a_bucket` fail once in a full run). New `tests/test_api/test_rate_limit_routes.py`: one 2×200-then-429 integration test per AC endpoint class (chapter generate-questions, analyze-summary, export/pdf with real PDF gen, avatar upload) pinning the `X-RateLimit-*`/`Retry-After` contract, plus a **wiring-completeness pin** walking the live route tree (FastAPI 0.138 `_IncludedRouter.effective_candidates()`) so any of the 26 rate-limited routes losing the dependency fails *by name*; superseded skipped `test_export_rate_limiting` deleted. **Mutation-verified both ways** (same sed on main = green; on branch = 2 RED naming the route; `showboat verify` green, exit 0). **Landmine found**: `test_billing_checkout/portal.py`'s `from tests.conftest import _sync_users` executes conftest a second time under a distinct module identity and rebinds `deps.get_rate_limiter` to an orphan object — the completeness test therefore derives the limiter identity from the routes themselves (by `__name__`, union), documented in its docstring. Reviews: opencode (GLM) hung 10 min both rounds → **codex fallback pre-PR + post-PR fresh sessions, both clean**; GLM CI review "no defects found". Backend **1117 passed / 12 skipped, 91.81% cov**.
  - **Status**: ✅ Complete

### 2026-07-12
- **Auth-flow test coverage: sign-in 2FA-redirect race, error mapping, real sign-up tests (#198, P2.6, test-trust)**: tests-only, PR #284. **Premise partially stale (verified)**: the middleware AC was already fully satisfied by `middleware.test.ts` (#185/#192/#190 — redirect/cookie/bypass branches, 16 tests) and `SignInPage.test.tsx` (#184) already pinned success→push(sanitized redirect) + error→no-nav. Real gaps closed: (1) sign-in error now pins the **mapped user-friendly message** rendered in the alert (leaking raw provider text would have shipped green); (2) the **`twoFactorRedirect` early return** (#64's race guard at `sign-in/page.tsx:112-114`) is pinned — no `router.push`, no error alert; (3) mislabeled `SignUp.test.tsx` (imported `@/app/page`) renamed via `git mv` to `HomePage.test.tsx`, and a real `SignUpPage.test.tsx` (4 tests) covers the actual registration form: success payload + `/dashboard` redirect, account-exists→mapped message + no nav, mismatch/weak-credential→submit gated + no API call. All four behavior pins **RED-verified by mutation** (each mutation fails exactly its intended test). Reviews: opencode (GLM) hung 10 min with zero output (the documented concurrent-session condition) → **codex fallback pre-PR + post-PR fresh sessions, both clean**. Demo (`docs/demos/2026-07-12-issue-198-auth-flow-tests.md`, **showboat verify green exit 0**): main-worktree-vs-branch mutation differential — the 2FA-early-return and error-mapping mutations run **GREEN on main** ("a regression here ships green", the issue's exact complaint) and **RED on the branch**; every mutation block restores the source, so the demo is idempotent. Frontend **116 suites, 2122 passed / 5 skipped**. NB the pre-commit secrets hook pattern (`password` + 8+-char quoted string on one line) false-positives on prose in docs — reword rather than `--no-verify`.
  - **Status**: ✅ Complete

- **Failed-save errors persist in QuestionDisplay — auto-save no longer wipes them (#197, P2.5, bug/ux)**: frontend-only, PR #283. The 3s auto-save `useEffect` re-fired after a failed manual save and (because `handleSaveDraft` clears `saveError` on entry) wiped the error banner ~3s after it appeared, then hammered the dead endpoint forever; three error-path tests were `it.skip`'d documenting exactly this. Fix per the CodeRabbit plan (design choice 2 pre-resolved): auto-save effect gated on `saveStatus !== 'error'` (+ dep); `VoiceTextInput` onChange wrapped so a user edit clears `saveError`, resets status to `idle`, and resets `retryCount` — the error persists until the user acts, auto-save resumes on new input; manual Retry untouched. **Pre-PR codex review caught 2 real P2s, both fixed + RED-pinned**: all four saved→idle 3s timers now use a functional conditional update (a stale timer from an earlier success could flip a later error back to `idle` and re-arm auto-save), and edit-after-error resets the retry allowance (else the next failure showed a banner with no Retry button). **Plan-authorized test corrections**: the skipped tests' timing comments miscounted `ErrorHandler` backoff (1s+2s+4s ≈ 7s incl. a wasted final sleep, not ~3s) → timeouts raised; the completion test's reject-once mock was silently absorbed by the *internal* retry (save succeeded, error never surfaced) → now rejects 3× then resolves for the manual Retry. 3 tests un-skipped + 4 new pins, all 5 behavior pins RED-verified. Reviews: opencode (GLM) hung both rounds (foreign-cwd occupation, then a 10-min silent timeout) → **codex fallback pre-PR (the 2 P2s above) + post-PR fresh session ("no introduced correctness issues")**. Demo (`docs/demos/2026-07-12-issue-197-autosave-error-persist.md`): real backend + local Mongo + genuine better-auth signup, branch :3000 vs pristine main worktree :3001, same seeded book/question, backend killed mid-session — main: per-second poll shows the banner true→false with no user action and the save-endpoint counter climbing 26→30 (endless re-saves); branch: counter frozen at exactly 3 (the internal retry budget), banner + Retry stable 11+s, a keystroke clears it in the same tick, and the resumed auto-save persists the edited answer to Mongo (doc shown). Frontend **115 suites, 2116 passed / 5 skipped** (the 3 un-skips). NB showboat verify intentionally diffs on the live-browser/one-way blocks (#203 precedent). Test-harness gotcha: `waitFor` on `queryByText(/retry/i)` disappearing passes prematurely while a save is in-flight (the banner clears during 'saving') — wait for the settled error state (banner text present + retry absent) instead.
  - **Status**: ✅ Complete

- **Dead 'Session Management' subsystem removed (#196, P2.4, security/reliability)**: full-stack deletion, PR #282. The advertised feature (idle/absolute timeouts, expiry warnings, suspicious-activity detection — listed Production Ready) never worked: `SessionMiddleware` gated on `request.state.user`, which nothing ever set (auth is a FastAPI dependency), so `/api/v1/sessions/*` was dead (`current` 404'd for authenticated users, `list` always `[]`) and the frontend `useSession` hook polled it for nothing. Took the AC's **remove** branch per the CodeRabbit plan (real session list/revoke is better-auth native via `ActiveSessionsList`): deleted the whole `app/api/middleware/` package, `/sessions` router, `session_service`, `db/session`, `models/session`, their 5 test files, and the never-mounted `hooks/useSession.ts` + `SessionWarning.tsx`; plan adaptations — also removed the dead `sessions_collection` from `db/base.py` + the conftest rebind (plan missed both). Regression test `test_sessions_removed.py` RED-verified (main served `/sessions/list` 200). Reviews: opencode (GLM) occupied both rounds (foreign-cwd delegation, the documented hang condition) → **codex fallback pre-PR ("no remaining live code paths") + post-PR fresh session (1 Minor: stale CLAUDE.md changelog advertisement — fixed by annotation)**. Demo (`docs/demos/2026-07-12-issue-196-remove-dead-sessions.md`, showboat verify green exit 0): two real uvicorn servers + real Mongo + one genuinely seeded better-auth session — main answers the authenticated user "No active session found" while advertising 6 OpenAPI session paths vs branch route-level 404 + zero paths; middleware stack diff shown live. Backend **1111 passed / 13 skipped, 91.81% cov**; frontend **115 suites, 2109 passed / 8 skipped**. NB the Mongo `sessions` collection on existing deployments is orphaned, not dropped (no migration needed).
  - **Status**: ✅ Complete

- **Notification toggles gated as disabled "Coming soon" (#195, P2.3, ux)**: frontend-only, PR #281. The Notifications settings tab rendered five interactive switches promising alerts (email, marketing, writing reminders, progress updates, backup) that persist to `UserPreferences` but nothing reads — the backend has zero delivery code (demo pins it: the only `writing_reminders` hits in `backend/app` are the model/schema field definitions; 0 smtp/send_email/notification_service hits). Fix per the CodeRabbit plan (both design choices pre-resolved: gate **all five** toggles; disable-in-place with the tab still visible): every `Switch` hard-disabled at the Radix root (blocks pointer/label/keyboard), "Coming soon" `Badge` beside the CardTitle, description now reads "Notification delivery isn't available yet. Your saved choices will apply once notifications launch." Stored contract preserved — checked values still render and round-trip unchanged through the shared save flow. **Plan adaptations**: skipped the optional Tooltip (Radix tooltips don't fire on disabled elements); removed the now-meaningless `disabled` prop from the component + its only callsite instead of keeping dead API. Reviews: opencode (GLM) hung twice (once occupied by a foreign-cwd delegation, once a 9-min silent timeout) → **codex fallback pre-PR + post-PR fresh sessions, both APPROVE with zero findings** (verified root-level disable semantics, other-tab saves can't drop the flags, tests strengthened not weakened). Demo (`docs/demos/2026-07-12-issue-195-notifications-coming-soon.md`, **showboat verify green, exit 0**): real backend + local Mongo + genuine better-auth signup, branch :3000 vs pristine main worktree :3001, same user — main lets the user flip+save Writing Reminders (false promise persisted to Mongo), branch shows the same stored `true` rendering on a disabled switch, a programmatic `.click()` leaves state `unchecked/disabled`, and an unrelated Writing-tab save round-trips every notification flag untouched. Tests: unit five-toggles test now pins badge + copy + all-disabled + stored-state rendering (RED-verified on old code); e2e merged-save flow asserts the gate and unchanged `writing_reminders` in the PATCH payload. Frontend **116 suites, 2120 passed / 8 skipped**.
  - **Status**: ✅ Complete

- **Legacy export page: EPUB/Markdown wired for real (#194, P2.2, bug/ux)**: frontend-only, PR #279. The legacy `/dashboard/books/[bookId]/export` route advertised all four formats from `GET /export/formats` but `handleExport` only dispatched pdf/docx — EPUB/Markdown dead-ended in `toast.error('...not yet implemented')`. Fix took the AC's **wire branch** (per the CodeRabbit plan; delete rejected — unlike #193's fabricated page this one is real and functional, and delete touches e2e page objects/deployment specs): epub/markdown dispatch to the existing `bookClient.exportEPUB`/`exportMarkdown`, new `multiFile` state + "Separate File Per Chapter" toggle, `export.epub`/`export.markdown` budgets in `timeEstimator` (no more silent DOCX-estimate borrowing; `exportFormat` type widened), epub 📖 icon, dead `getStatusColor`/`getStatusText` removed, and the duplicated pdf/docx include-empty blocks collapsed to one shared block (all 4 backend formats accept `include_empty_chapters`). **Plan correction**: the plan's "leave `handleDownload` unchanged" was wrong — multi-file Markdown returns a **ZIP** while `format.extension` is `.md`; the download now uses a `.zip` override (mirrors #61's `generateFilename` extensionOverride). Reviews: opencode (GLM) pre-PR **"clean to merge"** (minor adopted: test mocks now use the real backend labels `EPUB Ebook`/`Markdown Document`) + post-PR fresh session **"clean to merge"** (verified the toggle-after-export race is unreachable and cross-format state carryover can't mis-payload; its multiFile-doesn't-leak-into-EPUB test pin adopted; pre-existing generic-error-toast-discards-`userMessage` filed as **#280 [P3.14]**). New `page.test.tsx` (21 tests, first-ever for this page — pulled it into the coverage denominator at 90/81/80/90) + estimator budget pins; RED verified (12 new-behavior tests failed on old code, 8 baselines passed). Demo (`docs/demos/2026-07-12-issue-194-legacy-export-epub-markdown.md`): one real backend + local Mongo + real better-auth signup, branch :3000 vs pristine main worktree :3001, same seeded book — main shows the toast (captured via MutationObserver + screenshot) vs branch Export Complete with downloads named `.epub`/`.zip` (anchor-click hook), plus magic-byte proof (`file` says EPUB document / Zip archive with per-chapter `.md` entries); pdf/docx regression-checked. `showboat verify` green on all curl blocks after flushing the `:rl:` usage_counters keys (#244 gotcha); intentional diffs only on browser-session evals + ZIP entry timestamps. Frontend **116 suites, 2120 passed / 8 skipped**. Test-harness gotchas: React 19 `use(params)` never un-suspends from a plain `Promise.resolve()` in jest — pass a pre-fulfilled thenable (`status:'fulfilled'`, `value`); re-`spyOn`ing `document.createElement` across beforeEach without `restoreAllMocks` recurses into itself.
  - **Status**: ✅ Complete

### 2026-07-12
- **Remove mock /chapters route serving fabricated questions (#193, P2.1, trust/ux)**: frontend-only, PR #278. `/dashboard/books/[bookId]/chapters` was a real reachable route rendering a 100% fabricated "Chapter Prompts" page — hardcoded ML interview questions, `setTimeout` fake regeneration, `bookId` ignored (every book showed the same fake content). Fix took the AC's **delete branch** (per the CodeRabbit plan): page deleted outright — the real persisted Q&A flow is the ChapterEditor "Interview Questions" tab (`QuestionContainer`) on the tabbed book page; rewiring would have duplicated it behind an un-linked route. Sibling `[chapterId]/page.tsx` legacy redirect shim untouched; no `layout/loading/error` companions existed; no unit tests referenced the page. The only reference — step 4 of the fully-`test.skip`'d `complete-authoring-journey.spec.ts` — rewritten for the real tabbed interface with a **plan correction**: chapter-tab clicks don't change the URL (`?chapter=` is initial-state-only), so the step opens the first sidebar tab (`[data-testid="chapter-tab"]:not([data-tab])`, the `chapter-questions-tabs.spec.ts` idiom), waits on the "Chapter editor view" tablist, and reads the id from `data-rfd-draggable-id` (= `chapter.id`, stamped on the tab element itself). Reviews: opencode (GLM) pre-PR **"clean to merge"** (verified zero remaining links/redirects/imports to the bare route; `ChapterBreadcrumb` matches only with trailing slash) + post-PR fresh session **"clean to merge"** (independently re-verified selectors against ChapterTab/TabBar/ChapterEditor and App Router segment independence for the sibling). Demo (`docs/demos/2026-07-12-issue-193-remove-mock-chapters.md`, `showboat verify` green): real backend + Mongo + better-auth signup, branch :3000 vs pristine main worktree :3001, same session/book — main serves HTTP 200 with fake ML questions for a real gardening book vs branch 404; real Interview Questions tab works on the branch. Frontend **115 suites, 2096 passed / 8 skipped**. Demo gotchas: a main-worktree frontend on another port needs its `.env.local` `NEXT_PUBLIC_BETTER_AUTH_URL` repointed to its own port or the client session fetch is cross-origin and bounces to sign-in; `pkill -f` in a compound Bash command matches its own shell (exit 144) — use a `[b]racket` pattern.
  - **Status**: ✅ Complete

- **TOC clarifying-questions auto-save persists for real (#203, P2.11, data-integrity)**: frontend-only, PR #277. The wizard's debounced auto-save set the green "Auto-saved" indicator without calling any API ("Skipping save call due to type mismatch") — answers lost on refresh while the UI claimed saved. **Issue premise partially stale**: `bookClient.saveQuestionResponses` (PUT) already existed and the backend accepts exactly the `{question, answer}` shape; the sole blocker was the client typing the plural methods with the per-chapter `QuestionResponse` (`response_text`). Fix (AC branch 2 per the CodeRabbit plan): alias `@/types/toc` as `TocQuestionResponse` and retype only the plural book-level methods; wire the debounced effect to the real PUT with `lastSaved` set from the returned `answered_at` **only on success**; failure shows a red `role="alert"` "Auto-save failed" (recovers on next success). **Hydration was also silently broken** (read `response_text`, backend returns `answer` — saved answers never pre-filled); now matches **by question text** since auto-save omits empty answers (sparse lists). Reviews: opencode occupied by a concurrent delegation both rounds (the known hang condition) → **codex fallback, 5 pre-PR rounds**: 3 real P2s fixed (generation counter bumps on **every edit** so stale in-flight saves can't claim Auto-saved; sparse hydration; clearing the last answer PUTs `[]` — PUT is a replacement, else deletions resurrect on refresh), 1 rebutted with evidence (partial sets stored as `status:"completed"` — toc-readiness's responses composite is computed-then-discarded, wizard sends generate-toc body responses per #105; pre-existing backend semantics filed as **#276 [P3.13]**); post-PR fresh codex session + **GLM CI review both clean** (GLM independently traced the generation-counter, empty-PUT, and singular-method-untouched claims). Demo (`docs/demos/2026-07-11-issue-203-toc-autosave-persist.md`): one real backend + real local Mongo + genuine openai SDK against a wire stub (`OPENAI_BASE_URL`), branch frontend :3000 vs **pristine main worktree** :3001, real better-auth signup — same book: branch answer survives refresh (Mongo doc shown), main shows fake Auto-saved + writes nothing + loses the answer; killed backend mid-session → red failure alert, restart → truthful recovery. NB the demo is one-way state transitions, so `showboat verify` intentionally diffs on mid-narrative blocks (#189 precedent). Tests: 33 in `ClarifyingQuestions.test.tsx` (indicator gated on a **held save promise**, payload pin, failure, stale-save, sparse hydration, deletion, submit save); 5 fail on the old code = mutation evidence. Frontend **115 suites, 2093 passed / 8 skipped**. Demo gotchas: `agent-browser screenshot` resolves relative paths against its daemon cwd — pass absolute paths; native `<select>` via `agent-browser select` hit a validation error on this form — set value + dispatch `change` via `eval` instead.
  - **Status**: ✅ Complete

### 2026-07-11
- **AI integration observability: autospec'd OpenAI boundary + no silent clarifying-question fallback (#202, P2.10, test-trust)**: backend-tests-mostly, PR #275. Two defects: unit tests replaced the OpenAI client with bare `Mock`s (request-shape drift/invalid kwargs sailed through green), and `_parse_questions_response` silently substituted 4 hard-coded clarifying questions when AI output was unparseable (same class as #48's TOC bug). **AC1 took the autospec OR-branch** (nightly real-key job rejected: recurring spend + unverifiable secret + CI flake); the AC's literal `create_autospec(OpenAI)` is **unusable** — verified: the client reaches `chat.completions` via `cached_property`, so `.chat.completions` on the class-autospec raises `AttributeError`. New `tests/test_services/openai_autospec.py` autospecs the **real bound** `chat.completions.create` (openai 1.97.1) returning a real typed `ChatCompletion`; `test_openai_request_shape.py` adds meta-tests (helper rejects unknown/missing kwargs — guards silent degradation to bare Mock) + request-shape pins through `_make_openai_request` (the single choke point all 8 AI methods funnel through; exact kwarg set `{model, messages, temperature, max_tokens}`); `test_ai_service_style_transformation.py` moved off `Mock(spec=OpenAI)` (spec only guards top-level attrs). **AC2**: `_parse_questions_response` raises `AIServiceError` `AI_INVALID_RESPONSE` retryable=True (mirrors #48); endpoint maps base `AIServiceError` → **structured 500** (429/503 reserved for rate-limit/network/unavailable subclasses); chapter-question fallback already observable via `is_fallback` (#182). Mutation evidence: bogus kwarg in `_sync_request` → 6/6 green on main vs **7 failures** on branch. Reviews: opencode (GLM) hung on concurrent-session contention → **codex fallback pre-PR + post-PR fresh sessions, both "no discrete regressions"**, posted to PR. Demo (`docs/demos/2026-07-11-issue-202-ai-observability.md`, `showboat verify` green): main-vs-branch pytest drift differential + two real uvicorn servers + real Mongo + genuine SDK against a wire-logging stub via `OPENAI_BASE_URL` — same refusal prose → main 200 + 4 canned questions vs branch structured 500; well-formed output still parses to 200; wire log shows the exact pinned kwarg set. Backend **1165 passed / 13 skipped, 92.21% cov**. NB the openai SDK reads `OPENAI_BASE_URL` env when the client is built without explicit `base_url` — no sitecustomize needed for wire stubs.
  - **Status**: ✅ Complete

### 2026-07-10
- **PUT /users/{auth_id} sanitizes string fields like PATCH /users/me (#265, P1.13, security)**: backend-only, PR #274. Follow-up filed from the #244 review: `update_profile` (PATCH /me) ran string fields through `sanitize_input` before persisting, but `update_user_data` (PUT /{auth_id}) wrote the same document fields raw — inconsistent stored-XSS posture. Fix: new shared `sanitize_string_fields()` helper in `users.py` (byte-identical to PATCH's old inline comprehension); PATCH refactored onto it (behavior unchanged), PUT applies it after its existing None-filter (non-strings pass through untouched, same as PATCH). Test `test_put_sanitizes_strings_same_as_patch` (real Mongo): markup bio stored identically through both endpoints; an intermediate PUT with a different value guards against a tautological pass, and a `"<" not in via_patch` assert pins that PATCH actually sanitizes. Reviews: opencode (GLM) pre-PR **"clean to merge"** (verified helper equivalence, None-filter preservation, test soundness); its nested-`preferences`-strings note verified to have **no surface** — every `UserPreferences` string field is a `Literal` enum, markup can't pass validation. Demo (`docs/demos/2026-07-10-issue-265-put-sanitize.md`, `showboat verify` green): main vs branch uvicorn + real Mongo + seeded better-auth session — same markup bio via PUT stored raw `<script>` on main vs `'bold claim'` (byte-identical to PATCH) on the branch; clean input round-trips. Backend **1159 passed / 13 skipped, 92.21% cov**.
  - **Status**: ✅ Complete

- **Nonce-based CSP — drop unsafe-inline/unsafe-eval and dead Clerk origins (#190, P1.10, security)**: frontend-only, PR #273. The static `next.config.ts` CSP shipped `script-src 'unsafe-eval' 'unsafe-inline'` (neutering CSP as an XSS mitigation while the app renders AI/user HTML via `dangerouslySetInnerHTML`) plus dead origins: `clerk.*`/`clerk-telemetry` (better-auth migration 2025-12), `challenges.cloudflare.com` (Clerk-era captcha), `api.auto-author.dev` (pre-migration domain), google-fonts hosts (`next/font` self-hosts), `r2cdn.perplexity.ai`, and `http://localhost:8000`+`wss:` in production connect-src. Fix moves the CSP to per-request middleware (official Next.js pattern — a static header can't carry a nonce): new pure `src/lib/csp.ts` builder + `withCsp()` on every middleware path (public/authed/BYPASS_AUTH); prod `script-src 'self' 'nonce-…' 'strict-dynamic'` (dev adds only `'unsafe-eval'` for webpack HMR); **connect-src derives from `NEXT_PUBLIC_API_URL`** (same fallback as bookClient) so prod deploys ship only the real API origin while dev/CI E2E keep localhost automatically — no generic-env keying (#192 lesson); verified the var is **inlined at build time** into the middleware bundle and every deploy path sets it at build. Root layout reads `x-nonce` via `headers()` (forces the dynamic rendering nonce CSP requires — all routes now `ƒ`, accepted) and passes it to next-themes' `ThemeProvider` (its inline theme script). `frame-src` dropped entirely (no iframes; `default-src 'self'` covers). **Kept deliberately**: `style-src 'unsafe-inline'` WITHOUT a nonce — a style nonce makes browsers *ignore* unsafe-inline and would break styled-components/Tailwind/TipTap inline styles; AC targets script-src. Tests: `csp.test.ts` (13, per-directive pins for all 3 ACs + dead-origin bans + unparseable-URL fail-closed) + middleware CSP describe (5: all paths, x-nonce clobbers client-sent value, per-request uniqueness). Reviews: **opencode (GLM) hung with zero output across 4 attempts** (concurrent-session contention) — `codex review` fallback ran pre-PR + post-PR fresh sessions, both **"no discrete regression"**, posted to the PR. Demo (`docs/demos/2026-07-10-issue-190-nonce-csp.md`, `showboat verify` green): main-vs-branch prod headers; two requests → two nonces; 19/19 script tags nonce-stamped, 0 without; real better-auth signup → authenticated dashboard with **zero console CSP violations** and dark theme intact; **live enforcement differential** (no-cors fetch: allowed API origin sent vs reachable unlisted origin blocked — CORS ruled out as the explanation). Frontend **115 suites, 2091 passed / 8 skipped**. NB the stale `tests/e2e/deployment/csp-validator.ts` still expects Clerk origins (suite not run by CI — historical snapshot class). Demo gotchas: `curl -sI` header output ends CRLF — `tr -d "\r"` in captured blocks or `showboat verify` diffs invisibly; raw nonces in captured output are nondeterministic — mask them and assert "two nonces DIFFER" instead; CDP `eval` bypasses page CSP (DevTools semantics) so eval-blocking can't be demoed from agent-browser — use the no-cors connect-src differential for honest enforcement evidence; `showboat extract` → patch → replay rebuilds a demo without hand-editing.
  - **Status**: ✅ Complete

- **Production auth-bypass guard no longer exempted by the generic CI env var (#192, P1.12, security)**: frontend-only, PR #271. `middleware.ts`'s FATAL guard fired only when `BYPASS_AUTH=true && NODE_ENV==='production' && CI!=='true'` — but `CI=true` is set by most CI/PaaS/container runtimes, so a production artifact running with both vars **silently disabled all auth** (demo'd live: main's prod build served `/dashboard` unauthenticated with HTTP 200). The E2E infra deliberately drove a prod build through the hole by forwarding `CI`. Fix took the AC's **purpose-built-flag branch**: the only exemption is now `E2E_ALLOW_BYPASS=1`, set explicitly by the Playwright webServer env (which runs `npm run build && npm start` in CI) and never by real deploys; the `CI` var is no longer consulted anywhere in the guard; the AC's alternative (`NEXT_PUBLIC_ENVIRONMENT==='test'`) **rejected** — keying a security guard on a general-purpose env var re-creates the defect class being removed. Dev-mode `BYPASS_AUTH`-alone behavior deliberately unchanged (documented local `npm run dev` workflows). Tests (middleware.test.ts, 6 new): CI=true no longer exempts (the regression pin); no-flag production throws; only the exact value `'1'` exempts; **the flag alone is not a bypass** (BYPASS_AUTH still required — defense-in-depth pin); dev-mode unchanged. Reviews: opencode (GLM) pre-PR **"clean to merge"** (2 minor test-gap suggestions adopted → the last two pins above) + post-PR fresh session **"clean to merge"** (verified fail-closed 500, both build+runtime flag delivery to the CI E2E webServer, test isolation; its M1 — require the flag in ALL envs, since `NODE_ENV` is itself a generic var — filed as **#272 [P2.22]**). Demo (`docs/demos/2026-07-10-issue-192-bypass-guard-ci-hole.md`, `showboat verify` green): same no-bypass-vars prod artifact under 4 runtime env combos — main+`BYPASS_AUTH`+`CI` → 200 (bug), branch same → **500 + FATAL log**, branch+`E2E_ALLOW_BYPASS=1` → 200 (E2E path intact), branch no-bypass → 307 to sign-in. Frontend **114 suites, 2071 passed / 8 skipped**, coverage gates green. Demo gotchas: `grep` on a killed `next start` log needs `-a` (NUL bytes → "binary file matches" breaks `showboat verify`); strip jest `(N ms)` timings for deterministic verify; bare `npx jest` from repo root resolves an npx-cached jest without the project babel config — run from `frontend/`.
  - **Status**: ✅ Complete

- **Block fork PRs from the label-gated staging E2E job (#191, P1.11, security)**: workflow-config-only, PR #269. `e2e-staging-tests.yml` triggered on labeled `pull_request` (incl. `synchronize`) and ran PR-controlled code (`npm ci` lifecycle scripts, Playwright specs) in the `staging` environment (TEST_USER creds + Slack/Discord webhooks) — the pwn-request shape: maintainer labels a benign fork PR, attacker pushes, `synchronize` re-runs with the label attached. **Premise partially stale (verified)**: repo is public, so GitHub already withholds all secrets (incl. environment secrets) from fork `pull_request` runs — but fork code still *executed* against live staging, and the config was one drift step (`pull_request_target` swap / repo going private with fork-secrets on) from a real leak. Fix took **AC branch 2**: the job `if:` now also requires `github.event.pull_request.head.repo.full_name == github.repository` (fails closed on null `head.repo`); AC branch 1 (required reviewers on the `staging` environment) **rejected** because environment protection rules gate *every* run referencing the environment — it would stall the 6-hourly cron; branch 3 would remove the documented labeled-PR path. No unit tests (no workflow test framework — #189 precedent); RED/GREEN done with an **act 0.2.89 dry-run truth table** (synthetic fork-labeled/same-repo-labeled/unlabeled/schedule events: fork+label ran all steps on main → 0 steps on branch; same-repo+label and schedule unchanged) + actionlint clean, all reproduced in the demo (`docs/demos/2026-07-10-issue-191-staging-pwn-request.md`, `showboat verify` green). Live confirmation: PR #269's own check list shows `E2E Staging (Playwright): skipping` (same-repo, unlabeled). Reviews: opencode (GLM) pre-PR **"clean to merge"** (verified precedence, null fail-closed, `full_name` non-spoofable, no synchronize/TOCTOU bypass) + post-PR fresh session **"clean to merge"** (1 cosmetic minor: stale todo checkboxes — fixed). Follow-up **#270 [P2.21]** filed: `glm-review.yml` has the same latent class (`pull_request` + `ZHIPU_API_KEY`; also suggests SHA-pinning the action). NB `act --list` does NOT evaluate job `if:` conditions — use `act -n` (dry-run) for truth tables; act's first run needs `~/.config/act/actrc` or it blocks on an interactive image prompt.
  - **Status**: ✅ Complete

- **Bind app processes to loopback behind nginx on the shared VPS (#189, P1.9, security)**: deploy-config-only, PR #268. PM2 started uvicorn with `--host 0.0.0.0 --port 8000` and Next with its default wildcard bind, so both apps listened on the public IP past nginx's TLS/CORS (verified live: `ss -tlnp` showed `0.0.0.0:8000` / `*:3002`). Fix (AC branch 1): every deploy path binds loopback — `ecosystem.config.template.js` (the live staging path: backend `--host 127.0.0.1`, frontend `args: 'start -- -H 127.0.0.1'`), both legacy `scripts/deploy*.sh`, and the disabled prod workflow; AC branch 2 (firewall) delivered as documentation — the staging ufw baseline (default-deny, only 22/80/443 open; external curls to 8000/3002 time out) is now recorded in `docs/STAGING-DEPLOYMENT.md`'s new "Network Exposure (#189)" section, whose manual-setup examples no longer instruct `0.0.0.0`. opencode (GLM) pre-PR round 1 caught the real Major: I'd fixed only the backend lines in the deploy scripts — the frontend `pm2 start npm ... -- start` lines would have silently re-exposed :3002 on any manual/recovery deploy; round 2 + fresh post-PR session **"clean to merge"** (independently verified the `pm2 → npm → next` double-`--` forwarding chain and swept the repo's whole `0.0.0.0` surface). Post-PR minor adopted: legacy scripts' health checks curl `127.0.0.1` explicitly (server `/etc/hosts` maps `localhost` to `::1` too — same reason nginx `proxy_pass` was pointed at explicit `127.0.0.1` on the box, an ops change outside the repo). **The fix is live now, not just on next deploy**: the demo (`docs/demos/2026-07-10-issue-189-loopback-bind.md`) applied the identical sed to the deployed `ecosystem.config.js` + `pm2 delete`+`start` — after: `ss` shows only `127.0.0.1` binds, `https://dev.autoauthor.app` + api health 200 through nginx, on-box `localhost` health checks pass, direct external ports still dead. NB this demo is a one-way state transition, so `showboat verify` intentionally diffs on the BEFORE blocks (that diff IS the fix holding); mutation steps are idempotent. No unit tests — config-only; the live evidence is the verification.
  - **Status**: ✅ Complete

- **Close PATCH /users/me role self-elevation (#244, P0.9, security)**: backend-only, PR #266. `UserUpdate` exposed `role: Optional[str]` and both `PATCH /users/me` (`update_profile`) and `PUT /users/{auth_id}` (`update_user_data`) dumped `model_dump(exclude_unset=True)` straight into `update_user`'s generic `$set` — any authenticated user could `PATCH {"role": "admin"}` and everything gated on `SessionRoleChecker` became self-escalatable. Fix took the AC's **"removed"** branch at the root: `role` deleted from `UserUpdate` (+ its OpenAPI example), and **`extra="forbid"` added** so the schema's declared fields are the sole writable allowlist — an undeclared/privileged key (`role`, `plan`, `is_active`, `stripe_*`, `book_ids`, `auth_id`) is a **loud 422** at the validation boundary, closing the mass-assignment *class* not just the `role` instance (opencode's round-1 Major; its suggested duplicate handler-level allowlist rebutted — pydantic already enforces the schema, a second list drifts). The now-dead non-admin role guard in `PUT` deleted (it read the removed field → would `AttributeError`); **no API path writes role for anyone**, admins included (no admin role-change UI/script exists — roles are DB-managed). Verified the only live PATCH caller (`useProfileApi.ProfileUpdateData`) sends exclusively declared keys, so `forbid` breaks nothing (`userClient.ts` PUT client is dead code, zero importers). Tests: parameterized privileged-field regression (**422 + stored doc byte-identical**, real Mongo) for `PATCH /me`; `PUT` role rejection incl. **admin caller**; positive happy-path (declared fields still 200 + persist); the old 403-guard test superseded by the strictly-stronger unwritable pin. Reviews: opencode (GLM) pre-PR ×2 (Major adopted, 2 minors adopted, metadata + duplicate-allowlist rebutted → "clean after one doc-word fix") + post-PR fresh session (Major M1 verified clean, m2/m3 adopted) + **two GLM CI review passes, "✅ no defects found"** (independently traced all 5 `update_user` callers — signup hardcodes `role:user`, avatar/webhook/checkout never pass role — and confirmed metadata `$set`s under its own key so it can't clobber a top-level field). Demo (`docs/demos/2026-07-10-issue-244-role-self-elevation.md`, `showboat verify` green): two real uvicorn servers + real Mongo + a genuine seeded better-auth session — `main` self-elevates to `admin` (200, stored role `admin`); branch 422s and stored role stays `user`; normal profile edit still round-trips. Follow-up **#265 [P1.13]** filed (pre-existing `PUT` `sanitize_input` gap). Backend **1157 passed / 13 skipped, 92.21% cov**. Demo gotchas: bash `source .env` mangles the JSON-array `BACKEND_CORS_ORIGINS` (override it); `showboat verify` re-runs blocks back-to-back and trips the per-user rate limiter (#180) — flush `usage_counters` + wait the window, and make every exec block CWD-independent (verify runs from a different cwd than capture).
  - **Status**: ✅ Complete

### 2026-07-09
- **Retry OpenAI calls at exactly one layer (#188, P1.8, high/reliability)**: backend-only, PR #251. `generate_clarifying_questions` + `generate_toc_from_summary_and_responses` wrapped `_make_openai_request` (which already retries via `_retry_with_backoff`) in a **second** `_retry_with_backoff`. **Premise partially stale**: the feared `AI_MAX_RETRIES²` never manifested at that pair of layers — the inner converts every OpenAI error to an `AIServiceError` subclass and the outer's `except AIServiceError: raise` re-raises without retrying — but the demo's wire evidence exposed real multiplication at a layer the issue didn't name: the **openai SDK itself silently retries** (default `max_retries=2`), so a persistent failure made **9 real HTTP requests** (3 app × 3 SDK). Fix: both sites call `_make_openai_request` directly; it gains optional `correlation_id` threaded to its internal retry (attempt/backoff logs now share the request's id — main split the trace across 2 ids and logged a spurious 4th "Attempting" line); client built with **`max_retries=0`** (app layer already backs off on RateLimit/Timeout/Connection/InternalServer; only SDK-retryable class it lacks is 409 ConflictError, which Chat Completions never returns). `TestSingleRetryLayer` (5 tests): AC pins pass on main too (squaring was latent) — the **log-count + single-correlation-id tests are the real re-wrap guards**; `test_ai_service_error_handling` re-targeted from mocking `_make_openai_request` to the real `client.chat.completions.create` boundary (strictly stronger — exercises the real `except Exception → AI_UNEXPECTED_ERROR` conversion). Reviews: opencode (GLM) pre-PR + post-PR fresh session + incremental (SDK commit) all **"clean to merge"**. Demo (`docs/demos/2026-07-09-issue-188-single-retry-layer.md`): real `AIService` + genuine openai 1.97.1 SDK vs a wire-counting 429 stub, main worktree vs branch — **9 requests/4 logs/2 ids → 3/3/1** on both AC sites; `showboat verify` reproduced. Backend **1149 passed / 13 skipped, 92.21% cov**. Demo gotcha: `pkill -f <script>` inside a compound Bash command matches the shell's own command line and kills it (exit 144) — kill by PID.
  - **Status**: ✅ Complete

- **Route entitlement 402s to the Upgrade CTA in the TOC wizard + draft dialogs (#247, bug/commercial)**: frontend-only, PR #248 — closes the gap the #222 demo filed: the #174 entitlement pipeline (`aiError` → `handleAIServiceError` → Upgrade toast) existed but no shipped flow used it. Three fixes: (1) `bookClient.generateChapterDraft` non-OK → `throw await this.aiError(...)` (parsed detail message + `statusCode`; the raw `{"detail":{...}}` body can no longer leak into the UI); (2) `DraftGenerator` + `DraftGenerationButton` moved onto `generateChapterDraftWithErrorHandling` (never throws; 402 fires the shared ENTITLEMENT toast) and their local raw-message "Generation Failed" toasts deleted — `DraftGenerationButton` keeps its try/catch for local pre-checks (QA fetch, min-responses guard) feeding the inline error state with plain user-facing messages; (3) `TocGenerationWizard`'s nested analyze-summary catch **re-throws on `statusCode === 402`** (paywall ≠ transient analysis failure), every ERROR-transitioning catch captures `errorStatusCode` into `WizardState`, and `ErrorDisplay` renders an **Upgrade Required** panel (hard link to `/dashboard/settings?tab=billing`, matching the toast CTA idiom; no "Try Again"/troubleshooting tips) when 402. **Plan drift**: the CodeRabbit plan's Phase 4 (CTA retarget + settings `?tab=` handling) had already shipped in #246 — dropped; its optional `NotReadyMessage` task skipped (YAGNI — that path's `onRetry` re-runs `checkTocReadiness`, which now surfaces the entitlement panel). Dead `lib/api/draftClient.ts` deleted (zero production importers; would have bypassed entitlement routing if revived — opencode minor). **Gotchas hit**: a `usePerformanceTracking` mock returning a fresh object per render re-fired the wizard's mount effect forever → jest OOM (mock must return ONE stable reference); first-ever wizard tests pulled the 37%-functions component into the jest coverage denominator and **failed the global functions gate** — fixed by covering the wizard's full state machine (stubbed child steps; 37%→97% funcs, 11 tests). Reviews: opencode (GLM) pre-PR **"clean to merge"** (4 minors: 2 fixed — draftClient deletion, dead `errorStatusCode` in the stays-on-REVIEW `handleAcceptToc` catch; 2 accepted). Demo (`docs/demos/2026-07-09-issue-247-entitlement-402-cta.md`): real servers + real Mongo + real better-auth signup, plan flipped to `restricted` (the #174 gate 402s before any AI call — no OpenAI stub needed): wizard shows the Upgrade panel (link asserted, no Try Again, no payload fragments), clicking it lands on the Billing tab, draft dialog shows the classified Upgrade toast with zero raw JSON in the DOM. Frontend **114 suites, 2071 passed / 8 skipped**; lint 0 errors; typecheck clean. NB `agent-browser` httpOnly cookies: `state_save` + parse `.cookies[]`, join with `'; '` (multi-line Cookie header → uvicorn 400).
  - **Status**: ✅ Complete

- **Billing settings UI: Stripe portal + billing-tab deep link (#222, P0.2.3, commercial)**: full-stack, PR #246; parent epic #174. Most of the issue's CodeRabbit plan had already shipped (#174 plan field, #221 Billing tab/hook/Upgrade CTA; its `Literal["free","paid"]` and `useSearchParams`+Suspense approach were both wrong/rejected), so this delivers only the real gaps. New `POST /api/v1/billing/portal` (`billing.py`, mirrors checkout): session auth + rate limit 5/300s; **503 fail-closed** when `STRIPE_SECRET_KEY` unset (portal needs no price id); **409** when no `stripe_customer_id`; `stripe.billing_portal.Session.create` via `asyncio.to_thread`; `StripeError` → sanitized 502; `return_url` = `{BETTER_AUTH_URL}/dashboard/settings?tab=billing`; **plan never mutated** (webhook-only, #220). **The gate is the Stripe customer, NOT the plan** — the opencode pre-PR Major: the backend deliberately admits lapsed (`restricted`) users to fix their payment method, but the UI only showed Manage billing for `pro`, making the recovery flow unreachable. Fixed with `hasBillingAccount` (from `profile.stripe_customer_id`, returned by `/users/me` since the #221 drift fix) threaded page→form; restricted users see BOTH Upgrade and Manage billing plus "Your subscription is inactive" copy (post-PR minor — no misleading "Free plan" label). `useBillingApi.openBillingPortal()`; settings page honors `?tab=` deep links (validated against `SETTINGS_TABS`; same `window.location.search` mount-effect pattern as `?checkout=`); ErrorNotification ENTITLEMENT CTA → `/dashboard/settings?tab=billing`. Reviews: opencode (GLM) pre-PR ×2 (Major fixed; its 429-HTTP-test minor **rebutted** — conftest globally no-ops `get_rate_limiter` before app import so the test would only pin the fake, limiter mechanics live in `test_dependencies.py`; rebuttal accepted → "clean to merge") + post-PR fresh session **"clean to merge"** (verified no-IDOR/no-open-redirect/sole-plan-writer against the repo; 2 of 4 minors fixed, 2 accepted as #221-consistent). **Demo found a real gap, filed #247**: no shipped flow routes a 402 through the ENTITLEMENT toast — the TOC wizard renders an inline "Try Again" panel and the draft dialog leaks the raw 402 JSON inline — so the retargeted Upgrade CTA is currently reachable only via the aiErrorHandler pipeline (pinned by unit test). Demo (`docs/demos/2026-07-09-issue-222-billing-portal.md`): real better-auth signup + real servers + real Mongo, genuine stripe SDK against a wire-logging stub — deep link selects the Billing tab; free user 409 + 401; keyless backend 503; pro user's portal round trip with `customer`+`return_url` on the wire; restricted user sees both actions. Backend **1144 passed / 13 skipped, 92.23% cov**; frontend **113 suites, 2054 passed / 8 skipped**.
  - **Status**: ✅ Complete

### 2026-07-09 (later)
- **Stripe checkout flow for plan upgrade (#221, P0.2.2, commercial)**: full-stack, PR #245; parent epic #174. New `POST /api/v1/billing/checkout` (`billing.py`): session-auth + rate limit (5/300s); **503 fail-closed** when `STRIPE_SECRET_KEY`/`STRIPE_PRICE_ID_PRO` unset (webhook convention — the new `STRIPE_SECRET_KEY` closes #220's "deliberately omitted" note, whitespace-strip validator extended); **409** already-paid; `Literal["pro"]` body → 422 free. Reuses `stripe_customer_id` or `stripe.Customer.create` with **`idempotency_key=checkout-customer-{auth_id}`** (double-click can't mint two customers) persisted via audited `update_user`; subscription-mode Session stamped with `client_reference_id` + **`subscription_data.metadata.auth_id`** (the #220 webhook's user-lookup fallback); both sync SDK calls via `asyncio.to_thread` (#175); `StripeError` → sanitized 502 (pinned for both calls). **Plan never flips here — webhook-only.** Success/cancel URLs derive from `BETTER_AUTH_URL` (no new env). Frontend: `useBillingApi` hook + settings **Billing tab** (`BillingSettingsForm`: current plan, Upgrade → redirect; self-serves like the security tab) + `?checkout=success|cancel` mount-effect handling (toast + tab select + `replaceState` param strip; deliberately `window.location.search`, not `useSearchParams`, to avoid the Suspense-boundary requirement). **Plan drift**: the CodeRabbit plan predated #174/#220 ("entirely greenfield") — its user-fields phase was already shipped, its `stripe_service`/`stripe_errors` mirroring and `STRIPE_ENABLED`+price-mapping config rejected (two SDK calls; unset-key fail-closed IS the flag), its `create_new_user` step targets an endpoint deleted in #186. Reviews: opencode (GLM) pre-PR **"clean to merge"** (2 Minor fixed) + post-PR fresh session **"clean to merge"** (4 Minor: 1 rebutted with evidence — `main.py:165` global handler sanitizes 500s; 3 fixed incl. success-toast variant). **Demo found a real #220 drift**: `read_users_me` builds `UserResponse` field-by-field and dropped the stripe ids (always null in the API) — fixed + regression test. Demo (`docs/demos/2026-07-09-issue-221-stripe-checkout.md`): real better-auth signup in a real browser + real uvicorn ×2 + real next dev + real Mongo, genuine stripe SDK pointed at a wire-logging stub (`stripe.api_base` via sitecustomize) — fail-closed 503; checkout with full linkage visible on the wire; customer reuse (3 sessions / 1 customer); Billing-tab round trip with success toast + param strip; **genuinely HMAC-signed webhook flips plan to `pro`** (API + UI both reflect it); 409 double-purchase guard. Backend **1137 passed / 13 skipped, ~92.2% cov**; frontend **113 suites, 2044 passed / 8 skipped**. Demo gotchas: stripe v15 `construct_event` requires top-level `"object": "event"` in the payload (synthetic events without it crash before verification); showboat `image` takes no `<lang>` arg (unlike `exec`) and wants stdout to be only the image path.
  - **Status**: ✅ Complete

### 2026-07-09
- **Stripe subscription webhook with raw-body HMAC verify (#220, P0.2.1, commercial)**: backend-only, PR #243; parent epic #174 (ADR `docs/adr/2026-07-04-beta-entitlement-model.md`). New `POST /api/v1/webhooks/stripe` (extends the placeholder `webhooks.py`): verifies the Stripe signature against the **raw request body** via `stripe.Webhook.construct_event` (stripe==15.3.0 — NB its `StripeObject` has **no dict API**, so after verification the handler re-parses `raw_body` with `json.loads`); unset `STRIPE_WEBHOOK_SECRET` → **503 fail-closed**, bad/missing sig or unparseable body → 400. `customer.subscription.*` events map price→plan via new pure `resolve_plan_for_price()` in the **existing** entitlements registry (new `"pro"` tier, full access until paid launch; unknown/missing price → `free`; `deleted` → `free` + subscription id nulled, customer id retained) — **scans all line items**, not `items[0]`. User found by `stripe_customer_id` (new unique+sparse index) with `subscription.metadata.auth_id` fallback (#221 checkout will stamp it); persists plan + both stripe ids via `update_user` `$set` with `actor_id="stripe:<event_id>"` (audit trail). **Replay/idempotency**: atomic `insert_one` on `_id=event.id` in TTL'd `processed_stripe_events` (`usage.py` idiom, `app/db/stripe_events.py`); the claim is **released** on processing failure (Stripe's retry must work) AND on `no_matching_user` (a dashboard "Resend" after late linking must reprocess — post-PR Major). **Plan-drift corrections**: the CodeRabbit plan predated #174 (claimed `entitlements.py`/ADR don't exist; `plan` field already shipped); its "mirror fields into `UserUpdate`" step **rejected on security grounds** (would let users self-set plan via PATCH /users/me). `STRIPE_SECRET_KEY` deliberately omitted until #221 consumes it. Reviews: opencode (GLM) pre-PR ×2 → "clean to merge" (audit actor_id, dead-sub-id clear, full-app middleware raw-body test, collision comment); post-PR fresh session 1 Major/5 Minor all fixed (marker release, multi-item scan, failure-injection test, TTL-flag reset in fixtures, `STRIPE_*` whitespace-strip validator, retention assert) — its informational find, **pre-existing `PATCH /users/me` role self-elevation, filed as #244 (P0.9 security)**. Tests sign payloads with **real stdlib-HMAC** (no mocked verification seam) against real Mongo. Demo (`docs/demos/2026-07-09-issue-220-stripe-webhook.md`): real uvicorn + real Mongo — signed upgrade → `pro`+ids+audit doc; tampered byte → 400; out-of-band flip + replay → stays `free`; fresh event id → `pro`; `deleted` → `free`/null sub id. Backend **1128 passed / 13 skipped, 92.16% cov**. Accepted (documented): out-of-order deliveries can apply a stale plan (#221 re-fetches from Stripe API); crash between update and marker re-applies an idempotent `$set`; TOCTOU customer-id collision → deliberate 500 (Stripe dashboard is the ops signal).
  - **Status**: ✅ Complete

### 2026-07-08
- **Validate ownership/existence in batch question-response save (#187, P1.7, high/data-integrity)**: backend-only, PR #241. `save_question_responses_batch` (`app/db/questions.py`) upserted by `(question_id, user_id)` with only non-empty checks — unlike the single-response path (`question_generation_service.save_question_response`, which validates via `get_question_by_id` + book/chapter membership) — so a stale/foreign/mistyped `question_id` returned `success:true` and wrote an **orphaned response** the read path never surfaces. Fix: the function now requires `book_id`/`chapter_id` and pre-fetches all referenced ids in **one `$in` query** scoped to `user_id+book_id+chapter_id`; any id not found (nonexistent, foreign book/chapter, other-user, malformed/uppercase-hex) is flagged per-item ("Question not found in this book/chapter") with nothing written — the endpoint's partial-failure contract (HTTP 200, valid items still save) is unchanged; the batch endpoint threads its path params through. **Three existing endpoint tests were characterizing the bug** (posted fabricated ids `"q1"`/`"qX"` and asserted success) — rewritten to create real questions (the #182 pattern). Reviews: opencode (GLM) pre-PR **"clean to merge"**; post-PR fresh session **"no Critical/Major"** — its route-level cross-user test suggestion adopted, the pre-existing duplicate-`question_id`-within-one-batch gap filed as **#242**; TOCTOU (delete between pre-fetch and write) accepted as the same documented tech-debt class as other non-transactional question mutations; uppercase-hex false-reject **kept deliberately** (fail-closed; canonicalizing only the comparison would store a mismatched raw key and re-introduce an orphan variant). CodeRabbit post-CI: 2 Minor doc nits (todo.md wording fixed; demo's verbatim scratchpad paths kept — showboat records are evidence, not replay scripts). Demo (`docs/demos/2026-07-08-issue-187-batch-response-validation.md`): two real uvicorn servers + real Mongo — same 3-item batch (valid + foreign + stale id) saved **3/3 with orphan docs on main** vs **1/3 with zero orphans on the branch**. Backend **1107 passed / 13 skipped, 92.06% cov**.
  - **Status**: ✅ Complete

- **Remove unauthenticated `POST /users/` enumeration oracle (#186, P1.6, high/security)**: backend-only, PR #240. `POST /api/v1/users/` (`app/api/endpoints/users.py`) had **no auth dependency** and returned state-distinct responses — `201` for a new identity, `409 "…auth ID already exists"` for an existing `auth_id`, `409 "…email already exists"` for an existing `email` — an **account-enumeration oracle**; it also let any anonymous caller insert arbitrary user records that collide on the email unique index and `500` a victim's real first login. Fix takes the AC's **"or is removed"** branch: the endpoint had **zero production callers** (no frontend, scripts, or E2E — only `test_users_coverage.py`) and real signup rides the better-auth session auto-create in `app/core/security.py`, so the whole handler was deleted, closing both the oracle and the junk-record vector at the root (no auth gate / uniform-response / rate-limit needed on a nonexistent route). Dropped the now-orphaned file-local imports (`DuplicateKeyError`, `UserCreate`, `create_user`, `get_user_by_email`) and the stale "legacy POST /users/ → 409" sentence in `db/user.py`'s docstring. **Kept deliberately**: the `UserCreate` schema (model-tested, exported by models/schemas) and the `get_user_by_email` DAO (re-exported via `database.py`, consumed by the signup path). Tests: the 5 `create_new_user` endpoint tests replaced with 2 regression tests pinning the route gone — `404/405`, never `201/409` — for **both anonymous and authenticated** callers (an existing seeded record must not be distinguishable). opencode (GLM) pre-PR review: **clean to merge** (imports verified fully cleaned, DB primitives intact and still used by signup, no production callers, tests adequate); its two Minor doc-drift notes (`docs/analysis/backend-api-review.md`, the #174 changelog entry here) are **historical snapshots kept as-is** per the #120 precedent. CodeRabbit: no actionable comments. Demo (`docs/demos/2026-07-08-issue-186-remove-unauth-user-creation.md`): two real uvicorn servers (main worktree vs branch) on a local mongod — anonymous `POST /users/` on **main** returned `201`→`409 auth-id`→`409 email` and created **1** record; on **branch** returned an **identical `404`** regardless of identity existence and created **0** records. Backend **1102 passed / 13 skipped, 92.03% cov**; `ruff` clean. **Env note**: mongod died mid-run again (`ECONNREFUSED`) → the full suite hung ~14 min; a user-level `mongod --fork --dbpath <scratch>` restarted it without sudo (see [[mongodb-precommit-hang]]).
  - **Status**: ✅ Complete

### 2026-07-07
- **Guard /profile against unauthenticated access (#185, P1.5, high/security)**: frontend-only, PR #238. Middleware only protected `/dashboard*` and the profile page had no guard, so `/profile` (name/bio edit + delete-account UI) rendered for unauthenticated visitors. Fix mirrors the dashboard's two layers: `middleware.ts` now treats `/profile*` as protected (server 307 → `/auth/sign-in?redirect=/profile`, deep link validated by #184's `sanitizeRedirectPath`) and the page is wrapped in the existing `ProtectedRoute` (client guard for forged/expired sessions). `jest.setup.ts` browser-only globals guarded behind `hasWindow`/`typeof Element` so `@jest-environment node` suites can load — enabled the new `middleware.test.ts` (5 tests: redirect + both cookie names incl. `__Secure-` prod + dashboard/public regressions); `ProfilePage.test.tsx` gains a 3-test guard describe (tests must `delete process.env.NEXT_PUBLIC_BYPASS_AUTH` — `.env.test` sets it, same handling as `ProtectedRoute.test.tsx`). opencode (GLM) reviews: pre-PR ×2 → "clean to merge" (indent + delete-account assertion fixed; 5 findings rebutted with evidence); post-PR fresh session → "clean to merge" (prod-cookie test added; `ProtectedRoute`'s missing `?redirect` deep link on client-side expiry filed as **#239**). Demo (`docs/demos/2026-07-07-issue-185-profile-auth-guard.md`): two real dev servers — main served 200 + the full profile page (screenshot, Delete Account visible) and kept rendering with a forged cookie; branch 307'd before any HTML and the client guard bounced the forged cookie to sign-in. Frontend **110 suites, 2035 passed / 8 skipped**; lint 0 errors; typecheck clean.
  - **Status**: ✅ Complete

- **Close open redirect on sign-in via unvalidated `?redirect` (#184, P1.4, high/security)**: frontend-only, PR #236. `frontend/src/app/auth/sign-in/page.tsx` read `?redirect` and `router.push`ed it verbatim after auth, so `/auth/sign-in?redirect=https://evil.com` (or `//evil.com`, `javascript:…`) sent a freshly-authenticated user off-site — phishing open redirect. The existing `sanitizeUrl` deliberately allows external http(s)/`//` URLs (it validates book-cover URLs), so it was the wrong tool. Fix: new **`sanitizeRedirectPath(path)`** in `lib/security.ts` — accepts only same-origin relative paths (single-`/` rooted, no `//`, no `\`, no `://`, no control chars), else falls back to `/dashboard`. Checks run on the **percent-decoded** value (single decode, matching browser behavior) so `%2F`/`%5C` smuggling can't bypass; malformed percent-encoding also falls back. Returned value stays structurally safe for any sink (`router.push`, `location.href`, `<a href>`, server 302), not just today's client push. Verified this is the app's only `?redirect` consumer (`middleware.ts` sets it from `pathname`, always relative → no legit breakage). opencode (GLM) reviews: pre-PR ×2 — round 1 M1 (percent-encoded separator smuggling) fixed with decode-then-validate + tests, m2 (control chars) fixed, m1 (`://`-in-query rejected, e.g. `/search?q=https://…`→`/dashboard`) **kept deliberately per the AC**; round 2 "clean to merge" + its pinning tests added. Post-PR fresh session: clean to merge, 4 minor notes — #3 (2FA drops the `?redirect` deep-link, pre-existing) filed as **#237**, #4 (no no-push-on-error test) added (which also exposed that the suite's file-local `jest.mock('@/lib/auth-client')` was inert — the moduleNameMapper'd better-auth mock served all responses — so tests now drive that mock directly). Tests: `security.test.ts` `sanitizeRedirectPath` suite (12 cases incl. all AC inputs + encoded/CRLF/malformed/double-encoded edge cases) + new `SignInPage.test.tsx` (6, real component + real router spy). Frontend **109 suites, 2019 passed / 8 skipped**, coverage gates green; lint 0 errors; typecheck clean. Demo (`docs/demos/2026-07-07-issue-184-open-redirect.md`): **two real Next dev servers** (main :3011 from a worktree, branch :3010) + real better-auth sign-in + one seeded Mongo user — same malicious `?redirect` redirected the authenticated user **off-site to example.com on `main`** (screenshot) vs stayed on `localhost/dashboard` on the branch; plus a `tsx` run of the real validator on the AC inputs. CI all green (Frontend/Backend/E2E/CodeRabbit/GitGuardian/Snyk).
  - **Status**: ✅ Complete

### 2026-07-06
- **Create DB indexes at startup + 90-day access-log TTL (#183, P1.3, high/reliability)**: backend-only, PR #235. `ChapterTabIndexManager` (`app/db/indexing_strategy.py`) held the books `owner_id` indexes and the `chapter_access_logs` indexes + 90-day TTL but had **zero runtime callers** — the dashboard `find({owner_id})` COLLSCAN'd books on every load and access logs (written on ~every read/edit) grew forever. Fix: lifespan awaits `ChapterTabIndexManager(get_database()).create_all_indexes()` after the existing `ensure_*` calls (idempotent, per-index errors logged non-fatal; a `success:False` result is logged at ERROR, never bricks boot — queries work unindexed, just slower). New public `base.get_database()` (reads the module global, so test rebinds win). **Dropped the unused `chapter_content_text_idx` spec** — no `$text` query exists in `app/` and a text index over full chapter content re-tokenizes on every 3s autosave — with a defensive one-time `drop_index` for any env where a manual/migration run created it. **Deploy note: retention goes live** — access-log rows older than 90 days are permanently TTL-deleted (batched, ~60s cycles). opencode (GLM) reviews: pre-PR ×2 (drove the defensive drop, de-mocked real-lifespan test, access-log idempotency assert → "clean to merge"); post-PR fresh session: 7 findings — 3 fixed (startup logs failure; `get_database()`; `partialFilterExpression` pinned in test), 2 rebutted (TTL activation IS the AC; warm-collections race is fixture-specific), 2 deferred (per-boot drop_index style; pre-existing `background:` keys). Tests `test_startup_indexes.py` (4, real Mongo incl. a **real lifespan run**). Demo (`docs/demos/2026-07-06-issue-183-startup-indexes.md`): real uvicorn ×2 — main showed `["_id_"]` + COLLSCAN; branch showed owner indexes + TTL `expireAfterSeconds:7776000` + IXSCAN; a 100-day-old row was **genuinely deleted by the TTL monitor in ~45s** while the fresh row survived; idempotent restart clean. Backend **1105 passed / 13 skipped, 92.07% cov**.
  - **Status**: ✅ Complete

- **Stop swallowing AI question-generation failures into fake-200 template questions (#182, P1.2, high/bug)**: backend-only, PR #233. `ai_service.generate_chapter_questions` did `except Exception: return []` and the service layer substituted template questions on any failure — a genuine OpenAI outage returned HTTP 200 with plausible fake questions (the tests even *depended* on it: four test files made real 401'd OpenAI calls and passed via the fallback). Fix: `AIServiceError` re-raises through both layers to the routes' existing `handle_question_generation_error` → structured **503/500 `QUESTION_GENERATION_FAILED`** (TOC-path pattern) for generate, bulk regenerate, and single regenerate; template fallback stays only for empty/thin AI responses and non-AI unexpected errors, now tagged **`is_fallback: bool = False`** on `QuestionBase` (mirrors `regeneration_count`; no migration; flows response+persistence via `model_dump()`); `regenerate_single_question` carries the flag into its in-place replacement. The four bug-dependent test files got deterministic autouse AI-boundary fixtures (also removing live network calls from the suite; the regen stub honors the prompt's focus marker). opencode (GLM) reviews: round 1 — M1 (bulk regenerate's pre-existing delete-before-generate now surfaces as 503-with-empty-chapter) **rebutted** (user content never lost; templates-as-200 WAS the bug) and filed as **#234** with N5; M2/M3/N4 fixed with tests. Round 2: "clean to merge", rebuttal independently verified. Demo (`docs/demos/2026-07-06-issue-182-question-generation-errors.md`): real backend ×3 + real Mongo — `main` returned 200 + untagged fiction templates for a non-fiction book on a **real** stale-key 401; fix returned structured 500; wire-stub acts show `is_fallback` true/false. Backend **1101 passed / 13 skipped, 91.92% cov**. Env note: mongod died mid-session — a user-level `mongod --fork --dbpath <scratch>` works without sudo (tests create/drop their own DB).
  - **Status**: ✅ Complete

### 2026-07-05
- **Stop silent ~750-word truncation of chapter drafts (#181, P1.1, high/bug)**: backend-only, PR #231. `generate_chapter_draft` called `_make_openai_request` with the default `max_tokens=1000` and — unlike its three siblings — no `finish_reason=='length'` guard, so any draft request over ~750 words returned a truncated draft as `success:true` (inserted into the editor as-is); the endpoint's outer `except Exception` also swallowed its own `HTTPException`, degrading explicit failures to a generic 500 (a test even characterized this). Fix: `max_tokens = clamp(target_length × 1.6, 500, 4000)` (module constants `DRAFT_WORDS_TO_TOKENS_FACTOR`/`DRAFT_MAX_COMPLETION_TOKENS`; same fixed 4000 cap as the siblings, keeping prompt headroom in gpt-4's 8192 window — the 500 floor came out of review so tiny targets can't spuriously trip the guard); sibling truncation guard returns `success:False` with a clear message; endpoint raises **503** with the service message (sibling preview-endpoint pattern) behind `except HTTPException: raise`. opencode (GLM) pre-PR review: 1 Major rebutted (4000-token cap vs the UI's 5,000-word option — not deterministic failure since GPT-4 undershoots long targets and stops inside budget; loud failure when exhausted IS the AC; follow-up **#232** filed for a larger-output model or UI range alignment), 1 Minor fixed (the floor), 1 Minor verified-in-diff; post-PR round: no findings. Tests: budget scaling/clamp/floor + `test_truncated_output_is_rejected_not_saved` (sibling convention) + endpoint 503 pass-through (replacing the bug-characterization 500 test). Demo (`docs/demos/2026-07-05-issue-181-draft-truncation.md`): real uvicorn ×2 (main vs branch) + real Mongo + real OpenAI SDK against a wire-boundary stub logging `max_tokens` (local OpenAI key is stale/401 — NB for future AI demos) — old app sent 1000 and returned a mid-sentence 752-word draft as success; new app sent 3200 and returned a complete 1811-word draft; forced budget exhaustion → 503 with the explicit message. Backend **1089 passed / 13 skipped, 91.88% cov**. Demo gotcha: `showboat exec` needs the `<lang>` arg (`showboat exec file bash 'cmd'`) — omitting it reads code from stdin and hangs.
  - **Status**: ✅ Complete

### 2026-07-05
- **Per-user shared-store rate limiting + uvicorn proxy-header pin (#180, P0.8, critical/security)**: backend + deploy config, PR #230. `get_rate_limiter` keyed `{client_ip}:{endpoint}` in a plain in-process dict — per-worker (PM2 runs `--workers 2` since #175, so every limit was ~doubled), reset on restart, never evicted, and IP-keyed. Fix: the limiter now takes `Depends(get_current_user_from_session)` and keys buckets on **`auth_id`** — verified every rate-limited endpoint already requires session auth, so FastAPI's per-request dependency cache makes it free — persisting counts via the existing atomic `$inc`+TTL `increment_usage` DAO (#173) with **epoch-aligned fixed windows** (`rl:{path}:{bucket}` keys, TTL 2 windows, zero new DAO code). 429 + `X-RateLimit-*`/`Retry-After` contract unchanged; client IP only a None-guarded fallback subject. Deleted the deprecated `rate_limit()` + unbounded `rate_limit_cache` dict (zero prod callers). Ecosystem template pins `--proxy-headers --forwarded-allow-ips=127.0.0.1`; **issue premise partially stale** — uvicorn 0.35 defaults `proxy_headers=True` trusting 127.0.0.1, staging nginx already sends XFF from localhost, and staging logs already showed real client IPs (the `:0` port signature) — the flags pin that instead of relying on defaults. **Accepted tradeoffs (documented)**: fixed-window ≤2× boundary burst; per-path buckets on parameterized routes stay per-resource (AI endpoints backstopped by the #173 quota); Mongo failure fails **closed** (auth hits the same Mongo first → no new blast radius; pinned by test). opencode (GLM) review ×3 rounds: 5 findings fixed (client None-guard, HTTP-level DI wiring test, fail-closed pin, clock-patched deterministic window test, dead `import time`), M1/M2/M3 rebutted with evidence, all verified sound. Tests: `TestRateLimiting` rewritten against real Mongo (9 tests incl. the AC two-users test + cross-worker shared bucket). Demo: real uvicorn (2 workers, template args) + real better-auth sessions — 6th request 429s exactly at limit across workers, **429 survives full process restart**, XFF from trusted localhost rewrites the logged client IP. Backend **1086 passed / 13 skipped, 91.87% cov**. Demo gotcha: pydantic `EmailStr` rejects the reserved `.test` TLD at response validation — seed demo users with a routable domain.
  - **Status**: ✅ Complete

### 2026-07-05
- **Cascade account deletion + fix delete_user_books wrong-field filter (#179, P0.7, critical/data-integrity)**: backend-only, PR #229. `DELETE /users/me` **and** `DELETE /users/{auth_id}` only soft-deleted the user record — every owned book plus questions/responses/ratings/access logs persisted forever. Separately, `delete_user_books` filtered books on nonexistent `user_id` (books store `owner_id`) → matched zero real docs; its tests seeded `user_id`, masking the bug. Fix: (1) `delete_user_books` queries `owner_id` (kept per AC as a raw primitive; docstring warns it doesn't cascade); (2) new `app/db/book.py::delete_all_user_books(auth_id)` cascade-deletes every owned book via the existing atomic per-book `delete_book` path (#008); (3) both endpoints cascade **before** soft-deleting the user (children first, parent last) — cascade failure → structured 500 (504 on the auth_id route, its pre-existing convention), account stays active and retryable. User record retention (`is_active: False`) is intended; only content cascades. The `/users/{auth_id}` gap was a **Major from the opencode (GLM) pre-PR review**; round 2 verified fixes, no correctness defects. `test_account_deletion_with_data_cleanup` un-skipped + rewritten against real Mongo; new failure-containment/per-route/DAO-direct tests (incl. idempotent second pass, failure propagation). Demo: real app + real Mongo — old `user_id` filter matched 0 books vs 2 for `owner_id`; DELETE /users/me → 200, all owner data 0, bystander intact, user `is_active: False`. Backend **1086+ passed / 13 skipped, ~92% cov**. Rebutted (documented in PR): cross-user responses unreachable (single-owner model), per-book `isMaster` perf (rare + rate-limited 3/300s), cascade-then-soft-delete-fails window (retry-idempotent).
  - **Status**: ✅ Complete

### 2026-07-04
- **Stop lost-update clobber on TOC/summary writes (#177, P0.5, critical/data-integrity)**: backend-only, PR #227. `update_chapter_content` (the 3s autosave), `update_book_summary`/`patch_book_summary`, and `generate_table_of_contents` all persisted the **whole** `table_of_contents` (or the whole `summary_history` array) via `update_book`'s **version-less `$set`**, so two chapters auto-saving concurrently (multiple tabs) — or a concurrent TOC reorder — **silently clobbered each other** (real data loss). `generate_toc` also hardcoded `version:1`, resetting the CAS counter. Fix adds two DB helpers (`app/db/book.py`) mirroring #159's CAS pattern:
  - **`apply_chapter_content_update`**: targeted **arrayFilters positional `$set`** of only the one chapter's fields + atomic **`$inc table_of_contents.version`**. Concurrent saves to *different* chapters no longer collide → **zero false conflicts, no 409, no frontend change** (chosen over a whole-TOC version guard precisely because this is the high-frequency autosave path — the AC's "targeted positional/arrayFilters" branch). The update query requires the target chapter (and parent, for a subchapter) to still exist, so a chapter deleted mid-edit is a clean **404**, not a false success that only bumps the version. Supports top-level + 1 subchapter level (data-model max depth).
  - **`update_book_summary_atomic`**: an **aggregation-pipeline update** that archives the document's **current** summary at write time (not a client-read value), so two concurrent edits (A→B, A→C) both land in history (single-doc writes serialize; the 2nd sees the 1st's committed summary). History capped at 20; `$`-leading summaries wrapped in `$literal`. Both PUT + PATCH `/summary` route through it and **404** on a concurrent no-match.
  - **`generate_table_of_contents`**: version increments from the current TOC (`0→1` on first gen) instead of hardcoding 1. (Still a full-TOC replace — intended semantics for an explicit, 2-per-5-min rate-limited regenerate; only the hardcoded version is fixed per the AC.)
  - **Reviews**: `codex` (cross-family, 3 rounds) drove the stale-`previous_summary` clobber → pipeline archive; the `matched_count` false-success gap → chapter-existence query predicate + 404; PATCH-summary still RMW → shared helper; and a `$`-summary-as-field-path bug → `$literal`. CodeRabbit (post-PR) caught the summary-endpoint None→false-200 (→404) + a stale test docstring. All fixed with tests.
  - **Tests**: `tests/test_db/test_lost_update_guard.py` (real Mongo) — interleaved-writer no-lost-update for chapter content **and** summary history, subchapter targeting, stale-chapter/wrong-owner no-match, legacy-versionless TOC, `$literal` summary, None-return; + generate-toc version-increment endpoint test. A manual demo proved old-path-loses-`WRITER-B` vs new-path-preserves-both + version 1→3. Backend **1073 passed / 14 skipped, 92% cov**. Gates green (no `--no-verify`). **Env gotcha**: leftover parallel pytest procs (mine + an unrelated project) all drop/recreate the default `auto-author-test` DB → a create→404 race that looks like a code failure; kill stragglers or use an isolated `TEST_MONGO_URI`.
  - **Follow-up**: the same full-TOC-overwrite pattern still lives in other `books.py` handlers (reorder, etc.) — #159's deferred shared-fix, not in scope here.
  - **Status**: ✅ Complete

### 2026-07-04
- **Make production security fail-safes fire (#176, P0.4, critical/security)**: backend-only, PR #226. All three `config.py` guards + `main.py`'s `validate_production_security()` gated on `os.getenv("NODE_ENV") == "production"`, but PM2 sets only `ENVIRONMENT` on the **backend** process (`ecosystem.config.template.js:14` — the frontend block sets `NODE_ENV`, the backend doesn't). On the real deployment the fail-safes were silently dead: `BYPASS_AUTH=true` only warned instead of blocking startup, the built-in CI test secret was accepted as a valid prod secret, and the `<64`-char secret warning never fired. Fix adds one helper `is_production_env()` (True when **either** `ENVIRONMENT` **or** `NODE_ENV` == `"production"`) used in all four guards. Checking both markers — not a straight `NODE_ENV`→`ENVIRONMENT` swap — is more robust and keeps every existing `NODE_ENV`-based test green (backward compat); staging (`ENVIRONMENT=staging`) still allows `BYPASS_AUTH` for E2E, consistent with the existing staging tests. No PM2/deploy-config change needed. Tests set `ENVIRONMENT=production` with `NODE_ENV` unset (the real deployment shape): Settings() raises on `BYPASS_AUTH=true` and on the CI secret, startup RuntimeError blocks, staging still allowed. `codex` cross-family review clean; CodeRabbit rate-limited (no findings). Backend **1060 passed / 14 skipped, 91.97% cov**. Demo drove the real deploy env and observed each fail-safe firing.
  - **Status**: ✅ Complete

### 2026-07-04
- **Offload OpenAI calls off the FastAPI event loop (#175, P0.3, reliability)**: backend + deploy config. `_make_openai_request`'s `_async_wrapper` called the **synchronous** `OpenAI` client inline (`return _sync_request()`), so the multi-second-to-minute blocking HTTP call ran **on the event loop** — with a single Uvicorn worker, one user's generation froze the whole process (health checks, autosaves, every other request). Fix mirrors `export_service.py`'s pattern: `return await asyncio.to_thread(_sync_request)`. Existing tests mock `_make_openai_request`/`chat.completions.create` (above the wrapper), so **zero test churn**. Also set `--workers 2` on the PM2 backend (`ecosystem.config.template.js`) for headroom. **Known limitation**: multi-worker weakens the two *in-memory* mechanisms — the per-IP burst limiter (`get_rate_limiter`) and the Redis-less AI cache become per-worker — but the persisted per-user AI quota (#173, Mongo atomic `$inc`) and entitlement gate (#174, DB-backed) hold across workers, so no cost/access control is lost. Test: `test_ai_service_event_loop.py` proves (1) a concurrent coroutine keeps ticking while an AI call is in flight and (2) two AI calls run in parallel (~0.3s, not serialized ~0.6s). Backend service suite **321 passed**.
  - **Status**: ✅ Complete

### 2026-07-04
- **Billing / entitlement gate for paid access (#174, P0.2, commercial epic)**: full-stack, but ships the *entitlement hook* only — **no payment provider built**. Decision (ADR `docs/adr/2026-07-04-beta-entitlement-model.md`): free-invite beta, single `free` plan now, Stripe deferred. This is the piece P0.1 (#173) keys its per-user AI caps off, so paid launch adds a tier, not a rebuild. PR #224.
  - **Registry** (`app/core/entitlements.py`): plan→capability SSOT. `free`→`{"*"}` (all AI features), `restricted`→`{}` (the named deny path). `is_feature_allowed(plan, feature)`: missing/None plan → free (legacy docs, no backfill); explicit unknown plan → **fail-closed** (denied). `AI_FEATURES` enumerates the 10 gated features.
  - **Persisted plan**: `plan: str = "free"` on `UserBase` (models) + `UserResponse` (schemas); set at every creation point (lazy better-auth create in `security.py`, legacy `POST /users/`, echoed by `GET /users/me`). Model default covers legacy documents → no migration.
  - **Enforcement**: `PLAN_ENFORCEMENT_ENABLED` config flag (default True, bypassed with `BYPASS_AUTH`, mirrored in `.env.example`). `get_entitlement_checker(feature)` dependency in `dependencies.py` — **factory-function form** mirroring the #173 `get_ai_usage_quota` sibling (not a class; gets `Depends`-caching of the user), wired via `dependencies=[...]` onto all **10** AI endpoints in `books.py` alongside the quota dep. Denials → `handle_entitlement_denied()` → **402 `ENTITLEMENT_REQUIRED`** with `X-Entitlement-Plan/-Feature` headers (distinct from the transient 429; no dead `ENTITLEMENT_LIMIT_EXCEEDED` since #173 already owns the over-limit 429).
  - **Frontend clear-path**: `ErrorType.ENTITLEMENT`; 402 mapped in `HTTP_STATUS_TO_ERROR_TYPE`; `aiErrorHandler` classifies 402 as a non-retryable upgrade case; `ErrorNotification` shows an **Upgrade** CTA (→ settings) instead of a RetryCountdown; `plan?` on the `UserProfile` type. **codex caught** that `bookClient.aiError` read only `detail.message` and dropped the HTTP status, so structured 402s (text under `detail.error`) misclassified as 500 for analyze-summary/generate-questions/generate-toc — fixed by attaching `statusCode` (mirrors `exportError`) so both classifier pipelines map 402→entitlement.
  - **Decomposition** (AC4): Stripe work split into #220 (customer/subscription model + raw-body HMAC webhook), #221 (checkout), #222 (billing UI), #223 (optional invite-gating) — out of scope this PR.
  - **Tests**: backend `test_entitlements.py` (registry) + `test_entitlement_gate.py` (dependency allow/deny/bypass/disabled + route-level 402); frontend aiErrorHandler 402 classification (incl. attached-statusCode regression) + ErrorNotification upgrade CTA. Backend **1053 passed / 14 skipped, 91.95% cov**; frontend **2006 passed / 8 skipped, 108 suites**. Demo: real 402 payload + headers for a `restricted` user, free user passes. Free users are never blocked — the gate is a hook proven via the `restricted` path.
  - **Status**: ✅ Complete

### 2026-07-03
- **Cap per-user AI usage / OpenAI spend (#173, P0.1, security/cost-control)**: backend-only. Adds a per-user generation quota so a single beta user — or a leaked session cookie — can't trigger unbounded GPT-4 spend. The window-based `get_rate_limiter` is per-IP burst control; this is a persisted per-user *budget*.
  - **Config** (`config.py`): `AI_QUOTA_ENABLED` (True), `AI_QUOTA_DAILY_LIMIT` (50), `AI_QUOTA_MONTHLY_LIMIT` (500), all env-configurable; a limit ≤ 0 disables that window.
  - **Counter** (`app/db/usage.py`): `increment_usage(user_id, period_key, ttl)` — one tiny doc per (user, period-bucket) keyed `auth_id:day:YYYY-MM-DD` / `auth_id:month:YYYY-MM`, atomic `$inc` upsert with `ReturnDocument.AFTER` (racing generations serialize, no undercount). Lazy TTL index on `expires_at` (ensured once per process) reaps stale buckets so the collection stays bounded. Re-exported via `database.py`; 100% covered.
  - **Enforcement** (`get_ai_usage_quota()` in `dependencies.py`): a FastAPI dependency mirroring `get_rate_limiter`. Increments daily+monthly on entry and raises **429** (clear user-facing message + `X-AI-Quota-*` headers) once either cap is exceeded — enforced *before* the OpenAI call so the spend is reserved, not incurred. Bypasses under `BYPASS_AUTH`/when disabled; fails **closed** (401) if a user id can't be resolved. Wired via `dependencies=[Depends(get_ai_usage_quota())]` onto all **10** AI endpoints (analyze-summary, generate-questions, generate-toc, chapter generate-questions, regenerate single/all, generate-draft, transform-style, enhance-text, enhance-transcription) — decorator-level, no handler-signature churn.
  - **Design notes**: counts *attempts* (a rejected call still increments — matches the in-memory limiter); keys off `auth_id` today, swaps to plan/entitlement when P0.2 lands; real cross-nginx enforcement still needs P0.8. Because it's a pre-body dependency (like the rate limiter), a request that later 404s/403s still consumes quota — but it's keyed on the caller's own `auth_id`, so it's self-limiting, not a cross-user vector.
  - **Tests** (`test_ai_usage_quota.py`): DAO atomic increment + key independence + TTL field; the AC test proves the (cap+1)th call in a window is rejected with 429; per-user isolation; monthly-window enforcement; disabled-bypass; config defaults. `conftest.py` gains a no-op quota swap + `real_ai_quota` fixture (mirrors `real_rate_limiter`). codex pre-PR review: fail-closed fix applied; the pre-authz-charge and attempt-counting notes rebutted as deliberate (consistent with the existing limiter).
  - **Env gotcha**: mongod died mid full-suite once, producing a 30s-per-op hang cascade (not a code failure) — restart Mongo before the full run. Backend **1042 passed / 14 skipped, 91.91% cov**.
  - **Status**: ✅ Complete

### 2026-07-02
- **Complete account settings (#64, P3.6)**: full-stack. Adapted the CodeRabbit plan (2026-06-21), which had drifted on 5 counts — the settings page was **not** a stub (theme/email toggles already saved with a load-guard), the style list was the pre-#55 six, export lacked EPUB/Markdown, `userClient.ts` was superseded by `useProfileApi`, and its "Active Sessions via backend `/sessions/list`" targeted **dead infrastructure** (app-session middleware keys off `request.state.user`, which nothing sets post-better-auth → list always empty). Sessions use better-auth native `listSessions`/`revokeSession`/`revokeOtherSessions` instead.
  - **Backend**: `UserPreferences` (model + schema) gains validated fields — `default_writing_style` (Literal of the 5 shipped styles), `auto_save_interval` (3–30s, default 3 = shipped behavior), `default_export_format` (pdf/docx/epub/markdown), `default_page_size` (letter/A4), `include_empty_chapters`, `writing_reminders`, `progress_updates`, `backup_notifications`. No new endpoints — rides `PATCH /users/me`. NB: `UserUpdate.preferences` replaces the whole object (Pydantic fills omitted fields with defaults), so every client **merges loaded prefs before saving** — the page-level contract tested since #63. Notification toggles are stored contract only: the backend sends no email today (no SMTP/provider code); nothing was invented (YAGNI).
  - **Settings page** (`dashboard/settings`) → 4 Radix tabs (Writing/Export/Notifications/Security), keeping the load-before-save guard + merge-on-save. Theme select wired to next-themes `setTheme` → **applied immediately** (previously the stored theme never touched the UI). Decorative unwired controls (font size, 1–300s interval) removed. New `components/settings/*`: three controlled pref forms + `PasswordChangeForm` (better-auth `changePassword`, `revokeOtherSessions: true`), `TwoFactorSetup` (TOTP via better-auth `twoFactor` plugin: password → QR (`react-qr-code`) + copyable backup codes → verify), `ActiveSessionsList`.
  - **2FA plumbing**: `auth.ts` adds `appName` + `twoFactor()` plugin (Mongo adapter needs no migration); `auth-client.ts` adds `twoFactorClient` with redirect → new `/auth/verify-2fa` page (6-digit auto-submit, trust-device, backup-code path). **Sign-in fix**: the page unconditionally `router.push`ed after non-error sign-in — now returns early on `twoFactorRedirect` so it can't race the 2FA redirect to `/dashboard`. The auth-client cast was rebuilt (`typeof baseAuthClient & …`) so plugin method types survive.
  - **Prefs applied app-wide** via new cached `useUserPreferences` hook (one GET per page load; settings save calls `invalidateUserPreferencesCache`): `DraftGenerator`/`DraftGenerationButton` pre-select the default style (touched-guard so user picks win; shared `lib/constants/writing-styles` replaces duplicated arrays), `ExportOptionsModal` seeds format/page-size/include-empty, `ChapterEditor` auto-save delay = `auto_save_interval` (shared `lib/constants/auto-save`, invalid → 3s).
  - **Jest gotcha**: suites load the **real** `auth-client.ts` safely only because `better-auth/react` is moduleNameMapper'd to a mock — the new `better-auth/client/plugins` import (ESM-only) broke every such suite until mapped to `__mocks__/better-auth-client-plugins.ts`. Global mocks extended (authClient security methods, `useUserPreferences` → null so consumers keep shipped defaults; override per-suite for regression tests). Also: Radix `TabsTrigger` doesn't activate on `fireEvent.click` (mousedown-based) — use `userEvent.click`. A full-suite run alongside the dev server + Playwright produced 35 **contention flakes** (all pass isolated and in a quiet full run) — don't debug "failures" while a Next dev server is compiling.
  - **Reviews (pre-PR)**: CodeRabbit CLI (8 findings) — 5 fixed (verify-2fa missing catch on transport failure; cache-clobber race → generation counter; disable-2FA status stuck "Enabled" until session refetch → `localEnabledOverride` both directions; manual TOTP secret fallback beside the QR; missing `progress_updates` round-trip assert), 1 partially adopted (E2E failed-save + revoke-session cases added; full 2FA E2E skipped — unit-covered, plugin internals brittle to route-mock), 2 rebutted (native `<select>` is the #63 profile pattern — labeled, jsdom-testable; null-not-cached is intentional retry-on-error). Self-review also caught the **sign-in/2FA race** above. Report: `docs/code-review/2026-07-02-account-settings-review.md`.
  - **Tests**: backend preference validation/persistence (15, incl. 422 bounds + direct-Mongo round-trip — GET /users/me echoes the mocked session user in the harness, so persistence asserts against the collection); frontend settings page (10), security components (11), verify-2fa (4), `useUserPreferences` cache (4), applied-defaults regressions (7, incl. auto-save waits-for-10s test); route-mocked E2E `settings.spec.ts` (**5 passed**: merged-PATCH save, export-tab defaults, failed-save keeps edits, revoke-session, password change via `/api/auth/change-password`). Frontend **2003 passed / 8 skipped, 108/108 suites**, coverage 89.96/81.04/86.51/91.2; backend **1034 passed / 14 skipped, 91.87% cov**. **Local-env gotcha**: `backend/.env` had `BYPASS_AUTH=true` (leftover) — it makes exactly the auth-assertion tests fail (401-expected, role-forbidden, session-middleware); run backend suites with `BYPASS_AUTH=false` locally.
  - **Demo round (real better-auth, no bypass — signup→settings→2FA)** caught two real issues the unit/E2E nets missed, fixed post-PR: (1) **theme was invisible** — `tailwind.config.js` hardcoded dark RGBs for card/muted/accent/secondary/popover and pointed background/foreground at `var(--color-*)` names that only exist in the Tailwind-**v4** `@theme inline` block, which this **v3** project ignores (so `bg-background` never resolved). Config now reads the real `:root`/`.dark` variables — `.dark` values match the old RGBs, so the default dark look is pixel-equivalent, and Light genuinely flips the dashboard shell (root/dashboard layouts moved off `bg-gray-950` to tokens; brand indigo/destructive stay fixed). (2) **theme-change clobbered edits**: syncing the stored theme on load put next-themes' `setTheme` in `loadPreferences`' deps; its identity changes after a theme change → loader re-fired → wiped in-progress edits and reverted the theme. Fixed with a setTheme ref + once-per-visit sync guard; regression test makes the mock return a fresh `setTheme` identity per render. **Demo verified end-to-end**: prefs PATCH→reload persistence; light/dark immediate + on-load; full TOTP loop (enable → QR + manual secret + backup codes → verify with a Python-computed RFC-6238 code → sign-out → sign-in lands on `/auth/verify-2fa` → fresh code auto-submits → dashboard). NB `agent-browser click @ref` doesn't reliably fire React handlers on this page — use `eval` `.click()`; snapshot refs go stale after every `open`.
  - **Status**: ✅ Complete

### 2026-07-01
- **Complete user profile editing (#63, P3.5)**: PR #170 — full-stack. The backend user model + `GET/PATCH/DELETE /users/me` (better-auth) already existed; verified-before-building, this closed the real gaps: the missing frontend page, avatar upload, validation, and profile→export author info. **Plan drift corrected**: Traycer/CodeRabbit both mirrored `book_cover_upload.py` (**deleted in #93**) — mirrored the live cover path (`books.py` + `FileUploadService`) instead; `useOptimizedClerkImage` still exists (legacy name, the pre-existing `ProfilePage.test` requires it) so kept, not renamed; Clerk test mocks → better-auth.
  - **Frontend**: new `app/profile/page.tsx` (name/bio/preferences/avatar/delete-account) built to the **pre-existing `ProfilePage.test.tsx` contract** — which was in jest `testPathIgnorePatterns` ("missing module"); now un-ignored since the page exists. The test mocks `react-hook-form`/ui/`useProfileApi`/`useOptimizedClerkImage`, and its `useProfileApi` mock omits `getUserProfile` → the page **guards the profile fetch** and seeds initial state from `useSession()`, hydrating full data (bio/prefs) from GET /users/me when available. Only `Form`+`FormField` are mocked from `ui/form`, so the page uses a native `<form onSubmit={form.handleSubmit(onSubmit)}>` + plain `Label`/`Input`/`Switch` (no FormItem/Label/Control/Message). `useProfileApi` rewritten from Clerk-era "deprecated" throw-stubs to real cookie-auth `getUserProfile`/`updateUserProfile`/`deleteUserAccount`. New `ProfilePictureUpload` (client type/size validation, multipart POST). "Profile" nav → `/profile`.
  - **Backend**: `POST /users/me/avatar` + `FileUploadService.process_and_save_profile_picture` (fits 400×400 aspect-preserving — not cropped square, UI circles it via object-cover; single image no thumbnail). `UserUpdate` field-length limits (name ≤50, display ≤100, bio ≤1000) + `theme` Literal enum. Export author injection: the verified owner (`current_user`, no extra DB hit) supplies `author_name` (display_name → "first last") + `author_bio` merged into `book_data` for all 4 formats; PDF/DOCX render an "About the Author" section.
  - **codex (pre-PR, cross-family)** found 4, all fixed with tests: **decompression-bomb guard** in `validate_image_upload` (50MP cap, hardens cover too); **persist-before-delete-avatar** (update_user first, cleanup the new file on failure, then remove the old — no orphan / no dangling pointer); **bio XML-escaped** before ReportLab `Paragraph` (unescaped `<` would crash PDF); the relative-`/uploads` URL note is a **pre-existing app-wide pattern** (covers render `cover_image_url` the same way; prod uses cloud storage) → documented, not diverged. **Post-PR round (2026-07-02)**: a manually-triggered CodeRabbit review posted 8 findings — 5 fixed (display_name editable+persisted; `.min(1)` dropped so null-name users can save; hydration reset guarded by `isDirty`+unmount so a slow fetch can't clobber edits; errors read from public `form.formState` not private `control._formState`; PDF bio uses template-aware styles), 3 rebutted (default-export claim false — `useProfileApi.ts` has one; Vitest migration — repo is Jest; `verify()` stream concern — already re-seeks). A second `codex review` caught a real P2 the first round missed: hydration seeded `displayName` from `first_name` only when unset, so a later save persisted a **truncated author name** into exports — now seeds first+last (E2E regression test). Demo'd end-to-end with **real better-auth session** (signup→profile edit→avatar→DOCX/PDF containing "About the Author" + bio); NB the bypass-auth mock user can't demo export-author or PATCH persistence (mock isn't a DB record).
  - **Tests**: backend avatar endpoint (success/invalid-type/too-large/replaces-old/persists/401) + service (local/cloud/bomb/path-traversal) + export author (injection, real-DOCX "About the Author" bio, markup-doesn't-crash) + validation (422 over-length/bad-theme); frontend ProfilePage (7, un-ignored) + ProfilePictureUpload + useProfileApi units + route-mocked E2E `profile-editing.spec.ts` (edit→save asserts PATCH; avatar upload asserts POST + image). Backend **1024 passed / 14 skipped, 91.85% cov**; frontend **1972 passed / 8 skipped**; CI Backend/Frontend/**E2E (real backend)** all green.
  - **Status**: ✅ Complete

- **Question regeneration with improved quality (#62, P3.4)**: PR #169 — full-stack. Adapted the CodeRabbit/Traycer plan, whose **Phase 2 was stale** (it wired in `QuestionFeedbackService`/`question_quality_service`/`RefinementAction`, all deleted in #120) — dropped and replaced with a minimal rating→prompt wiring (YAGNI). Verified before building: per-question regenerate button, full-set `regenerate-questions` endpoint + `regenerateChapterQuestions`, thumbs rating UI, focus types, and rate limiting already existed.
  - **Confirmed bug fixed**: `QuestionContainer.handleRegenerateQuestion` called `bookClient.generateQuestions` (the TOC clarifying-questions method) instead of a chapter regenerate → per-question regenerate was broken. Now hits the new single-question endpoint.
  - **New endpoint** `POST /books/{id}/chapters/{cid}/questions/{qid}/regenerate` (books.py) — regenerate one question in place, ownership 403/404, rate-limited 2/180s, **429** at a per-question cap (`MAX_QUESTION_REGENERATION_COUNT=5`). Replacement is a single atomic **CAS `find_one_and_update`** on `regeneration_count` (`replace_question_in_place` in `db/questions.py`): same `_id` preserved, so there's **no delete/create data-loss window**, racing regenerations serialize (loser gets no doc → 409-style `QuestionNotFoundError`), the counter can't double-increment, and the prior **rating stays attached** (feedback isn't orphaned). The question's stale response is cleared (old answer no longer applies). AI candidate is generated **before** any mutation.
  - **Prompt quality**: both regen paths now thread **previous question texts** ("generate meaningfully different… don't repeat") + **feedback guidance** aggregated from prior low ratings (≤2★, via new `get_ratings_for_chapter`). Also fixed a **pre-existing** `audience`/`target_audience` key mismatch that silently dropped audience guidance from all generation.
  - **Frontend**: `regenerateSingleQuestion` client (parses structured error, attaches `statusCode` so the 429 cap is detected without string-matching); "Regenerate All" button → `RegenerateQuestionsDialog` (focus checkboxes + keep-answered toggle); per-question "Regenerated N/5" display, regenerate disabled at the cap **and** while a request is in flight; single-regen refreshes `cachedQuestions` + progress so stale-while-revalidate can't resurrect the replaced question.
  - **Reviews**: `codex` (pre-PR) caught the concurrency-duplicate + over-generation; CodeRabbit (post-PR) caught the delete/create loss window, the audience key bug, stale cache/progress, missing in-flight disable, and raw-error leakage — all fixed (the atomic in-place replace resolved three data-integrity findings at once). The "feedback orphaned on delete" finding is moot with in-place replace (same id keeps the rating).
  - **Tests**: backend unit (prompt context, `_build_feedback_guidance`, single-regen success/limit/not-found/wrong-chapter/lost-race, count=1) + integration (200/429/404/403, stale-response cleared); frontend unit (client statusCode, container rewire asserting the TOC method is NOT called, limit + in-flight UI, dialog) + route-mocked E2E `question-regeneration.spec.ts`. Backend **1001 passed / 15 skipped, ~92% cov**; frontend **1959+ passed**, gates green; CI (Backend/Frontend/E2E) green.
  - **Status**: ✅ Complete

- **chapters.py bulk-status concurrency guard + read-handler error handling (#159, P3.8)**: PR #165 — backend-only; two latent defects from the #94 verbatim move, flagged by CodeRabbit on #157.
  - **Adaptation**: the CodeRabbit plan targeted `books.py` claiming `chapters.py` didn't exist — **stale** (#94/#157 already extracted these handlers). Fixes applied in `chapters.py`. **Dropped plan Phase 3** (repo-wide ruff `B008`/`B904` config): ruff B rules aren't enabled here and the lint hook is non-blocking (`|| true`) — new lint scope for an optional nit, out of scope for a bug fix (YAGNI).
  - **Lost-update fix**: `update_chapter_status_bulk` overwrote the entire `table_of_contents` via `update_book()` with **no version check** — a concurrent TOC edit was silently clobbered. Now persists through a new `update_chapter_statuses_with_version_guard()` in `toc_transactions.py`: a **single compare-and-swap `update_one`** filtered on `table_of_contents.version`. A bulk change touches one document, so a single conditional update is atomic on its own — **no transaction** — so the guard holds on both replica-set and standalone (a transaction would surface a concurrent commit as a `WriteConflict`→500). Stale version → `modified_count==0` → `Version conflict` → **409**, mirroring create/update/delete_chapter. Handler keeps its ownership pre-check (wrong-owner **403**, missing book **404**) and up-front transition validation (invalid **400**). Helper re-emits the `book_update` audit log the old `update_book()` path produced. **codex + CodeRabbit** drove: CAS-not-transaction (reliable 409), audit-log preservation, version-**absent** legacy TOC matched on `$exists:false` (no false conflict), and wrapping the post-commit `log_access` loop so a logging failure can't fail an already-committed update (matches `update_chapter_content`).
  - **Structured errors**: `get_chapters_metadata`, `get_tab_state`, `list_chapters`, `save_tab_state` had no `try/except` → unlogged 500 on unexpected error. Each now `except HTTPException: raise / except Exception: logger.error(exc_info=True) → structured 500`, preserving 404/403.
  - **Tests**: helper unit tests (happy+audit, stale→conflict-no-write, version-less TOC, nested, no-match, timestamp, not-found, wrong-owner) + endpoint tests (409 mapping, structured 500 per handler, 404 preserved, logging-failure→200-and-persisted). Backend **986 passed / 15 skipped, 92.17% cov**. CI green (Backend/Frontend/E2E); CodeRabbit findings all addressed.
  - **Follow-up**: the same non-transactional full-TOC-overwrite pattern lives in other `books.py` handlers (`update_chapter_content`, summary/toc) — the issue's deferred "shared fix", not done here.
  - **Status**: ✅ Complete

### 2026-06-30
- **Markdown export format (#61, P3.3)**: PR #164 — fourth export format alongside PDF/DOCX/EPUB, built by mirroring the EPUB pattern (#147).
  - **Backend**: `ExportService.generate_markdown(book_data, chapters, multi_file=False)` — single `.md` (book title `#` + metadata + per-chapter `##` + html2text-converted content) or a ZIP of `NN-slug.md` files (`zipfile`). A **dedicated `html2text` instance with `ignore_images=False`** preserves image refs (`![alt](src)`) — the shared text-extraction converter strips them. Worker thread (asyncio.to_thread) like PDF/DOCX/EPUB; `HTML2TEXT_AVAILABLE` guard → `ExportUnavailableError`. `export_book()` gains a `multi_file` param + `'markdown'`/`'md'` dispatch. New `GET /books/{id}/export/markdown` (`include_empty_chapters`, `multi_file`) — auth/ownership/10-per-hr rate-limit, `text/markdown` (single) or `application/zip` (multi, `_chapters.zip`), `access_type="export_markdown"`; markdown added to `/export/formats`.
  - **Frontend**: `ExportFormat` += `'markdown'`; `ExportOptions` += `markdownMultiFile`. `ExportOptionsModal` Markdown radio + **markdown-only "Separate File Per Chapter" switch**; `bookClient.exportMarkdown`; `page.tsx` handleExport routing; `generateFilename` maps `markdown`→`.md` (`.zip` for multi-file via an extension-override arg). Fixed stale `validateExportOptions` allowlist (was pdf/docx only).
  - **Scope**: **dropped** the Traycer/CodeRabbit plan's GFM-vs-standard flavor toggle (YAGNI — html2text output is already standard/GitHub-compatible Markdown, not an AC). Subtitle renders as emphasis, not `##`, so it doesn't compete with chapter headings in a viewer outline. Legacy `export/page.tsx` left pdf/docx-only (already lacked EPUB — same as #147). Content sub-headings converted verbatim (max fidelity).
  - **Tests**: backend service (single hierarchy, image refs, multi-file zip, dispatch, availability guard) + endpoint (single/multi/404/403, `/formats` lists markdown, `len(formats)` 3→4); frontend modal option/switch, `bookClient` URL, `generateFilename`. Backend **970 passed, 92.08% cov** (export_service 94%); frontend **1943 passed**, gates green.
  - **Status**: ✅ Complete

- **Decompose books.py — map + first extraction (#94, P3.1)**: PR #157 — backend-only, **behavior-preserving move** (not a redesign). First slice of the 3,496-line `books.py` decomposition.
  - **Drift**: plan was written at 3,184 lines; `books.py` had grown to **3,496** — re-derived ranges per the plan's drift-check. Key structural fact: **no module-level helpers** — every `def` is a route handler, so a cluster's only cross-file deps are imports + shared services (`chapter_access_service` spans chapters/content/questions; `chapter_status_service` is chapters-only). That's why the chapters slice extracted with zero helper duplication.
  - **Extracted** the 9 chapter-management handlers (a **contiguous block**, orig. lines 1442–1994: create/get/update/delete/list/metadata/bulk-status/tab-state) verbatim into new `chapters.py`, mounted `include_router(chapters.router, prefix="/books")` **after** the books include. `books.py`: 3,496 → **2,928** lines (−568), 43 → 34 handlers; trimmed the 10 imports the move orphaned (pre-existing dead imports left alone — out of scope). Handler order preserved so the GET literals `/metadata`, `/tab-state` still precede `/{chapter_id}` (the #121 route-shadow bug); `bulk-status` is PATCH-only so its order is moot.
  - **Route table (method, path) verified byte-identical** before/after (69 routes, diff clean) — the invariant that matters for a move. Deliverable **`plans/010-books-decomposition-map.md`** catalogs all 43 handlers by cluster + line range with the suggested extraction order for the remaining slices (content/analytics → questions → drafts → summaries/toc).
  - **Tests**: new `test_chapters_characterization.py` asserts route-table identity (every chapter path still served, owned by `chapters.router`, no duplicate mount, GET-literal ordering). Existing `test_books_chapters_crud_coverage` + `test_books_chapter_content_coverage` are the behavioral net (pass **before + after**). Full backend **961 passed / 15 skipped, 92.38% cov** (`chapters.py` 87%). CI all green (Backend/Frontend/**E2E Playwright**).
  - **CodeRabbit triage (verify-before-fix)**: 3 Major findings, all on **verbatim-moved code** (byte-identical to backup) → deferred as out-of-scope for a move, tracked as follow-ups: dead `create_chapter` "Parent not found" branch (404 vs 400) → **#158**; missing structured try/except on read handlers + bulk-status non-transactional full-TOC overwrite (lost-update) → **#159**. CR's suggestion to assert `bulk-status` precedes `{chapter_id}` was **rejected** — it's PATCH-only, no collision; the assertion fails and encodes a false invariant (caught by running it).
  - **Status**: ✅ Complete

### 2026-06-30
- **Wire Interview Questions / Chapter Editor tabs (#110, P2.12)**: PR #156 — frontend-only. The issue premise was **stale**: `QuestionContainer` was already wired live into `ChapterEditor` (the #105/#54 hand-rolled "Write / Interview Questions" button toggle), so AC-1 (reachable) + AC-2 (answer + persist) were already met. The orphaned `ChapterQuestions.tsx` (Radix tabs) was never in a live route. Closed the real gap: proper tab semantics + un-skipping the E2E infra.
  - **`ChapterEditor.tsx`**: button toggle → Radix `<Tabs>` ("Interview Questions" / "Chapter Editor"), which supplies `role=tab/tablist/tabpanel`, `data-state`, `aria-selected`, `aria-labelledby`, and native arrow-key roving for free (less code than hand-adding them). `QuestionContainer` in the questions tab; TipTap editor in the editor tab. Chose to **adapt the shipped toggle**, not resurrect `ChapterQuestions` (which lacks an editor panel; its CodeRabbit-plan `editor→draft` rename would break the tabs-nav spec's `sessionStorage==='editor'` assertion).
  - **Editor stays the default view** — `saveStatus`/`localStorage`/`questionsToggle` unit tests (~10) assume the editor renders on mount; the E2E specs assumed questions-first. Adapting the specs I was un-skipping is a far smaller blast radius than breaking the unit suite. Tab `value="editor"` **plus** a separate `data-tab="draft"` attribute satisfies both the tabs-nav spec (`'editor'`) and the journey spec (`[data-tab="draft"]`) without a conflicting rename.
  - **Per-chapter persistence**: selected tab saved in `sessionStorage['chapterQuestionsTab_<book>_<chapter>']`, restored in an effect keyed on the storage key (not the `useState` initializer) — `TabContent` renders `ChapterEditor` **without a key**, so a once-only initializer left the tab on the previous chapter's view + risked an SSR hydration mismatch (codex P2, fixed pre-merge; +rerender regression test).
  - **Ctrl+digit intentionally NOT bound** to the view toggle — `ChapterTabs` owns `Ctrl+1..9` for chapter quick-switch (shipped + tested); binding it here hijacked chapter nav (caught in local E2E). Tabs stay keyboard-operable via Radix arrow roving + click.
  - **Gotcha**: a `display` utility (`flex`) on a Radix `TabsContent` **overrides the `hidden` attribute** (`.flex{display:flex}` beats `[hidden]{display:none}`), leaving the inactive panel visible and covering the active panel's buttons — moved the flex layout to an inner wrapper. jsdom didn't apply the stylesheet so unit tests missed it; the real-browser E2E (`chapter-questions-progress` "Next Unanswered" click) caught it.
  - **Tests**: un-skipped + rewrote `chapter-questions-tabs.spec.ts` (5 skipped → live; removed silent `if(isVisible)` guards; **7 passed / 1 AI-skip** in CI on real backend). The AI-dependent `complete-authoring-journey` full journey **stays skipped** (CI has no OpenAI key; uses fixed timeouts) — its `data-tab` selectors are now satisfied so it can be un-skipped once AI is keyed/mocked. Frontend **1932 passed**, coverage 90.7/82.9/87.2/91.8 (gates green); backend untouched. CI all green (Frontend/Backend/**E2E Playwright**); codex P2 fixed; CodeRabbit clean (1 Minor stale-docstring nit fixed).
  - **Status**: ✅ Complete

### 2026-06-29
- **Accessibility — WCAG 2.1 AA (#50, P2.10)**: PR #154 — frontend-only, evidence-driven from a 3-explorer + jest-axe audit (foundation already solid: Radix, jest-axe 0 violations on tested components, correctly-labeled forms — so this closed the real gaps, not a blind sweep).
  - **ARIA labels** on icon-only controls (a bare `title=` is an unreliable SR name): `EditorToolbar`'s 14 buttons → `aria-label` + `aria-pressed`, wrapped in `role="toolbar"`; `TabBar` scroll up/down, `TabOverflowMenu` trigger, `UserButton` avatar.
  - **Skip link + landmarks**: root layout adds a "Skip to main content" link and its wrapper `<main>`→`<div>`. Exactly **one `<main id="main-content" tabIndex={-1}>` per route in every render state** — dashboard content, `auth/layout` (covers all auth pages + Suspense fallbacks), landing (content/loading/error), `ProtectedRoute` loading/redirect, `error.tsx`, and the root ErrorBoundary fallback. `QuestionContainer`'s self-`<main>`→ labeled `<section>` (no nested main). Dashboard `<nav>`s labeled. **codex's 4-round adversarial review drove this robustness** — each round caught a real fallback-state gap (public/auth targets, ProtectedRoute loading, nested main, route-error states).
  - **Keyboard/forms**: `DeleteBookModal` wrapped in `<form>` (Enter submits when confirmation matches; async `handleConfirm` guarded against unhandled rejection); input `aria-invalid` + `aria-describedby`, error `role="alert"`.
  - **Focus/contrast**: global `:focus-visible` outline fallback for `a`/native controls (`button`/`input`/`select`/`textarea`/`summary`)/`[role=button]`/`[tabindex]`; `SummaryInput` help text `gray-600`-on-dark (failed AA) → `gray-400`.
  - **Deferred (documented)**: arrow-key roving tab nav — `TabBar` uses react-beautiful-dnd, which reserves Space/arrows for keyboard drag-reorder; roving nav would conflict. Tabs are already keyboard-operable (`tabIndex=0` + Enter/Space → WCAG 2.1.1 met) + Ctrl+1-9. Arrow roving is an ARIA-APG recommendation, not an AA criterion. **Manual-only ACs**: Lighthouse >95, NVDA/JAWS.
  - **Tests**: new `EditorToolbar` a11y test (14 accessible names + `role=toolbar` + `aria-pressed` + axe); `DeleteBookModal` Enter-submit + `aria-invalid`/`role=alert`; `QuestionContainer` a11y tests retargeted to the labeled region. Frontend **1930 passed**, coverage 90.7/82.9/87.2/91.8 (gates green). CI all green (Frontend/Backend/E2E). codex clean; CodeRabbit's actionable items addressed (Vitest-migration nitpick rejected — repo is Jest end-to-end, no Vitest config).
  - **Status**: ✅ Complete

### 2026-06-29
- **Mobile responsiveness (#51, P2.9)**: PR #153 — frontend-only. Driven by the orphaned `responsive.spec.ts` (the real acceptance spec), not the CodeRabbit plan's wording.
  - **Touch targets (WCAG 2.5.5, 44px on `<768px`)** applied via responsive base classes (`max-md:`) instead of the plan's **opt-in `mobile`/`icon-mobile` button variants** — the spec asserts *every rendered button* is ≥44px, which an unused variant can't satisfy. One edit per primitive, desktop sizes unchanged: `ui/button` (`max-md:min-h-11 max-md:min-w-11` on the CVA base → all buttons app-wide, no call-site churn), `ui/input`/`ui/select` (`max-md:min-h-11`). `ui/radio-group`/`ui/switch` keep the compact visual but expand the tap area to 44px via a transparent `::before` overlay. Raw `<button>`s that bypass the Button component (auth password toggles; dashboard nav/menu toggles) got explicit mobile sizing + `max-md:pr-14` on password inputs so the bigger toggle doesn't overlap text.
  - **Swipe navigation**: new `hooks/useSwipeGesture` (native touch events, threshold + horizontal/vertical discrimination so it won't hijack vertical scroll, SSR-safe). Uses a **callback ref** (not a ref object) so it binds when the swipeable element mounts *after* the first render — `useMediaQuery` starts `false`, so `ChapterTabs` renders the swipe wrapper only on a later render; a one-time `[]` effect would never attach (codex caught this as a P1). `ChapterTabs` wires swipe left/right → next/prev chapter on mobile only (`touch-action: pan-y`), walking the full `state.chapters` order (what the mobile selector shows), not `tab_order`.
  - **Viewport**: `app/layout` exports Next.js `viewport` (`device-width`, `initial-scale=1`, `viewport-fit=cover`). **No `maximum-scale`** — blocking zoom is a WCAG 1.4.4 violation (plan hedged; dropped it).
  - **E2E activation**: moved orphaned `frontend/e2e/responsive.spec.ts` → `frontend/src/e2e/` (into `testDir`); removed forbidden `waitForTimeout`; fixed a `button.first()` flaw that resolved the DOM-present-but-hidden mobile-menu toggle on desktop. The CI **E2E Tests (Playwright)** job runs `--project=chromium` with backend+Mongo, so the spec's in-test `setViewportSize` mobile checks run there; the 6 chapter-page-fixture-dependent tests stay `skip`ped.
  - **Dropped as already-satisfied** (verified, not re-done): `QuestionNavigation` already `min-h-[44px] min-w-[44px]`; `textarea` already `min-h-16` (64px).
  - **Tests**: `useSwipeGesture.test` (incl. a late-mount regression test that fails against the old one-time-effect version) + `ChapterTabs` mobile-swipe cases. Frontend **1909 passed**, coverage 91.0/83.1/88.8/92.1 (gates green); `responsive.spec.ts` **36 passed/6 skipped** under the CI prod-build config. Backend untouched. CI all green (Frontend/Backend/E2E). `codex` cross-family review clean (P1 callback-ref, P2 swipe-order, P3 password-padding all fixed pre-merge); CodeRabbit App auto-skipped on a title-keyword false-positive.
  - **Status**: ✅ Complete

### 2026-06-29
- **Comprehensive loading indicators & skeleton screens (#52, P2.8)**: PR #152 — frontend-only; adapted the CodeRabbit issue plan, reusing existing `Skeleton`/`LoadingStateManager`/inline-spinner (no new abstraction, no new deps)
  - **Page-level skeletons** (replace centered spinners → mirror real layout, prevent layout shift, `role="status"`/`aria-live`/`aria-busy` + sr-only text): `dashboard/page.tsx` + `dashboard/loading.tsx` (book-card grid), `dashboard/books/[bookId]/page.tsx` (breadcrumb/title/stepper/two-column/tabs), `ChapterTabs.tsx` (**orientation-aware** tab-list + content — vertical split or horizontal stack).
  - **Component loading-state gaps**: `TocReview` "Accept & Continue" spinner + "Saving…"; `ClarifyingQuestions` skeleton + disabled inputs during initial response load (new `isLoadingResponses`); `BookMetadataForm` spinner + `disabled` inputs while auto-saving; `ChapterQuestions` explicit "Loading progress…" indicator (was a blank gap).
  - **Already-satisfied tasks dropped** (verified in code, not re-done): DraftGenerator dead `LoadingStateManager` (fixed in #55 — `isGenerating` checked first; only the now-dead inline button spinner removed here) and DraftGenerationButton fetch-gap (`step='generating'` is set *before* the fetch, so `LoadingStateManager` already shows). Plan's `LoadingSpinner` doesn't exist → used inline spinner/`Loading03Icon`. The big-ticket ACs (>2s progress %, >5s est. time) were already met by `LoadingStateManager` on the AI ops.
  - **Tests**: new `TocReview.test.tsx`, `BookMetadataForm.test.tsx`, `pages/LoadingSkeletons.test.tsx`; extended `ClarifyingQuestions`/`ChapterTabs`/`ChapterQuestionsTabs` tests (skeleton role/aria, disabled state, skeleton→content transition, orientation). The new initial-load skeleton made 12 `ClarifyingQuestions` tests query before the mocked load resolved → switched those to `await findBy*`. Frontend **1898 passed**, coverage 91/83/89/92 (gates green); backend untouched.
  - **Process note**: an initial `git add -A` swept pre-existing untracked working files (`plans/`, `tasks/lessons.md`, a **staging-only** E2E spec, helper scripts) into the commit; the staging spec needs live auth and **failed the normal E2E job** (looked like the feature broke E2E — it hadn't). Fixed with `git rm --cached` (kept on disk), no force-push. Lesson logged. **Stage explicitly when untracked files are outside the change.**
  - **Status**: ✅ Complete

### 2026-06-29
- **Chapter-question progress tracking (#53, P2.7)**: PR #151 — frontend-only; backend already supplied progress + per-question `response_status`
  - The CodeRabbit/Traycer "replace stub progress bar with shadcn `Progress`" task was **already done** in the codebase, so it was omitted. Closed the real gaps:
    - `QuestionContainer.handleResponseSaved` now re-fetches the **questions array** (via `fetchQuestions(true)`, which also refreshes progress), not just the aggregate summary — so dropdown/dot statuses update in real time instead of going stale until reload.
    - `QuestionProgress` dots colour from each question's `response_status` (green/amber/blue-current/gray) instead of positional `index < completed` logic (wrong for out-of-order answers); falls back to positional when no `questions` prop.
    - `QuestionNavigation` gains a **"Next Unanswered"** button (`findNextUnanswered`, wraps, disabled when all completed) and marks unanswered dropdown items distinctly (`○` + `text-muted-foreground`; completed `✓`/draft `⚙️` unchanged).
  - **Tests**: `QuestionProgress.test.tsx` (per-question dots + positional fallback), `QuestionNavigation.test.tsx` (`findNextUnanswered`, Next-Unanswered button, `○` marker), `QuestionContainer.test.tsx` (refresh-on-save); route-mocked E2E `chapter-questions-progress.spec.ts` reaches `QuestionContainer` via the ChapterEditor "Interview Questions" tab (#105). Two pre-existing `getByRole('button',{name:/next/i})` queries tightened to `/^next$/i` to disambiguate the new button. Frontend **1890 passed**, coverage 90.98/82.99/88.62/91.97 (gates green); backend unchanged. `ResponseStatus` enum has only DRAFT/COMPLETED — unanswered = `undefined` (the plan's `'not_answered'` string isn't in the frontend type).
  - **Status**: ✅ Complete

### 2026-06-29
- **AI voice-input enhancement / dictation cleanup (#56, P2.6)**: built by **mirroring the #57 enhance-text pattern** end to end (no new deps, no transcription-router changes)
  - **Backend**: `app/services/transcription_enhancement.py` (single `TRANSCRIPTION_CLEANUP_GUIDANCE` + `get_transcription_enhancement_prompt(content)` — fact-preserving). `ai_service.enhance_transcription(content)` (temp **0.3**, conservative; rejects length-truncated output so a long dictation can't be silently shortened; structured `{success, enhanced, metadata}`). New `POST /books/{id}/chapters/{cid}/enhance-transcription` (session auth, ownership 403, **chapter-existence 404**, 10/h rate limit, 400 empty-content, 503 on AI failure). **Preview-only, no persistence.**
  - **Single "cleanup" mode** (one pass: filler removal + paragraph breaks at natural pauses + grammar/punctuation) rather than the Traycer plan's 3 boolean toggles — the AC lists all three as expected *outcomes*, not user options; "toggle raw vs enhanced" = the side-by-side preview + revert.
  - **Frontend**: `VoiceEnhancer.tsx` dialog (intro→enhancing→preview; DOMPurify-sanitized raw-vs-cleaned side-by-side; mirrors `ContentEnhancer`); `bookClient.enhanceVoiceTranscription()`. `ChapterEditor` toolbar **Clean up dictation** button — **reuses** the existing `getEnhanceContent` + `handleApplyEnhancement` + **"Revert enhancement"** snapshot/revert (no new editor state).
  - **Tests**: backend `test_transcription_enhancement` + `test_ai_service_transcription` + `test_transcription_enhancement_endpoint` (success/400/404-book/404-chapter/403/503); frontend `VoiceEnhancer.test.tsx`; route-mocked E2E `voice-enhancement.spec.ts` (raw dictation→clean up→preview→apply→revert). Backend **957 passed, 92.36% cov** (`transcription_enhancement.py` 100%); frontend **1878 passed**, gates green (85/85/75/85).
  - **NB**: the unmounted `/transcribe` router and the Traycer plan's references to the deleted `chapter_error_handler`/`chapter_cache_service` (gone in #120) are intentionally untouched. E2E route-mocks the endpoint — browser SpeechRecognition is native/non-deterministic and unavailable headless (webkit/Mobile-Safari editor-load fails pre-existingly in this env; same as the #57 spec).
  - **Status**: ✅ Complete

### 2026-06-28
- **EPUB export format (#60, P2.3)**: PR #147 — third export format alongside PDF/DOCX
  - **Backend**: `ExportService.generate_epub()` via `ebooklib==0.20` (async worker thread, same pattern as PDF/DOCX). Title page + per-chapter `EpubHtml`, `EpubNcx` (EPUB2 nav) **and** `EpubNav` (EPUB3 nav) for max ereader compat, ordered spine. Reuses the shared HTML→formatted-text pipeline (`_extract_text_formatting`) so chapter content renders as **well-formed XHTML** — raw TipTap HTML isn't always XML-valid and would break ereaders/lxml. **Gotcha fixed**: no `<?xml … encoding …?>` prolog on `EpubHtml.content` — ebooklib parses it as a `str` during nav generation and lxml rejects a unicode string carrying an encoding decl (silently empties the body → `ParserError: Document is empty`). ebooklib writes its own prolog.
  - `export_book()` gains `'epub'` dispatch (no page_size/template — EPUB is reflowable); guarded import → `EPUB_AVAILABLE`. New `GET /books/{id}/export/epub` endpoint (auth, ownership, `log_access("export_epub")`, 10/h rate limit, 503 when ebooklib missing). EPUB listed in `/export/formats`.
  - **Frontend**: `ExportFormat` union gains `'epub'`; EPUB radio option in `ExportOptionsModal` (page-size stays PDF-only); `bookClient.exportEPUB()`; `handleExport` routing. `generateFilename` already keys off `format` → `.epub` automatic. `TemplateSelector.format` prop widened to `ExportFormat`.
  - **Tests**: backend service (valid EPUB zip: `mimetype` first+STORED, nav+ncx+chapter XHTML, chapter text survives), `export_book('epub')`, availability guard; endpoint happy/404/403 + `/formats` lists epub; frontend modal option + `bookClient.exportEPUB` URL. Backend suite **923 passed, 92.32% cov** (export_service 95%); frontend gates green.
  - **Known limits**: flat TOC (each chapter top-level — navigable; nest by `level` later); no ISBN (book model has no field); device testing (Kindle/Kobo/Apple Books) is manual, covered here by spec-conformant structure assertions.
  - **Status**: ✅ Complete

- **AI content enhancement for existing chapter text (#57, P2.5)**: PR #149 — built by **mirroring the #58 style-transformation pattern** end to end (no new deps, no diff library, no floating-selection UI)
  - **Backend**: `app/services/content_enhancement.py` (4 fact-preserving dimensions — clarity/grammar/tone/vocabulary — `ENHANCEMENT_LABELS`/`ENHANCEMENT_GUIDANCE`/`is_valid_enhancement`/`get_enhancement_prompt`, mirrors `style_templates.py`). `ai_service.enhance_text(content, enhancement_type)` (temp **0.3** — conservative vs style's 0.7; rejects length-truncated output so a too-long chapter can't be silently shortened; structured `{success, enhanced, metadata}`). New `POST /books/{id}/chapters/{cid}/enhance-text` (session auth, ownership 403, **chapter-existence 404**, 10/h rate limit, 400 validation, 503 on AI failure). **Preview-only, no persistence.**
  - **Frontend**: `ContentEnhancer.tsx` dialog (options→enhancing→preview; DOMPurify-sanitized side-by-side before/after; mirrors `StyleTransformer`); `bookClient.enhanceChapterText()`. `ChapterEditor` toolbar **Enhance** button — enhances the **current selection if any, else the whole chapter** (captures the range so apply replaces exactly that), snapshot + **"Revert enhancement"** single-level undo.
  - **Tests**: backend `test_content_enhancement` + `test_ai_service_enhancement` + `test_enhancement_endpoint` (all 4 types, 400/404-book/404-chapter/403/503); frontend `ContentEnhancer.test.tsx`; route-mocked E2E `content-enhancement.spec.ts` (open→pick→preview→apply→revert). Backend **943 passed, 92.4% cov** (`content_enhancement.py` 100%); frontend gates green.
  - **NB**: `#41` ("robust AI error handling") listed as a blocker was already satisfied — the structured AI-failure→503 path exists. The mirrored `transform-style` endpoint still lacks the chapter-existence check (not retrofitted here). codex pre-PR review caught the missing chapter check; fixed before opening the PR.
  - **Status**: ✅ Complete

### 2026-06-27
- **Restore pre-commit/CI gate enforcement — stop merging with `--no-verify`/`--admin` (#118, capstone)**: process/enforcement, no app behavior change
  - **Gates verified green at baseline**: backend coverage **92.4%** (`pytest --cov=app --cov-fail-under=85`, 888 passed/15 skipped); frontend coverage clears **85/85/75/85** (1856 passed/8 skipped, 90 suites). `pre-commit run --all-files` passes with no bypass. All four blocking coverage issues (#68, #93, #116, #117) closed; no coverage gate remains red.
  - **CI now actually enforces coverage**: removed `continue-on-error: true` from both "Check coverage threshold" steps in `.github/workflows/tests.yml` (the old "don't fail CI until we reach 85%" escape) — a coverage regression now fails `Frontend Tests` / `Backend Tests`.
  - **Branch protection on `main`** (was unprotected): required status checks (strict/up-to-date) = `Frontend Tests` + `Backend Tests`; merges route through a PR. `--admin` override stays for true emergencies but is no longer the norm. (E2E intentionally out of scope per the issue.)
  - **Docs**: neutralized the stale `--no-verify`/"baseline gates red" boilerplate in this file; the Pre-Commit section now states gates are green and enforced. (No PR template file exists, so nothing to scrub there.)
  - **Demonstrated**: this issue's own PR merged through required checks **without** `--admin`.
  - **Status**: ✅ Complete

### 2026-06-26
- **Test coverage for books.py endpoints 41% → 89% + 6 real bug fixes (#121)**: PR #138 (reliability-labeled)
  - **244 new integration tests** across 7 files in `tests/test_api/test_routes/` (one per endpoint group: book CRUD/summary, pre-TOC AI, TOC, chapter CRUD, chapter content/tab-state, chapter questions, draft/style). Each endpoint covers happy-path + 404 + 403 (wrong owner) + validation/AI-error branches. Real local MongoDB + mocked session auth (`auth_client_factory`); AI endpoints patch `ai_service`. Full backend suite green: **714 passed, 17 skipped**.
  - **Real production bugs found while testing and fixed** (tests now assert correct behavior, not the bugs):
    1. `create_chapter` passed `add_chapter_with_transaction(parent_id=…)` but the param is `parent_chapter_id` → every chapter create 500'd.
    2. `update_chapter` passed `update_chapter_with_transaction(updates=…)` but the param is `chapter_updates` → every chapter update 500'd.
    3. `get_chapter_analytics` passed `user_id=`/`chapter_id=` kwargs the service rejects → always 500. Now `get_chapter_analytics(book_id, days)`.
    4. `batch-content` with `include_metadata` `await`ed the **sync** `calculate_reading_time` and passed content text instead of a word count → crash.
    5. `GET /chapters/metadata` and `GET /chapters/tab-state` were registered **after** `/chapters/{chapter_id}` → permanently route-shadowed (404). Moved both before the parameterized route.
    6. Offensive-summary filter regex used `"\\b"` (literal backslash-b) not `"\b"` → never matched real input.
  - **Test infra (`conftest.py`)**: test DB name now env-overridable via `TEST_MONGO_URI` (default unchanged, enables parallel/sharded runs); `motor_reinit_db` now rebinds `app.db.toc_transactions` to the per-test client (it captured `_client`/`books_collection` at import), so transactional chapter endpoints run for real instead of against a closed loop.
  - **NB (historical)**: this PR predated the coverage work and was committed with `--no-verify` while overall backend coverage was still <85%. As of #118 the backend gate is green (92%) and enforcement is restored — `--no-verify`/`--admin` are no longer used as the norm. Coordinates with #94 (covers the monolith as-is; tests grouped by area to move cleanly when split).
  - **Status**: ✅ Complete

### 2026-06-26
- **Remove dead service code + omit seed script from coverage (#120)**: backend cleanup, no behavior change
  - **Deleted 9 dead service modules (4,983 LOC)**: `content_analysis_service`, `historical_data_service`, `question_feedback_service`, `chapter_error_handler`, `chapter_cache_service`, `user_level_adaptation`, `question_quality_service`, `genre_question_templates`, `chapter_soft_delete_service`. Each verified unreferenced in `app/` (no importers, no `services/__init__.py` re-exports, no dynamic/class-name refs). `chapter_error_handler` ↔ `chapter_cache_service` were mutually-dead (only imported each other).
  - **Deleted 5 ghost validation scripts** that referenced the chapter cache/error modules and were run by nothing (pytest collected 0 tests; not in CI): `tests/test_chapter_tabs_api.py`, `archived_tests/test_chapter_tabs_api.py`, root `validate_chapter_tabs.py` / `quick_validate.py` / `simple_validate.py`.
  - **Coverage**: added `*/populate_db_test_data.py` (seed script) to `.coveragerc` omit. Backend coverage **~50% → 71%** with zero new tests (the dead modules were the drag). Suite green: **466 passed, 17 skipped**.
  - **Docs**: scrubbed deleted-module refs from `docs/ai-caching-and-error-handling.md` (tree + links); added a removal note to `docs/developer-guide-question-system.md` (4 of its documented modules were dead). Historical analysis snapshots (`docs/analysis/*`, `TEST_COVERAGE_REPORT.md`) left as-is — they identify this dead code.
  - **Status**: ✅ Complete

### 2026-06-26
- **Harden full staging E2E journey + wire chapter Q&A (#105)**: PRs #134 + #135
  - **Root finding**: the #54 interview-questions Q&A loop (`QuestionContainer`, with real `PUT .../questions/{id}/response` persistence) existed but was **never mounted** in any navigable route — only a hardcoded-mock `/chapters` page used it. So #54 was untestable. `ChapterEditor` now has a **Write / Interview Questions** tab toggle that mounts `QuestionContainer`, making generate→answer→persist real. +3 unit tests.
  - **Real backend bugs fixed (both blocked the live wizard)**:
    1. `generate-toc` only read the *persisted* `book.question_responses`, but the `ClarifyingQuestions` wizard sends responses in the request **body** and never persists them → every wizard TOC generation 400'd "Question responses are required". Now reads body first, falls back to persisted. +1 test.
    2. `analyze-summary` **persisted failed AI analyses**, which permanently poisoned readiness (`has_analysis=true`, `meets_minimum=false`) and blocked TOC forever after one transient error. Now returns a retryable 503 and doesn't persist, so readiness falls back to the deterministic word/char check. +1 test.
    3. OpenAI key: service only read `OPENAI_AUTOAUTHOR_API_KEY`; staging's was stale/invalid. Now reads canonical `OPENAI_API_KEY` (legacy fallback); deploy writes it. +2 tests. **NB: the running staging key only refreshes on redeploy.**
  - **Test hardening**: new shared `tests/e2e/staging/fixtures/journey.helpers.ts` (real selectors + network waits + a `READY_SUMMARY` the AI judges ready); `complete-user-journey.spec.ts` and the #54 regression **un-`fixme`'d**; removed **every** `page.waitForTimeout()` and silent `if(isVisible)` skip (CLAUDE.md forbidden). Fixes all four issue items: delayed book-create nav, summary fill-race (re-fill-until-submit-enables), the auto-running TOC wizard, and the forbidden patterns.
  - **Verify**: full staging suite **4/4 pass, 3 consecutive runs** (12/12) against live `dev.autoauthor.app` with real Better-auth + real AI — meets the issue's >95% bar.
  - **Status**: ✅ Complete

### 2026-06-26
- **Nova migration residual cleanup (#65)**: finished the lucide→hugeicons + zinc→gray drift left after PR #73
  - **Context**: PR #73 (Dec 24) already did the bulk nova migration (style/baseColor/iconLibrary in `components.json`, Nunito Sans). #65 stayed open because the literal AC ("no lucide-react imports", "no zinc colors") weren't fully met.
  - **Icons**: converted the remaining 14 source files off `lucide-react` to `<HugeiconsIcon icon={…}/>` from `@hugeicons/core-free-icons` — 6 feature files (auth sign-in/up, reset/forgot-password, `PasswordRequirements`, `SessionWarning`) + 8 stock shadcn `ui/*` primitives (dialog, select, checkbox, dropdown-menu, sheet, radio-group, breadcrumb, sonner). Removed `lucide-react` from `package.json`/lockfile and two dead `jest.mock('lucide-react')` blocks. **Zero lucide refs remain.**
  - **Colors**: `zinc-* → gray-*` across 20 files (mechanical className swap). **Zero zinc refs remain.**
  - **Cleanup**: removed the now-obsolete `frontend/backup-pre-nova/` migration-backup dir (git preserves history).
  - **Verify**: typecheck clean, lint 0 errors, prod build green (compiles every converted route), 89/89 suites + 1853 tests pass, coverage stmt 92 / lines 93 / func 90 / branch 83.
  - **Status**: ✅ Complete

### 2026-06-25
- **Flaky test fix + frontend coverage to 85% (#68)**: tests-mostly
  - **Flaky `TabStatePersistence`**: the "saves tab state…" case raced the 1s debounced auto-save under real timers. Now uses `jest.useFakeTimers()` + `advanceTimersByTime(1000)` and an `afterEach(jest.useRealTimers())` so it's deterministic and can't leak timer state into the full run.
  - **Coverage**: global was stmt 74 / lines 75 / func 67 / branch 62 → now **stmt 92 / lines 93 / func 90 / branch 83**, clearing the pre-commit gate (85/85/75) without `--no-verify`. ~700 unit tests added across `lib/errors/*`, `lib/api/bookClient.ts`, `lib/security.ts`, `lib/performance/*`, `lib/loading/timeEstimator.ts`, `lib/utils/toc-to-tabs-converter.ts`, `lib/toast.ts`, hooks (`useTocSync`, `usePerformanceTracking`), and components (`ErrorNotification`, `QuestionDisplay/Container/Navigation/Generator`, `ClarifyingQuestions`, `ChapterTabs`/`MobileChapterTabs`/`TabBar`/`TabContextMenu`/`TabOverflowMenu`, `ui/dropdown-menu`, `ui/sheet`).
  - **Real bugs fixed while testing**: `sanitizeFileName` regex `[^a-zA-Z0-9.-_]` was a char *range* (46–95) so `/ : \ @` slipped through while `-` was stripped — hyphen now escaped (path-traversal hardening); `showRecoveryNotification` printed "2 attempt" (singular) — fixed to plural; removed a dead empty `useEffect`/`getToken` + orphaned `useSession` in `ClarifyingQuestions.tsx`.
  - **Status**: ✅ Complete

- **Transcription test coverage + dead-code removal (#93)**: tests-only plan 009
  - **transcription.py**: 40% → 85% via new `backend/tests/test_api/test_transcription.py` (POST /transcribe auth/413/400/happy/service-error; GET /status; POST /validate). Router isn't mounted on the app, so tests mount it on a bare FastAPI app + override auth; transcription service patched (no AWS/audio)
  - **Drift**: `app/api/endpoints/book_cover_upload.py` was dead code (never imported) — an unmounted duplicate of the live cover endpoint in `books.py`. Removed it (same pattern as #92's `book_cascade_delete.py`); added a wrong-owner (404) case to the existing `test_book_cover_upload.py` which already exercises the live `books.py` path
  - **Status**: ✅ Complete (PR #131)

- **Writing style transformation (#58)**: New feature — rewrite existing chapter text into a chosen style (distinct from draft-from-Q&A)
  - **Backend**: `app/services/style_templates.py` (5 documented styles with distinct tone/vocab/structure guidance + `get_style_transformation_prompt`); `ai_service.transform_text_style(content, target_style)` (temp 0.7, preserves facts); new endpoint `POST /books/{id}/chapters/{cid}/transform-style` (auth + ownership + rate limit, **preview-only, no persistence**)
  - **Frontend**: `StyleTransformer.tsx` dialog (pick style → before/after preview → apply); wired into `ChapterEditor` toolbar with a **client-side snapshot revert** ("Revert style" button) — single-level undo, no backend version storage; `bookClient.transformChapterStyle`
  - **Tests**: backend `test_style_templates` + `test_ai_service_style_transformation` + `test_style_transformation` (15 tests: distinct prompts per style, validation, auth, AI-failure→503); frontend `StyleTransformer.test.tsx`; deterministic route-mocked E2E `frontend/src/e2e/style-transformation.spec.ts` (transform → preview → apply → revert)
  - **Note**: the stale deployment spec `tests/e2e/deployment/06-draft-writing-styles.spec.ts` still references the old 6 draft styles (real-auth suite) — not rewritten here
  - **Status**: ✅ Complete

- **AI Draft Generation alignment (#55)**: Feature was already ~95% built; closed the real gaps the stale issue/bot plans missed
  - **Writing styles**: both `DraftGenerator.tsx` and `DraftGenerationButton.tsx` now ship the 5 documented styles (Professional, Conversational, Academic, Creative, Technical) matching the user manual + AC, replacing the prior mismatched 6. Backend is style-agnostic (free-text into the prompt) → no backend change
  - **Bug fix**: `DraftGenerator.tsx` loading state was unreachable (ternary checked `!generatedDraft` before `isGenerating`, so the form always rendered during generation); reordered so the loading view shows. `DraftGenerationButton.tsx` already had a correct step machine
  - **A11y**: associated the style/length selects and the per-question input with labels in `DraftGenerator.tsx`
  - **Tests**: added a regression test asserting the loading state renders during generation; new deterministic route-mocked E2E `frontend/src/e2e/draft-generation.spec.ts` (open → pick style → generate → preview → insert into editor)
  - **Status**: ✅ Complete

### 2026-06-24
- **Error/Success Feedback Unification (#46)**: Closed user-facing feedback gaps and standardized the notification path
  - **Duplicate Toaster**: `layout.tsx` mounted two sonner Toasters → duplicate toasts; removed the redundant one, kept theme-aware `SonnerToaster`
  - **new-book silent failure**: create errors only `console.error`'d; now classified and shown via `showErrorNotification` with a retry action, plus a success toast on create
  - **ChapterTabs retry**: load-error "Retry" did a full `window.location.reload()`; now calls `refreshChapters()` (data refresh, no page reload)
  - **Standardization**: all toasts route through the single `@/lib/toast` wrapper (added a `variant` compat shim); migrated 5 direct-`sonner` + 6 `useToast` call sites by import swap
  - **Tests**: `NewBookPage.test.tsx` (success toast + redirect / error notification + no redirect), `ChapterTabs.test.tsx` (retry refreshes, no reload); migration mocks updated
  - **Status**: ✅ Complete (PR #115)

### 2026-06-22
- **TOC Generation Hardening (#48)**: Closed reliability gaps in the AI TOC flow
  - **analyze-summary endpoint**: now uses the same structured AI-error handling as generate-questions/generate-toc (timeouts → 503 with retry info, instead of an opaque 500)
  - **Frontend**: `bookClient` AI methods surface the backend's `detail.message`, and `TocGenerationWizard` shows it (meaningful error text + existing retry button) rather than a generic string
  - **Malformed AI responses**: `ai_service._parse_toc_response` now rejects unusable output (empty/title-less chapters, unparseable text) with a retryable `AI_INVALID_RESPONSE` error instead of silently fabricating a generic placeholder TOC; it also unwraps the common `table_of_contents` JSON wrapper so valid-but-wrapped responses parse correctly
  - **Tests**: backend integration tests for AI timeouts/invalid responses across all 3 TOC endpoints; `bookClient` error-surfacing unit tests; deterministic route-mocked E2E (`frontend/src/e2e/toc-generation-resilience.spec.ts`) for the error→retry recovery path
  - **Status**: ✅ Complete

### 2025-12-24
- **Cookie-Based Authentication Reconciliation**: Aligned backend auth with better-auth's cookie-based session management
  - **Problem**: Backend expected JWT tokens in Authorization headers, but better-auth uses httpOnly session cookies
  - **Solution**: Created new session validation module to read and validate better-auth session cookies
  - **Changes**:
    - New module: `backend/app/core/better_auth_session.py` for session cookie validation
    - New dependency: `get_current_user_from_session()` replaces JWT-based authentication
    - New role checker: `SessionRoleChecker` for cookie-based authorization
    - Updated all 25+ protected endpoints to use session-based auth
    - Frontend: Removed Bearer token logic, uses `credentials: 'include'` for cookies
  - **Files Modified**:
    - `backend/app/core/security.py` - Added session-based auth functions
    - `backend/app/core/better_auth_session.py` - New session validator
    - `backend/app/api/endpoints/*.py` - Updated all endpoints
    - `frontend/src/hooks/useAuthFetch.ts` - Cookie-based fetch
    - `frontend/src/lib/api/bookClient.ts` - Deprecated token methods
  - **Test Updates**: All test fixtures updated to mock session-based auth
  - **Documentation**: Updated migration guide with cookie-based auth section
  - **Status**: ✅ Complete - Backend now validates session cookies from better-auth

### 2025-12-17
- **Better-Auth Migration**: Complete migration from Clerk to better-auth authentication
  - **Scope**: 70+ files across frontend (Next.js) and backend (FastAPI)
  - **Changes**:
    - JWT algorithm: RS256 (Clerk) → HS256 (better-auth)
    - User ID field: `clerk_id` → `auth_id`
    - Frontend: Removed `@clerk/nextjs`, added `better-auth` with MongoDB adapter
    - Backend: Removed Clerk JWKS verification, added HS256 JWT validation
    - Environment: Simplified to `BETTER_AUTH_SECRET` and `BETTER_AUTH_URL`
  - **Security Fixes**:
    - **BLOCKER**: Removed hardcoded JWT secret, added strong validation (min 32 chars)
    - **HIGH**: Changed `NEXT_PUBLIC_BYPASS_AUTH` to server-only `BYPASS_AUTH` with production safety check
    - **HIGH**: Disabled auto-user creation from JWT - require explicit registration
  - **Test Results**: 231/251 backend tests passing (92%), all security tests updated for better-auth
  - **Cleanup**: Removed Clerk documentation, test files, and CSP headers
  - **Status**: ✅ Migration complete with all security vulnerabilities fixed

### 2025-11-22
- **Auto-Create Users from Clerk on First Login**: Enhanced authentication to automatically create user records
  - **Problem**: Users authenticating via Clerk weren't being created in backend database
  - **Solution**: Modified `security.py` to auto-create users from Clerk JWT on first login
  - **Changes**: Enhanced `get_current_user()` to create missing users, added comprehensive logging
  - **Impact**: Seamless user onboarding without manual database setup
  - **Status**: ✅ Deployed to staging - authentication now fully automated

- **Staging Deployment Workflow**: GitHub Actions workflow for automated staging deployments
  - **Achievement**: Complete CI/CD pipeline for staging environment
  - **Infrastructure**: SSH deployment, PM2 process management, health checks with retries
  - **Configuration**: Backend on port 8000, frontend on port 3003, CORS validation
  - **Process**: Uses `pm2 delete` + `pm2 start` instead of restart for clean release pickup
  - **Status**: ✅ Operational at https://dev.autoauthor.app (frontend) and https://api.dev.autoauthor.app (backend)

- **Public Access to Landing Page**: Fixed middleware to allow unauthenticated access to root
  - **Problem**: Root landing page was requiring authentication
  - **Solution**: Updated middleware.ts to explicitly allow public access to `/`
  - **Impact**: Marketing/landing page now accessible without login
  - **Status**: ✅ Deployed to staging

### 2025-11-07
- **E2E Test Suite Complete**: Comprehensive automated testing with 85%+ coverage
  - **Achievement**: Created comprehensive deployment test suite (01-05) with 54+ tests
  - **Infrastructure**: Fixtures (auth, test-data, performance), Helpers (console/network/CSP monitors), Page Objects (7 pages)
  - **Coverage**: Pre-flight (7 tests), User Journey (8 tests), Advanced Features (8 tests), Security/Performance (12 tests), Regression (19+ tests)
  - **Performance Budgets**: All operations validated (TOC <3000ms, Export <5000ms, Auto-save <1000ms, Page Nav <500ms)
  - **Status**: ✅ auto-author-59 completed - 85%+ automation coverage achieved, ready for CI/CD

- **MongoDB Atlas SSL Connection Fix**: Resolved test database connection issues
  - **Problem**: 13 tests failing with SSL handshake errors connecting to MongoDB Atlas
  - **Solution**: Updated test infrastructure to use local MongoDB for all tests
  - **Changes**: Added sessions_collection to conftest fixture, updated session.py to use base.sessions_collection
  - **Impact**: 9/15 session service tests now passing (was 3/15), all SSL errors eliminated
  - **Status**: ✅ auto-author-70 completed - tests now use local MongoDB correctly

- **Frontend Test Suite Status**: All environmental test issues resolved
  - **Test Results**: 732/735 tests passing (99.6% pass rate, 3 skipped)
  - **Test Suites**: 51/51 passing (100%)
  - **Resolution**: Mocks already in place (Next.js router, ResizeObserver, TipTap, Clerk)
  - **Excluded Tests**: ProfilePage.test.tsx, SystemIntegration.test.tsx (awaiting feature implementation) — ⚠️ historical: ProfilePage un-ignored in #63; SystemIntegration deleted as unrunnable in #200 (2026-07-13)
  - **errorHandler.test.ts**: All 43 tests passing with Jest
  - **Status**: ✅ auto-author-60 completed - no fixes needed, infrastructure working correctly

### 2025-11-06
- **TOC JWT Bug Fix**: Fixed JWT token expiration during long TOC workflows (11+ seconds) by implementing token provider pattern in BookClient
- **E2E Tests Enabled**: Complete authoring journey E2E test now active in `frontend/src/e2e/complete-authoring-journey.spec.ts`
- **TDD Enforcement**: Pre-commit hooks now enforce unit tests, E2E tests, and ≥85% coverage for all commits
- **GitHub Actions**: Implemented automated test workflow for frontend, backend, and E2E tests
- **Documentation Automation**: Pre-commit hooks auto-sync CURRENT_SPRINT.md and IMPLEMENTATION_PLAN.md from bd tracker (local only - .beads/ is gitignored)

### 2025-11-01
- **Session Management (NEW)** — ⚠️ removed as dead code in #196 (2026-07-12): the middleware gated on `request.state.user`, which nothing ever set, so none of the below ever functioned; session list/revoke is better-auth native
- **Session Tracking**: Automatic session creation and activity monitoring
- **Security Features**: Session fingerprinting, suspicious activity detection, concurrent session limits
- **Session Timeouts**: 30-minute idle timeout, 12-hour absolute timeout
- **Frontend Integration**: `useSession` hook with auto-refresh and warning notifications
- **API Endpoints**: Complete session management API (`/api/v1/sessions/*`)
- **Comprehensive Tests**: 85%+ test coverage for session management

### Security & Authentication (2025-10-29)
- **JWT Verification Fix**: Switched from hardcoded public key to Clerk JWKS endpoint (`https://clerk.{domain}/.well-known/jwks.json`)
- **Auth Bypass Mode**: Added `BYPASS_AUTH=true` environment variable for E2E testing
- **Security Audit**: Comprehensive authentication middleware review completed

### Testing Infrastructure
- **E2E Test Suite**: Complete Playwright tests with auth bypass support
- **Test Data Helpers**: Comprehensive fixtures for books, chapters, and TOC data
- **Condition-based Waiting**: Replaced arbitrary timeouts with state polling
- **Page Objects**: Full coverage (auth, dashboard, books, summary, TOC wizard, chapter editor, export)

### Test Analysis Reports
- `docs/POST_DEPLOYMENT_TEST_REPORT.md`: Comprehensive test status after staging deployment
  - Frontend: 99.6% pass rate (732/735 tests passing, 3 skipped)
  - Backend: 98.9% pass rate (2 asyncio failures), 41% coverage vs 85% target
- `backend/TEST_COVERAGE_REPORT.md`: Module-by-module coverage analysis with 4-week improvement plan
- `frontend/docs/TEST_FAILURE_ANALYSIS.md`: Categorized frontend failures with fix priorities

### Known Issues
- **Backend Coverage**: ✅ resolved — now **~92%** (≥85% gate enforced as of #118; was 41%). Historical gaps (`security.py`, `transcription.py`, `book_cover_upload.py` duplicate) closed via #93/#116/#117.
- **Backend Asyncio**: 2 test failures related to event loop lifecycle
- **Backend Module Structure**: Missing `__init__.py` in `app/api/middleware/` causing import errors

### Package Updates
- Upgraded `lucide-react` to 0.468.0
- Resolved 5 npm audit vulnerabilities
- Updated `.gitignore` to exclude test artifacts

---

## Project Structure
- `frontend/` - Next.js application
- `backend/` - FastAPI Python application
- `docs/` - Project documentation
  - `POST_DEPLOYMENT_TEST_REPORT.md` - Comprehensive test analysis
  - `references/` - On-demand reference documentation (read when needed)
- `backend/TEST_COVERAGE_REPORT.md` - Backend coverage details
- `frontend/docs/TEST_FAILURE_ANALYSIS.md` - Frontend test categorization
- `claudedocs/` - Claude-specific analysis reports and detailed plans
- `archive/` - Historical planning documents (read-only)

---

## 📚 On-Demand Reference Documentation

For detailed information on specific topics, **read these files when needed** using the Read tool:

### Task Management
**File**: `docs/references/beads-workflow.md`
**When to read**: Before creating tasks, checking task status, or planning work
**Summary**: bd (Beads) is the single source of truth for all task tracking. Contains workflow patterns, commands, and integration guidelines.

### Documentation Standards
**File**: `docs/references/documentation-management.md`
**When to read**: Before creating new documentation, updating docs, or organizing files
**Summary**: Document hierarchy, decision trees, lifecycle management, and quality standards for all project documentation.

### Component Usage Patterns
**File**: `docs/references/component-documentation.md`
**When to read**: When using LoadingStateManager, ProgressIndicator, DeleteBookModal, or similar components
**Summary**: Comprehensive usage examples, props, integration patterns, and test coverage for reusable components.

### Quality Requirements
**File**: `docs/references/quality-standards.md`
**When to read**: Before marking features complete, submitting PRs, or implementing new features
**Summary**: Testing requirements (85% coverage), git workflow, documentation synchronization, and feature completion checklist.

### Performance Guidelines
**File**: `docs/references/performance-monitoring.md`
**When to read**: When implementing performance-sensitive features, tracking operations, or optimizing code
**Summary**: Performance tracking system, budgets (TOC: 3000ms, Export: 5000ms), Core Web Vitals, and integration patterns.

### Testing Practices
**File**: `docs/references/testing-infrastructure.md`
**When to read**: When writing tests, fixing test issues, or implementing TDD workflows
**Summary**: Test helpers (condition-based waiting, test data setup, error handling), E2E test suites, running tests, and known issues.

---

## Project Overview

This project uses SPARC (Specification, Pseudocode, Architecture, Refinement, Completion) methodology with Claude-Flow orchestration for systematic Test-Driven Development.

## Quick Start Commands

### SPARC Commands
- `npx claude-flow sparc modes` - List available modes
- `npx claude-flow sparc run <mode> "<task>"` - Execute specific mode
- `npx claude-flow sparc tdd "<feature>"` - Run complete TDD workflow

### Task Management (bd/Beads)
- `bd ready` - View unblocked tasks ready to start
- `bd list --status open` - View all open tasks
- `bd create "Task" -p 0 -t feature -d "Description"` - Create task
- `bd close <task-id> --reason "Completed"` - Close completed task

### Build & Test
- `npm run build` - Build project
- `npm test` - Run tests
- `npm run test:coverage` - Run tests with coverage
- `npm run lint` - Linting
- `npm run typecheck` - Type checking

### Backend Testing
Test/load tooling is in optional extras (`[project.optional-dependencies]`), so
production installs stay lean. Install the `test` extra once before running:
```bash
cd backend
uv sync --extra test    # one-time: installs pytest, faker, httpx, coverage…
uv run pytest --cov=app tests/ --cov-report=term-missing
```

### E2E Testing
```bash
cd frontend
npx playwright test --ui    # Run with UI mode (recommended)

# With auth bypass (for testing without real auth)
BYPASS_AUTH=true npx playwright test
```

#### Staging E2E (real auth against https://dev.autoauthor.app)
```bash
cd frontend
cp tests/e2e/staging/.env.test.example tests/e2e/staging/.env.test  # set STAGING_TEST_EMAIL / STAGING_TEST_PASSWORD
npm run test:e2e:staging
```
- Specs: `tests/e2e/staging/complete-user-journey.spec.ts` (full journey) and `regressions.spec.ts` (Issue #83 regressions: session/401, ObjectId, #54 answer persistence).
- CI: `.github/workflows/e2e-staging-tests.yml` runs on a 6h schedule, manual dispatch, and PRs labeled `e2e-staging`. Requires GitHub Secrets `TEST_USER_EMAIL` / `TEST_USER_PASSWORD` (the fixture also accepts `STAGING_TEST_EMAIL` / `STAGING_TEST_PASSWORD` locally).
- See `tests/e2e/staging/README.md` for details.

---

## Key Features

### ✅ Production Ready
- User authentication (better-auth with HS256 JWT verification; session list/revoke via better-auth native APIs in Settings → Security)
- Book CRUD operations with metadata
- **Book Deletion UI** (Type-to-confirm with data loss warnings)
- TOC generation with AI wizard
- Chapter tabs interface (vertical layout with keyboard shortcuts)
- **Rich Text Editor** (TipTap with full formatting)
- **AI Draft Generation** (Q&A to narrative with multiple styles)
- **Auto-save System** (3s debounce + localStorage backup on network failure)
- **Keyboard Accessibility** (WCAG 2.1 compliant)
- **Voice Input Integration** (Browser Speech API)
- **Export functionality** (PDF/DOCX with customizable options)
- **Performance Monitoring** (Core Web Vitals + operation budgets)
- **Unified Error Handling** (automatic retry with exponential backoff)

### 🚧 In Progress
See `CURRENT_SPRINT.md` for active tasks or run `bd ready` for unblocked work.

### 🔧 Test Infrastructure Status
- **Frontend**: 88.7% pass rate (613/691 tests passing)
  - 75 failures are environmental (missing mocks, not code bugs)
  - Fix plan: 3.5-5.5 hours across 4 phases
- **Backend**: 888 passed / 15 skipped; **~92% coverage** (≥85% gate enforced as of #118)
- **E2E**: Comprehensive Playwright suite with auth bypass support

---

## Code Style & Best Practices

- **Modular Design**: Files under 500 lines
- **Environment Safety**: Never hardcode secrets
- **Test-First**: Write tests before implementation (TDD)
- **Clean Architecture**: Separate concerns
- **Documentation**: Keep synchronized with code

---

## 🔒 MANDATORY: TDD & E2E Test Enforcement

**CRITICAL**: This project REQUIRES Test-Driven Development and E2E test coverage for ALL features. No feature is complete without proper test coverage.

### Pre-Commit Hook Requirements

**ALL commits MUST pass these gates:**

1. **Unit Tests**: All unit tests must pass
   ```bash
   # Frontend
   cd frontend && npm test

   # Backend
   cd backend && uv run pytest tests/
   ```

2. **E2E Tests**: All E2E tests must pass
   ```bash
   # Basic E2E tests
   cd frontend && npx playwright test

   # Deployment test suite (comprehensive)
   cd frontend && npx playwright test --config=tests/e2e/deployment/playwright.config.ts
   ```

3. **Test Coverage**: Minimum 85% coverage required
   ```bash
   # Frontend
   cd frontend && npm test -- --coverage --coverageThreshold='{"global":{"lines":85}}'

   # Backend
   cd backend && uv run pytest --cov=app tests/ --cov-fail-under=85
   ```

4. **Linting & Type Checking**: No errors allowed
   ```bash
   cd frontend && npm run lint && npm run typecheck
   cd backend && uv run mypy app/
   ```

### Feature Branch Workflow (MANDATORY)

**NEVER commit directly to `main` or `develop`. Always use feature branches:**

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit (pre-commit hooks will run automatically)
git add .
git commit -m "feat: implement your feature"

# Push to remote
git push -u origin feature/your-feature-name

# Create Pull Request for review
# PR must have:
# - All tests passing
# - ≥85% test coverage
# - E2E test for user-facing features
# - Updated documentation
```

### Feature Completion Checklist (ENFORCED)

**A feature is NOT complete until ALL of these are done:**

- [ ] **Unit tests written** (≥85% coverage for new code)
- [ ] **E2E test created** (for user-facing features)
- [ ] **All tests passing** (unit + E2E)
- [ ] **Documentation updated** (CLAUDE.md, API docs, user guides)
- [ ] **Performance validated** (meets operation budgets)
- [ ] **Accessibility verified** (WCAG 2.1 Level AA minimum)
- [ ] **Code reviewed** (PR approved by team)
- [ ] **bd task closed** (`bd close <task-id> --reason "Completed in PR #123"`)

### E2E Test Coverage Requirements

**EVERY user-facing feature MUST have an E2E test that validates:**

1. **Happy Path**: Complete user journey from start to finish
2. **Error Handling**: How the system handles failures
3. **Performance**: Operation completes within budget
4. **Accessibility**: Keyboard navigation works
5. **Data Integrity**: Data persists correctly

**Example - TOC Generation Feature:**
```typescript
// frontend/tests/e2e/toc-generation.spec.ts
test('user can generate TOC from book summary', async ({ page }) => {
  // 1. Create book with summary
  // 2. Navigate to TOC wizard
  // 3. Answer clarifying questions
  // 4. Verify TOC generates within 3000ms budget
  // 5. Verify TOC data saves to database
  // 6. Verify TOC appears in book view
});
```

### Pre-Commit Hook Setup

**✅ PRE-COMMIT HOOKS ARE CONFIGURED AND ENFORCED**

**Gates are green at baseline and enforced (#118).** Backend coverage is ~92% and frontend coverage clears 85/85/75/85, so `pre-commit run --all-files` passes cleanly. Commit and merge **without** `--no-verify` / `gh pr merge --admin` — `main` branch protection requires the `Frontend Tests` and `Backend Tests` checks (coverage included) to pass before merge. The `--no-verify` escape hatch below is for genuine emergencies only, not routine use.

This project uses automated pre-commit hooks that run before every commit. These hooks enforce TDD and quality standards.

**Install pre-commit hooks (one-time setup):**

```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Install the git hook scripts
cd /home/frankbria/projects/auto-author
pre-commit install

# Test the hooks
pre-commit run --all-files
```

**What runs on every commit:**

1. **Documentation Auto-Sync** (always runs)
   - Exports current sprint from bd tracker
   - Exports implementation plan from bd tracker
   - Auto-adds updated docs to commit

2. **Frontend Quality Gates** (runs when frontend/ files change)
   - Linting (`npm run lint`)
   - Type checking (`npm run typecheck`)
   - Unit tests (`npm test`)
   - Coverage check (≥85% required)
   - E2E tests (Playwright)

3. **Backend Quality Gates** (runs when backend/ files change)
   - Linting (`ruff check`)
   - Unit tests (`pytest tests/`)
   - Coverage check (≥85% required)

4. **General Code Quality** (always runs)
   - Trailing whitespace removal
   - End-of-file fixing
   - YAML/JSON validation
   - Merge conflict detection
   - Large file detection (>1MB blocked)
   - Private key detection

**Configuration:** See `.pre-commit-config.yaml` in project root for full details.

**Bypassing hooks (emergency only):**
```bash
git commit --no-verify -m "hotfix: emergency fix"
# Then immediately create follow-up task:
bd create "Add tests for emergency hotfix" -p 0 -t bug
```

### Test Quality Standards

**Tests MUST be:**
- **Isolated**: No dependencies on external services (use mocks)
- **Repeatable**: Same result every time
- **Fast**: Unit tests <1s each, E2E tests <30s each
- **Meaningful**: Test behavior, not implementation
- **Maintainable**: Clear, well-documented test code

**Tests MUST NOT:**
- Use arbitrary timeouts (`await page.waitForTimeout(5000)` ❌)
- Depend on test execution order
- Leave side effects (data, files, processes)
- Test internal implementation details

---

## Deployment Information
- The staging server is located at: https://dev.autoauthor.app (frontend) and https://api.dev.autoauthor.app (backend)
- You can access the staging server with SSH with username root. The keys are local; no password is required.
- There are deployment scripts in the git workflow directories
- **IMPORTANT** there are other aplications on the server. Be aware of port considerations. Right now, the backend uses 8000 and the frontend uses 3002, but be aware that this could change. Check nginx settings for the latest information.
- The applications are managed via PM2 on the server. Since the deployment has a symlinked current release directory, sometimes that needs to be checked if things are out of sync.

---

## 🚀 Available Agents


---

## 🎯 Claude Code vs MCP Tools

### Claude Code Handles ALL:
- File operations (Read, Write, Edit, MultiEdit, Glob, Grep) unless the edits are complex or long
- Code generation and programming
- Bash commands and system operations
- Implementation work
- Project navigation and analysis
- TodoWrite and task management
- Git operations
- Package management
- Testing and debugging

---

## Important Workflow Notes

### Before Starting Work
1. Run `bd ready` to see unblocked tasks
2. Check `CURRENT_SPRINT.md` for sprint context
3. Read relevant reference docs from `docs/references/` as needed

### Before Completing Features
1. Read `docs/references/quality-standards.md` for completion checklist
2. Verify 85% test coverage minimum
3. Run linting and type checking
4. Commit with conventional commit messages
5. Close task in bd: `bd close <task-id> --reason "Completed in PR #123"`

### When Creating Documentation
1. Read `docs/references/documentation-management.md` first
2. Check existing documents before creating new ones
3. Default to updating IMPLEMENTATION_PLAN.md
4. Use bd for tasks: `bd create "Task" -p 1 -t feature`

### When Using Components
1. Read `docs/references/component-documentation.md` for usage patterns
2. Check LoadingStateManager, ProgressIndicator, DeleteBookModal examples
3. Follow accessibility standards (WCAG 2.1 compliant)

---

## Quick Reference: When to Read Reference Docs

| Scenario | Read This File |
|----------|---------------|
| Creating/checking tasks | `docs/references/beads-workflow.md` |
| Creating documentation | `docs/references/documentation-management.md` |
| Using reusable components | `docs/references/component-documentation.md` |
| Completing features | `docs/references/quality-standards.md` |
| Performance optimization | `docs/references/performance-monitoring.md` |
| Writing/fixing tests | `docs/references/testing-infrastructure.md` |
| Understanding test status | `docs/POST_DEPLOYMENT_TEST_REPORT.md` |
| Backend coverage details | `backend/TEST_COVERAGE_REPORT.md` |
| Frontend test failures | `frontend/docs/TEST_FAILURE_ANALYSIS.md` |

---

## Environment Information

**Package Management**:
- Python: uv for environment and package management
- Node.js: npm for frontend dependencies

**Task Tracking**:
- Use bd (Beads) for all task management
- Run `bd quickstart` to learn the system
- Markdown files (CURRENT_SPRINT.md, IMPLEMENTATION_PLAN.md) are auto-generated snapshots

**Documentation Structure**:
- `CLAUDE.md` (this file) - Quick reference and core guidelines
- `docs/references/*.md` - Detailed reference documentation (read on-demand)
- `claudedocs/*.md` - Technical analysis and detailed plans
- `archive/*.md` - Historical planning documents (read-only)

**Environment Variables**:
- `BYPASS_AUTH=true` - Disable authentication for E2E testing (development only)
- Standard Next.js and FastAPI environment variables (see `.env.example`)

---

## API Overview

### Authentication
- **Production**: Better-auth JWT verification using HS256 shared secret
- **Testing**: `BYPASS_AUTH=true` creates mock authenticated context
- **Security**: Never use auth bypass in production environments

### Core Endpoints
- `/api/v1/books` - Book CRUD operations
- `/api/v1/chapters` - Chapter management
- `/api/v1/toc` - Table of Contents generation
- `/api/v1/export` - PDF/DOCX export

See backend API documentation for full endpoint reference.
