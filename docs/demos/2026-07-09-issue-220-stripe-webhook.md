# Issue #220 — Stripe subscription webhook: raw-body HMAC verify, plan sync, replay dedup

*2026-07-09T17:15:00Z*

Setup: a real uvicorn server (branch `feature/issue-220-stripe-webhook`) on port 8321 against a real local MongoDB (dedicated db `auto_author_demo_220`), with `STRIPE_WEBHOOK_SECRET=whsec_demo_secret_220` and `STRIPE_PRICE_ID_PRO=price_demo_pro`. One seeded user on the `free` plan, already linked to Stripe customer `cus_demo_1`. Signatures below are computed with the real Stripe scheme (`t=<ts>,v1=HMAC-SHA256("{t}.{payload}")`) by a 7-line stdlib script — the server verifies them with `stripe.Webhook.construct_event`, nothing is mocked.

```bash
mongosh --quiet mongodb://localhost:27017/auto_author_demo_220 --eval 'db.users.findOne({auth_id: "auth-demo-220"}, {_id: 0, auth_id: 1, plan: 1, stripe_customer_id: 1, stripe_subscription_id: 1})'
```

```output
{
  auth_id: 'auth-demo-220',
  plan: 'free',
  stripe_customer_id: 'cus_demo_1'
}
```

**AC 1 — a signed webhook updates `user.plan`.** POST a genuinely-signed `customer.subscription.updated` event carrying the configured pro price:

```bash
SIG=$(python3 /tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/sign.py whsec_demo_secret_220 /tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_upgrade.json) && curl -s -w '\nHTTP %{http_code}\n' -X POST http://localhost:8321/api/v1/webhooks/stripe -H "stripe-signature: $SIG" --data-binary @/tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_upgrade.json
```

```output
{"status":"processed","plan":"pro"}
HTTP 200
```

The user document in Mongo now carries the pro plan plus both Stripe identifiers:

```bash
mongosh --quiet mongodb://localhost:27017/auto_author_demo_220 --eval 'db.users.findOne({auth_id: "auth-demo-220"}, {_id: 0, auth_id: 1, plan: 1, stripe_customer_id: 1, stripe_subscription_id: 1})'
```

```output
{
  auth_id: 'auth-demo-220',
  plan: 'pro',
  stripe_customer_id: 'cus_demo_1',
  stripe_subscription_id: 'sub_demo_1'
}
```

The plan change is attributed to the Stripe event in the audit log, and the event id is recorded in the TTL-reaped replay-dedup collection:

```bash
mongosh --quiet mongodb://localhost:27017/auto_author_demo_220 --eval 'printjson(db.audit_logs.findOne({actor_id: "stripe:evt_demo_upgrade_1"}, {_id: 0, action: 1, actor_id: 1, target_id: 1})); printjson(db.processed_stripe_events.findOne({_id: "evt_demo_upgrade_1"}))'
```

```output
{
  action: 'user_update',
  actor_id: 'stripe:evt_demo_upgrade_1',
  target_id: 'auth-demo-220'
}
{
  _id: 'evt_demo_upgrade_1',
  expires_at: ISODate('2026-08-08T17:15:23.320Z')
}
```

**AC 2 — invalid signature → 400.** Sign the payload, then tamper one byte of the body (an attacker rewriting the customer id). The header is valid for the *original* bytes, so raw-body HMAC verification must reject it:

```bash
SIG=$(python3 /tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/sign.py whsec_demo_secret_220 /tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_upgrade.json) && sed 's/cus_demo_1/cus_evil_9/' /tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_upgrade.json > /tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_tampered.json && curl -s -w '\nHTTP %{http_code}\n' -X POST http://localhost:8321/api/v1/webhooks/stripe -H "stripe-signature: $SIG" --data-binary @/tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_tampered.json
```

```output
{"detail":"Invalid Stripe webhook signature or payload"}
HTTP 400
```

