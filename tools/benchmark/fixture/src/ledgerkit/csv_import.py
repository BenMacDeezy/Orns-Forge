"""Load transactions from a CSV file."""

from __future__ import annotations

import csv
import logging
from datetime import date

from .accounts import ChartOfAccounts
from .transactions import Entry, Transaction

logger = logging.getLogger(__name__)


def load_transactions_csv(path: str, chart: ChartOfAccounts) -> list[Transaction]:
    """Load transactions from the CSV file at ``path``.

    Expected columns: ``id``, ``date`` (``YYYY-MM-DD``), ``description``,
    ``debit_account``, ``credit_account``, ``amount_cents``. Each row
    becomes a single two-entry transaction: ``debit_account`` is debited
    ``amount_cents`` and ``credit_account`` is credited the same amount.
    ``chart`` is used only to validate that both accounts exist.
    """
    transactions: list[Transaction] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            chart.get(row["debit_account"])
            chart.get(row["credit_account"])
            tx_date = date.fromisoformat(row["date"])
            amount = int(row["amount_cents"])
            entries = [
                Entry(account_id=row["debit_account"], amount_cents=amount),
                Entry(account_id=row["credit_account"], amount_cents=-amount),
            ]
            transaction = Transaction(
                id=row["id"],
                date=tx_date,
                description=row["description"],
                entries=entries,
            )
            transactions.append(transaction)
            logger.info(f"loaded transaction {transaction.id} from {path}")
    return transactions
