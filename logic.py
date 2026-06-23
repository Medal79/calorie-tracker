from data_service import get_by_date, get_all_entries

ACTIVITY_COEFFICIENTS = {
    "sedentary":   1.2,
    "light":       1.375,
    "moderate":    1.55,
    "active":      1.725,
    "very_active": 1.9,
}

GOALS = {
    "loss": -500,
    "keep": 0,
    "gain": +500,
}


def calculate_daily_norm(weight_kg: float, height_cm: float,
                         age: int, gender: str,
                         activity: str = "moderate",
                         goal: str = "keep") -> float:
    if weight_kg <= 0:
        raise ValueError("Вес должен быть положительным.")
    if height_cm <= 0:
        raise ValueError("Рост должен быть положительным.")
    if age <= 0:
        raise ValueError("Возраст должен быть положительным.")
    if gender not in ("male", "female"):
        raise ValueError("Пол: 'male' или 'female'.")
    if activity not in ACTIVITY_COEFFICIENTS:
        raise ValueError(f"Неверный уровень активности: {activity}.")
    if goal not in GOALS:
        raise ValueError(f"Неверная цель: {goal}.")

    if gender == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    tdee = bmr * ACTIVITY_COEFFICIENTS[activity]
    norm = tdee + GOALS[goal]
    return round(norm, 2)


def daily_summary(target_date: str, daily_norm: float = None) -> dict:
    entries = get_by_date(target_date)
    total = sum(float(e["total_calories"]) for e in entries)
    total = round(total, 2)

    result = {
        "entries": entries,
        "total_calories": total,
        "norm": daily_norm,
        "remaining": None,
        "over_norm": None,
        "over_norm_pct": None,
    }

    if daily_norm is not None:
        remaining = round(daily_norm - total, 2)
        result["remaining"] = remaining
        result["over_norm"] = total > daily_norm
        if daily_norm > 0:
            pct = max(0.0, round((total / daily_norm * 100) - 100, 2))
        else:
            pct = 0.0
        result["over_norm_pct"] = pct

    return result


def search_by_product(keyword: str) -> list:
    if not keyword or not keyword.strip():
        raise ValueError("Ключевое слово не может быть пустым.")
    kw = keyword.strip().lower()
    return [e for e in get_all_entries() if kw in e["product"].lower()]


def top_products_by_day(target_date: str, n: int = 3) -> list:
    entries = get_by_date(target_date)
    sorted_entries = sorted(entries, key=lambda e: float(e["total_calories"]), reverse=True)
    return sorted_entries[:n]


def period_stats(start_date: str, end_date: str) -> dict:
    all_entries = get_all_entries()
    filtered = [e for e in all_entries if start_date <= e["date"] <= end_date]
    if not filtered:
        return {"entries": [], "total_calories": 0, "days": 0, "avg_per_day": 0}

    days = len({e["date"] for e in filtered})
    total = round(sum(float(e["total_calories"]) for e in filtered), 2)
    avg = round(total / days, 2) if days else 0

    return {
        "entries": filtered,
        "total_calories": total,
        "days": days,
        "avg_per_day": avg,
    }
