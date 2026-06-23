import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import data_service as ds
import logic


@pytest.fixture(autouse=True)
def clean_data(tmp_path, monkeypatch):
    tmp_file = str(tmp_path / "food_log.csv")
    monkeypatch.setattr(ds, "DATA_FILE", tmp_file)
    os.makedirs(os.path.dirname(tmp_file), exist_ok=True)
    yield


class TestBug01SearchCaseInsensitive:
    def test_search_finds_uppercase_product(self):
        ds.add_entry("ГРЕЧЕСКИЙ ЙОГУРТ", 200, 59, "2024-01-10")
        results = logic.search_by_product("греческий")
        assert len(results) == 1

    def test_search_finds_mixed_case(self):
        ds.add_entry("Греческий Йогурт", 200, 59, "2024-01-10")
        results = logic.search_by_product("ГРЕЧЕСКИЙ")
        assert len(results) == 1

    def test_search_partial_case_insensitive(self):
        ds.add_entry("Куриная грудка", 150, 113, "2024-01-10")
        results = logic.search_by_product("ГРУД")
        assert len(results) == 1


class TestBug02CommaDecimalInput:
    def test_normalize_comma(self):
        from menu import normalize_decimal
        assert normalize_decimal("100,5") == 100.5

    def test_normalize_dot_unchanged(self):
        from menu import normalize_decimal
        assert normalize_decimal("100.5") == 100.5

    def test_normalize_integer_string(self):
        from menu import normalize_decimal
        assert normalize_decimal("200") == 200.0


class TestImp01TopProducts:
    def test_top_returns_sorted_by_calories(self):
        ds.add_entry("Масло", 50, 900, "2024-01-10")
        ds.add_entry("Гречка", 200, 329, "2024-01-10")
        ds.add_entry("Огурец", 200, 15, "2024-01-10")
        top = logic.top_products_by_day("2024-01-10", n=3)
        assert top[0]["product"] == "Гречка"
        assert top[1]["product"] == "Масло"
        assert top[2]["product"] == "Огурец"

    def test_top_n_limits_results(self):
        ds.add_entry("Масло", 50, 900, "2024-01-10")
        ds.add_entry("Гречка", 200, 329, "2024-01-10")
        ds.add_entry("Огурец", 200, 15, "2024-01-10")
        top = logic.top_products_by_day("2024-01-10", n=2)
        assert len(top) == 2

    def test_top_empty_day(self):
        top = logic.top_products_by_day("2024-01-10")
        assert top == []


class TestChg01OverNormPercent:
    def test_over_norm_pct_when_exceeded(self):
        ds.add_entry("Шоколад", 500, 550, "2024-01-10")
        summary = logic.daily_summary("2024-01-10", daily_norm=2000)
        assert summary["over_norm_pct"] == pytest.approx(37.5)

    def test_over_norm_pct_when_not_exceeded(self):
        ds.add_entry("Яблоко", 100, 52, "2024-01-10")
        summary = logic.daily_summary("2024-01-10", daily_norm=2000)
        assert summary["over_norm_pct"] == pytest.approx(0.0)

    def test_over_norm_pct_none_when_no_norm(self):
        ds.add_entry("Яблоко", 100, 52, "2024-01-10")
        summary = logic.daily_summary("2024-01-10", daily_norm=None)
        assert summary.get("over_norm_pct") is None
