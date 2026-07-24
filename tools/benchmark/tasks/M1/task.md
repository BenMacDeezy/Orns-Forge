# Task: rename `Account.balance()` to `Account.current_balance()`

## Context

You are working in `ledgerkit`, a small Python library for tracking
accounts, transactions, and simple expense splitting. Every account is
represented by the `Account` class in `src/ledgerkit/accounts.py`, which
currently exposes its running balance through a method named `balance()`.

The name is a poor fit going forward (it is easily confused with the
account's balance *field*, and a future change needs the name
`current_balance` for a related concept). The method needs to be renamed
package-wide, without breaking anyone who still calls the old name.

## Goal

Rename the public method `Account.balance()` to
`Account.current_balance()` everywhere in this package, while keeping a
backward-compatible alias.

## Requirements

1. In `src/ledgerkit/accounts.py`, rename the `Account.balance()` method to
   `Account.current_balance()`. It must return exactly the same value it
   does today (the account's signed running balance in cents).
2. Keep `balance()` as a deprecated alias on `Account`: calling
   `account.balance()` must still work, must return the same value as
   `account.current_balance()`, and must emit a `DeprecationWarning`
   pointing callers at `current_balance()`.
3. Update every call site inside `src/ledgerkit/` that currently calls
   `.balance()` on an `Account` instance to call `.current_balance()`
   instead, so the package's own code never triggers the new deprecation
   warning. Search the whole `src/ledgerkit/` tree for `.balance()` call
   sites rather than assuming you already know all of them.
4. Update the test suite in `tests/` to match: tests exercising normal
   balance reads should call `.current_balance()`. Keep or add at least one
   test that calls the deprecated `.balance()` alias directly and asserts
   both that it still returns the correct value and that it raises (or
   warns) `DeprecationWarning`.
5. Do not change any other observable behavior: transaction posting,
   report output, and CLI output must be identical to before this change
   (other than the new deprecation warning when the old name is used).

## Constraints

- Do not change the CLI's or reports' output format.
- Do not touch files outside `src/ledgerkit/`, `tests/`, and this task's
  own scope. If you find something else that looks broken while working,
  leave it alone unless it blocks this rename.

## Done when

- `pytest tests/` passes.
- `ruff check .` is clean.
- No remaining call site inside `src/ledgerkit/` triggers the new
  deprecation warning (only the dedicated regression test for the
  deprecated alias should).
