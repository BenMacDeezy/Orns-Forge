"""ledgerkit: a small double-entry-flavored ledger library.

Accounts hold a running balance in integer cents. Transactions are made up
of two or more signed entries that must sum to zero (double-entry
balancing). ``Ledger`` ties a chart of accounts and a list of posted
transactions together and is the object most of the other modules operate
on; ``report`` computes read-only views over a ``Ledger``; ``csv_import``
loads transactions from a CSV file; ``cli`` exposes a small command-line
front end.

Nothing in this package stores a monetary amount as a float -- everything
is an integer number of cents, converted at the edges by ``money``.
"""

from .accounts import Account, AccountType, ChartOfAccounts
from .ledger import Ledger
from .money import format_cents, split_evenly, to_cents
from .transactions import Entry, Transaction

__version__ = "0.1.0"

__all__ = [
    "Account",
    "AccountType",
    "ChartOfAccounts",
    "Entry",
    "Ledger",
    "Transaction",
    "format_cents",
    "split_evenly",
    "to_cents",
]
