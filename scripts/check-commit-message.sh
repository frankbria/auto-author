#!/usr/bin/env bash
# Reject a commit message that closes an issue by accident.
#
# GitHub's linked-issue parser matches `close|fixes|resolved #<n>` anywhere in a
# commit message or PR body, and it does not parse negation. So a disclaimer
# written to PREVENT a closure causes one:
#
#   "Does not close #584 — its condition is the rules back at `error`."
#
# closed #584 on merge, with 17 violations outstanding (auto-author #584, and
# the sentence above is the real one that did it).
#
# To reference an issue without closing it, drop the keyword: "#584's close
# condition", "per #584", "partial progress on #584".
#
# Limitation, stated rather than hidden: a PR *body* can close an issue too, and
# no local hook can see that. This covers commit messages only.
set -euo pipefail

message_file="${1:?usage: check-commit-message.sh <path-to-commit-message>}"
# Every line is checked, comments included.
#
# The first cut skipped lines starting with `#`, reasoning that git strips them.
# It does — in editor mode. `git commit -m` uses --cleanup=whitespace and keeps
# them, and the very first message this guard ran on opened a body line with
# "#676's merge commit carried ...", which the skip discarded along with the
# "Does not close #584" inside it. The guard passed and the message still closed
# the issue.
#
# So: no stripping. A genuine comment line that trips this is a reword; a missed
# closure is the failure that already cost us.
body="$(cat "$message_file")"

keywords='close[sd]?|fix(e[sd])?|resolve[sd]?'

# Newlines collapse to spaces first. grep is line-based, and commit bodies wrap
# at ~72 columns, so "This does not" / "close #123" lands on two lines and reads
# as safe while GitHub, which does not care about the wrap, closes the issue.
# Found by the pre-PR reviewer, reproduced before fixing.
flattened="$(printf '%s' "$body" | tr '\n' ' ' | tr -s '[:space:]' ' ')"

negated="$(printf '%s' "$flattened" | grep -oiE ".{0,40}(not|n't)[[:space:]]+(${keywords})[[:space:]]*:?[[:space:]]*#[0-9]+" || true)"

if [ -n "$negated" ]; then
  echo "Commit message would close an issue it says it does not close:" >&2
  printf '  ...%s\n' "$negated" >&2
  cat >&2 <<'MSG'

GitHub matches the keyword regardless of the negation in front of it.
Rewrite without the keyword, for example:
  "Does not close #584"   ->  "#584 stays open; its condition is ..."
  "This doesn't fix #12"  ->  "#12 is unaffected"
MSG
  exit 1
fi
