"""The staging billing pre-flight refuses any price checkout couldn't sell.

set-staging-billing.yml runs scripts/staging_billing_preflight.py inside the
backend container before it writes .env. These tests run it against a stub
`stripe` module, so they need no network and no key.
"""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parent / "staging_billing_preflight.py"
WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "set-staging-billing.yml"

STUB = textwrap.dedent(
    '''
    import json, os
    from types import SimpleNamespace as NS

    class StripeError(Exception):
        user_message = None

    class Price:
        @staticmethod
        def retrieve(price_id, api_key, expand):
            spec = json.loads(os.environ["STUB_PRICE"])
            if spec is None:
                raise StripeError(f"No such price: '{price_id}'; a similar object exists in live mode, but a test mode key was used to make this request.")
            product = NS(**spec.pop("product"))
            recurring = NS(**spec.pop("recurring")) if spec.get("recurring") else None
            spec.pop("recurring", None)
            return NS(product=product, recurring=recurring, **spec)
    '''
)

GOOD = {
    "livemode": False,
    "active": True,
    "type": "recurring",
    "recurring": {"interval": "month"},
    "currency": "usd",
    "unit_amount": 4900,
    "product": {"active": True, "name": "Auto Author Pro", "tax_code": "txcd_10105002"},
}


@pytest.fixture
def run(tmp_path):
    (tmp_path / "stripe.py").write_text(STUB)

    def _run(price, managed="true", key="sk_test_placeholder"):
        env = {"PYTHONPATH": str(tmp_path), "STUB_PRICE": json.dumps(price), "STRIPE_SECRET_KEY": key}
        # Same shape as the workflow: the script on stdin, the inputs as arguments.
        return subprocess.run(
            [sys.executable, "-", "price_1AbCdEfGhIjKl", managed],
            stdin=SCRIPT.open(),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    return _run


def _with(**changes):
    spec = json.loads(json.dumps(GOOD))
    for key, value in changes.items():
        if key in ("tax_code", "product_active"):
            spec["product"]["tax_code" if key == "tax_code" else "active"] = value
        else:
            spec[key] = value
    return spec


def test_a_sellable_price_passes_and_names_its_amount_and_mode(run):
    result = run(GOOD)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PREFLIGHT OK" in result.stdout
    assert "$49.00/month" in result.stdout and "test mode" in result.stdout


def test_a_price_the_key_cant_see_stops_with_stripes_reason(run):
    result = run(None)

    assert result.returncode == 1
    assert "can't see price_1AbCdEfGhIjKl" in result.stdout
    assert "exists in live mode" in result.stdout


@pytest.mark.parametrize(
    "spec, reason",
    [
        (_with(livemode=True), "live-mode price but the box's key is test mode"),
        (_with(active=False), "archived"),
        (_with(type="one_time", recurring=None), "not a monthly recurring price"),
        (_with(recurring={"interval": "year"}), "not a monthly recurring price"),
        (_with(currency="eur"), "not usd"),
        (_with(product_active=False), "archived product"),
        (_with(tax_code=None), "no tax code"),
    ],
)
def test_a_price_checkout_couldnt_sell_is_refused(run, spec, reason):
    result = run(spec)

    assert result.returncode == 1
    assert reason in result.stdout


def test_no_tax_code_is_fine_without_managed_payments(run):
    assert run(_with(tax_code=None), managed="false").returncode == 0


def test_a_live_key_is_read_as_live_mode(run):
    assert run(_with(livemode=True), key="sk_live_placeholder").returncode == 0
    assert run(GOOD, key="rk_live_placeholder").returncode == 1


def test_the_key_is_never_printed(run):
    for spec in (GOOD, None, _with(active=False)):
        result = run(spec, key="sk_test_DO_NOT_PRINT")
        assert "DO_NOT_PRINT" not in result.stdout + result.stderr


def test_an_unset_key_stops_before_stripe_is_asked(run):
    result = run(GOOD, key="")

    assert result.returncode == 1
    assert "STRIPE_SECRET_KEY is not set" in result.stdout


def test_the_workflow_checks_before_it_writes_and_rolls_back_a_failed_apply():
    steps = [s["name"] for s in yaml.safe_load(WORKFLOW.read_text())["jobs"]["set"]["steps"]]

    preflight = next(i for i, n in enumerate(steps) if n.startswith("Pre-flight"))
    write = next(i for i, n in enumerate(steps) if n.startswith("Write"))
    rollback = next(i for i, n in enumerate(steps) if n.startswith("Roll back"))
    assert preflight < write < rollback
    assert "staging_billing_preflight.py" in WORKFLOW.read_text()
