# Task: convert eager f-string logging to lazy `%`-style logging

## Context

You are working in `ledgerkit`, a small Python library for tracking
accounts, transactions, and simple expense splitting. Several modules call
`logging.Logger` methods (`logger.debug`, `logger.info`, `logger.warning`,
...) with an f-string built directly in the call, e.g.:

```python
logger.info(f"added account {account.id} ({account.name})")
```

This eagerly formats the string on every call, even when that log level is
disabled, which is wasted work at that log level and inconsistent with the
standard library's lazy `%`-style logging convention:

```python
logger.info("added account %s (%s)", account.id, account.name)
```

## Goal

Convert every eager f-string used as the first argument to a `logging`
call, anywhere in `src/ledgerkit/`, to the lazy `%`-args form, without
changing anything else.

## Requirements

1. Find every call in `src/ledgerkit/` of the shape
   `logger.<level>(f"...")` (any of `debug`, `info`, `warning`, `error`,
   `critical`, `exception`) and rewrite it to pass a plain `%s`-style
   format string as the first argument, with the interpolated values
   passed as separate positional arguments, e.g.
   `logger.info("posted transaction %s: %s", transaction.id, transaction.description)`.
2. Do not touch f-strings that are **not** the first argument of a
   `logging` call — e.g. f-strings used in `raise ValueError(f"...")`,
   `click.echo(f"...")`, or `return f"..."` must be left exactly as they
   are. This task is scoped to logging calls only.
3. The text of every resulting log message, once formatted, must read
   identically to what the original f-string produced (same wording, same
   values, same punctuation) — only the mechanism (eager f-string vs. lazy
   `%`-args) changes.
4. Do not add, remove, or change the level of any log call, and do not
   change what triggers a log call.

## Constraints

- Do not touch files outside `src/ledgerkit/`.
- Do not change any non-logging string formatting (error messages, CLI
  output, docstrings) even if it uses an f-string.

## Done when

- `pytest tests/` passes (existing tests do not assert on log text, but
  must keep passing — the change must not alter any other behavior).
- `ruff check .` is clean.
- No `logger.<level>(f"...")` call remains anywhere in `src/ledgerkit/`.
