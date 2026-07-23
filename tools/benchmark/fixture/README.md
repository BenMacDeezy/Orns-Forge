# ledgerkit

A small double-entry-flavored ledger library for tracking accounts,
transactions, and simple expense splitting. Amounts are always integer
cents; nothing here uses floats for money.

## Install

```
pip install -e .
```

## Quick start

```python
from datetime import date

from ledgerkit.accounts import Account, AccountType, ChartOfAccounts
from ledgerkit.ledger import Ledger
from ledgerkit.transactions import Entry, Transaction

chart = ChartOfAccounts()
checking = chart.add(Account(id="checking", name="Checking", type=AccountType.ASSET))
rent = chart.add(Account(id="rent", name="Rent", type=AccountType.EXPENSE, category="rent"))

ledger = Ledger(chart)
ledger.post(Transaction(
    id="tx-1",
    date=date(2026, 1, 1),
    description="January rent",
    entries=[Entry("checking", -120000), Entry("rent", 120000)],
))

print(checking.get_balance())    # -> -1000.00
```

See `docs/architecture.md` for the module layout and design rationale.

## Date-range queries

`Ledger` supports filtering by date range with inclusive endpoints:

```python
ledger.transactions_between(start=date(2026, 1, 1), end=date(2026, 1, 31))
```

## Splitting an expense

`Ledger.split_expense` records one payer's outlay and debits each
participant's account for their even share:

```python
ledger.split_expense(
    tx_id="split-1",
    tx_date=date(2026, 1, 1),
    description="groceries",
    payer_id="checking",
    participant_ids=["food", "rent"],
    total_cents=200,
)
```

## Importing transactions from CSV

`ledgerkit.csv_import.load_transactions_csv(path, chart)` reads a CSV file
of `id, date, description, debit_account, credit_account, amount_cents`
rows into a list of `Transaction` objects, ready to `ledger.post(...)`.

## Reports

See `ledgerkit/report.py` for balance and category-total reports built on
top of a `Ledger`.

## Command line

```
python -m ledgerkit.cli balance checking transactions.csv
```

## Running the tests

```
pytest tests/
```
