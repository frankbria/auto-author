"""Staging billing check: the launch runbook's steps 57 to 64, run by a machine.

Run by staging-billing-check.yml on the runner, with the ssh command that
reaches the box after `--`:

    python3 scripts/staging_billing_check.py -- ssh -i KEY -o ... user@box

It makes a throwaway account and uses staging over HTTPS the way a customer
does, with Stripe's sandbox only:

  57  the free trial's limits and the $49 renewal terms the billing page shows
  58  export refused on the trial, with the upgrade message
  59  a second chapter's AI draft refused (the first is recorded, not generated,
      so no model call is paid for)
  60  Upgrade to Pro opens a $49.00 USD subscription checkout on the Pro price
  61  paying with Stripe's test Visa token makes the account Pro (the webhook is
      the only thing that changes the plan)
  62  export works on Pro
  63  Manage billing opens; cancel at period end keeps Pro, the end of the
      subscription drops it to the trial, and Stripe delivered every
      subscription event to the webhook with a 2xx
  then deletes the account and its Stripe customer, also after a failure.

What it can't check is the Checkout page itself: Stripe's hosted page is built
in the browser and can't be filled in by a script, so the payment is made with
the API on the customer the app's checkout created. The page's Link branding
and its tax line are a human's to see.

Standard library only. The steps that need the box's keys (verify the email,
pay, cancel, read Stripe's deliveries) run in the backend container through
scripts/staging_billing_box.py; see there.
"""

import json
import os
import re
import secrets
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HELPER = Path(__file__).resolve().with_name("staging_billing_box.py")
CONTAINER = "auto-author-backend-1"
SESSION_COOKIE = "__Secure-better-auth.session_token"
RENEWAL_TERMS = "Auto Author Pro is $49.00 per month plus any applicable tax"
EXPORT_REFUSED = "Exporting your book is part of Pro"
DRAFT_REFUSED = "The free trial includes an AI draft of one chapter"


class Failed(Exception):
    pass


def expect(condition, message):
    if not condition:
        raise Failed(message)


class Box:
    """Runs one staging_billing_box.py command in the backend container."""

    def __init__(self, ssh):
        self.ssh = ssh

    def __call__(self, command, *args):
        remote = f"docker exec -i {CONTAINER} python - " + " ".join(shlex.quote(a) for a in (command, *args))
        with HELPER.open("rb") as script:
            done = subprocess.run([*self.ssh, remote], stdin=script, capture_output=True, timeout=300, check=False)
        lines = done.stdout.decode(errors="replace").strip().splitlines()
        last = lines[-1] if lines else ""
        if done.returncode != 0 or not last.startswith("{"):
            raise Failed(f"box {command}: {last or 'no output'} (exit {done.returncode})")
        return json.loads(last)


