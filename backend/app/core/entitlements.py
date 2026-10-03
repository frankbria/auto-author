"""Plan / entitlement registry (issue #174, P0.2).

Single source of truth for which plan is entitled to which AI feature, and how
many AI generations each plan may run per day/month. Free and pro may use every
feature; what a paid plan buys is the larger quota (#766). ``restricted`` is the
named deny path (e.g. lapsed subscription).
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

DEFAULT_PLAN = "free"

# plan -> allowed feature set. "*" means "all features".
PLAN_ENTITLEMENTS: dict[str, frozenset[str]] = {
    "free": frozenset({"*"}),  # every feature, small quota
    "pro": frozenset({"*"}),  # every feature, larger quota (see ai_quota_for_plan)
    "restricted": frozenset(),  # deny path: no AI features
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
