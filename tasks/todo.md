# Issue #221 — [P0.2.2] Plan upgrade / Stripe checkout flow

Parent epic #174 (ADR `docs/adr/2026-07-04-beta-entitlement-model.md`). Full-stack (backend endpoint + minimal frontend entry point).
**Plan source**: CodeRabbit plan comment, heavily adapted — it predates #174/#220 and claims the whole integration is greenfield.
**No architectural fork** — every decision follows an established repo idiom → approved autonomously.

## Plan drift corrections (vs the CodeRabbit issue plan)

- **Stale**: "no Stripe, billing, or plan/tier concept exists — entirely greenfield." False since #174/#220: `plan`/`stripe_customer_id`/`stripe_subscription_id` exist on models `UserBase` + schemas `UserResponse` (deliberately NOT in `UserUpdate`); `stripe==15.3.0` is pinned; `STRIPE_WEBHOOK_SECRET`/`STRIPE_PRICE_ID_PRO` exist in config with a whitespace-strip validator; `app/core/entitlements.py` has `free/pro/restricted` + `resolve_plan_for_price()`; the webhook (#220) already reconciles `customer.subscription.*` and reads `subscription.metadata.auth_id` as its user-lookup fallback — this issue must stamp it. **Its Phase 2 (user model fields) is entirely done — skipped.**
- **Stale**: Phase 2 Task 2 targets `create_new_user` in `users.py` — that endpoint was deleted in #186. New users get `plan: "free"` via the model default + the security.py auto-create path. Nothing to do.
- **Rejected (over-engineering / ponytail)**: the plan's `stripe_service.py` singleton + `stripe_errors.py` hierarchy mirroring `ai_service`/`ai_errors`. The endpoint makes exactly two SDK calls; the #220 webhook already calls the `stripe` SDK directly in the endpoint module. Same pattern here: direct SDK calls in `billing.py`, offloaded via `asyncio.to_thread` (the #175 event-loop lesson — Stripe's SDK is sync/blocking). A wrapper earns its keep when a third consumer appears.
- **Rejected (config sprawl)**: `STRIPE_ENABLED` flag + plan→price mapping dict + new success/cancel URL settings. "Configured" is the flag: unset `STRIPE_SECRET_KEY`/`STRIPE_PRICE_ID_PRO` → 503 fail-closed (exact #220 webhook convention). The only paid tier is `pro` → reuse `STRIPE_PRICE_ID_PRO`. Success/cancel URLs derive from `BETTER_AUTH_URL` (documented "must match frontend URL"); no new env vars beyond the secret key.
- **Adapted**: `UserPlan` enum — not added; the codebase deliberately uses plain-`str` plans with the entitlements registry as SSOT (#174 fail-closed design). An enum would fight `resolve_plan_for_price` and legacy docs.
- **Adapted**: frontend `?checkout=` reading via `window.location.search` in a mount effect instead of `useSearchParams` (avoids the Next.js Suspense-boundary requirement on the settings page).

## Steps

- [x] **Config**: add `STRIPE_SECRET_KEY: str = ""` to the existing Stripe block in `config.py`; extend `strip_stripe_values` validator to cover it; update the "#221 deliberately omitted" comment; mirror in `.env.example` + dated `ENV_VAR_CHANGELOG.md` entry.
- [x] **Backend endpoint** (TDD): new `app/api/endpoints/billing.py`, `POST /checkout` → mounted at `/api/v1/billing/checkout` via `router.py` (NOT in session-middleware skip_paths — flows through normal cookie-session auth). Handler:
  - `Depends(get_current_user_from_session)` + `Depends(get_rate_limiter(limit=5, window=300))`.
  - Body: `{plan: Literal["pro"]}` (default `"pro"`) — unknown tier is a 422 for free.
  - 503 fail-closed when `STRIPE_SECRET_KEY` or `STRIPE_PRICE_ID_PRO` unset (webhook convention).
  - 409 when the user is already on a paid plan (`plan` in the paid set — plan is the SSOT per #174; subscription id is not consulted).
  - Reuse `current_user["stripe_customer_id"]`; else `stripe.Customer.create(email, metadata={auth_id})` with `idempotency_key` keyed on auth_id (dedups the concurrent-double-click race within Stripe's 24h idempotency window) and persist via `update_user(auth_id, {"stripe_customer_id": ...}, actor_id=auth_id)`.
  - `stripe.checkout.Session.create(mode="subscription", customer=..., line_items=[{price: STRIPE_PRICE_ID_PRO, quantity: 1}], client_reference_id=auth_id, subscription_data={"metadata": {"auth_id": auth_id}}, success_url=f"{BETTER_AUTH_URL}/dashboard/settings?checkout=success", cancel_url=...?checkout=cancel)` — the `subscription_data.metadata.auth_id` stamp is what webhooks.py:112 reads.
  - Both SDK calls behind `asyncio.to_thread`. `stripe.StripeError` → structured 502 (no internals leaked); plan flip NEVER happens here — webhook-only (#220).
- [x] **Backend tests** `tests/test_api/test_billing_checkout.py` (8 tests, RED→GREEN) (`auth_client_factory` + real Mongo; patch the SDK boundary `stripe.Customer.create`/`stripe.checkout.Session.create` — same wire-boundary class as the OpenAI stubs; the paid API itself is the one thing we don't call for real): happy path returns session URL + persists customer id; existing customer id reused (no `Customer.create` call); session kwargs carry `client_reference_id`+`subscription_data.metadata.auth_id`+configured price; already-pro → 409; unconfigured → 503; unauthenticated → 401; Stripe API failure → 502 and no partial user write beyond customer id; settings-default test (`STRIPE_SECRET_KEY` defaults empty).
- [ ] **Frontend** (TDD): `hooks/useBillingApi.ts` (`startCheckout(plan)` → POST `/billing/checkout`, returns `{url}`, mirrors `useProfileApi`); `components/settings/BillingSettingsForm.tsx` (shows current plan from loaded profile, Upgrade button → `startCheckout` → `window.location.assign(url)`, disabled while in flight / already pro); new `billing` tab in `dashboard/settings/page.tsx` (controlled-tabs pattern; self-serve like the security tab — hide shared Save); mount-effect reads `?checkout=success|cancel` → toast ("processing — plan updates shortly via Stripe confirmation" / "canceled") + selects billing tab.
- [ ] **Frontend tests**: page-level billing tab (SettingsPageSave.test.tsx pattern — mocked `useAuthFetch`), BillingSettingsForm unit (upgrade click POSTs + redirects, in-flight disable, pro state), checkout=success/cancel return handling.
- [ ] **Quality gate**: full backend + frontend suites, lint/typecheck, deslop, opencode (GLM) pre-PR review, PR, post-PR review, demo (real uvicorn + real Mongo + SDK-boundary stub logging the outbound Stripe kwargs; real browser for the tab), CI green, docs sync, merge.

## Accepted tradeoffs (documented, not bugs)

- **Success redirect is informational only** — the settings page shows "processing"; the authoritative plan flip arrives via the #220 webhook. No polling loop (YAGNI for beta; user refreshes or revisits).
- **Orphaned Stripe customer possible** if two checkouts race past the idempotency window — last `$set` wins, the orphan has no subscription and costs nothing; the unique+sparse index still guarantees 1:1 for the winner.
- **`BETTER_AUTH_URL` doubles as frontend origin** for redirect URLs — true in every current deployment shape; a dedicated `FRONTEND_URL` var appears when they ever diverge.
