"""The ledger: a chart of accounts plus the transactions posted against it."""

from __future__ import annotations

import logging
from datetime import date

from .accounts import ChartOfAccounts
from .money import split_evenly
from .transactions import Entry, Transaction, validate_balanced

logger = logging.getLogger(__name__)


class Ledger:
    """Ties a chart of accounts to the list of transactions posted against
    it. Posting is the only way an account's balance changes."""

    def __init__(self, chart: ChartOfAccounts) -> None:
        self.chart = chart
        self.transactions: list[Transaction] = []

    def post(self, transaction: Transaction) -> None:
        """Validate ``transaction`` balances, apply its entries to the
        touched accounts, and record it."""
        validate_balanced(transaction)
        for entry in transaction.entries:
            account = self.chart.get(entry.account_id)
            account._apply(entry.amount_cents)
        self.transactions.append(transaction)
        logger.info(f"posted transaction {transaction.id}: {transaction.description}")

    def split_expense(
        self,
        tx_id: str,
        tx_date: date,
        description: str,
        payer_id: str,
        participant_ids: list[str],
        total_cents: int,
    ) -> Transaction:
        """Record an expense ``payer_id`` paid in full, split evenly across
        ``participant_ids`` (each participant's account is debited their
        share; the payer's account is credited the total)."""
        shares = split_evenly(total_cents, len(participant_ids))
        entries = [Entry(account_id=payer_id, amount_cents=-total_cents)]
        entries.extend(
            Entry(account_id=participant_id, amount_cents=share)
            for participant_id, share in zip(participant_ids, shares)
        )
        transaction = Transaction(id=tx_id, date=tx_date, description=description, entries=entries)
        self.post(transaction)
        return transaction

    def transactions_between(self, since: date, until: date) -> list[Transaction]:
        """Return transactions dated inclusive of both ``since`` and
        ``until``."""
        return [t for t in self.transactions if since <= t.date < until]
