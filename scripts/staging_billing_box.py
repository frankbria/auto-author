"""The box side of the staging billing check: what needs the box's own keys.

staging-billing-check.yml runs scripts/staging_billing_check.py on the runner.
That script uses staging the way a customer does, over HTTPS. The few steps a
customer can't take (marking the new account's email verified, paying with
Stripe's test card, cancelling) run here, inside the running backend container,
which already holds the Stripe key and the database URI. So no key leaves the
box, and none is printed:

    docker exec -i auto-author-backend-1 python - COMMAND ARGS... < this file

Every command refuses a live Stripe key and any environment but staging, and
acts only on the check's own throwaway account: an email of the form
delivered+billing-check-<run>@resend.dev (Resend's test inbox, so the
verification email sent at sign-up goes nowhere), and Stripe objects whose
customer has that email. It prints one JSON line, or "BOX FAILED: reason".
"""

import json
import os
import re
import sys
import time

CHECK_EMAIL = re.compile(r"^delivered\+billing-check-[a-z0-9]{6,40}@resend\.dev$")
PATTERNS = {
    "email": CHECK_EMAIL,
    "session": re.compile(r"^cs_test_[A-Za-z0-9]{8,200}$"),
    "customer": re.compile(r"^cus_[A-Za-z0-9]{8,40}$"),
    "subscription": re.compile(r"^sub_[A-Za-z0-9]{8,40}$"),
    "draft_key": re.compile(r"^[a-f0-9]{24}:[A-Za-z0-9_-]{1,40}$"),
    "since": re.compile(r"^[0-9]{10}$"),
}
# Each command and what its arguments must look like, in order.
COMMANDS = {
    "mode": [],
    "verify-email": ["email"],
    "seed-draft": ["email", "draft_key"],
    "checkout": ["email", "session"],
    "subscribe": ["email", "customer"],
    "cancel-at-period-end": ["email", "subscription"],
    "cancel": ["email", "subscription"],
    "deliveries": ["email", "customer", "since"],
    "cleanup": ["email"],
}
SUBSCRIPTION_EVENTS = [
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
]


class Refused(Exception):
    pass


def out(**facts):
    print(json.dumps(facts, sort_keys=True))


def stripe_key():
    key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not key:
        raise Refused("STRIPE_SECRET_KEY is not set in the backend container")
    if not key.startswith(("sk_test_", "rk_test_")):
        # The check buys and cancels a subscription: never with real money.
        raise Refused("the box's Stripe key is not a test-mode key; this check runs only against the sandbox")
    if os.environ.get("ENVIRONMENT") != "staging":
        raise Refused("ENVIRONMENT is not staging")
    return key


def users():
    from pymongo import MongoClient

    uri = os.environ.get("MONGODB_URI") or os.environ.get("DATABASE_URL")
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    return client[os.environ["DATABASE_NAME"]]


def as_dict(obj):
    return obj.to_dict() if hasattr(obj, "to_dict") else obj


def own_customer(stripe, key, email, customer_id):
    """The customer, refused unless it belongs to the check's account."""
    customer = as_dict(stripe.Customer.retrieve(customer_id, api_key=key))
    if customer.get("deleted") or customer.get("email") != email:
        raise Refused(f"{customer_id} is not the check's customer")
    return customer


def own_subscription(stripe, key, email, subscription_id):
    subscription = as_dict(stripe.Subscription.retrieve(subscription_id, api_key=key))
    own_customer(stripe, key, email, subscription["customer"])
    return subscription


def cmd_mode(stripe, key):
    endpoints = []
    try:
        for endpoint in stripe.WebhookEndpoint.list(api_key=key, limit=100).auto_paging_iter():
            e = as_dict(endpoint)
            if e.get("url", "").endswith("/api/v1/webhooks/stripe"):
                events = e.get("enabled_events") or []
                endpoints.append(
                    {
                        "url": e["url"],
                        "status": e.get("status"),
                        "sends_subscription_events": "*" in events
                        or all(name in events for name in SUBSCRIPTION_EVENTS),
                    }
                )
    except stripe.StripeError as exc:
        endpoints = f"could not list webhook endpoints: {exc.user_message or type(exc).__name__}"
    out(
        key_mode="test",
        environment="staging",
        price_id=os.environ.get("STRIPE_PRICE_ID_PRO"),
        managed_payments=os.environ.get("STRIPE_MANAGED_PAYMENTS"),
        webhook_endpoints=endpoints,
    )


def cmd_verify_email(stripe, key, email):
    # The account a customer would verify by clicking the emailed link.
    result = users()["users"].update_one({"email": email, "emailVerified": False}, {"$set": {"emailVerified": True}})
    if result.matched_count != 1:
        raise Refused("no unverified account with the check's email")
    out(verified=True)


def cmd_seed_draft(stripe, key, email, draft_key):
    # What the app records after the trial's one AI draft, without paying for the
    # model call: the next draft of another chapter must then be refused.
    result = users()["users"].update_one({"email": email}, {"$set": {"trial_draft_chapters": [draft_key]}})
    if result.matched_count != 1:
        raise Refused("no account with the check's email")
    out(seeded=draft_key)


