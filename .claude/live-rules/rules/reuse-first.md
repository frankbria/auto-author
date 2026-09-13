---
description: Reuse-first implementation
priority: 90
---
This repo is a Next.js frontend and a FastAPI backend over MongoDB, with a large existing surface of
guards, helpers and idioms. Before adding anything, trace how the existing pieces already cover the
case: a helper in `frontend/src/__tests__/theme/helpers/`, an established class idiom, an existing
DAO in `backend/app/db/`, a ledger file, or a skill already in the workflow.

Prefer deleting or tightening over adding. Fix the smallest shared root cause rather than patching
each call site. Keep input validation at trust boundaries and the auth, ownership and data-loss
safeguards regardless of how small the change looks.

Two repo-specific traps worth naming, both of which have shipped bugs here:
- A new guard that duplicates an existing sweep will disagree with it, and the file that falls into
  the gap is the one that ships the defect. Extend the existing guard or share its helper.
- Removing a thing also removes its tripwire. Before deleting a file because "script X reads it",
  run X.

Files under 500 lines. Never hardcode secrets, host IPs, SSH users or cluster hostnames anywhere in
the repo, an issue, a PR or a commit — several of these repos are public.
