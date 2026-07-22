import pytest

from ledgerkit.money import format_cents, split_evenly, to_cents


class TestToCents:
    def test_parses_positive_amount(self):
        assert to_cents("12.34") == 1234

    def test_parses_negative_amount(self):
        assert to_cents("-3") == -300

    def test_parses_zero(self):
        assert to_cents("0") == 0

    def test_rejects_garbage(self):
        with pytest.raises(ValueError):
            to_cents("not-a-number")


class TestFormatCents:
    def test_formats_positive(self):
        assert format_cents(1234) == "12.34"

    def test_formats_negative(self):
        assert format_cents(-305) == "-3.05"

    def test_formats_zero(self):
        assert format_cents(0) == "0.00"

    def test_pads_single_digit_cents(self):
        assert format_cents(105) == "1.05"

    def test_round_trips_with_to_cents(self):
        assert to_cents(format_cents(4321)) == 4321


class TestSplitEvenly:
    def test_splits_evenly_divisible_amount(self):
        assert split_evenly(300, 3) == [100, 100, 100]

    def test_splits_two_ways(self):
        assert split_evenly(200, 2) == [100, 100]

    def test_rejects_zero_parts(self):
        with pytest.raises(ValueError):
            split_evenly(100, 0)

    def test_rejects_negative_parts(self):
        with pytest.raises(ValueError):
            split_evenly(100, -1)
