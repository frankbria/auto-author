# Renewal-consent records kept until the subscription ends + 4 years (#948)

*2026-11-25T20:56:04Z by Showboat 0.6.1*
<!-- showboat-id: d9ecc325-ad67-4ea5-a200-5ea5b1ba92d8 -->

Driver: a script outside the repo (`/tmp/demo948/demo.py`) runs this branch's backend code against a scratch local MongoDB database `auto-author-demo-948`. Webhook events go through the real `/stripe` route with genuine HMAC signatures; account deletion calls the real `cancel_subscription_for_deletion` and `delete_user`, with a local HTTP server standing in for api.stripe.com. Each step prints the user's `billing.renewal_consent` row as stored.

Consent is recorded before Checkout. With no subscription yet, the row expires 4 years after the consent (an abandoned checkout).

```bash
(cd backend && PYTHONPATH=$PWD ENVIRONMENT=test MONGODB_URI=mongodb://localhost:27017 DATABASE_NAME=auto-author-demo-948 STRIPE_WEBHOOK_SECRET=whsec_demo STRIPE_SECRET_KEY=sk_test_demo STRIPE_PRICE_ID_PRO=price_demo uv run python /tmp/demo948/demo.py reset 2>&1 | grep -v -e ' - INFO - ' -e '^INFO' -e WARNING)
```

```output
<claude-code-hint v="1" type="plugin" value="stripe@claude-plugins-official" />
after checkout consent (no subscription yet): consent row 2026-11-25 ip=203.0.113.7 expires_at=2030-11-25 20:56:07
```

The subscription goes live: the stamp is cleared. A paused subscription can resume, so it has not ended and the row still has no expiry.

```bash
(cd backend && PYTHONPATH=$PWD ENVIRONMENT=test MONGODB_URI=mongodb://localhost:27017 DATABASE_NAME=auto-author-demo-948 STRIPE_WEBHOOK_SECRET=whsec_demo STRIPE_SECRET_KEY=sk_test_demo STRIPE_PRICE_ID_PRO=price_demo uv run python /tmp/demo948/demo.py active 2>&1 | grep -v -e ' - INFO - ' -e '^INFO' -e WARNING); (cd backend && PYTHONPATH=$PWD ENVIRONMENT=test MONGODB_URI=mongodb://localhost:27017 DATABASE_NAME=auto-author-demo-948 STRIPE_WEBHOOK_SECRET=whsec_demo STRIPE_SECRET_KEY=sk_test_demo STRIPE_PRICE_ID_PRO=price_demo uv run python /tmp/demo948/demo.py paused 2>&1 | grep -v -e ' - INFO - ' -e '^INFO' -e WARNING)
```

```output
<claude-code-hint v="1" type="plugin" value="stripe@claude-plugins-official" />
webhook customer.subscription.updated sub_A status=active: {'status': 'processed', 'plan': 'pro'}
subscription live: consent row 2026-11-25 ip=203.0.113.7 expires_at=(none)
<claude-code-hint v="1" type="plugin" value="stripe@claude-plugins-official" />
webhook customer.subscription.updated sub_A status=paused: {'status': 'processed', 'plan': 'free'}
subscription paused (can resume): consent row 2026-11-25 ip=203.0.113.7 expires_at=(none)
```

The subscription ends on 2027-06-01: the row expires 2031-06-01. Then the user subscribes again: the stamp is cleared.

```bash
(cd backend && PYTHONPATH=$PWD ENVIRONMENT=test MONGODB_URI=mongodb://localhost:27017 DATABASE_NAME=auto-author-demo-948 STRIPE_WEBHOOK_SECRET=whsec_demo STRIPE_SECRET_KEY=sk_test_demo STRIPE_PRICE_ID_PRO=price_demo uv run python /tmp/demo948/demo.py deleted 2>&1 | grep -v -e ' - INFO - ' -e '^INFO' -e WARNING); (cd backend && PYTHONPATH=$PWD ENVIRONMENT=test MONGODB_URI=mongodb://localhost:27017 DATABASE_NAME=auto-author-demo-948 STRIPE_WEBHOOK_SECRET=whsec_demo STRIPE_SECRET_KEY=sk_test_demo STRIPE_PRICE_ID_PRO=price_demo uv run python /tmp/demo948/demo.py restart 2>&1 | grep -v -e ' - INFO - ' -e '^INFO' -e WARNING)
```

