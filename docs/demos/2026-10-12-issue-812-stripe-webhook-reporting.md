# A Stripe webhook that cannot do its job says so (#812)

*2026-10-12T19:45:18Z by Showboat 0.6.1*
<!-- showboat-id: 17a34008-fc4e-4ead-a75c-ca6bad75f02b -->

Three failures of the Stripe webhook left nothing an operator would see. This demo runs the real backend from main and from this branch, posts the same subscription event to it the way Stripe does (a real HMAC signature over the raw body), and then reads what each delivery left behind: the webhook's own log lines and what the backend sent to a stand-in for Sentry on this machine. Every Stripe value is made up.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo812/env.sh; echo "main:   $(git -C $MAIN log --oneline -1 | cut -c1-7)"; echo "branch: $(git -C $WT rev-parse --abbrev-ref HEAD)"; echo 'the event posted:'; python3 -c "import json; e = json.load(open('$D/event.json')); print(' ', e['id'], e['type'], '| customer', e['data']['object']['customer'], '| metadata', e['data']['object']['metadata'])"
```

```output
main:   0afaf98
branch: feature/issue-812-stripe-webhook-logs
the event posted:
  evt_demo_unmatched customer.subscription.updated | customer cus_DEMO_CUSTOMER | metadata {'email': 'payer@example.com'}
```

A rotated signing secret. Stripe signs with a secret the backend no longer has, three deliveries in a row. On main each is a 400 and nothing else: no log line, no report. Stripe retries for days and then disables the endpoint.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo812/env.sh; backend $MAIN; for i in 1 2 3; do deliver whsec_demo_rotated; done; traces; stop
```

```output
answered 400 {"detail":"Invalid Stripe webhook signature or payload"}
answered 400 {"detail":"Invalid Stripe webhook signature or payload"}
answered 400 {"detail":"Invalid Stripe webhook signature or payload"}
log lines from the webhook: 0
reports sent to Sentry: 0
  the customer id: in neither the log nor a report
  the payer's email: in neither the log nor a report
  the signature: in neither the log nor a report
```

The same on this branch. Each refusal is an error in the log. Sentry gets one report for the three, under a fixed fingerprint: the route is public, so anyone can post a bad signature, and one report every five minutes is enough to be told.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo812/env.sh; backend $WT; for i in 1 2 3; do deliver whsec_demo_rotated; done; traces; stop
```

```output
answered 400 {"detail":"Invalid Stripe webhook signature or payload"}
answered 400 {"detail":"Invalid Stripe webhook signature or payload"}
answered 400 {"detail":"Invalid Stripe webhook signature or payload"}
log lines from the webhook: 3
  3x app.api.endpoints.webhooks - ERROR - Stripe webhook refused a delivery: its signature or payload did not verify
reports sent to Sentry: 1
  error | fingerprint ['stripe-webhook', 'signature'] | Stripe webhook refused a delivery: its signature or payload did not verify
  the customer id: in neither the log nor a report
  the payer's email: in neither the log nor a report
  the signature: in neither the log nor a report
```

An event for a customer nobody has, correctly signed. Main answers 200 and logs a warning that names the customer. The branch logs an error and reports it, naming the event to resend from the Stripe dashboard, and not the customer.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo812/env.sh; echo 'main:'; backend $MAIN; deliver $SIGNING; traces; echo; echo 'branch:'; backend $WT; deliver $SIGNING; traces; stop
```

```output
main:
answered 200 {"status":"no_matching_user"}
log lines from the webhook: 1
  1x app.api.endpoints.webhooks - WARNING - Stripe customer.subscription.updated for customer cus_DEMO_CUSTOMER matches no user
reports sent to Sentry: 0
  the customer id: in the log
  the payer's email: in neither the log nor a report
  the signature: in neither the log nor a report

branch:
answered 200 {"status":"no_matching_user"}
log lines from the webhook: 1
  1x app.api.endpoints.webhooks - ERROR - Stripe customer.subscription.updated matches no user (event evt_demo_unmatched): resend it once the user is linked
reports sent to Sentry: 1
  error | fingerprint ['stripe-webhook', 'no-matching-user'] | Stripe customer.subscription.updated matches no user (event evt_demo_unmatched): resend it once the user is li
  the customer id: in neither the log nor a report
  the payer's email: in neither the log nor a report
  the signature: in neither the log nor a report
```

No signing secret configured. The 503 is reported on both, by the Sentry SDK itself, which reports any 5xx a route raises. On main there is no log line, and that report carries the delivery's Stripe-Signature header with the rest of the request's headers. On the branch the refusal is logged and the header is filtered.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo812/env.sh; echo 'main:'; backend $MAIN STRIPE_WEBHOOK_SECRET=; deliver $SIGNING; traces; echo; echo 'branch:'; backend $WT STRIPE_WEBHOOK_SECRET=; deliver $SIGNING; traces; stop
```

```output
main:
answered 503 {"detail":"Stripe webhook is not configured"}
log lines from the webhook: 0
reports sent to Sentry: 1
  error | fingerprint default | HTTPException: Stripe webhook is not configured
  the customer id: in neither the log nor a report
  the payer's email: in neither the log nor a report
  the signature: in a report

branch:
answered 503 {"detail":"Stripe webhook is not configured"}
log lines from the webhook: 1
  1x app.api.endpoints.webhooks - ERROR - Stripe webhook refused a delivery: STRIPE_WEBHOOK_SECRET is not set
reports sent to Sentry: 1
  error | fingerprint default | HTTPException: Stripe webhook is not configured
  the customer id: in neither the log nor a report
  the payer's email: in neither the log nor a report
  the signature: in neither the log nor a report
```

A request with no signature at all is not Stripe. On the branch it is answered and nothing more.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo812/env.sh; backend $WT; deliver none; traces | head -2; stop
```

```output
answered 400 {"detail":"Missing Stripe-Signature header"}
log lines from the webhook: 0
reports sent to Sentry: 0
```

The same behaviour as tests, with real signatures and the real Sentry SDK.

```bash
cd /home/frankbria/projects/worktrees/issue-812-stripe-webhook-logs/backend && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo812 uv run pytest tests/test_api/test_stripe_webhook_reporting.py -q -p no:cacheprovider --no-cov 2>&1 | tail -1 | sed -E 's/ in [0-9.]*s//; s/, [0-9]+ warnings?//'
```

```output
======================== 9 passed =========================
```
