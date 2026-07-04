# ADR: Beta launch entitlement model (free-invite now, Stripe later)

- **Date:** 2026-07-04
- **Status:** Accepted
- **Issue:** [#174](https://github.com/frankbria/auto-author/issues/174) — [P0.2] Billing / entitlement gate for paid access (epic)
- **Related:** #173 (P0.1, per-user AI quota) which keys its caps off the plan established here.

## Context

The codebase has **zero** billing/subscription/entitlement infrastructure
(`grep -riE 'stripe|billing|subscription|payment|entitlement|plan_tier'` returns
only RxJS `form.watch` false-positives). The roadmap describes a phased launch
(invited beta users → capped limited production), implying monetization is
intentionally deferred. But the per-user AI cost cap (P0.1, #173) needs *some*
notion of plan to key off, and a paid launch shouldn't require a rebuild.

## Decision

**Free-invite beta with a single `free` plan now; Stripe deferred.**

We ship the *entitlement hook*, not a payment provider:

- Every user record carries a durable `plan` field (default `"free"`). Legacy
  documents lacking the field are treated as `free` at read time — no backfill.
- A central plan→capability registry (`app/core/entitlements.py`) is the single
  source of truth. Today `free` is entitled to all AI features; a paid tier is
  added as one registry entry later, with no change at call sites.
- A reusable `get_entitlement_checker(feature)` dependency gates the AI
  endpoints (mirroring the sibling `get_ai_usage_quota`/`get_rate_limiter`
  dependencies already on those routes). It is bypassed under `BYPASS_AUTH` /
  when `PLAN_ENFORCEMENT_ENABLED` is off.
- The frontend renders an entitlement denial as a distinct **upgrade** path
  (CTA to settings/contact), not the transient "retry later" AI-error framing.

**No payment provider (Stripe checkout, webhooks, subscription sync, billing UI)
is built in this epic.** That work is decomposed into follow-up sub-issues.

## Alternatives considered

1. **Free-invite + entitlement hook now, Stripe later (chosen).** Matches the
   ticket's "pragmatic path", the phased roadmap, and the acceptance criteria
   (payment integration is conditional/decomposable). Delivers the P0.1 hook so
   paid launch is not a rebuild.
2. **Paid-at-launch.** Build Stripe checkout, webhooks, subscription sync, and
   billing UI as part of this epic. Rejected: premature for a closed beta with no
   billing infrastructure and a phased-launch roadmap; large surface area, higher
   risk, no beta user need today.

## Entitlement contract (for downstream sub-issues)

- **Denial status:** `402 Payment Required` with `error_code =
  ENTITLEMENT_REQUIRED`, using the standard `ErrorResponse` shape plus
  `X-Entitlement-Plan` / `X-Entitlement-Feature` headers. This is distinct from
  the transient `429` used by the rate limiter (#48) and the per-user quota
  (#173). The over-limit case already ships as `429` in #173, so no separate
  `ENTITLEMENT_LIMIT_EXCEEDED` code is added here (YAGNI).
- **Plans:** `free` (full AI access), `restricted` (no AI access — the named
  deny path, e.g. invite revoked / trial expired). Missing/None plan → `free`;
  an explicit unknown plan → denied (fail-closed).
- **Enforcement flag:** `PLAN_ENFORCEMENT_ENABLED` (default `True`, bypassed with
  `BYPASS_AUTH`), following the `BYPASS_AUTH`/`AI_QUOTA_ENABLED` convention.

## How P0.1 keys off this

`get_ai_usage_quota` currently keys per-user caps off `auth_id`. With `plan`
persisted and the registry in place, P0.1's caps become plan-scoped (e.g. daily
limit varies by tier) by reading `current_user["plan"]` against the registry —
no endpoint-signature change, since both are pre-body `Depends` on the same 10
AI routes.

## Consequences

- Beta users are never blocked (free allows everything); the gate is a hook that
  proves out end-to-end and is demonstrable via the `restricted` deny path.
- Adding a paid tier later = one registry entry + the decomposed Stripe sub-issues
  below; no rebuild of the enforcement layer.

## Decomposed follow-up sub-issues (deferred)

- [#220](https://github.com/frankbria/auto-author/issues/220) — Stripe customer/subscription model + webhook (raw-body HMAC verify)
- [#221](https://github.com/frankbria/auto-author/issues/221) — Plan upgrade / Stripe checkout flow
- [#222](https://github.com/frankbria/auto-author/issues/222) — Billing settings UI (plan status + manage/upgrade)
- [#223](https://github.com/frankbria/auto-author/issues/223) — (optional) Invite-gating enforcement for closed beta
