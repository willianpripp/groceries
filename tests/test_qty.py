# The quantity rules are pure functions in app/qty.py, so they run without a
# database; the template tests render with Jinja directly.

import pathlib
import sys
from decimal import Decimal

import pytest
from jinja2 import Environment, FileSystemLoader

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "app"))

import qty  # noqa: E402


@pytest.mark.parametrize("text,expected", [
    ("6", (Decimal(6), "un")),
    ("2 lb", (Decimal(2), "lb")),
    ("2lbs", (Decimal(2), "lb")),
    ("1,5 kg", (Decimal("1.5"), "kg")),
    ("  500G ", (Decimal(500), "g")),
    ("3 un", (Decimal(3), "un")),
    ("4 OZ", (Decimal(4), "oz")),
    ("0.5", (Decimal("0.5"), "un")),
])
def test_parse_text_clear(text, expected):
    assert qty.parse_text(text) == expected


@pytest.mark.parametrize("text", ["", "1 pack", "a few", "2 dozen", "lb", "1.5.2", "2 x 3", None])
def test_parse_text_unclear(text):
    assert qty.parse_text(text) is None


def test_parse_input_defaults_and_fallbacks():
    assert qty.parse_input("", "un") == (Decimal(1), "un")
    assert qty.parse_input("abc", "lb") == (Decimal(1), "lb")
    assert qty.parse_input("0", "kg") == (Decimal(1), "kg")
    assert qty.parse_input("-2", "g") == (Decimal(1), "g")
    assert qty.parse_input("nan", "g") == (Decimal(1), "g")
    assert qty.parse_input("1,5", "lb") == (Decimal("1.5"), "lb")
    assert qty.parse_input("2", "bushel") == (Decimal(2), "un")


@pytest.mark.parametrize("num,unit,text", [
    (Decimal(6), "un", "6"),
    (Decimal("6.0"), "un", "6"),
    (Decimal(2), "lb", "2 lb"),
    (Decimal("1.5"), "kg", "1.5 kg"),
    (Decimal(500), "g", "500 g"),
    (Decimal("100"), "g", "100 g"),
])
def test_normalise(num, unit, text):
    assert qty.normalise(num, unit) == text


def test_normalised_text_round_trips_through_the_parser():
    for num, unit in [(Decimal(6), "un"), (Decimal("1.5"), "lb"), (Decimal(100), "g")]:
        assert qty.parse_text(qty.normalise(num, unit)) == (num, unit)


def test_steps_cover_every_unit():
    assert set(qty.STEPS) == set(qty.UNITS)
    assert qty.STEPS == {"un": 1, "lb": 0.5, "kg": 0.5, "g": 100, "oz": 4}


def test_badge_variants():
    assert qty.badge(Decimal(6), "un", "6") == '<span class="q">6</span>'
    assert qty.badge(Decimal(1), "un", "1") == '<span class="q">1</span>'
    assert qty.badge(Decimal(1), "lb", "1 lb") == '<span class="q">1<small>lb</small></span>'
    assert qty.badge(Decimal("2.0"), "lb", "2 lb") == '<span class="q">2<small>lb</small></span>'
    assert qty.badge(None, None, "1 pack") == '<span class="q raw">1 pack</span>'
    assert qty.badge(None, None, "") == '<span class="q">1</span>'


def test_badge_escapes_legacy_text():
    assert "<script>" not in qty.badge(None, None, "<script>x</script>")


# --- templates ------------------------------------------------------------------


def _env():
    env = Environment(loader=FileSystemLoader(ROOT / "app" / "templates"), autoescape=True)
    qty.register(env)
    return env


def _entry(**kw):
    e = dict(id=1, name="Milk", qty="1", qty_num=Decimal(1), unit="un", note="",
             planned_store=1, added_by="Willian")
    e.update(kw)
    return e


def _render_row(**kw):
    tpl = _env().from_string(
        '{% from "_entry.html" import entry_row with context %}{{ entry_row(e) }}')
    return tpl.render(e=_entry(**kw), base="", stores=[{"id": 1, "name": "Aldi"}])


def test_row_has_badge_before_name_and_no_initial():
    html = _render_row(qty_num=Decimal(2), unit="lb", qty="2 lb")
    assert html.index('class="q"') < html.index('class="nm"')
    assert "<small>lb</small>" in html
    assert 'class="by"' not in html


def test_row_edit_panel_has_stepper_and_units_without_text_qty():
    html = _render_row(qty_num=Decimal("1.5"), unit="kg", qty="1.5 kg")
    assert 'name="qty_num"' in html and 'value="1.5"' in html
    for u in qty.UNITS:
        assert f'value="{u}"' in html
    assert 'value="kg" checked' in html
    assert 'name="qty"' not in html


def test_row_legacy_text_shows_as_written_and_blank_stepper():
    html = _render_row(qty_num=None, unit=None, qty="1 pack")
    assert '<span class="q raw">1 pack</span>' in html
    assert 'placeholder="1 pack"' in html
