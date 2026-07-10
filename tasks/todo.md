# Issue #244 — [P0.9] Privilege escalation: PATCH /users/me accepts role

**Plan source**: self-authored (no plan comment on the issue; CodeRabbit boilerplate only).
**Approved**: autonomously (no architectural fork — the AC itself allows "removed … or ignored/stripped"; removal matches repo precedent: #220 deliberately kept stripe fields out of `UserUpdate`, #186 deleted rather than gated).

## Root cause
`UserUpdate` (`backend/app/schemas/user.py:94`) exposes `role: Optional[str]`; `PATCH /api/v1/users/me` (`update_profile`) dumps `exclude_unset=True` straight into the generic `update_user()` `$set` — any authenticated user can persist `{"role": "admin"}` and everything gated on `SessionRoleChecker` is escalatable.

## Decision
Remove `role` from `UserUpdate` entirely (root fix — no current or future handler can pass it through), rather than stripping it in one handler. Consequences:
- `PUT /users/{auth_id}`'s non-admin role guard becomes dead code (references the removed field) → deleted. Role is now unwritable via the API for **everyone**, admins included — no admin role-change path exists in any UI/script/test today (verified), so per YAGNI roles are managed directly in the DB.
- Unknown `role` key in a request body is ignored by pydantic (BaseModel default) → 200 with role untouched, other fields applied.

## Audit of other privileged fields (AC 3)
- `plan`, `stripe_customer_id`, `stripe_subscription_id`, `is_active`, `book_ids`, `auth_id`: already absent from `UserUpdate` (deliberate, #220).
- `metadata` (arbitrary dict): stored under its own key, never read for authz anywhere in `app/` — not privileged.
- `email`: self-service with duplicate-key guard; pre-existing intended behavior, out of scope.
→ `role` was the only privileged field reachable.

## Steps (TDD)
- [ ] 1. Branch `fix/244-role-self-elevation`
- [ ] 2. RED — tests in `tests/test_api/test_routes/test_users_coverage.py`:
  - AC regression: `PATCH /users/me` with `{"role": "admin", "first_name": "X"}` → 200, response role `user`, **stored DB role unchanged**, first_name applied
  - Same stored-role-unchanged property for `PUT /users/{auth_id}` (self-target)
  - Re-target `test_put_user_non_admin_role_change_returns_403`: the 403 guard is superseded by field removal — replaced with a strictly stronger assertion (stored role unchanged; the 403 only proved the request was rejected, not that role was unwritable)
- [ ] 3. GREEN — remove `role` from `UserUpdate` + its json_schema example; delete the dead PUT role guard
- [ ] 4. Full backend suite + coverage + ruff
- [ ] 5. Deslop scan, quality gate (opencode GLM pre-PR review), PR, post-PR review, demo (two real servers: main self-elevates, branch doesn't), CI, docs sync, merge
