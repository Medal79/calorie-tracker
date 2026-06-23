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


class TestCalculateDailyNorm:
    def test_male_moderate_keep(self):
        norm = logic.calculate_daily_norm(
            weight_kg=80, height_cm=180, age=30,
            gender="male", activity="moderate", goal="keep"
        )
        assert norm == pytest.approx(2759.0, abs=1)

    def test_female_sedentary_loss(self):
        norm = logic.calculate_daily_norm(
            weight_kg=60, height_cm=165, age=25,
            gender="female", activity="sedentary", goal="loss"
        )
        assert norm == pytest.approx(1114.3, abs=1)

    def test_gain_adds_500(self):
        norm_keep = logic.calculate_daily_norm(70, 175, 28, "male", "light", "keep")
        norm_gain = logic.calculate_daily_norm(70, 175, 28, "male", "light", "gain")
        assert norm_gain == pytest.approx(norm_keep + 500, abs=0.01)

    def test_loss_subtracts_500(self):
        norm_keep = logic.calculate_daily_norm(70, 175, 28, "male", "light", "keep")
        norm_loss = logic.calculate_daily_norm(70, 175, 28, "male", "light", "loss")
        assert norm_loss == pytest.approx(norm_keep - 500, abs=0.01)

    def test_invalid_gender_raises(self):
        with pytest.raises(ValueError, match="male.*female"):
            logic.calculate_daily_norm(70, 175, 28, "other")

    def test_invalid_activity_raises(self):
        with pytest.raises(ValueError, match="активности"):
            logic.calculate_daily_norm(70, 175, 28, "male", activity="super")

    def test_invalid_goal_raises(self):
        with pytest.raises(ValueError, match="цель"):
            logic.calculate_daily_norm(70, 175, 28, "male", goal="unknown")

    def test_zero_weight_raises(self):
        with pytest.raises(ValueError, match="положительным"):
            logic.calculate_daily_norm(0, 175, 28, "male")

    def test_zero_height_raises(self):
        with pytest.raises(ValueError):
            logic.calculate_daily_norm(70, 0, 28, "male")

    def test_zero_age_raises(self):
        with pytest.raises(ValueError):
            logic.calculate_daily_norm(70, 175, 0, "male")

    def test_very_active_coefficient(self):
        norm = logic.calculate_daily_norm(70, 175, 28, "male", "very_active", "keep")
        assert norm == pytest.approx(3151.6, abs=1)


class TestDailySummary:
    def test_empty_day(self):
        summary = logic.daily_summary("2024-01-10")
        assert summary["entries"] == []
        assert summary["total_calories"] == 0

    def test_total_calories_sum(self):
        ds.add_entry("Рис", 200, 344, "2024-01-10")
        ds.add_entry("Курица", 150, 165, "2024-01-10")
        summary = logic.daily_summary("2024-01-10")
        assert summary["total_calories"] == pytest.approx(935.5)

    def test_norm_not_exceeded(self):
        ds.add_entry("Яблоко", 200, 52, "2024-01-10")
        summary = logic.daily_summary("2024-01-10", daily_norm=2000)
        assert summary["over_norm"] is False
        assert summary["remaining"] == pytest.approx(2000 - 104)

    def test_norm_exceeded(self):
        ds.add_entry("Шоколад", 500, 550, "2024-01-10")
        summary = logic.daily_summary("2024-01-10", daily_norm=2000)
        assert summary["over_norm"] is True

    def test_norm_none_no_remaining(self):
        ds.add_entry("Рис", 100, 344, "2024-01-10")
        summary = logic.daily_summary("2024-01-10", daily_norm=None)
        assert summary["remaining"] is None
        assert summary["over_norm"] is None

    def test_only_counts_target_date(self):
        ds.add_entry("Рис", 100, 344, "2024-01-10")
        ds.add_entry("Гречка", 100, 329, "2024-01-11")
        summary = logic.daily_summary("2024-01-10")
        assert len(summary["entries"]) == 1
        assert summary["total_calories"] == pytest.approx(344.0)


class TestSearchByProduct:
    def test_search_found(self):
        ds.add_entry("Гречка варёная", 200, 100, "2024-01-10")
        ds.add_entry("Рис", 150, 344, "2024-01-10")
        results = logic.search_by_product("гречка")
        assert len(results) == 1
        assert results[0]["product"] == "Гречка варёная"

    def test_search_case_insensitive(self):
        ds.add_entry("КУРИЦА", 150, 165, "2024-01-10")
        results = logic.search_by_product("курица")
        assert len(results) == 1

    def test_search_partial_match(self):
        ds.add_entry("Греческий йогурт", 200, 59, "2024-01-10")
        ds.add_entry("Гречка", 100, 329, "2024-01-10")
        results = logic.search_by_product("гре")
        assert len(results) == 2

    def test_search_empty_keyword_raises(self):
        with pytest.raises(ValueError, match="пустым"):
            logic.search_by_product("")

    def test_search_whitespace_keyword_raises(self):
        with pytest.raises(ValueError):
            logic.search_by_product("   ")

    def test_search_no_results(self):
        ds.add_entry("Рис", 100, 344, "2024-01-10")
        results = logic.search_by_product("творог")
        assert results == []


class TestPeriodStats:
    def test_period_total(self):
        ds.add_entry("Рис", 100, 344, "2024-01-10")
        ds.add_entry("Гречка", 100, 329, "2024-01-11")
        ds.add_entry("Курица", 100, 165, "2024-01-12")
        stats = logic.period_stats("2024-01-10", "2024-01-12")
        assert stats["total_calories"] == pytest.approx(838.0)
        assert stats["days"] == 3

    def test_period_excludes_outside_dates(self):
        ds.add_entry("Рис", 100, 344, "2024-01-09")
        ds.add_entry("Гречка", 100, 329, "2024-01-10")
        ds.add_entry("Курица", 100, 165, "2024-01-11")
        stats = logic.period_stats("2024-01-10", "2024-01-10")
        assert stats["total_calories"] == pytest.approx(329.0)
        assert stats["days"] == 1

    def test_period_empty_returns_zeros(self):
        stats = logic.period_stats("2024-01-01", "2024-01-05")
        assert stats["total_calories"] == 0
        assert stats["days"] == 0

    def test_period_avg_per_day(self):
        ds.add_entry("Рис", 100, 200, "2024-01-10")
        ds.add_entry("Рис", 100, 200, "2024-01-10")
        ds.add_entry("Рис", 100, 600, "2024-01-11")
        stats = logic.period_stats("2024-01-10", "2024-01-11")
        assert stats["avg_per_day"] == pytest.approx(500.0)
