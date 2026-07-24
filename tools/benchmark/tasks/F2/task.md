# Task: add an `import` CLI command with row validation and dedupe

## Context

You are working in `ledgerkit`, a small Python library for tracking
accounts, transactions, and simple expense splitting. The command line
front end lives in `src/ledgerkit/cli.py`. Transactions are already loaded
from CSV by `src/ledgerkit/csv_import.py`'s `load_transactions_csv(path,
chart)`, which reads rows with columns `id, date, description,
debit_account, credit_account, amount_cents` and turns each row into a
two-entry `Transaction`. Today that function assumes every row is
well-formed and lets a malformed row raise whatever exception the
underlying parsing raises (e.g. a raw `ValueError` from `date.fromisoformat`
or `int(...)`, or a `KeyError` from an unknown account).

## Goal

Add an `import` command to the CLI that loads a transactions CSV against
the built-in demo chart, validates every row up front with clear error
reporting, skips exact duplicate rows instead of double-posting them, and
prints a summary.

## Requirements

1. Add an `import` command to the `cli` group in `src/ledgerkit/cli.py`,
   taking one required argument: the path to a transactions CSV file using
   the same column schema `load_transactions_csv` already expects (`id,
   date, description, debit_account, credit_account, amount_cents`).
2. **Validation.** Before posting anything, validate every row:
   - `date` must parse as `YYYY-MM-DD`.
   - `amount_cents` must parse as an integer.
   - `debit_account` and `credit_account` must both exist in the built-in
     demo chart.
   If any row fails validation, the command must not post *any*
   transaction from the file (all-or-nothing), must print a clear message
   identifying which row failed (its 1-based row number and, if available,
   its `id` column) and what was wrong with it, and must exit with a
   non-zero status — never an unhandled traceback.
3. **Deduplication.** Two rows are exact duplicates if they have identical
   `id`, `date`, `description`, `debit_account`, `credit_account`, and
   `amount_cents` values. If the input file contains exact duplicate rows,
   only the first occurrence of each is posted; later occurrences are
   skipped (not posted again, not treated as an error). This makes
   importing a file that happens to contain repeated rows idempotent: the
   resulting ledger only reflects each distinct row once, no matter how
   many times that row appears in the file.
4. **Success output.** On success, print a one-line summary reporting how
   many transactions were posted and how many duplicate rows were skipped,
   and exit with status code `0`.

## Constraints

- Do not change `load_transactions_csv`'s existing signature or behavior;
  build the new validation/dedupe logic in the CLI layer (or a small
  helper you add), reusing what already exists rather than duplicating CSV
  parsing from scratch.
- Do not add a persistence layer or any state beyond a single command
  invocation. "Idempotent" here means duplicate rows *within the same
  input file* are only posted once — it does not require remembering what
  was imported by a previous, separate run of the command.
- Do not change the existing `balance` command's behavior or output.

## Done when

- `pytest tests/` passes, including new tests covering: a normal import
  with several distinct rows, a file containing exact duplicate rows
  (only the first of each posted), a file with an invalid row (nothing
  posted, non-zero exit, clear message), and a file referencing an unknown
  account (nothing posted, non-zero exit).
- `ruff check .` is clean.
