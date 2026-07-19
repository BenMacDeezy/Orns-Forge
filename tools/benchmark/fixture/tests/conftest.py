from datetime import date

import pytest

from ledgerkit.accounts import Account, AccountType, ChartOfAccounts
from ledgerkit.ledger import Ledger
from ledgerkit.transactions import Entry, Transaction


@pytest.fixture
def chart() -> ChartOfAccounts:
    """A small chart of accounts: one asset account and three categorized
    expense accounts, matching the categories ``report.py`` knows about."""
    c = ChartOfAccounts()
    c.add(Account(id="checking", name="Checking", type=AccountType.ASSET))
    c.add(Account(id="food", name="Food", type=AccountType.EXPENSE, category="food"))
    c.add(Account(id="rent", name="Rent", type=AccountType.EXPENSE, category="rent"))
    c.add(Account(id="utilities", name="Utilities", type=AccountType.EXPENSE, category="utilities"))
    c.add(Account(id="misc", name="Misc", type=AccountType.EXPENSE))  # no category
    return c


@pytest.fixture
def ledger(chart: ChartOfAccounts) -> Ledger:
    return Ledger(chart)


def post_simple(
    ledger: Ledger, tx_id: str, tx_date: date, debit: str, credit: str, amount_cents: int
) -> Transaction:
    """Helper: post a two-entry (debit/credit) transaction."""
    transaction = Transaction(
        id=tx_id,
        date=tx_date,
        description=f"{debit} <- {credit}",
        entries=[
            Entry(account_id=debit, amount_cents=amount_cents),
            Entry(account_id=credit, amount_cents=-amount_cents),
        ],
    )
    ledger.post(transaction)
    return transaction
