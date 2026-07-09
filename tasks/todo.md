# Issue #222 — [P0.2.3] Billing settings UI (plan status + manage/upgrade)

Parent epic #174. **No architectural fork** — every decision mirrors the shipped #221 checkout idiom → approved autonomously.

## Plan drift (CodeRabbit plan of 2026-07-04 predates #174/#220/#221 — mostly shipped)

- Its Phase 1 (`plan` field end-to-end) — **shipped** in #174 (+ `read_users_me` mapping fixed in #221). Its `Literal["free","paid"]` is also wrong: real plans are `free`/`pro`/`restricted`.
- Its Phase 2 Tasks 2–4 (`useBillingApi`, `BillingSettingsForm`, Billing tab in settings) — **shipped** in #221 (PR #245), including the free-user Upgrade CTA → Stripe checkout.
- Its `useSearchParams` + Suspense approach — **rejected in #221 deliberately**; the settings page reads `window.location.search` in a mount effect to avoid the Suspense-boundary requirement. The `?tab=` deep-link reuses that pattern.
- Its "link free users to `/dashboard/checkout`" — **stale**: checkout is a backend-created Stripe redirect (`POST /billing/checkout`), shipped.

## Remaining gaps (the actual work)

AC recap: user sees plan ✅ (shipped) · free upgrade CTA ✅ (shipped) · **paid users can manage billing** ❌ · **ErrorNotification CTA deep-links to the billing tab** ❌.

- [x] **Backend `POST /api/v1/billing/portal`** (extend `billing.py`, mirrors checkout):
  session auth + rate limit 5/300; **503 fail-closed** when `STRIPE_SECRET_KEY` unset (portal needs no price id); **409** when the user has no `stripe_customer_id` (nothing to manage — upgrade first); `stripe.billing_portal.Session.create(customer=…, return_url={BETTER_AUTH_URL}/dashboard/settings?tab=billing)` via `asyncio.to_thread`; `StripeError` → sanitized 502. No plan mutation.
- [x] **`useBillingApi.openBillingPortal()`** — POST `/billing/portal`, returns `{url}`.
- [x] **`BillingSettingsForm`**: Manage billing button gated on `hasBillingAccount` (`stripe_customer_id` presence — the portal's exact backend gate), NOT on plan: the pre-PR review's Major was that lapsed (`restricted`) users couldn't reach the payment-recovery portal through the UI. Restricted users see BOTH Upgrade and Manage billing, with "Your subscription is inactive" copy (post-PR minor).
- [x] **Settings page `?tab=` deep-link**: mount effect reads `tab` from `window.location.search`, validated against `SETTINGS_TABS`; checkout param handling runs after and may override. `tab` param left in the URL.
- [x] **ErrorNotification** ENTITLEMENT CTA: `/dashboard/settings` → `/dashboard/settings?tab=billing`. **Demo finding**: no shipped flow actually routes a 402 through that toast (wizard + draft dialog render inline errors; draft dialog leaks raw JSON) — filed as **#247**.

## Tests (TDD — write first)

- [x] `backend/tests/test_api/test_billing_portal.py` (6): happy path (full-string `return_url`, no plan flip), restricted-user allowed, 409 no-customer, 503 unconfigured, 401 unauth, 502 sanitized StripeError.
- [x] `useBillingApi.test.ts`, `BillingSettingsForm.test.tsx` (8, incl. restricted both-buttons + inactive copy), `SettingsPageBilling.test.tsx` (7, incl. deep-link + restricted page-level), `ErrorNotification.test.tsx` CTA target.

## Gates

- [x] Backend **1144 passed / 13 skipped, 92.23% cov**; frontend **113 suites, 2054+ passed**, coverage/lint/typecheck clean
- [x] opencode (GLM) pre-PR ×2 (1 Major fixed → "clean to merge"; 429-test minor rebutted, accepted) + post-PR fresh session "clean to merge" (2 of 4 minors fixed, 2 accepted) — posted to PR #246
- [x] Demo `docs/demos/2026-07-09-issue-222-billing-portal.md` (found #247)
- [ ] CI green → merge
