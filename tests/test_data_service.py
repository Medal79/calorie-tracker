import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import data_service as ds


@pytest.fixture(autouse=True)
def clean_data(tmp_path, monkeypatch):
    tmp_file = str(tmp_path / "food_log.csv")
    monkeypatch.setattr(ds, "DATA_FILE", tmp_file)
    os.makedirs(os.path.dirname(tmp_file), exist_ok=True)
    yield


class TestAddEntry:
    def test_add_basic(self):
        row = ds.add_entry("Гречка", 200, 329, "2024-01-10")
        assert row["product"] == "Гречка"
        assert float(row["weight_g"]) == 200
        assert float(row["calories_per_100g"]) == 329
        assert float(row["total_calories"]) == pytest.approx(658.0)
        assert row["date"] == "2024-01-10"
        assert int(row["id"]) == 1

    def test_add_multiple_ids_increment(self):
        ds.add_entry("Яблоко", 150, 52, "2024-01-10")
        ds.add_entry("Банан", 120, 89, "2024-01-10")
        rows = ds.load_all()
        assert len(rows) == 2
        assert int(rows[0]["id"]) == 1
        assert int(rows[1]["id"]) == 2

    def test_add_strips_whitespace(self):
        row = ds.add_entry("  Творог  ", 100, 101, "2024-01-10")
        assert row["product"] == "Творог"

    def test_add_empty_product_raises(self):
        with pytest.raises(ValueError, match="пустым"):
            ds.add_entry("", 100, 200, "2024-01-10")

    def test_add_whitespace_product_raises(self):
        with pytest.raises(ValueError):
            ds.add_entry("   ", 100, 200, "2024-01-10")

    def test_add_zero_weight_raises(self):
        with pytest.raises(ValueError, match="положительным"):
            ds.add_entry("Рис", 0, 344, "2024-01-10")

    def test_add_negative_weight_raises(self):
        with pytest.raises(ValueError):
            ds.add_entry("Рис", -50, 344, "2024-01-10")

    def test_add_negative_calories_raises(self):
        with pytest.raises(ValueError, match="отрицательной"):
            ds.add_entry("Огурец", 100, -5, "2024-01-10")

    def test_add_zero_calories_allowed(self):
        row = ds.add_entry("Вода", 500, 0, "2024-01-10")
        assert float(row["total_calories"]) == 0

    def test_calories_calculation(self):
        row = ds.add_entry("Масло", 10, 900, "2024-01-10")
        assert float(row["total_calories"]) == pytest.approx(90.0)

    def test_default_date_is_today(self):
        from datetime import date
        row = ds.add_entry("Кофе", 200, 2)
        assert row["date"] == str(date.today())


class TestGetByDate:
    def test_filter_by_date(self):
        ds.add_entry("Рис", 100, 344, "2024-01-10")
        ds.add_entry("Гречка", 100, 329, "2024-01-11")
        ds.add_entry("Курица", 150, 165, "2024-01-10")
        result = ds.get_by_date("2024-01-10")
        assert len(result) == 2
        assert all(r["date"] == "2024-01-10" for r in result)

    def test_empty_date_returns_empty_list(self):
        ds.add_entry("Рис", 100, 344, "2024-01-10")
        result = ds.get_by_date("2024-01-15")
        assert result == []


class TestDeleteEntry:
    def test_delete_existing(self):
        row = ds.add_entry("Рис", 100, 344, "2024-01-10")
        eid = int(row["id"])
        assert ds.delete_entry(eid) is True
        assert ds.get_all_entries() == []

    def test_delete_nonexistent_returns_false(self):
        assert ds.delete_entry(999) is False

    def test_delete_correct_entry_among_multiple(self):
        r1 = ds.add_entry("Рис", 100, 344, "2024-01-10")
        r2 = ds.add_entry("Гречка", 100, 329, "2024-01-10")
        ds.delete_entry(int(r1["id"]))
        rows = ds.get_all_entries()
        assert len(rows) == 1
        assert rows[0]["product"] == "Гречка"


class TestUpdateEntry:
    def test_update_product_name(self):
        row = ds.add_entry("Рис", 100, 344, "2024-01-10")
        updated = ds.update_entry(int(row["id"]), product="Рис варёный")
        assert updated["product"] == "Рис варёный"

    def test_update_weight_recalculates_calories(self):
        row = ds.add_entry("Гречка", 100, 329, "2024-01-10")
        updated = ds.update_entry(int(row["id"]), weight_g=200)
        assert float(updated["total_calories"]) == pytest.approx(658.0)

    def test_update_calories_per_100g_recalculates(self):
        row = ds.add_entry("Масло", 10, 500, "2024-01-10")
        updated = ds.update_entry(int(row["id"]), calories_per_100g=900)
        assert float(updated["total_calories"]) == pytest.approx(90.0)

    def test_update_nonexistent_returns_none(self):
        result = ds.update_entry(999, product="Что-то")
        assert result is None

    def test_update_empty_product_raises(self):
        row = ds.add_entry("Рис", 100, 344, "2024-01-10")
        with pytest.raises(ValueError):
            ds.update_entry(int(row["id"]), product="")

    def test_update_zero_weight_raises(self):
        row = ds.add_entry("Рис", 100, 344, "2024-01-10")
        with pytest.raises(ValueError):
            ds.update_entry(int(row["id"]), weight_g=0)

    def test_update_negative_calories_raises(self):
        row = ds.add_entry("Рис", 100, 344, "2024-01-10")
        with pytest.raises(ValueError):
            ds.update_entry(int(row["id"]), calories_per_100g=-10)


class TestPersistence:
    def test_data_persists_between_calls(self):
        ds.add_entry("Творог", 200, 101, "2024-01-10")
        loaded = ds.load_all()
        assert len(loaded) == 1
        assert loaded[0]["product"] == "Творог"

    def test_clear_all(self):
        ds.add_entry("Рис", 100, 344, "2024-01-10")
        ds.clear_all()
        assert ds.load_all() == []
