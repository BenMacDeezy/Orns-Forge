# Task: add a `report --by-category` CLI command

## Context

You are working in `ledgerkit`, a small Python library for tracking
accounts, transactions, and simple expense splitting. The command line
front end lives in `src/ledgerkit/cli.py`; it currently has one command,
`balance`, which posts a CSV of transactions against a built-in demo chart
of accounts (`_seed_chart()`) and prints one account's resulting balance.

`src/ledgerkit/report.py` already has a `category_totals(ledger)` function
that returns a `dict[str, int]` of each category's total signed cents
across all posted transactions (entries on accounts with no `category` are
excluded, unchanged from today).

## Goal

Add a new `report` command to the CLI with a `--by-category` flag that
prints a per-category totals table.

## Requirements

1. Add a `report` command to the `cli` group in `src/ledgerkit/cli.py`,
   taking one required argument: the path to a transactions CSV file (same
   format `balance` already accepts, loaded with
   `load_transactions_csv` against the built-in demo chart from
   `_seed_chart()`).
2. Support a `--by-category` flag. When passed, the command must:
   - Post every transaction from the CSV against the demo chart.
   - Print one line per category that has a non-empty total, in the form
     `<category>: <amount>` where `<amount>` is formatted with
     `format_cents` (never a Python float).
   - Sort the printed lines by descending total (largest total first). If
     two categories have the exact same total, break the tie by category
     name in ascending alphabetical order.
   - If there are no categorized entries at all (e.g. an empty CSV, or a
     CSV that only touches uncategorized accounts), print a single line
     saying there is nothing to report (e.g. `no categorized entries`) and
     exit with status code `0` — this is a valid, non-error outcome, not a
     failure.
3. Preserve the existing failure behavior other commands already have:
   a missing or unreadable CSV file, or a CSV row referencing an account
   id that doesn't exist in the chart, must make the command exit with a
   non-zero status rather than an unhandled traceback.
4. Do not change the existing `balance` command's behavior or output.

## Constraints

- Reuse `report.category_totals` and `money.format_cents` rather than
  reimplementing totals or formatting.
- Do not add a persistence layer or any state beyond a single command
  invocation — the command loads the CSV, posts it against a fresh chart,
  prints, and exits, exactly like `balance` does today.

## Done when

- `pytest tests/` passes, including new tests for `report --by-category`
  covering: normal multi-category output sorted descending, a tie broken
  alphabetically, the empty/no-categorized-entries case, and a failure
  case (missing file or unknown account).
- `ruff check .` is clean.
