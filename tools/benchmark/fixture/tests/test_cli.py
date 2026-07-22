import csv

from click.testing import CliRunner

from ledgerkit.cli import cli


def _write_csv(path, rows):
    fieldnames = ["id", "date", "description", "debit_account", "credit_account", "amount_cents"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


class TestBalanceCommand:
    def test_prints_resulting_balance(self, tmp_path):
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

        runner = CliRunner()
        result = runner.invoke(cli, ["balance", "checking", str(csv_path)])

        assert result.exit_code == 0
        assert "Checking: -10.00" in result.output

    def test_unknown_account_id_fails(self, tmp_path):
        csv_path = tmp_path / "transactions.csv"
        _write_csv(csv_path, [])

        runner = CliRunner()
        result = runner.invoke(cli, ["balance", "does-not-exist", str(csv_path)])

        assert result.exit_code != 0

    def test_missing_csv_file_fails(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["balance", "checking", "/no/such/file.csv"])

        assert result.exit_code != 0
