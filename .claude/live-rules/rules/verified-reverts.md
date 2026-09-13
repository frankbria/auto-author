---
description: Mutation checks and reverts that actually revert
priority: 70
prompt: ["mutation", "mutate", "revert", "verify the guard", "mutation-check"]
---
Commit before mutating. A `git checkout` revert discards uncommitted work, so an unstaged change made
just before a mutation check is gone. A **brand-new file has nothing to revert to** — `git checkout HEAD --`
on it silently does nothing and the mutation persists into the next check.

Before any `git reset --hard`, `git checkout --` or `git clean`, read `git status` as a list of things
about to be lost, not as noise. The likeliest casualty is a file changed hours ago for an unrelated
reason, because it has stopped registering as work in progress. Fix a branch mix-up with the narrowest
tool — `git branch <name>` and switch away — rather than resetting a tree that may be carrying
something else.

Check for a stale `.git/index.lock` first, and assert every revert:

```sh
[ -e .git/index.lock ] && rm -f .git/index.lock   # only when no git process is actually running
git checkout HEAD -- <paths>
git diff --quiet HEAD -- <paths> || { echo "REVERT FAILED"; exit 1; }
```

A leftover lock silently no-ops every `checkout` and `commit`: reverts stop reverting, mutations pile
up on each other, and the results of every later check become meaningless. It is not hypothetical —
it has occurred repeatedly in this repo, and only the assertion caught it. Confirm no git process is
genuinely running before removing a lock (a 0-byte lock with no `git` in `ps` is stale).

For a group PR or any branch cut from a main that has since had commits squash-merged, rebasing will
try to replay the pre-squash commits. Rebuild the branch from `origin/main` and cherry-pick your own
commits instead of fighting the conflicts.

State mutation results honestly: "guard PASSED under mutation" is a finding about the guard, not a
step to retry until it goes green.
