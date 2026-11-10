"""The staging billing check (runbook steps 57 to 64) and its box-side helper.

The helper runs against a stub `stripe` module, the check against a fake
staging that answers as the app does. Neither needs a network or a key.

Run: uvx --with pytest --with pyyaml pytest scripts/test_staging_billing_check.py -q
"""

import json
import subprocess
import sys
import textwrap
from email.message import Message
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import staging_billing_check as check  # noqa: E402

HELPER = Path(__file__).resolve().parent / "staging_billing_box.py"
WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "staging-billing-check.yml"
EMAIL = "delivered+billing-check-a1b2c3d4e5f6@resend.dev"
PRICE = "price_1AbCdEfGhIjKlMnO"

STUB = textwrap.dedent(
    """
    import json, os
    from types import SimpleNamespace as NS

    class StripeError(Exception):
        user_message = None

    class Obj(dict):
        def to_dict(self):
            return dict(self)

    class Listing:
        def __init__(self, items):
            self.items = items
        def auto_paging_iter(self):
            return iter(self.items)

    class Customer:
        @staticmethod
        def retrieve(customer_id, api_key):
            return Obj(json.loads(os.environ["STUB_CUSTOMER"]))

    class Subscription:
        @staticmethod
        def retrieve(subscription_id, api_key):
            return Obj(id=subscription_id, customer="cus_1AbCdEfGhIj")
        @staticmethod
        def cancel(subscription_id, api_key):
            print("CANCELLED " + subscription_id)
            return Obj(status="canceled")

    class WebhookEndpoint:
        @staticmethod
        def list(api_key, limit):
            return Listing([Obj(url="https://api.example/api/v1/webhooks/stripe", status="enabled",
                                enabled_events=["customer.subscription.created", "customer.subscription.updated",
                                                "customer.subscription.deleted"])])
    """
)


@pytest.fixture
def box(tmp_path):
    (tmp_path / "stripe.py").write_text(STUB)

    def _run(*args, key="sk_test_placeholder", environment="staging", customer_email=EMAIL):
        env = {
            "PYTHONPATH": str(tmp_path),
            "STRIPE_SECRET_KEY": key,
            "ENVIRONMENT": environment,
            "STRIPE_PRICE_ID_PRO": PRICE,
            "STUB_CUSTOMER": json.dumps({"id": "cus_1AbCdEfGhIj", "email": customer_email}),
        }
        # Same shape as the workflow: the script on stdin, the command as arguments.
        return subprocess.run(
            [sys.executable, "-", *args], stdin=HELPER.open(), env=env, capture_output=True, text=True, check=False
        )

    return _run


def test_the_helper_reports_the_mode_without_the_key(box):
    result = box("mode", key="sk_test_DO_NOT_PRINT")

    assert result.returncode == 0, result.stdout + result.stderr
    facts = json.loads(result.stdout.splitlines()[-1])
    assert facts["key_mode"] == "test" and facts["price_id"] == PRICE
    assert facts["webhook_endpoints"][0]["sends_subscription_events"] is True
    assert "DO_NOT_PRINT" not in result.stdout + result.stderr


@pytest.mark.parametrize("key", ["sk_live_placeholder", "rk_live_placeholder", ""])
def test_the_helper_refuses_anything_but_a_sandbox_key(box, key):
    result = box("mode", key=key)

    assert result.returncode == 1
    assert result.stdout.startswith("BOX FAILED")


def test_the_helper_refuses_outside_staging(box):
    result = box("mode", environment="production")

    assert result.returncode == 1 and "not staging" in result.stdout


@pytest.mark.parametrize(
    "args",
    [
        ("cancel", "someone@example.com", "sub_1AbCdEfGhIj"),  # a real customer's address
        ("cancel", "delivered+billing-check-ABC123@resend.dev", "sub_1AbCdEfGhIj"),
        ("cancel", EMAIL, "sub_1AbCdEfGhIj; id"),
        ("checkout", EMAIL, "cs_live_1AbCdEfGhIj"),
        ("verify-email", EMAIL, "extra"),
        ("drop-database",),
    ],
)
def test_the_helper_refuses_arguments_outside_its_own_account(box, args):
    result = box(*args)

    assert result.returncode == 1 and result.stdout.startswith("BOX FAILED"), result.stdout
    assert "CANCELLED" not in result.stdout


