# Quantity as a number plus a unit, kept apart from the database so the rules
# are testable as plain functions. `un` means a count and is shown bare.

import re
from decimal import Decimal, InvalidOperation

from markupsafe import Markup, escape

UNITS = ("un", "lb", "oz", "kg", "g")
# What one tap of - / + moves, per unit.
STEPS = {"un": 1, "lb": 0.5, "kg": 0.5, "g": 100, "oz": 4}

_CLEAR = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(lb|lbs|oz|kg|g|un)?\s*$", re.I)


def parse_text(text):
    """Old free-text qty -> (Decimal, unit), or None when it does not clearly
    parse ("1 pack", "a few", ""). No unit means a count."""
    m = _CLEAR.match(text or "")
    if not m:
        return None
    num = Decimal(m.group(1).replace(",", "."))
    unit = (m.group(2) or "un").lower()
    return num, ("lb" if unit == "lbs" else unit)


def parse_input(num, unit):
    """Form fields -> (Decimal, unit). Blank, invalid or non-positive numbers
    fall back to 1; an unknown unit falls back to un."""
    unit = unit if unit in UNITS else "un"
    try:
        n = Decimal((num or "").strip().replace(",", "."))
    except InvalidOperation:
        return Decimal(1), unit
    if not n.is_finite() or n <= 0:
        return Decimal(1), unit
    return n, unit


def fmt_num(n):
    """Decimal -> shortest text: 2, 1.5, 0.25."""
    s = format(Decimal(n).normalize(), "f")
    return s


def normalise(num, unit):
    """The text written to the legacy `qty` column: '6', '2 lb'."""
    n = fmt_num(num)
    return n if unit == "un" else f"{n} {unit}"


def badge(qty_num, unit, qty_text):
    """Markup for the quantity badge, the same highlight for every quantity
    (1 included) so it reads at a glance in the store. Unparseable rows show
    their original text; nothing at all shows 1."""
    if qty_num is None:
        txt = (qty_text or "").strip()
        if not txt:
            return Markup('<span class="q">1</span>')
        return Markup('<span class="q raw">%s</span>') % txt
    inner = Markup(escape(fmt_num(qty_num)))
    if unit and unit != "un":
        inner += Markup("<small>%s</small>") % unit
    return Markup('<span class="q">%s</span>') % inner


def stepper_value(qty_num):
    return "" if qty_num is None else fmt_num(qty_num)


def register(env):
    env.globals.update(qty_badge=badge, qty_value=stepper_value,
                       qty_units=UNITS, qty_steps=STEPS)