A payload with no signature header at all is likewise rejected, and an unsigned request cannot downgrade or upgrade anyone — the user is untouched:

```bash
curl -s -w '\nHTTP %{http_code}\n' -X POST http://localhost:8321/api/v1/webhooks/stripe --data-binary @/tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_deleted.json; mongosh --quiet mongodb://localhost:27017/auto_author_demo_220 --eval 'db.users.findOne({auth_id: "auth-demo-220"}, {_id: 0, plan: 1})'
```

```output
{"detail":"Missing Stripe-Signature header"}
HTTP 400
{ plan: 'pro' }
```

**AC 3 — replay/idempotency.** To prove a replay is a genuine no-op (not just "same result twice"), first flip the plan out-of-band to `free`, then re-deliver the exact same signed upgrade event (`evt_demo_upgrade_1`). If replay protection works, the plan must STAY `free`:

```bash
mongosh --quiet mongodb://localhost:27017/auto_author_demo_220 --eval 'db.users.updateOne({auth_id: "auth-demo-220"}, {$set: {plan: "free"}}); print("plan flipped to free out-of-band")' && SIG=$(python3 /tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/sign.py whsec_demo_secret_220 /tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_upgrade.json) && curl -s -w '\nHTTP %{http_code}\n' -X POST http://localhost:8321/api/v1/webhooks/stripe -H "stripe-signature: $SIG" --data-binary @/tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_upgrade.json && mongosh --quiet mongodb://localhost:27017/auto_author_demo_220 --eval 'db.users.findOne({auth_id: "auth-demo-220"}, {_id: 0, plan: 1})'
```

```output
plan flipped to free out-of-band
{"status":"replay","event_id":"evt_demo_upgrade_1"}
HTTP 200
{ plan: 'free' }
```

**Cancellation lifecycle.** Re-upgrade with a fresh event id (proving new event ids process normally after a replay), then deliver `customer.subscription.deleted` — the plan reverts to `free`, the dead subscription id is cleared, and the customer link is retained:

```bash
sed 's/evt_demo_upgrade_1/evt_demo_upgrade_2/' /tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_upgrade.json > /tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_upgrade2.json && SIG=$(python3 /tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/sign.py whsec_demo_secret_220 /tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_upgrade2.json) && curl -s -X POST http://localhost:8321/api/v1/webhooks/stripe -H "stripe-signature: $SIG" --data-binary @/tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_upgrade2.json && echo && SIG=$(python3 /tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/sign.py whsec_demo_secret_220 /tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_deleted.json) && curl -s -X POST http://localhost:8321/api/v1/webhooks/stripe -H "stripe-signature: $SIG" --data-binary @/tmp/claude-1000/-home-frankbria-projects-auto-author/2bad4e1f-bc41-4a98-80d7-8615047ad323/scratchpad/demo220/evt_deleted.json && echo && mongosh --quiet mongodb://localhost:27017/auto_author_demo_220 --eval 'db.users.findOne({auth_id: "auth-demo-220"}, {_id: 0, plan: 1, stripe_customer_id: 1, stripe_subscription_id: 1})'
```

```output
{"status":"processed","plan":"pro"}
{"status":"processed","plan":"free"}
{
  plan: 'free',
  stripe_customer_id: 'cus_demo_1',
  stripe_subscription_id: null
}
```

**Fail-closed configuration.** The same request against a server started WITHOUT `STRIPE_WEBHOOK_SECRET` returns 503 and never processes the payload (pinned by `tests/test_api/test_stripe_webhook.py::test_unconfigured_secret_fails_closed_503`). Full verification after all review fixes: backend suite **1128 passed / 13 skipped, 92.16% coverage** (≥85% gate green) — including 17 webhook tests signing payloads with real HMAC against real Mongo, a full-app middleware integration test pinning that nothing consumes the raw body before verification, a failure-injection test proving a persistence error releases the replay marker for Stripe's retry, and a link-then-resend recovery test for events that arrive before the user is linked.
