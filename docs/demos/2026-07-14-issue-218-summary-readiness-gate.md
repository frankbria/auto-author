# Demo — #218: summary readiness gate (PR #294)

**Date**: 2026-07-14
**Setup**: real backend (uvicorn :8000) + real local Mongo + genuine better-auth signup.
Branch frontend :3000 vs **pristine `main` worktree** :3001 (`/tmp/aa-main-218`), same
backend, same Mongo, same session, same book — so every difference below is the diff.

**Environment notes**
- The shared mongod on :27017 was wedged (process alive, not listening) and :27018 belongs to
  another workload on this box. Neither was touched. This demo runs its own loopback-only
  mongod on **:27099** (`--dbpath /tmp/aa-demo-mongo`), with both the backend and better-auth
  (`DATABASE_URL`) pointed at it.
- The local `OPENAI_API_KEY` is stale (401) — the known local condition. It affects the AI step
  *after* readiness and is present identically on both branches; see the control in AC3.

**Fixtures**
- Real user: `demo218@autoauthor.app` — confirmed in Mongo:
  `{"name":"Demo User 218","email":"demo218@autoauthor.app"}`
- Real book via the real API with the real session cookie: `6a5715a36fc38bb680c317c3`
- Probe summary: `"A gardening book for beginners"` — **30 characters, 5 words**. Exactly the
  input `main`'s `MIN_SUMMARY_LENGTH = 30` was written to accept.

---

## The ground truth

What the backend says about the probe summary (`GET /books/{id}/toc-readiness`, real response):

```json
{"word_count": 5, "character_count": 30, "meets_minimum_requirements": false}
```

The gate is **30 words AND 150 characters**, identical on both backend paths
(`books.py` deterministic fallback, `ai_service.py` AI path). The AI does not decide readiness.

---

## AC1 — the words/characters copy mismatch is fixed

Same page, same summary, both servers.

**main (:3001)** — three numbers, none of them the real one:

```json
{"counter": ["30 characters", "Minimum: 30 characters"],
 "guideline": "...Minimum 30 words recommended.",
 "submitDisabled": false}
```

The counter says the 30-character minimum is **met**; the guideline two lines below says the
minimum is **30 words** (it is 5); the NOT_READY screen says **"Aim for at least 500-1000 words"**.
Screenshot: `2026-07-14-issue-218-main-contradiction.png`

**branch (:3000)** — one number, everywhere, matching the backend:

```json
{"counter": ["5 / 30 words", "30 / 150 characters"],
 "error": "Summary must be at least 30 words (currently 5).",
 "guideline": "...At least 30 words and 150 characters are required to generate a table of contents...",
 "submitDisabled": true}
```

`5` and `30` are byte-for-byte the backend's own `word_count: 5, character_count: 30`.
Screenshot: `2026-07-14-issue-218-branch-blocked.png` (counter, error, and guideline in one frame)

**VERIFIED** — counter, guideline, and NOT_READY tips now state the same enforced numbers.

## AC2 — the client gate matches the real AI readiness threshold

| | main (:3001) | branch (:3000) | backend |
|---|---|---|---|
| 30-char / 5-word summary | submit **enabled** | submit **disabled** | `meets_minimum_requirements: false` |

main disagrees with the backend; the branch agrees with it. **VERIFIED**

### Counting parity — the two ways a naive gate still disagrees

Both verified against the real runtimes, not reasoned about.

**Characters (codex pre-PR P2).** Summary = 30 one-letter words + 46 emoji:

```
python len()      : 106   -> backend gate NOT met
js .length        : 152   -> a naive client thinks the gate IS met
js Array.from()   : 106
```

Live, same string, same DOM:

- **main**: counter `"152 characters"`, submit **enabled** → walks into the dead-end.
  Screenshot: `2026-07-14-issue-218-main-emoji-152.png`
- **branch**: counter `"106 / 150 characters"`, error `"at least 150 characters (currently 106)"`,
  submit **disabled** — while `document.querySelector("#summary").value.length` in that same DOM
  is still `152`. The page reports Python's number, not JS's.

**Whitespace.** JS `/\s/` is not Python's `str.isspace()` set:

```
len("word1\x85word2".split()) == 2   but JS /\s+/ -> 1   (would falsely reject a valid summary)
len("word1﻿word2".split()) == 1 but JS /\s+/ -> 2   (would accept one the backend rejects)
```

A BOM is common in pasted text. The module spells out Python's exact set; 6 pins cover it.

**VERIFIED**

## AC3 — the dead-end is gone

**main**: clicked "Continue to TOC Generation" on the summary the page had just called valid →
landed on `/generate-toc` → **"Summary Needs More Detail"**, `Word Count 5`, `Meets Requirements: No`,
advised to *"Aim for at least 500-1000 words"*. That is the reported dead-end, reproduced live.
Screenshot: `2026-07-14-issue-218-main-deadend.png`

**branch**: the same summary never gets that far — submit is disabled with an explanation naming
the shortfall, before the user invests any time.

With a genuinely ready summary (47 words / 322 characters) the branch's gate opens and the wizard
**does not** show NOT_READY:

```json
branch page:  {"notReady": false}
backend:      {"word_count": 47, "character_count": 322, "meets_minimum_requirements": true}
```

**Control for the AI error.** Past readiness, the wizard hits "Something Went Wrong — Unexpected AI"
because the local OpenAI key is stale:

```
POST /api/v1/books/{id}/generate-questions -> 401 invalid_api_key -> 500
```

`main` loaded with the *same* ready summary gives `{"notReady": false, "aiError": true}` — identical
to the branch. The AI failure is environmental and present on both; it is downstream of the readiness
gate, and reaching it is itself evidence that readiness **passed**. **VERIFIED**

---

## Evidence table

| Criterion | Action | Outcome evidence | Status |
|---|---|---|---|
| AC1 copy mismatch fixed | render summary page, both servers | main: `"30 characters"/"Minimum: 30 characters"` + `"Minimum 30 words recommended"` + `"500-1000 words"`. branch: `"5 / 30 words"`, `"30 / 150 characters"`, guideline + NOT_READY tip state the same 30/150 | VERIFIED |
| AC2 gate matches real threshold | type the 30-char summary | main submit **enabled**; branch submit **disabled** w/ `"at least 30 words (currently 5)"`; backend `meets_minimum_requirements: false` — branch agrees, main does not | VERIFIED |
| AC2 counting parity (chars) | emoji summary, backend len 106 | main counter `152` + enabled; branch counter `106 / 150` + disabled, w/ raw `value.length === 152` in the same DOM | VERIFIED |
| AC3 dead-end gone | click Continue | main → NOT_READY `Word Count 5, Meets Requirements: No, "500-1000 words"`. branch → blocked pre-submit; ready summary → `notReady: false` + backend `meets_minimum_requirements: true` | VERIFIED |
| No work lost under stricter gate | type sub-threshold text | debounced auto-save still PATCHes independently of validation (unit-pinned) | VERIFIED |

**DEMO_PASSED = true**

## Notes / one-way state

The signup and book creation are one-way, and the wizard's AI step depends on a stale local key, so
`showboat verify` would diff on those blocks (#203 precedent). The differential blocks (counter,
button state, backend readiness JSON) are re-runnable against a fresh book.