def cmd_checkout(stripe, key, email, session_id):
    session = as_dict(stripe.checkout.Session.retrieve(session_id, api_key=key, expand=["line_items"]))
    own_customer(stripe, key, email, session["customer"])
    items = (session.get("line_items") or {}).get("data") or []
    facts = {
        "mode": session.get("mode"),
        "status": session.get("status"),
        "currency": session.get("currency"),
        "amount_subtotal": session.get("amount_subtotal"),
        "price_ids": [((item.get("price") or {}).get("id")) for item in items],
        "customer": session["customer"],
        "managed_payments": session.get("managed_payments"),
        "livemode": session.get("livemode"),
    }
    # Close it, so the check leaves no payable checkout behind.
    if session.get("status") == "open":
        stripe.checkout.Session.expire(session_id, api_key=key)
        facts["expired_after_reading"] = True
    out(**facts)


def cmd_subscribe(stripe, key, email, customer_id):
    """Pay for Pro with Stripe's test Visa token, as checkout would have."""
    customer = own_customer(stripe, key, email, customer_id)
    auth_id = (customer.get("metadata") or {}).get("auth_id")
    if not auth_id:
        raise Refused(f"{customer_id} has no auth_id; the app did not create it")
    price = os.environ.get("STRIPE_PRICE_ID_PRO", "")
    method = as_dict(stripe.PaymentMethod.attach("pm_card_visa", customer=customer_id, api_key=key))
    subscription = as_dict(
        stripe.Subscription.create(
            api_key=key,
            customer=customer_id,
            items=[{"price": price, "quantity": 1}],
            default_payment_method=method["id"],
            # What checkout stamps, so the webhook finds the user the same way.
            metadata={"auth_id": auth_id, "source": "staging-billing-check"},
            payment_behavior="error_if_incomplete",
            expand=["latest_invoice"],
        )
    )
    invoice = subscription.get("latest_invoice") or {}
    out(
        subscription=subscription["id"],
        status=subscription.get("status"),
        amount_paid=invoice.get("amount_paid"),
        currency=invoice.get("currency"),
        tax=invoice.get("tax"),
    )


def cmd_cancel_at_period_end(stripe, key, email, subscription_id):
    """What Manage billing's Cancel does: the portal cancels at period end."""
    own_subscription(stripe, key, email, subscription_id)
    subscription = as_dict(stripe.Subscription.modify(subscription_id, cancel_at_period_end=True, api_key=key))
    out(status=subscription.get("status"), cancel_at_period_end=subscription.get("cancel_at_period_end"))


def cmd_cancel(stripe, key, email, subscription_id):
    """End it now, as the end of the paid period would."""
    own_subscription(stripe, key, email, subscription_id)
    subscription = as_dict(stripe.Subscription.cancel(subscription_id, api_key=key))
    out(status=subscription.get("status"))


def cmd_deliveries(stripe, key, email, customer_id, since):
    """The check's subscription events, once Stripe has delivered each to every
    endpoint with a 2xx (pending_webhooks counts the endpoints still owed one)."""
    own_customer(stripe, key, email, customer_id)
    deadline = time.time() + 120
    while True:
        events = []
        listed = stripe.Event.list(api_key=key, types=SUBSCRIPTION_EVENTS, created={"gte": int(since)}, limit=100)
        for event in listed.auto_paging_iter():
            e = as_dict(event)
            if ((e.get("data") or {}).get("object") or {}).get("customer") == customer_id:
                events.append({"type": e["type"], "pending_webhooks": e.get("pending_webhooks")})
        if events and all(e["pending_webhooks"] == 0 for e in events) or time.time() > deadline:
            out(events=list(reversed(events)))
            return
        time.sleep(5)


def cmd_cleanup(stripe, key, email):
    """Cancel and delete the check's Stripe customers; remove an account that
    never got as far as being verified. A verified account is deleted through
    the app instead (DELETE /users/me), and is only reported here if it is left."""
    customers = 0
    for customer in stripe.Customer.list(email=email, api_key=key, limit=100).auto_paging_iter():
        c = as_dict(customer)
        for subscription in stripe.Subscription.list(customer=c["id"], status="all", api_key=key).auto_paging_iter():
            s = as_dict(subscription)
            if s.get("status") not in ("canceled", "incomplete_expired"):
                stripe.Subscription.cancel(s["id"], api_key=key)
        stripe.Customer.delete(c["id"], api_key=key)
        customers += 1
    db = users()
    removed = 0
    for doc in db["users"].find({"email": email, "emailVerified": False}, {"_id": 1}):
        for collection in ("account", "session"):
            db[collection].delete_many({"userId": {"$in": [doc["_id"], str(doc["_id"])]}})
        db["users"].delete_one({"_id": doc["_id"]})
        removed += 1
    left = db["users"].count_documents({"email": email, "deleted_at": {"$exists": False}})
    out(stripe_customers_deleted=customers, unverified_accounts_removed=removed, accounts_left=left)


def main(argv):
    if len(argv) < 2 or argv[1] not in COMMANDS:
        raise Refused(f"usage: COMMAND ARGS..., COMMAND one of {', '.join(COMMANDS)}")
    command, args = argv[1], argv[2:]
    kinds = COMMANDS[command]
    if len(args) != len(kinds):
        raise Refused(f"{command} takes {len(kinds)} argument(s)")
    for kind, value in zip(kinds, args):
        if not PATTERNS[kind].match(value):
            raise Refused(f"{command}: the {kind} argument is not one this check may touch")
    key = stripe_key()
    import stripe

    handler = globals()["cmd_" + command.replace("-", "_")]
    try:
        handler(stripe, key, *args)
    except stripe.StripeError as exc:
        raise Refused(f"Stripe refused {command}: {exc.user_message or exc}") from None


if __name__ == "__main__":
    try:
        main(sys.argv)
    except Refused as exc:
        print(f"BOX FAILED: {exc}")
        sys.exit(1)
