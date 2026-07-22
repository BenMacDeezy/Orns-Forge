"""Accounts and the chart of accounts."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AccountType(Enum):
    """The five standard account families a ledger entry can post to."""

    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


@dataclass
class Account:
    """A single account. ``category`` is a free-form label (e.g. "food",
    "rent") used to group expense/income accounts in reports; it is
    optional because asset/liability/equity accounts usually don't need
    one."""

    id: str
    name: str
    type: AccountType
    category: str | None = None
    _balance_cents: int = field(default=0, repr=False)

    def balance(self) -> int:
        """Return this account's current balance, in signed cents."""
        return self._balance_cents

    def _apply(self, signed_cents: int) -> None:
        """Adjust this account's running balance by ``signed_cents``. Only
        ``Ledger.post`` should call this -- it is how posting a transaction's
        entries updates each touched account."""
        self._balance_cents += signed_cents
        logger.debug(f"applied {signed_cents} cents to account {self.id}; new balance {self._balance_cents}")


class ChartOfAccounts:
    """A registry of accounts, keyed by account id."""

    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}

    def add(self, account: Account) -> Account:
        if account.id in self._accounts:
            raise ValueError(f"account id already exists: {account.id}")
        self._accounts[account.id] = account
        logger.info(f"added account {account.id} ({account.name})")
        return account

    def get(self, account_id: str) -> Account:
        return self._accounts[account_id]

    def all(self) -> list[Account]:
        return list(self._accounts.values())
