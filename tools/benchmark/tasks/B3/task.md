# Bug: `running_totals_by_category` crashes on an unexpected category

## Context

You are working in `ledgerkit`, a small Python library for tracking
accounts, transactions, and simple expense splitting. Accounts have a
free-form `category` field (see `Account` in `src/ledgerkit/accounts.py`):
"it is optional... used to group expense/income accounts in reports" and
nothing restricts it to a fixed set of values anywhere accounts are
created. `report.py`'s `running_totals_by_category(ledger)` is supposed to
return, for each category present in the ledger, the running (cumulative)
balance after every transaction entry touching that category, in posting
order.

## Bug report

Posting a transaction to an account whose category is anything other than
`"food"`, `"rent"`, or `"utilities"`, and then calling
`running_totals_by_category`, crashes with `KeyError` naming the
unexpected category. For example:

```python
from datetime import date
from ledgerkit.accounts import Account, AccountType, ChartOfAccounts
from ledgerkit.ledger import Ledger
from ledgerkit.transactions import Entry, Transaction
from ledgerkit import report

chart = ChartOfAccounts()
chart.add(Account(id="checking", name="Checking", type=AccountType.ASSET))
chart.add(Account(id="travel", name="Travel", type=AccountType.EXPENSE, category="travel"))

ledger = Ledger(chart)
ledger.post(Transaction(
    id="tx-1", date=date(2026, 1, 1), description="flight",
    entries=[Entry("checking", -500), Entry("travel", 500)],
))

report.running_totals_by_category(ledger)
# raises KeyError: 'travel'
```

(`Account.category` places no restriction on which strings are valid —
`"travel"` is exactly as legitimate a category as `"food"`.)

## Root cause

`running_totals_by_category` in `src/ledgerkit/report.py` pre-seeds its
`totals`/`series` dicts only from a hardcoded module-level tuple,
`_KNOWN_CATEGORIES = ("food", "rent", "utilities")`. `totals[category] +=
...` then raises `KeyError` the first time it sees any other category
string, even though nothing elsewhere in the codebase restricts
`Account.category` to those three values.

## Fix

Fix `running_totals_by_category` so it never assumes a fixed category set.
Any category actually present on an account touched by a transaction must
be handled without crashing. At the same time, preserve the function's
existing behavior for categories that exist in the chart but are never
touched by any transaction: today those still appear in the returned dict
with an empty list (see `tests/test_report.py`'s
`test_untouched_categories_stay_empty`), so the fix should keep deriving
the known-categories set from the chart passed in (`ledger.chart`) at call
time, rather than switching to a scheme that only reports categories that
were actually posted to.

## Requirements

1. Fix `running_totals_by_category` in `src/ledgerkit/report.py` so
   posting to an account with any category value no longer raises
   `KeyError`.
2. Preserve existing behavior: every category present on any account in
   `ledger.chart` appears as a key in the returned dict (with an empty
   list if untouched), in the same shape as today.
3. Add a regression test in `tests/test_report.py` that posts an entry to
   an account whose category is not `"food"`, `"rent"`, or `"utilities"`
   (e.g. `"travel"`) and asserts `running_totals_by_category` returns the
   correct running totals for it instead of raising.
4. Do not change the behavior of the three previously-hardcoded
   categories.

## Done when

- `pytest tests/` passes, including the new regression test.
- `ruff check .` is clean.
