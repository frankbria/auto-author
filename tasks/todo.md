# Issue #342 — Supply-chain automation mis-aimed

Branch: `feature/342-supply-chain-automation`

Plan source: maintainer's premise-check comment (corrected AC list), re-verified against
`main @ ee1da24`.

## Verified premise

| Claim | Verdict |
|---|---|
| Dependabot npm targets `/` (root has zero deps, no lockfile) | ✅ confirmed — `.github/dependabot.yml:7` |
| No audit gate in any live workflow | ✅ confirmed — `npm audit` only in `.tbd`/`.disabled` files |
| `python-jose` dead | ✅ confirmed — zero `jose` imports in `app/` or `tests/` |
| `passlib` "unused" | ⚠️ narrower — imported at `app/core/security.py:1`, loaded on every request path; only `hash_password`/`verify_password`/`pwd_context` are production-dead (5 tests are the sole callers) |
| stray untracked `frontend/scripts/package-lock.json` | ❌ no such file; `frontend/scripts/{package.json,system-test.js}` are **tracked**. `colors` comes from the dep declaration, not a lockfile |

**New finding:** `frontend/scripts/system-test.js` is not merely unused — it is **broken**.
It authenticates via `Authorization: Bearer ${API_TOKEN}` (line 39), but the backend
replaced JWT/bearer auth with better-auth session cookies
(`app/core/better_auth_session.py` reads cookies only). It cannot succeed against the
current API. `SYSTEM_TESTS.md` documents this dead script.

## Design decision (approved)

Both audit tools **fail on the current tree**: backend has advisories in
pillow/starlette/pyasn1/python-multipart/python-dotenv; frontend has 7 high + 1 critical
even with `--omit=dev`. A literal `npm audit --audit-level=high` step would red-line
`main` immediately.

**Chosen: baseline-allowlisted blocking gate.** A committed `security-baseline.json`
records today's known advisory IDs with reasons; `scripts/audit_gate.py` diffs live
audit output against it and **fails CI only on advisories not in the baseline**. Real
gate on new vulnerabilities from day one; the existing backlog becomes explicit,
reviewable debt.

## Steps

1. **Dependabot** — point the npm ecosystem at `/frontend` (the only tree with a lockfile).
2. **Audit gate (TDD)** — `scripts/test_audit_gate.py` first, then `scripts/audit_gate.py`:
   parse `pip-audit --format=json` + `npm audit --json`, filter npm to high/critical,
   diff against `security-baseline.json`, exit 1 on un-baselined IDs, report resolved
   entries as prunable (non-blocking).
3. **`python-jose` removal** — drop from `pyproject.toml`, re-lock. Expect `ecdsa`, `rsa`,
   `pyasn1` to leave the tree with it.
4. **`passlib` removal (ordered)** — delete `hash_password`, `verify_password`,
   `pwd_context`, and the import from `app/core/security.py`; delete the 5 covering tests
   in `tests/test_core/test_security.py`; *then* drop `passlib[bcrypt]` and re-lock.
5. **Dead script** — delete `frontend/scripts/` and `SYSTEM_TESTS.md`.
6. **Wire CI** — new `security-audit` job in `.github/workflows/tests.yml`.
7. **Generate the baseline** from the post-removal tree, so it does not carry entries the
   removals already fixed.

## Acceptance criteria

- [ ] Point Dependabot at `/frontend`
- [ ] Committed `pip-audit` + `npm audit` CI step
- [ ] `python-jose` removed and re-locked
- [ ] `passlib` removed via the 3-step order
- [ ] `frontend/scripts/` deleted (with its doc)
