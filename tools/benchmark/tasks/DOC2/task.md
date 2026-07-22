# Task: document the undocumented functions in report.py

## Context

You are working in `ledgerkit`, a small Python library for tracking
accounts, transactions, and simple expense splitting. `src/ledgerkit/
report.py` holds a handful of read-only report functions over a `Ledger`.
Some of them already have docstrings (`account_balances`,
`running_totals_by_category`); three do not: `total_balance`,
`category_totals`, and `largest_category`.

## Goal

Add an accurate docstring to each of the three undocumented functions in
`src/ledgerkit/report.py`. "Accurate" means the docstring must describe
what the function actually does by reading its implementation and, where
useful, its tests — not what its name might suggest it does at a glance.
At least one of these three has a behavior that a docstring written from
the name alone would get wrong; read the code carefully.

## Requirements

For each of `total_balance`, `category_totals`, and `largest_category` in
`src/ledgerkit/report.py`, add a docstring that states:

1. What the function takes and returns (types, in the style already used
   by the module's other docstrings).
2. What it computes, precisely enough that a reader would not be
   surprised by its actual behavior on realistic input. In particular:
   - For `category_totals`: does it include every account that was ever
     touched by a transaction, or does it treat some accounts specially?
     Check what happens to entries posted to an account that has no
     `category` set (`category is None`) and say so explicitly if it
     differs from "every touched account is included."
   - For `largest_category`: what does it return when the ledger has no
     categorized entries at all? And if two categories are tied for the
     highest total, which one does it return — is the tie-break arbitrary,
     or deterministic? State the actual behavior.
   - For `total_balance`: what does it return for an empty ledger, and is
     it expected to always be a particular value (e.g. always zero) for
     any ledger where every posted transaction balances, or can it be
     nonzero?

## Constraints

- Do not change any function's behavior — this is a documentation-only
  task. If you notice what looks like a bug while documenting a function,
  document the *actual* current behavior accurately; do not silently fix
  it.
- Match the docstring style already used elsewhere in `report.py` (a short
  summary line, plain prose, no invented markup conventions the rest of
  the file doesn't use).

## Done when

- `total_balance`, `category_totals`, and `largest_category` each have a
  docstring in `src/ledgerkit/report.py`.
- Each docstring's description of behavior matches what the function
  actually does, including the edge cases called out above (uncategorized
  entries, empty ledger, ties).
- `pytest tests/` still passes (this task doesn't touch behavior, but must
  not break anything).
- `ruff check .` is clean.
