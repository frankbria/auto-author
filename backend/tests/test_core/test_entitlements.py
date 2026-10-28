"""Tests for the plan/entitlement registry (issue #174, P0.2)."""

from app.core.entitlements import (
    AI_FEATURES,
    DEFAULT_PLAN,
    EXPORT_FEATURE,
    PLAN_ENTITLEMENTS,
    TRIAL_DENIAL_MESSAGES,
    ai_trial_total_for_plan,
    draft_chapter_cap_for_plan,
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
    assert PLAN_ENTITLEMENTS["pro"] == frozenset({"*"})
    assert is_feature_allowed("pro", "any-future-feature") is True


class TestFreeIsATrial:
    """Owner decision 2026-10-28: Free tests one chapter and can't make a book."""

    def test_free_has_every_ai_feature_and_nothing_else(self):
        assert PLAN_ENTITLEMENTS["free"] == AI_FEATURES
        # A feature added later is Pro until someone decides the trial gets it.
        assert is_feature_allowed("free", "any-future-feature") is False

    def test_free_cannot_export_and_pro_can(self):
        assert is_feature_allowed("free", EXPORT_FEATURE) is False
        assert is_feature_allowed(None, EXPORT_FEATURE) is False  # legacy doc = free
        assert is_feature_allowed("pro", EXPORT_FEATURE) is True
        assert is_feature_allowed("restricted", EXPORT_FEATURE) is False

    def test_only_free_has_a_lifetime_allowance(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "AI_QUOTA_FREE_TOTAL", 30)
        assert ai_trial_total_for_plan("free") == 30
        assert ai_trial_total_for_plan(None) == 30
        assert ai_trial_total_for_plan("pro") == 0

    def test_only_free_has_a_draft_chapter_cap(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "AI_QUOTA_FREE_DRAFT_CHAPTERS", 1)
        assert draft_chapter_cap_for_plan("free") == 1
        assert draft_chapter_cap_for_plan("") == 1
        assert draft_chapter_cap_for_plan("pro") == 0

    def test_trial_defaults_fit_one_chapter_not_a_book(self):
        from app.core.config import Settings

        defaults = Settings.model_fields
        assert defaults["AI_QUOTA_FREE_TOTAL"].default == 30
        assert defaults["AI_QUOTA_FREE_DRAFT_CHAPTERS"].default == 1
        # No window that refills: a trial that reset monthly would write a book slowly.
        assert defaults["AI_QUOTA_FREE_DAILY"].default == 0
        assert defaults["AI_QUOTA_FREE_MONTHLY"].default == 0

    def test_every_trial_refusal_says_what_pro_adds(self):
        for feature, message in TRIAL_DENIAL_MESSAGES.items():
            assert "Pro" in message, feature
            assert "trial" in message, feature


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