def test_the_helper_never_touches_another_customers_subscription(box):
    result = box("cancel", EMAIL, "sub_1AbCdEfGhIj", customer_email="a.real.customer@example.com")

    assert result.returncode == 1 and "not the check's customer" in result.stdout
    assert "CANCELLED" not in result.stdout


def test_the_helper_cancels_the_checks_own_subscription(box):
    result = box("cancel", EMAIL, "sub_1AbCdEfGhIj")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "CANCELLED sub_1AbCdEfGhIj" in result.stdout


# --- The check, against a fake staging ------------------------------------------------------


def _response(status, body=None, cookie=None, raw=None):
    headers = Message()
    if cookie:
        headers["Set-Cookie"] = f"{check.SESSION_COOKIE}={cookie}; Path=/; Secure; HttpOnly"
    payload = raw if raw is not None else json.dumps(body).encode()
    return check.Response(status, headers, payload)


class FakeStaging:
    """Answers as staging does; `breaks` names a behaviour to get wrong."""

    def __init__(self, breaks=None):
        self.breaks = breaks
        self.cookie = None
        self.plan = "free"
        self.subscription = None
        self.customer = None
        self.account = False
        self.calls = []

    # The HTTP side.
    def __call__(self, method, url, body=None, follow=False):
        self.calls.append((method, url.split("?")[0]))
        path = url.split("/api/v1", 1)[-1].split("?")[0] if "/api/v1" in url else url
        if url.endswith("/api/auth/sign-up/email"):
            self.account = True
            return _response(200, {"user": {}})
        if url.endswith("/api/auth/sign-in/email"):
            return _response(200, {"user": {}}, cookie="token.sig")
        if path == "/users/me" and method == "GET":
            return _response(200, {"plan": self.plan, "stripe_subscription_id": self.subscription,
                                   "stripe_customer_id": self.customer})
        if path == "/users/me" and method == "DELETE":
            self.account = False
            return _response(200, {"message": "Account deactivated"})
        if path == "/billing/quotas":
            return _response(200, {"free": {"total": 30, "draft_chapters": 1, "export": False},
                                   "pro": {"total": None, "draft_chapters": None, "export": True}})
        if path == "/billing/disclosure":
            return _response(200, {"text": check.RENEWAL_TERMS + ", billed monthly.", "sha256": "abc", "price_id": PRICE})
        if path == "/books/":
            return _response(201, {"id": "a" * 24})
        if path.endswith("/toc"):
            return _response(200, {"success": True})
        if path.endswith("/export/pdf"):
            if self.plan == "pro":
                return _response(200, raw=b"%PDF-1.7 ...")
            return _response(402, {"detail": {"message": check.EXPORT_REFUSED + ". Upgrade."}})
        if path.endswith("/generate-draft"):
            return _response(402, {"detail": {"message": check.DRAFT_REFUSED + ", and you've used it."}})
        if path == "/billing/checkout":
            self.customer = "cus_1AbCdEfGhIj"
            return _response(200, {"url": "https://checkout.stripe.com/c/pay/cs_test_a1B2c3D4e5#frag"})
        if path == "/billing/portal":
            return _response(200, {"url": "https://billing.stripe.com/p/session/test_x"})
        if url.startswith("https://checkout.stripe.com/"):
            return _response(200, raw=b"<html>")
        raise AssertionError(f"unexpected {method} {url}")

    # The box side.
    def box(self, command, *args):
        self.calls.append(("box", command))
        if command == "mode":
            return {"key_mode": "test", "price_id": PRICE, "managed_payments": "true", "webhook_endpoints": []}
        if command == "checkout":
            return {"mode": "subscription", "livemode": False, "currency": "usd", "amount_subtotal": 4900,
                    "price_ids": [PRICE], "customer": self.customer, "managed_payments": {"enabled": True}}
        if command == "subscribe":
            self.subscription = "sub_1AbCdEfGhIj"
            if self.breaks != "webhook":
                self.plan = "pro"
            return {"subscription": self.subscription, "status": "active", "amount_paid": 4900}
        if command == "cancel-at-period-end":
            return {"status": "active", "cancel_at_period_end": True}
        if command == "cancel":
            self.plan, self.subscription = "free", None
            return {"status": "canceled"}
        if command == "deliveries":
            pending = 1 if self.breaks == "delivery" else 0
            return {"events": [{"type": t, "pending_webhooks": pending} for t in
                               ("customer.subscription.created", "customer.subscription.updated",
                                "customer.subscription.deleted")]}
        if command == "cleanup":
            return {"stripe_customers_deleted": 1, "unverified_accounts_removed": 0, "accounts_left": int(self.account)}
        return {}


