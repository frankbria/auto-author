"""Tests for the plan/entitlement registry (issue #174, P0.2)."""

from app.core.entitlements import (
    AI_FEATURES,
    DEFAULT_PLAN,
    PLAN_ENTITLEMENTS,
    is_feature_allowed,
)


def test_free_plan_allows_every_ai_feature():
    for feature in AI_FEATURES:
        assert is_feature_allowed("free", feature) is True


def test_restricted_plan_denies_all_ai_features():
    for feature in AI_FEATURES:
        assert is_feature_allowed("restricted", feature) is False


def test_missing_plan_defaults_to_free():
    # Legacy documents lacking the field (None/empty) are treated as free.
    assert is_feature_allowed(None, "generate_toc") is True
    assert is_feature_allowed("", "generate_toc") is True
    assert DEFAULT_PLAN == "free"


def test_unknown_explicit_plan_fails_closed():
    # An explicit but unrecognized plan is denied (billing gate is fail-closed).
    assert is_feature_allowed("enterprise-typo", "generate_toc") is False


def test_wildcard_semantics():
    assert PLAN_ENTITLEMENTS["free"] == frozenset({"*"})
    assert is_feature_allowed("free", "any-future-feature") is True
