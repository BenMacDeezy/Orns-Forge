import pytest

from ledgerkit.accounts import Account, AccountType, ChartOfAccounts


class TestAccount:
    def test_starts_at_zero_balance(self):
        account = Account(id="a", name="A", type=AccountType.ASSET)
        assert account.balance() == 0

    def test_apply_adjusts_balance(self):
        account = Account(id="a", name="A", type=AccountType.ASSET)
        account._apply(500)
        account._apply(-200)
        assert account.balance() == 300

    def test_category_defaults_to_none(self):
        account = Account(id="a", name="A", type=AccountType.ASSET)
        assert account.category is None

    def test_category_can_be_set(self):
        account = Account(id="rent", name="Rent", type=AccountType.EXPENSE, category="rent")
        assert account.category == "rent"


class TestChartOfAccounts:
    def test_add_then_get(self):
        chart = ChartOfAccounts()
        added = chart.add(Account(id="checking", name="Checking", type=AccountType.ASSET))
        assert chart.get("checking") is added

    def test_add_duplicate_id_raises(self):
        chart = ChartOfAccounts()
        chart.add(Account(id="checking", name="Checking", type=AccountType.ASSET))
        with pytest.raises(ValueError):
            chart.add(Account(id="checking", name="Checking 2", type=AccountType.ASSET))

    def test_get_missing_account_raises(self):
        chart = ChartOfAccounts()
        with pytest.raises(KeyError):
            chart.get("does-not-exist")

    def test_all_returns_every_account(self):
        chart = ChartOfAccounts()
        chart.add(Account(id="a", name="A", type=AccountType.ASSET))
        chart.add(Account(id="b", name="B", type=AccountType.LIABILITY))
        ids = {account.id for account in chart.all()}
        assert ids == {"a", "b"}
