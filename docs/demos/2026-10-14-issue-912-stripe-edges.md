# Issue #912: Stripe billing edges after #768

*2026-10-14T18:50:51Z by Showboat 0.6.1*
<!-- showboat-id: b215deb6-1040-47a2-a64a-7f6bd17b5543 -->

Signed webhooks through the real endpoint and real MongoDB; checkout through the real route with Stripe's SDK stubbed (the paid external API). Each test failed before its fix.

```bash
cd backend && TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-demo912 ENVIRONMENT=test uv run pytest tests/test_api/test_stripe_webhook_subscription_edges.py tests/test_api/test_billing_checkout_tabs.py -q -p no:cacheprovider -v 2>&1 | grep -E "PASSED|FAILED|passed|failed" | sed -E "s/ +\[ *[0-9]+%\]//; s/^tests\/test_api\///"
```

```output
test_stripe_webhook_subscription_edges.py::TestEachSubscriptionHasItsOwnWatermark::test_a_new_subscription_older_than_the_last_deletion_is_applied PASSED
test_stripe_webhook_subscription_edges.py::TestEachSubscriptionHasItsOwnWatermark::test_a_late_event_for_the_deleted_subscription_still_cannot_revive_it PASSED
test_stripe_webhook_subscription_edges.py::TestEachSubscriptionHasItsOwnWatermark::test_an_older_event_for_the_same_subscription_is_still_stale PASSED
test_stripe_webhook_subscription_edges.py::TestTheCurrentSubscriptionIsDecidedByTheWrite::test_two_first_events_for_different_subscriptions_do_not_both_land PASSED
test_billing_checkout_tabs.py::test_a_second_checkout_closes_the_first PASSED
test_billing_checkout_tabs.py::test_a_checkout_after_one_already_paid_is_refused PASSED
test_billing_checkout_tabs.py::test_a_first_checkout_closes_nothing PASSED
test_billing_checkout_tabs.py::test_a_paused_subscriber_is_sent_to_resume_it PASSED
test_billing_checkout_tabs.py::test_a_paid_checkout_from_before_a_cancellation_does_not_block_a_new_one PASSED
test_billing_checkout_tabs.py::test_a_stripe_error_after_the_swap_keeps_the_earlier_checkout_recorded PASSED
============================== 10 passed in 1.09s ==============================
```

Mutation check (scratch script, each reverted and asserted clean), each caught by name: one watermark per user again; the write not checking the current subscription; the settled checkout not cleared by the webhook; the earlier open checkout left payable; the earlier checkout dropped on a Stripe error; a paused subscriber allowed to check out.
