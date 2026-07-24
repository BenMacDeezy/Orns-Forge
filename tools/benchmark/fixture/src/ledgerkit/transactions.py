"""Transactions: a dated group of signed entries that must sum to zero."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class Entry:
    """One leg of a transaction. ``amount_cents`` is signed: positive is a
    debit, negative is a credit."""

    account_id: str
    amount_cents: int


@dataclass
class Transaction:
    """A dated, described group of entries. A transaction is only valid if
    its entries balance (see ``validate_balanced``); ``Ledger.post`` enforces
    this before recording it."""

    id: str
    date: date
    description: str
    entries: list[Entry] = field(default_factory=list)


def validate_balanced(transaction: Transaction) -> None:
    """Raise ``ValueError`` if ``transaction``'s entries do not sum to zero."""
    total = sum(entry.amount_cents for entry in transaction.entries)
    if total != 0:
        logger.warning(f"transaction {transaction.id} is unbalanced by {total} cents")
        raise ValueError(f"transaction {transaction.id} does not balance: off by {total} cents")
