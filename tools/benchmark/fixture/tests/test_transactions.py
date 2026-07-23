from datetime import date

import pytest

from ledgerkit.transactions import Entry, Transaction, validate_balanced


class TestValidateBalanced:
    def test_balanced_transaction_does_not_raise(self):
        transaction = Transaction(
            id="tx-1",
            date=date(2026, 1, 1),
            description="rent",
            entries=[Entry("checking", -1000), Entry("rent", 1000)],
        )
        validate_balanced(transaction)  # should not raise

    def test_unbalanced_transaction_raises(self):
        transaction = Transaction(
            id="tx-2",
            date=date(2026, 1, 1),
            description="oops",
            entries=[Entry("checking", -1000), Entry("rent", 999)],
        )
        with pytest.raises(ValueError):
            validate_balanced(transaction)

    def test_empty_entries_is_balanced(self):
        transaction = Transaction(id="tx-3", date=date(2026, 1, 1), description="empty", entries=[])
        validate_balanced(transaction)  # should not raise
