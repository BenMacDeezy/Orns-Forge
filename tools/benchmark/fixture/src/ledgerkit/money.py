"""Cent-precision money helpers.

Every amount in ledgerkit is an integer number of cents. These helpers are
the only place decimal strings get parsed or formatted, so the rest of the
package never has to think about rounding or locale.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def to_cents(amount: str) -> int:
    """Parse a decimal amount string such as ``"12.34"`` or ``"-3"`` into an
    integer number of cents (``1234`` and ``-300`` respectively)."""
    try:
        value = Decimal(amount)
    except InvalidOperation as exc:
        raise ValueError(f"not a valid amount: {amount!r}") from exc
    return int((value * 100).to_integral_value())


def format_cents(cents: int) -> str:
    """Format an integer cent amount as a fixed two-decimal string, e.g.
    ``-305`` -> ``"-3.05"``."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def split_evenly(total_cents: int, num_parts: int) -> list[int]:
    """Split ``total_cents`` into ``num_parts`` equal integer shares."""
    if num_parts <= 0:
        raise ValueError("num_parts must be positive")
    share = total_cents // num_parts
    return [share] * num_parts
