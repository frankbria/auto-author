"""Check a Stripe price against the staging box's own Stripe key, before any write.

Run by set-staging-billing.yml inside the running backend container, which
already holds STRIPE_SECRET_KEY, so the key never leaves the box:

    docker exec -i auto-author-backend-1 python - PRICE_ID MANAGED_PAYMENTS < this file

It refuses (exit 1) a price the key's account and mode cannot see, such as a
live-mode price on a box with sandbox keys: checkout would fail with "No such
price" for every buyer. It also refuses a price checkout can't sell as Pro (not
active, not a flat monthly recurring USD price), and, with Managed Payments on, a
product with no tax code, which Stripe rejects at checkout. Prints only the
price's public facts, never the key.
"""

import os
import sys

import stripe


def fail(message):
    print(f"PREFLIGHT FAILED: {message}")
    sys.exit(1)


def main(argv):
    if len(argv) != 3:
        fail("usage: staging_billing_preflight.py PRICE_ID true|false")
    price_id, managed_payments = argv[1], argv[2] == "true"

    key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not key:
        fail("STRIPE_SECRET_KEY is not set in the backend container")
    key_mode = "live" if key.startswith(("sk_live_", "rk_live_")) else "test"

    try:
        price = stripe.Price.retrieve(price_id, api_key=key, expand=["product"])
    except stripe.StripeError as exc:
        # Stripe's own message says when the price exists in the other mode.
        fail(f"the box's Stripe key ({key_mode} mode) can't see {price_id}: {exc.user_message or exc}")

    price_mode = "live" if price.livemode else "test"
    if price_mode != key_mode:
        fail(f"{price_id} is a {price_mode}-mode price but the box's key is {key_mode} mode")
    if not price.active:
        fail(f"{price_id} is archived; checkout can't sell it")
    recurring = price.recurring
    if (
        price.type != "recurring"
        or recurring is None
        or recurring.interval != "month"
        or getattr(recurring, "interval_count", 1) != 1
    ):
        fail(f"{price_id} is not a monthly recurring price (every 1 month)")
    # Checkout sends quantity 1, which Stripe refuses for a metered price, and
    # a tiered price has no single amount to show the buyer.
    if getattr(recurring, "usage_type", "licensed") != "licensed":
        fail(f"{price_id} is metered; checkout sells a fixed monthly price")
    if getattr(price, "billing_scheme", "per_unit") != "per_unit" or price.unit_amount is None:
        fail(f"{price_id} is not a flat per-unit price")
    if price.currency != "usd":
        fail(f"{price_id} is in {price.currency}, not usd")

    product = price.product
    if not product.active:
        fail(f"{price_id} belongs to an archived product")
    if managed_payments and not product.tax_code:
        fail(f"product '{product.name}' has no tax code; Managed Payments checkout would be rejected")

    amount = f"${price.unit_amount / 100:.2f}"
    print(
        f"PREFLIGHT OK: {price_id} is {amount}/month (usd) on '{product.name}', "
        f"tax code {product.tax_code or 'none'}, {price_mode} mode"
    )


if __name__ == "__main__":
    main(sys.argv)
