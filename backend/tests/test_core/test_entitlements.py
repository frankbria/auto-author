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


class TestStripePricePlanResolution:
    """resolve_plan_for_price (issue #220) — pure price-id → plan mapping."""

    def test_configured_pro_price_resolves_to_pro(self, monkeypatch):
        from app.core.config import settings
        from app.core.entitlements import resolve_plan_for_price

        monkeypatch.setattr(settings, "STRIPE_PRICE_ID_PRO", "price_pro_x")
        assert resolve_plan_for_price("price_pro_x") == "pro"

    def test_unknown_or_missing_price_defaults_to_free(self, monkeypatch):
        from app.core.config import settings
        from app.core.entitlements import resolve_plan_for_price

        monkeypatch.setattr(settings, "STRIPE_PRICE_ID_PRO", "price_pro_x")
        assert resolve_plan_for_price("price_other") == DEFAULT_PLAN
        assert resolve_plan_for_price(None) == DEFAULT_PLAN
        assert resolve_plan_for_price("") == DEFAULT_PLAN

    def test_unconfigured_price_id_never_matches(self, monkeypatch):
        # Empty STRIPE_PRICE_ID_PRO must not make empty/any price map to pro.
        from app.core.config import settings
        from app.core.entitlements import resolve_plan_for_price

        monkeypatch.setattr(settings, "STRIPE_PRICE_ID_PRO", "")
        assert resolve_plan_for_price("") == DEFAULT_PLAN
        assert resolve_plan_for_price("price_anything") == DEFAULT_PLAN

    def test_pro_plan_is_registered_with_full_access(self):
        assert PLAN_ENTITLEMENTS["pro"] == frozenset({"*"})
        for feature in AI_FEATURES:
            assert is_feature_allowed("pro", feature) is True