def _run(staging):
    http = staging
    http.cookie = None
    said = []
    run = check.Check(http, staging.box, "https://app.example", "https://api.example",
                      say=said.append, sleep=lambda s: None, now=lambda: 1_800_000_000)
    failure = None
    try:
        run.run()
    except check.Failed as exc:
        failure = str(exc)
    problems = run.cleanup()
    return run, failure, problems, said


def test_every_step_passes_on_a_staging_that_works_and_the_account_is_removed():
    staging = FakeStaging()

    run, failure, problems, said = _run(staging)

    assert failure is None, failure
    assert run.passed == ["57", "58", "59", "60", "61", "62", "63"]
    assert problems == []
    assert ("DELETE", "https://api.example/api/v1/users/me") in staging.calls
    assert staging.calls[-1] == ("box", "cleanup")
    assert run.email.startswith("delivered+billing-check-") and run.email.endswith("@resend.dev")


def test_a_webhook_that_never_lands_fails_61_and_still_cancels_and_removes_everything():
    staging = FakeStaging(breaks="webhook")

    run, failure, problems, _ = _run(staging)

    assert run.passed == ["57", "58", "59", "60"]
    assert "on 'free'" in failure
    assert ("box", "cancel") in staging.calls  # the paid subscription does not outlive the check
    assert problems == [] and not staging.account


def test_an_undelivered_event_fails_63():
    run, failure, _, _ = _run(FakeStaging(breaks="delivery"))

    assert "63" not in run.passed
    assert "has not had a 2xx" in failure


def test_the_session_cookie_is_read_from_sign_in():
    assert check.session_cookie(_response(200, {}, cookie="tok.sig")) == f"{check.SESSION_COOKIE}=tok.sig"
    assert check.session_cookie(_response(200, {})) is None


def test_the_box_commands_quote_their_arguments(tmp_path, monkeypatch):
    seen = {}

    def fake_run(argv, stdin, capture_output, timeout, check):
        seen["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout=b'{"ok": true}\n', stderr=b"")

    monkeypatch.setattr(check.subprocess, "run", fake_run)
    check.Box(["ssh", "user@box"])("verify-email", "a b;id")

    assert seen["argv"][:2] == ["ssh", "user@box"]
    assert seen["argv"][2] == "docker exec -i auto-author-backend-1 python - verify-email 'a b;id'"


def test_the_workflow_checks_the_key_before_it_makes_an_account():
    wf = yaml.safe_load(WORKFLOW.read_text())
    steps = [s["name"] for s in wf["jobs"]["check"]["steps"]]
    on = wf.get(True) or wf["on"]

    assert steps.index("Pre-flight, the box's Stripe key is a sandbox key") < steps.index("Run steps 57 to 63")
    assert on["workflow_dispatch"] is None  # no inputs: nothing a caller types reaches the box
    assert wf["permissions"] == {"contents": "read"}
