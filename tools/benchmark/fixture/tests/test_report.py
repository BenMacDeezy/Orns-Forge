from datetime import date

from conftest import post_simple
from ledgerkit import report


class TestAccountBalances:
    def test_reflects_posted_transactions(self, ledger):
        post_simple(ledger, "tx-1", date(2026, 1, 1), debit="rent", credit="checking", amount_cents=1000)
        balances = report.account_balances(ledger)
        assert balances["rent"] == 1000
        assert balances["checking"] == -1000

    def test_empty_ledger_has_zero_balances(self, ledger):
        balances = report.account_balances(ledger)
        assert all(value == 0 for value in balances.values())


class TestTotalBalance:
    def test_sums_to_zero_for_balanced_ledger(self, ledger):
        post_simple(ledger, "tx-1", date(2026, 1, 1), debit="rent", credit="checking", amount_cents=1000)
        post_simple(ledger, "tx-2", date(2026, 1, 2), debit="food", credit="checking", amount_cents=500)
        # every posted transaction balances to zero, so the ledger-wide total
        # (the sum of every account's balance) is always zero too.
        assert report.total_balance(ledger) == 0


class TestCategoryTotals:
    def test_groups_by_category(self, ledger):
        post_simple(ledger, "tx-1", date(2026, 1, 1), debit="rent", credit="checking", amount_cents=1000)
        post_simple(ledger, "tx-2", date(2026, 1, 2), debit="food", credit="checking", amount_cents=500)
        post_simple(ledger, "tx-3", date(2026, 1, 3), debit="food", credit="checking", amount_cents=250)

        totals = report.category_totals(ledger)

        assert totals == {"rent": 1000, "food": 750}

    def test_empty_ledger_has_no_categories(self, ledger):
        assert report.category_totals(ledger) == {}


class TestLargestCategory:
    def test_returns_the_category_with_the_highest_total(self, ledger):
        post_simple(ledger, "tx-1", date(2026, 1, 1), debit="rent", credit="checking", amount_cents=1000)
        post_simple(ledger, "tx-2", date(2026, 1, 2), debit="food", credit="checking", amount_cents=500)

        assert report.largest_category(ledger) == "rent"

    def test_empty_ledger_returns_none(self, ledger):
        assert report.largest_category(ledger) is None


class TestRunningTotalsByCategory:
    def test_accumulates_in_posting_order(self, ledger):
        post_simple(ledger, "tx-1", date(2026, 1, 1), debit="food", credit="checking", amount_cents=100)
        post_simple(ledger, "tx-2", date(2026, 1, 2), debit="food", credit="checking", amount_cents=50)

        series = report.running_totals_by_category(ledger)

        assert series["food"] == [100, 150]

    def test_untouched_categories_stay_empty(self, ledger):
        post_simple(ledger, "tx-1", date(2026, 1, 1), debit="food", credit="checking", amount_cents=100)

        series = report.running_totals_by_category(ledger)

        assert series["rent"] == []
