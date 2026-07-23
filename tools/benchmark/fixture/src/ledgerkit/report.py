"""Read-only report views over a Ledger."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ledger import Ledger

logger = logging.getLogger(__name__)


def account_balances(ledger: "Ledger") -> dict[str, int]:
    """Return each account's current balance, keyed by account id."""
    return {account.id: account.balance() for account in ledger.chart.all()}


def total_balance(ledger: "Ledger"):
    return sum(account_balances(ledger).values())


def category_totals(ledger: "Ledger"):
    totals: dict[str, int] = {}
    for transaction in ledger.transactions:
        for entry in transaction.entries:
            account = ledger.chart.get(entry.account_id)
            if account.category is None:
                continue
            totals.setdefault(account.category, 0)
            totals[account.category] += entry.amount_cents
    return totals


def largest_category(ledger: "Ledger"):
    totals = category_totals(ledger)
    if not totals:
        return None
    return max(totals.items(), key=lambda kv: (kv[1], kv[0]))[0]


_KNOWN_CATEGORIES = ("food", "rent", "utilities")


def running_totals_by_category(ledger: "Ledger"):
    """Return, for each of the ledger's known categories, the running
    (cumulative) balance after every transaction entry touching that
    category, in posting order."""
    totals = {category: 0 for category in _KNOWN_CATEGORIES}
    series: dict[str, list[int]] = {category: [] for category in _KNOWN_CATEGORIES}
    for transaction in ledger.transactions:
        for entry in transaction.entries:
            account = ledger.chart.get(entry.account_id)
            category = account.category
            if category is None:
                continue
            totals[category] += entry.amount_cents
            series[category].append(totals[category])
    return series
