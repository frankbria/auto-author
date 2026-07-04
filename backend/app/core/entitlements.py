"""Plan / entitlement registry (issue #174, P0.2).

Single source of truth for which plan is entitled to which AI feature. For the
free-invite beta the only real plan is ``free`` (full access) — this module is
the *hook* so per-user AI caps (P0.1) can key off plan and a paid launch adds a
tier here instead of a rebuild. No payment provider is built yet.

ponytail: today ``free`` allows everything, so no real beta user is ever denied;
``restricted`` is the named deny path (e.g. invite revoked / trial expired).
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

# plan -> allowed feature set. "*" means "all features". A paid tier is added
# here (e.g. "pro": frozenset({"*"})) with no code change at call sites.
PLAN_ENTITLEMENTS: dict[str, frozenset[str]] = {
    "free": frozenset({"*"}),  # beta: full AI access
    "restricted": frozenset(),  # deny path: no AI features
}


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
