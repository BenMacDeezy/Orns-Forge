# Task: fix README.md to match the current code

## Context

You are working in `ledgerkit`, a small Python library for tracking
accounts, transactions, and simple expense splitting. `README.md` is meant
to be a working, copy-pasteable introduction to the package, but it has
drifted out of sync with the actual code in `src/ledgerkit/`.

## Goal

Bring `README.md` back in sync with the current code: every method or
parameter name it shows must be real, every example's claimed output must
match what running that example actually produces, and every link/
cross-reference must point at something that exists.

## Requirements

Go through `README.md` top to bottom and fix everything you find wrong.
At minimum, check and fix these:

1. **Quick start example.** It calls a method on `Account` to read the
   balance. Confirm the method name it uses actually exists on `Account`
   in `src/ledgerkit/accounts.py`; if it doesn't, use the real method
   name.
2. **Quick start example's printed output.** The example posts a
   transaction and then shows a comment claiming what the printed balance
   is. Actually work out (by reading `Account.balance()` and
   `money.format_cents`) what that example's code would really print, and
   fix the comment if it's wrong.
3. **Date-range queries example.** It calls `Ledger.transactions_between`
   with two keyword arguments. Check `Ledger.transactions_between`'s real
   parameter names in `src/ledgerkit/ledger.py` and fix the example if the
   keywords shown don't match (calling the example as shown must not raise
   `TypeError` once fixed).
4. **Cross-reference to a design-rationale doc.** The README points readers
   to a file for "module layout and design rationale". Confirm that file
   exists in this repository; if it doesn't, either remove the dangling
   reference or point it at something that does exist — do not leave a
   link to a nonexistent file.
5. While you're reading through the rest of the README (Splitting an
   expense, Importing transactions from CSV, Reports, Command line,
   Running the tests), fix anything else you find that doesn't match the
   current code in `src/ledgerkit/`.

## Constraints

- Do not change any code in `src/ledgerkit/` or `tests/` — this is a
  documentation-only task. If a README example is wrong because the code
  itself has a bug, fix the README's description of the *actual* current
  behavior rather than changing the code.
- Keep the README's existing structure and tone; fix inaccuracies, don't
  rewrite sections that are already correct.

## Done when

- Every example shown in `README.md` can be copy-pasted and run against
  the current code in `src/ledgerkit/` without raising an error caused by
  a wrong name.
- Every claimed example output in `README.md` matches what that example's
  code actually produces.
- Every file `README.md` references by path exists in the repository.
- `pytest tests/` still passes (this task doesn't touch code, but must not
  break anything).
