# Bug: splitting an odd amount loses or gains a cent

## Context

You are working in `ledgerkit`, a small Python library for tracking
accounts, transactions, and simple expense splitting. `Ledger.split_expense`
(in `src/ledgerkit/ledger.py`) records one payer's outlay and debits each
participant's account for an even share, using
`money.split_evenly(total_cents, num_parts)` to compute the shares.

## Bug report

Splitting an amount that does not divide evenly across the participants
fails. For example, splitting 100 cents three ways currently raises
`ValueError` from inside `Ledger.post` complaining the transaction "does
not balance" — the payer's entry is `-100` cents but the three participant
shares computed by `split_evenly` only sum to `99` cents, so the
transaction's entries don't sum to zero and posting is rejected.

Reproduce it:

```python
from datetime import date
from ledgerkit.accounts import Account, AccountType, ChartOfAccounts
from ledgerkit.ledger import Ledger

chart = ChartOfAccounts()
chart.add(Account(id="checking", name="Checking", type=AccountType.ASSET))
chart.add(Account(id="a", name="A", type=AccountType.EXPENSE))
chart.add(Account(id="b", name="B", type=AccountType.EXPENSE))
chart.add(Account(id="c", name="C", type=AccountType.EXPENSE))

ledger = Ledger(chart)
ledger.split_expense(
    tx_id="split-1", tx_date=date(2026, 1, 1), description="test",
    payer_id="checking", participant_ids=["a", "b", "c"], total_cents=100,
)
# raises ValueError: transaction split-1 does not balance: off by -1 cents
```

## Root cause

Look at `split_evenly` in `src/ledgerkit/money.py`. It computes
`share = total_cents // num_parts` and returns `[share] * num_parts`,
which silently drops the remainder (`total_cents % num_parts`) instead of
distributing it. Any evenly-divisible split (the only kind the current
tests exercise) happens to work by coincidence; any split that isn't
evenly divisible loses `total_cents % num_parts` cents.

## Fix

Fix `split_evenly` so that the returned list of shares always sums to
exactly `total_cents`, for any positive `num_parts`. The conventional way
to do this is a largest-remainder / round-robin allocation: give the base
`share = total_cents // num_parts` to every part, then distribute the
`total_cents % num_parts` leftover cents one at a time to the first that
many entries in the returned list, so the earliest participants get one
extra cent each when the split doesn't divide evenly. (Evenly-divisible
splits must keep returning exactly what they return today — this is a
generalization, not a behavior change for the case that already worked.)

## Requirements

1. Fix `split_evenly` in `src/ledgerkit/money.py` per the above.
2. Add a regression test in `tests/test_money.py` proving
   `sum(split_evenly(total_cents, num_parts)) == total_cents` for at least
   one case where `total_cents % num_parts != 0` (e.g. `split_evenly(100,
   3)`), and asserting the exact expected share list, not just the sum.
3. Add a regression test in `tests/test_ledger.py` proving
   `Ledger.split_expense` no longer raises when the split amount doesn't
   divide evenly across participants (e.g. splitting 100 cents three
   ways), and that the resulting account balances still sum to the total.
4. Do not change the behavior of any evenly-divisible split.

## Done when

- `pytest tests/` passes, including the new regression tests.
- `ruff check .` is clean.
