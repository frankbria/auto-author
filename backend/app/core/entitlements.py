"""Plan / entitlement registry (issue #174, P0.2).

Single source of truth for which plan is entitled to which feature, and how
many AI generations each plan may run. ``restricted`` is the named deny path
(e.g. lapsed subscription).

Free is a trial, not a plan to write a book on (owner decision 2026-10-28): it
may use every AI feature, but has a lifetime allowance of AI generations, an AI
draft for one chapter, and no export. Pro has every feature, a daily and
monthly allowance, and export.
"""

from typing import Optional

# Feature keys gating the AI generation endpoints (mirror the wiring in books.py).
AI_FEATURES = frozenset(
    {
        "analyze_summary",
        "generate_questions",
        "generate_toc",
        "chapter_generate_questions",
        "regenerate_question",
        "regenerate_questions",
        "generate_draft",
        "transform_style",
        "enhance_text",
        "enhance_transcription",
    }
)

# Downloading the book (PDF, DOCX, EPUB, Markdown). Not an AI feature: it is
# not metered, only gated. It is what makes a book, so the trial doesn't get it.
EXPORT_FEATURE = "export"

DEFAULT_PLAN = "free"

# plan -> allowed feature set. "*" means "all features".
PLAN_ENTITLEMENTS: dict[str, frozenset[str]] = {
    "free": AI_FEATURES,  # the trial: every AI feature, no export
    "pro": frozenset({"*"}),  # everything, larger quota (see ai_quota_for_plan)
    "restricted": frozenset(),  # deny path: no AI features
}

# What a 402 tells the user, for a feature the trial doesn't include. The
# client shows it under an Upgrade button.
TRIAL_DENIAL_MESSAGES: dict[str, str] = {
    EXPORT_FEATURE: (
        "Exporting your book is part of Pro. The free trial is for trying "
        "Auto Author on one chapter; upgrade to export PDF, DOCX, EPUB or Markdown."
    ),
    "generate_draft": (
        "The free trial includes an AI draft of one chapter, and you've used it "
        "on another chapter. Upgrade to Pro to draft the rest of your book."
    ),
}


def resolve_plan_for_price(price_id: Optional[str]) -> str:
    """Map a Stripe price id to an internal plan (issue #220).

    Only the configured pro price resolves to ``pro``; anything unknown or
    missing falls back to the default free plan. Pure — no I/O.
    """
    from app.core.config import settings

    if price_id and settings.STRIPE_PRICE_ID_PRO and price_id == settings.STRIPE_PRICE_ID_PRO:
        return "pro"
    return DEFAULT_PLAN


# Stripe subscription status -> plan (#767). The price only decides the plan
# while the subscription is actually paid for:
#   active, trialing    -> PRICED: the plan the price buys (resolve_plan_for_price)
#   past_due            -> KEEP: plan unchanged. Stripe is retrying the renewal,
#                          so a pro user keeps pro meanwhile, but past_due never
#                          *grants* pro (a free user stays free).
#   unpaid              -> restricted: retries exhausted on a lapsed subscriber
#   incomplete          -> free: first payment not confirmed yet
#   incomplete_expired  -> free: the first payment never succeeded, so the user
#                          was never pro. Not restricted (the #767 proposal):
#                          that would leave someone whose card was declined at
#                          checkout worse off than if they had never tried.
#   paused, canceled    -> free
# Any status not listed (Stripe adds them) is free: below paid, not locked out.
PRICED = "priced"
KEEP = "keep"
SUBSCRIPTION_STATUS_PLAN: dict[str, str] = {
    "active": PRICED,
    "trialing": PRICED,
    "past_due": KEEP,
    "unpaid": "restricted",
    "incomplete": "free",
    "incomplete_expired": "free",
    "paused": "free",
    "canceled": "free",
}


# A subscription Stripe is still billing (#768): the paid statuses plus past_due,
# which is mid-retry. Checkout refuses a second one while it exists, and the
# webhook won't let another subscription's events replace it as current.
LIVE_SUBSCRIPTION_STATUSES = frozenset(
    status for status, policy in SUBSCRIPTION_STATUS_PLAN.items() if policy in (PRICED, KEEP)
)


def has_live_subscription(user: dict) -> bool:
    """Whether the user's current Stripe subscription is still being billed."""
    status = user.get("stripe_subscription_status")
    if status is None and user.get("stripe_subscription_id"):
        # Written before #768 recorded the status: pro is only ever granted by
        # an active/trialing subscription, so take it as the live signal.
        return user.get("plan") == "pro"
    return status in LIVE_SUBSCRIPTION_STATUSES


def plan_for_subscription(status: Optional[str], price_ids: list) -> Optional[str]:
    """Plan a subscription in ``status`` with these line-item prices grants.

    ``None`` means leave the user's plan as it is (past_due). Pure — no I/O.
    """
    policy = SUBSCRIPTION_STATUS_PLAN.get(status or "", DEFAULT_PLAN)
    if policy == KEEP:
        return None
    if policy != PRICED:
        return policy
    # Scan every line item: the plan-bearing price need not be listed first.
    for price_id in price_ids:
        plan = resolve_plan_for_price(price_id)
        if plan != DEFAULT_PLAN:
            return plan
    return DEFAULT_PLAN


def is_feature_allowed(plan: Optional[str], feature: str) -> bool:
    """Return whether ``plan`` may use ``feature``.

    A missing/empty plan is treated as the default free plan so legacy user
    documents (written before this field existed) keep working with no backfill.
    An *explicit* unknown plan fails closed (denied) — it's a billing gate.
    """
    allowed = PLAN_ENTITLEMENTS.get(plan or DEFAULT_PLAN)
    if allowed is None:
        return False
    return "*" in allowed or feature in allowed


def ai_quota_for_plan(plan: Optional[str]) -> Optional[tuple[int, int]]:
    """Return ``(daily, monthly)`` AI-generation caps for ``plan`` (#766).

    Read from settings on every call so the billing UI and the enforcing
    dependency share one source. A missing plan is ``free`` (legacy docs).
    ``None`` means no allowance at all: ``restricted`` and any unknown plan
    (fails closed, like :func:`is_feature_allowed`).
    """
    from app.core.config import settings

    plan = plan or DEFAULT_PLAN
    if plan == "free":
        return settings.AI_QUOTA_FREE_DAILY, settings.AI_QUOTA_FREE_MONTHLY
    if plan == "pro":
        return settings.AI_QUOTA_PRO_DAILY, settings.AI_QUOTA_PRO_MONTHLY
    return None


def ai_trial_total_for_plan(plan: Optional[str]) -> int:
    """Lifetime AI generations ``plan`` may run, which never reset (0 = no cap).

    Only free has one: it is a trial. Missing plan is free, like the others.
    """
    from app.core.config import settings

    return settings.AI_QUOTA_FREE_TOTAL if (plan or DEFAULT_PLAN) == "free" else 0


def draft_chapter_cap_for_plan(plan: Optional[str]) -> int:
    """How many distinct chapters ``plan`` may get an AI draft for (0 = no cap)."""
    from app.core.config import settings

    return settings.AI_QUOTA_FREE_DRAFT_CHAPTERS if (plan or DEFAULT_PLAN) == "free" else 0