```output
<claude-code-hint v="1" type="plugin" value="stripe@claude-plugins-official" />
webhook customer.subscription.deleted sub_A status=canceled: {'status': 'processed', 'plan': 'free'}
subscription ended 2027-06-01: consent row 2026-11-25 ip=203.0.113.7 expires_at=2031-06-01 00:00:00
<claude-code-hint v="1" type="plugin" value="stripe@claude-plugins-official" />
webhook customer.subscription.updated sub_B status=active: {'status': 'processed', 'plan': 'pro'}
re-subscribed (sub_B live): consent row 2026-11-25 ip=203.0.113.7 expires_at=(none)
```

The user deletes their account. Stripe reports the cancel at 2028-02-10. The users document is gone; the consent row (IP included) survives, dated to 2032-02-10.

```bash
(cd backend && PYTHONPATH=$PWD ENVIRONMENT=test MONGODB_URI=mongodb://localhost:27017 DATABASE_NAME=auto-author-demo-948 STRIPE_WEBHOOK_SECRET=whsec_demo STRIPE_SECRET_KEY=sk_test_demo STRIPE_PRICE_ID_PRO=price_demo uv run python /tmp/demo948/demo.py delete-account 2>&1 | grep -v -e ' - INFO - ' -e '^INFO' -e WARNING)
```

```output
<claude-code-hint v="1" type="plugin" value="stripe@claude-plugins-official" />
account deleted: True
users document left: None
after account deletion (Stripe canceled_at 2028-02-10): consent row 2026-11-25 ip=203.0.113.7 expires_at=2032-02-10 00:00:00
```

Existing rows: a row written before this change, for a user whose subscription ended on 2026-08-15 (its last applied webhook event), is stamped at startup by `ensure_audit_log_indexes`.

```bash
(cd backend && PYTHONPATH=$PWD ENVIRONMENT=test MONGODB_URI=mongodb://localhost:27017 DATABASE_NAME=auto-author-demo-948 STRIPE_WEBHOOK_SECRET=whsec_demo STRIPE_SECRET_KEY=sk_test_demo STRIPE_PRICE_ID_PRO=price_demo uv run python /tmp/demo948/demo.py backfill 2>&1 | grep -v -e ' - INFO - ' -e '^INFO' -e WARNING); (cd backend && PYTHONPATH=$PWD ENVIRONMENT=test MONGODB_URI=mongodb://localhost:27017 DATABASE_NAME=auto-author-demo-948 STRIPE_WEBHOOK_SECRET=whsec_demo STRIPE_SECRET_KEY=sk_test_demo STRIPE_PRICE_ID_PRO=price_demo uv run python /tmp/demo948/demo.py drop 2>&1 | grep -v -e ' - INFO - ' -e '^INFO' -e WARNING)
```

```output
<claude-code-hint v="1" type="plugin" value="stripe@claude-plugins-official" />
legacy row before startup: consent row 2026-03-01 ip=198.51.100.4 expires_at=(none)
legacy row after startup backfill (sub ended 2026-08-15): consent row 2026-03-01 ip=198.51.100.4 expires_at=2030-08-15 00:00:00
<claude-code-hint v="1" type="plugin" value="stripe@claude-plugins-official" />
dropped auto-author-demo-948
```

Privacy Policy section 8 as rendered (printed from a throwaway jest render of `/privacy`, not committed):

```bash
(cd frontend && npx jest src/__demo948__/print.test.tsx 2>&1 | grep -A1 "===")
```

```output
=== 8. Data Retention and Deletion (last paragraph) ===
We keep an audit log of actions taken on your account (for example creating, updating or deleting a book), which can include the IP address and browser user-agent of the request. Audit log entries are deleted automatically 90 days after they are written; deleting your account does not remove them sooner. The one exception is the record of your agreement to the automatic-renewal terms when you subscribe, which holds the IP address and browser user-agent you agreed from, the date and time, and the exact terms you were shown. We keep it while your subscription lasts and until four years after your subscription ends (or, if you agree but never complete the subscription, four years after you agreed), even after your account is deleted, so that we can answer a legal claim about the renewal. If you subscribe again, the period restarts from the end of the new subscription. After that the record is deleted automatically.
```
