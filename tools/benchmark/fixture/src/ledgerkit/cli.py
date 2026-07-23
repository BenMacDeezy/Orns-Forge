"""Command-line front end for ledgerkit."""

from __future__ import annotations

import logging

import click

from .accounts import Account, AccountType, ChartOfAccounts
from .csv_import import load_transactions_csv
from .ledger import Ledger
from .money import format_cents

logger = logging.getLogger(__name__)


def _seed_chart() -> ChartOfAccounts:
    """The built-in demo chart of accounts the CLI posts CSV transactions
    against."""
    chart = ChartOfAccounts()
    chart.add(Account(id="checking", name="Checking", type=AccountType.ASSET))
    chart.add(Account(id="food", name="Food", type=AccountType.EXPENSE, category="food"))
    chart.add(Account(id="rent", name="Rent", type=AccountType.EXPENSE, category="rent"))
    chart.add(Account(id="utilities", name="Utilities", type=AccountType.EXPENSE, category="utilities"))
    return chart


@click.group()
def cli() -> None:
    """ledgerkit command-line interface."""


@click.command(name="balance")
@click.argument("account_id")
@click.argument("transactions_csv", type=click.Path(exists=True))
def balance_cmd(account_id: str, transactions_csv: str) -> None:
    """Post TRANSACTIONS_CSV against the built-in demo chart of accounts and
    print ACCOUNT_ID's resulting balance."""
    chart = _seed_chart()
    ledger = Ledger(chart)
    for transaction in load_transactions_csv(transactions_csv, chart):
        ledger.post(transaction)
    account = chart.get(account_id)
    logger.info(f"computed balance for {account_id} from {transactions_csv}")
    click.echo(f"{account.name}: {format_cents(account.balance())}")


cli.add_command(balance_cmd)


if __name__ == "__main__":
    cli()