class Response:
    def __init__(self, status, headers, body):
        self.status, self.headers, self.body = status, headers, body

    def json(self):
        return json.loads(self.body or b"null")

    @property
    def text(self):
        return self.body.decode(errors="replace")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Http:
    """A tiny client: JSON in, the status, headers and body out, never an exception for a 4xx."""

    def __init__(self, origin, hosts):
        self.origin = origin
        # The session goes only to staging's own hosts, never to Stripe, and never
        # on a request that follows redirects (urllib would carry it along).
        self.hosts = set(hosts)
        self.cookie = None
        self._plain = urllib.request.build_opener(_NoRedirect)
        self._follow = urllib.request.build_opener()

    def __call__(self, method, url, body=None, follow=False):
        headers = {"Accept": "application/json", "Origin": self.origin, "User-Agent": "auto-author-billing-check"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if self.cookie and not follow and urllib.parse.urlsplit(url).hostname in self.hosts:
            headers["Cookie"] = self.cookie
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with (self._follow if follow else self._plain).open(request, timeout=120) as reply:
                return Response(reply.status, reply.headers, reply.read())
        except urllib.error.HTTPError as error:
            return Response(error.code, error.headers, error.read())


def session_cookie(response):
    for header in response.headers.get_all("Set-Cookie") or []:
        pair = header.split(";", 1)[0]
        if pair.startswith(SESSION_COOKIE + "="):
            return pair
    return None


def wait_for(read, done, seconds, sleep):
    """read() until done(value) or the time runs out; returns the last value."""
    for _ in range(max(1, seconds // 3)):
        value = read()
        if done(value):
            return value
        sleep(3)
    return value


class Check:
    def __init__(self, http, box, app, api, say=print, sleep=time.sleep, now=time.time):
        self.http, self.box, self.app = http, box, app.rstrip("/")
        api = api.rstrip("/")
        self.api = api if api.endswith("/api/v1") else api + "/api/v1"
        self.say, self.sleep, self.now = say, sleep, now
        self.email = f"delivered+billing-check-{secrets.token_hex(6)}@resend.dev"
        self.signed_up = False
        self.subscription = None
        self.cancelled = False
        self.passed = []

    def ok(self, step, detail):
        self.passed.append(step)
        self.say(f"PASS {step}: {detail}")

    def me(self):
        response = self.http("GET", f"{self.api}/users/me")
        expect(response.status == 200, f"GET /users/me answered {response.status}")
        return response.json()

    def export(self, book):
        return self.http("GET", f"{self.api}/books/{book}/export/pdf?include_empty_chapters=true")

    def run(self):
        mode = self.box("mode")
        price = mode.get("price_id")
        expect(mode.get("key_mode") == "test", "the box's Stripe key is not in test mode")
        expect(bool(price), "STRIPE_PRICE_ID_PRO is not set on the box")
        hooks = mode.get("webhook_endpoints")
        self.say(f"staging sells {price}, managed payments {mode.get('managed_payments')}, webhook endpoints {hooks}")

        # A new account, as the sign-up page makes one.
        password = "Bc1" + secrets.token_urlsafe(18)
        response = self.http(
            "POST", f"{self.app}/api/auth/sign-up/email",
            {"name": "Billing Check", "email": self.email, "password": password},
        )
        expect(response.status == 200, f"sign-up answered {response.status}: {response.text[:300]}")
        self.signed_up = True
        self.box("verify-email", self.email)
        response = self.http("POST", f"{self.app}/api/auth/sign-in/email", {"email": self.email, "password": password})
        expect(response.status == 200, f"sign-in answered {response.status}: {response.text[:300]}")
        cookie = session_cookie(response)
        expect(cookie is not None, f"sign-in set no {SESSION_COOKIE} cookie")
        self.http.cookie = cookie
        me = self.me()
        expect(me.get("plan") == "free", f"a new account is on {me.get('plan')!r}, not free")
        self.say("a fresh account is signed in, on the free trial")

        # 57: the trial and the renewal terms the billing page shows.
        quotas = self.http("GET", f"{self.api}/billing/quotas")
        expect(quotas.status == 200, f"GET /billing/quotas answered {quotas.status}")
        free, pro = quotas.json()["free"], quotas.json()["pro"]
        expect(free.get("total") == 30, f"the trial allows {free.get('total')} AI generations, not 30")
        expect(free.get("draft_chapters") == 1, f"the trial drafts {free.get('draft_chapters')} chapters, not 1")
        expect(free.get("export") is False, "the trial is allowed to export")
        expect(pro.get("export") is True, "Pro is not allowed to export")
        disclosure = self.http("GET", f"{self.api}/billing/disclosure")
        expect(disclosure.status == 200, f"GET /billing/disclosure answered {disclosure.status}: {disclosure.text[:300]}")
        terms = disclosure.json()
        expect(terms["text"].startswith(RENEWAL_TERMS), f"the renewal terms read: {terms['text'][:120]!r}")
        expect(terms.get("price_id") == price, f"the terms are for {terms.get('price_id')}, not {price}")
        self.ok("57", f"free trial is 30 AI generations, one chapter draft, no export; terms say {RENEWAL_TERMS!r}")

        # 58: a book with a table of contents, and export refused.
        response = self.http("POST", f"{self.api}/books/", {"title": "Billing check"})
        expect(response.status == 201, f"creating a book answered {response.status}: {response.text[:300]}")
        book = response.json()["id"]
        chapters = [
            {"id": f"ch-{n}", "title": f"Chapter {n}", "description": "", "level": 1, "order": n, "subchapters": []}
            for n in (1, 2)
        ]
        response = self.http("PUT", f"{self.api}/books/{book}/toc", {"toc": {"chapters": chapters}})
        expect(response.status == 200, f"saving the table of contents answered {response.status}: {response.text[:300]}")
        # The server gives every new chapter its own id (#754); use the stored ones.
        first, second = [c["id"] for c in response.json()["toc"]["chapters"]][:2]
        response = self.export(book)
        expect(response.status == 402, f"export on the trial answered {response.status}, not 402")
        expect(EXPORT_REFUSED in response.text, f"the refusal reads: {response.text[:300]}")
        self.ok("58", f"export refused with 402 and {EXPORT_REFUSED!r}")

        # 59: the trial's one draft is used on chapter 1; chapter 2 is refused.
        self.box("seed-draft", self.email, f"{book}:{first}")
        response = self.http(
            "POST", f"{self.api}/books/{book}/chapters/{second}/generate-draft",
            {"question_responses": [{"question": "What is this?", "answer": "A billing check."}]},
        )
        expect(response.status == 402, f"a second chapter's draft answered {response.status}, not 402")
        expect(DRAFT_REFUSED in response.text, f"the refusal reads: {response.text[:300]}")
        self.ok("59", "a second chapter's AI draft refused with 402, before any model call")

        # 60: Upgrade to Pro, after agreeing to the terms shown.
        response = self.http(
            "POST", f"{self.api}/billing/checkout",
            {"plan": "pro", "accept_renewal_terms": True, "disclosure_sha256": terms["sha256"]},
        )
        expect(response.status == 200, f"checkout answered {response.status}: {response.text[:300]}")
        url = response.json()["url"]
        match = re.search(r"cs_test_[A-Za-z0-9]+", url)
        expect(url.startswith("https://checkout.stripe.com/") and match, "checkout did not return a sandbox Checkout page")
        page = self.http("GET", url, follow=True)
        expect(page.status == 200, f"the Checkout page answered {page.status}")
        session = self.box("checkout", self.email, match.group(0))
        expect(session.get("mode") == "subscription", f"checkout is {session.get('mode')}, not a subscription")
        expect(session.get("livemode") is False, "checkout is in live mode")
        expect(session.get("currency") == "usd", f"checkout is in {session.get('currency')}")
        expect(session.get("amount_subtotal") == 4900, f"checkout is for {session.get('amount_subtotal')} cents, not 4900")
        expect(session.get("price_ids") == [price], f"checkout sells {session.get('price_ids')}, not {price}")
        customer = session["customer"]
        self.ok("60", f"Upgrade to Pro opens Stripe Checkout: $49.00 USD a month on {price}, "
                f"managed payments {session.get('managed_payments')}")

        # 61: pay, and the webhook makes the account Pro.
        since = int(self.now()) - 120
        paid = self.box("subscribe", self.email, customer)
        self.subscription = paid["subscription"]
        expect(paid.get("status") == "active", f"the subscription is {paid.get('status')}, not active")
        expect(paid.get("amount_paid") == 4900, f"the first invoice took {paid.get('amount_paid')} cents, not 4900")
        me = wait_for(self.me, lambda m: m.get("plan") == "pro", 90, self.sleep)
        expect(me.get("plan") == "pro", f"90 seconds after paying the account is on {me.get('plan')!r}")
        expect(me.get("stripe_subscription_id") == self.subscription, "the account holds another subscription")
        self.ok("61", "paid $49.00 with the test Visa; the webhook made the account Pro")

        # 62: export now works.
        response = self.export(book)
        expect(response.status == 200, f"export on Pro answered {response.status}: {response.text[:300]}")
        expect(response.body.startswith(b"%PDF"), "export on Pro did not return a PDF")
        self.ok("62", f"PDF export works on Pro ({len(response.body)} bytes)")

        # 63: Manage billing, then cancel.
        response = self.http("POST", f"{self.api}/billing/portal")
        expect(response.status == 200, f"Manage billing answered {response.status}: {response.text[:300]}")
        expect(response.json()["url"].startswith("https://billing.stripe.com/"), "Manage billing did not open Stripe's portal")
        ending = self.box("cancel-at-period-end", self.email, self.subscription)
        expect(ending.get("cancel_at_period_end") is True, "the subscription is not set to end")
        self.sleep(10)
        expect(self.me().get("plan") == "pro", "cancelling at period end ended Pro early")
        self.box("cancel", self.email, self.subscription)
        self.cancelled = True
        me = wait_for(self.me, lambda m: m.get("plan") == "free", 90, self.sleep)
        expect(me.get("plan") == "free", f"90 seconds after the subscription ended the account is on {me.get('plan')!r}")
        expect(me.get("stripe_subscription_id") is None, "the ended subscription is still on the account")
        response = self.export(book)
        expect(response.status == 402, f"export after cancelling answered {response.status}, not 402")
        deliveries = self.box("deliveries", self.email, customer, str(since))["events"]
        kinds = {e["type"] for e in deliveries}
        for kind in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
            expect(kind in kinds, f"Stripe sent no {kind} for the check's subscription")
        owed = [e["type"] for e in deliveries if e["pending_webhooks"] != 0]
        expect(not owed, f"Stripe has not had a 2xx from the webhook for: {', '.join(owed)}")
        self.ok("63", f"Manage billing opens; cancel at period end keeps Pro, the end drops to the trial; "
                f"{len(deliveries)} subscription events all delivered with a 2xx")

    def cleanup(self):
        """Always runs. Each part is tried even if an earlier one fails."""
        problems = []
        # A transport error (staging or the box unreachable) is recorded, never
        # allowed to skip the parts after it.
        if self.subscription and not self.cancelled:
            try:
                self.box("cancel", self.email, self.subscription)
            except Exception as exc:
                problems.append(f"cancelling the subscription: {exc}")
        if self.http.cookie:
            try:
                response = self.http("DELETE", f"{self.api}/users/me")
                if response.status != 200:
                    problems.append(f"deleting the account answered {response.status}")
            except Exception as exc:
                problems.append(f"deleting the account: {exc}")
        if self.signed_up:
            try:
                left = self.box("cleanup", self.email)
                if left.get("accounts_left"):
                    problems.append("the check's account is still on staging")
            except Exception as exc:
                problems.append(f"box cleanup: {exc}")
        for problem in problems:
            self.say(f"CLEANUP: {problem}")
        return problems


def main(argv):
    if "--" not in argv or argv.index("--") == len(argv) - 1:
        print("usage: staging_billing_check.py -- SSH COMMAND...")
        return 2
    ssh = argv[argv.index("--") + 1:]
    # From the staging environment's variables, as the image build reads them.
    app, api = os.environ.get("APP_URL", ""), os.environ.get("API_URL", "")
    if not (app.startswith("https://") and api.startswith("https://")):
        print("APP_URL and API_URL must be set to staging's https addresses")
        return 2
    hosts = [urllib.parse.urlsplit(u).hostname for u in (app, api)]
    check = Check(Http(app, hosts), Box(ssh), app, api)
    failure = None
    try:
        check.run()
    except Exception as exc:  # a Failed check, or staging or the box out of reach
        failure = str(exc) if isinstance(exc, Failed) else f"{type(exc).__name__}: {exc}"
        print(f"FAIL after {', '.join(check.passed) or 'no step'}: {failure}")
    finally:
        problems = check.cleanup()
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write("## Staging billing check (runbook steps 57 to 63)\n")
            fh.write(f"- passed: {', '.join(check.passed) or 'none'}\n")
            fh.write(f"- failed: {failure}\n" if failure else "- failed: none\n")
            fh.write(f"- cleanup: {'; '.join(problems) if problems else 'account and Stripe customer removed'}\n")
    if failure or problems:
        return 1
    print("ALL PASSED: steps 57 to 63")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
