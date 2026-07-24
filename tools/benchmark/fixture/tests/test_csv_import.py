import csv
from pathlib import Path

import pytest

from ledgerkit.csv_import import load_transactions_csv


def _write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = ["id", "date", "description", "debit_account", "credit_account", "amount_cents"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


class TestLoadTransactionsCsv:
    def test_loads_one_row_into_one_transaction(self, tmp_path, chart):
        csv_path = tmp_path / "transactions.csv"
        _write_csv(
            csv_path,
            [
                {
                    "id": "tx-1",
                    "date": "2026-01-01",
                    "description": "rent",
                    "debit_account": "rent",
                    "credit_account": "checking",
                    "amount_cents": "1000",
                }
            ],
        )

        transactions = load_transactions_csv(str(csv_path), chart)

        assert len(transactions) == 1
        assert transactions[0].id == "tx-1"
        assert transactions[0].entries[0].account_id == "rent"
        assert transactions[0].entries[0].amount_cents == 1000
        assert transactions[0].entries[1].account_id == "checking"
        assert transactions[0].entries[1].amount_cents == -1000

    def test_loads_multiple_rows(self, tmp_path, chart):
        csv_path = tmp_path / "transactions.csv"
        _write_csv(
            csv_path,
            [
                {
                    "id": "tx-1",
                    "date": "2026-01-01",
                    "description": "rent",
                    "debit_account": "rent",
                    "credit_account": "checking",
                    "amount_cents": "1000",
                },
                {
                    "id": "tx-2",
                    "date": "2026-01-02",
                    "description": "groceries",
                    "debit_account": "food",
                    "credit_account": "checking",
                    "amount_cents": "500",
                },
            ],
        )

        transactions = load_transactions_csv(str(csv_path), chart)

        assert [t.id for t in transactions] == ["tx-1", "tx-2"]

    def test_unknown_account_raises(self, tmp_path, chart):
        csv_path = tmp_path / "transactions.csv"
        _write_csv(
            csv_path,
            [
                {
                    "id": "tx-1",
                    "date": "2026-01-01",
                    "description": "rent",
                    "debit_account": "does-not-exist",
                    "credit_account": "checking",
                    "amount_cents": "1000",
                }
            ],
        )

        with pytest.raises(KeyError):
            load_transactions_csv(str(csv_path), chart)
