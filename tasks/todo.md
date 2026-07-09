# Issue #222 — [P0.2.3] Billing settings UI (plan status + manage/upgrade)

Parent epic #174. **No architectural fork** — every decision mirrors the shipped #221 checkout idiom → approved autonomously.

## Plan drift (CodeRabbit plan of 2026-07-04 predates #174/#220/#221 — mostly shipped)

- Its Phase 1 (`plan` field end-to-end) — **shipped** in #174 (+ `read_users_me` mapping fixed in #221). Its `Literal["free","paid"]` is also wrong: real plans are `free`/`pro`/`restricted`.
- Its Phase 2 Tasks 2–4 (`useBillingApi`, `BillingSettingsForm`, Billing tab in settings) — **shipped** in #221 (PR #245), including the free-user Upgrade CTA → Stripe checkout.
- Its `useSearchParams` + Suspense approach — **rejected in #221 deliberately**; the settings page reads `window.location.search` in a mount effect to avoid the Suspense-boundary requirement. The `?tab=` deep-link reuses that pattern.
- Its "link free users to `/dashboard/checkout`" — **stale**: checkout is a backend-created Stripe redirect (`POST /billing/checkout`), shipped.

## Remaining gaps (the actual work)

AC recap: user sees plan ✅ (shipped) · free upgrade CTA ✅ (shipped) · **paid users can manage billing** ❌ · **ErrorNotification CTA deep-links to the billing tab** ❌.

- [ ] **Backend `POST /api/v1/billing/portal`** (extend `billing.py`, mirrors checkout):
  session auth + rate limit 5/300; **503 fail-closed** when `STRIPE_SECRET_KEY` unset (portal needs no price id); **409** when the user has no `stripe_customer_id` (nothing to manage — upgrade first); `stripe.billing_portal.Session.create(customer=…, return_url={BETTER_AUTH_URL}/dashboard/settings?tab=billing)` via `asyncio.to_thread`; `StripeError` → sanitized 502. No plan mutation.
- [ ] **`useBillingApi.openBillingPortal()`** — POST `/billing/portal`, returns `{url}`.
- [ ] **`BillingSettingsForm`**: pro branch gains a "Manage billing" button → portal redirect (mirror `handleUpgrade`'s isRedirecting + error toast).
- [ ] **Settings page `?tab=` deep-link**: in the existing mount effect, read `tab` from `window.location.search`, validate against the 5 tab values, `setActiveTab`. Checkout param handling runs after and may override (both target billing anyway). `tab` param left in the URL (benign, unlike the re-toasting checkout param).
- [ ] **ErrorNotification** ENTITLEMENT CTA: `/dashboard/settings` → `/dashboard/settings?tab=billing`.

## Tests (TDD — write first)

- [ ] `backend/tests/test_api/test_billing_portal.py` (mirror `test_billing_checkout.py`): happy path (portal URL returned; `customer` + `return_url` with `tab=billing` on the wire; no plan flip), 409 no-customer, 503 unconfigured, 401 unauth, 502 sanitized StripeError.
- [ ] `useBillingApi.test.ts`: portal method endpoint/verb.
- [ ] `BillingSettingsForm.test.tsx`: pro → Manage billing → redirect to portal URL; error → destructive toast, button re-enabled.
- [ ] `SettingsPageBilling.test.tsx`: `?tab=billing` selects the billing tab; invalid `?tab=` ignored (default writing).
- [ ] `ErrorNotification.test.tsx`: Upgrade CTA navigates to `?tab=billing`.

## Gates

- [ ] Backend + frontend suites green, coverage gates green, lint/typecheck clean
- [ ] opencode (GLM) review pre-PR + post-PR
- [ ] Demo (real servers + wire-logging Stripe stub, per #221 pattern)
- [ ] CI green → merge
