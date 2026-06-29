"""Tests for the export template registry (issue #59)."""
import pytest

from app.services.export_templates import (
    TEMPLATES,
    PAGE_SIZES_INCHES,
    MIN_MARGIN_INCHES,
    list_templates,
    get_template,
    resolve_template,
)


def test_ships_at_least_three_templates():
    assert len(TEMPLATES) >= 3
    assert {"classic_fiction", "modern_nonfiction", "academic"} <= set(TEMPLATES)


def test_every_template_has_required_fields_and_valid_page_size():
    required = {"id", "name", "description", "page_size", "margins", "font",
                "line_height", "first_line_indent", "header", "footer"}
    for tid, t in TEMPLATES.items():
        assert required <= set(t), f"{tid} missing fields"
        assert t["id"] == tid
        assert t["page_size"] in PAGE_SIZES_INCHES
        assert {"top", "bottom", "inside", "outside"} <= set(t["margins"])
        # POD-safe: no default margin below the floor.
        for side, val in t["margins"].items():
            assert val >= MIN_MARGIN_INCHES, f"{tid}.{side} below POD floor"
        assert {"pdf_font", "docx_font", "size"} <= set(t["font"])


def test_list_templates_returns_copies():
    a = list_templates()
    a[0]["name"] = "mutated"
    b = list_templates()
    assert b[0]["name"] != "mutated"  # registry untouched


def test_get_template_unknown_raises():
    with pytest.raises(KeyError):
        get_template("does_not_exist")


def test_resolve_none_id_returns_none():
    assert resolve_template(None) is None
    assert resolve_template("") is None


def test_resolve_without_overrides_returns_template():
    t = resolve_template("academic")
    assert t["id"] == "academic"
    assert t["font"]["size"] == 12


def test_resolve_merges_font_size_and_clamps():
    t = resolve_template("classic_fiction", {"font_size": 14})
    assert t["font"]["size"] == 14
    # Out-of-range clamps, doesn't crash.
    assert resolve_template("classic_fiction", {"font_size": 999})["font"]["size"] == 18
    assert resolve_template("classic_fiction", {"font_size": 2})["font"]["size"] == 8


def test_resolve_merges_margins_with_floor():
    t = resolve_template("classic_fiction", {"margins": {"inside": 0.05}})
    assert t["margins"]["inside"] == MIN_MARGIN_INCHES  # clamped up
    assert t["margins"]["top"] == 0.75  # untouched side preserved


def test_resolve_merges_header_text():
    t = resolve_template("academic", {"header": {"left": "My Running Head"}})
    assert t["header"]["left"] == "My Running Head"
    assert t["header"]["right"] == TEMPLATES["academic"]["header"]["right"]


def test_resolve_unknown_id_raises():
    with pytest.raises(KeyError):
        resolve_template("nope", {"font_size": 11})


def test_resolve_bad_custom_options_type_raises():
    with pytest.raises(ValueError):
        resolve_template("academic", "not-a-dict")  # type: ignore[arg-type]
