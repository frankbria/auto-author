# Lessons

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
