from datetime import date

import pytest

from conftest import post_simple
from ledgerkit.transactions import Entry, Transaction


class TestPost:
    def test_post_updates_account_balances(self, ledger):
        post_simple(ledger, "tx-1", date(2026, 1, 1), debit="rent", credit="checking", amount_cents=1000)
        assert ledger.chart.get("rent").balance() == 1000
        assert ledger.chart.get("checking").balance() == -1000

    def test_post_records_transaction(self, ledger):
        transaction = post_simple(
            ledger, "tx-1", date(2026, 1, 1), debit="rent", credit="checking", amount_cents=1000
        )
        assert ledger.transactions == [transaction]

    def test_post_unbalanced_transaction_raises_and_does_not_apply(self, ledger):
        transaction = Transaction(
            id="tx-bad",
            date=date(2026, 1, 1),
            description="broken",
            entries=[Entry("checking", -1000), Entry("rent", 999)],
        )
        with pytest.raises(ValueError):
            ledger.post(transaction)
        assert ledger.chart.get("checking").balance() == 0
        assert ledger.transactions == []

    def test_post_unknown_account_raises(self, ledger):
        transaction = Transaction(
            id="tx-bad",
            date=date(2026, 1, 1),
            description="broken",
            entries=[Entry("checking", -1000), Entry("nonexistent", 1000)],
        )
        with pytest.raises(KeyError):
            ledger.post(transaction)


class TestSplitExpense:
    def test_splits_evenly_across_three_participants(self, ledger):
        ledger.split_expense(
            tx_id="split-1",
            tx_date=date(2026, 1, 1),
            description="groceries",
            payer_id="checking",
            participant_ids=["food", "rent", "utilities"],
            total_cents=300,
        )
        assert ledger.chart.get("food").balance() == 100
        assert ledger.chart.get("rent").balance() == 100
        assert ledger.chart.get("utilities").balance() == 100
        assert ledger.chart.get("checking").balance() == -300

    def test_splits_evenly_across_two_participants(self, ledger):
        ledger.split_expense(
            tx_id="split-2",
            tx_date=date(2026, 1, 1),
            description="utilities",
            payer_id="checking",
            participant_ids=["food", "rent"],
            total_cents=200,
        )
        assert ledger.chart.get("food").balance() == 100
        assert ledger.chart.get("rent").balance() == 100

    def test_split_expense_records_a_transaction(self, ledger):
        transaction = ledger.split_expense(
            tx_id="split-3",
            tx_date=date(2026, 1, 1),
            description="groceries",
            payer_id="checking",
            participant_ids=["food", "rent"],
            total_cents=200,
        )
        assert transaction in ledger.transactions


class TestTransactionsBetween:
    def test_includes_transactions_within_range(self, ledger):
        post_simple(ledger, "tx-1", date(2026, 1, 1), debit="rent", credit="checking", amount_cents=100)
        post_simple(ledger, "tx-2", date(2026, 1, 15), debit="food", credit="checking", amount_cents=100)
        post_simple(ledger, "tx-3", date(2026, 1, 31), debit="utilities", credit="checking", amount_cents=100)

        results = ledger.transactions_between(date(2026, 1, 1), date(2026, 2, 1))

        assert {t.id for t in results} == {"tx-1", "tx-2", "tx-3"}

    def test_since_boundary_is_inclusive(self, ledger):
        post_simple(ledger, "tx-1", date(2026, 1, 1), debit="rent", credit="checking", amount_cents=100)
        post_simple(ledger, "tx-2", date(2026, 1, 15), debit="food", credit="checking", amount_cents=100)

        results = ledger.transactions_between(date(2026, 1, 15), date(2026, 2, 1))

        assert {t.id for t in results} == {"tx-2"}

    def test_excludes_transactions_before_since(self, ledger):
        post_simple(ledger, "tx-1", date(2025, 12, 1), debit="rent", credit="checking", amount_cents=100)
        post_simple(ledger, "tx-2", date(2026, 1, 15), debit="food", credit="checking", amount_cents=100)

        results = ledger.transactions_between(date(2026, 1, 1), date(2026, 2, 1))

        assert {t.id for t in results} == {"tx-2"}
