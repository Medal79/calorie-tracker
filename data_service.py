import csv
import os
from datetime import date

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "food_log.csv")
FIELDNAMES = ["id", "date", "product", "weight_g", "calories_per_100g", "total_calories"]


def _ensure_file():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def _next_id(rows: list) -> int:
    if not rows:
        return 1
    return max(int(r["id"]) for r in rows) + 1


def load_all() -> list:
    _ensure_file()
    with open(DATA_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_all(rows: list):
    _ensure_file()
    with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def add_entry(product: str, weight_g: float, calories_per_100g: float,
              entry_date: str = None) -> dict:
    if not product or not product.strip():
        raise ValueError("Название продукта не может быть пустым.")
    if weight_g <= 0:
        raise ValueError("Вес должен быть положительным числом.")
    if calories_per_100g < 0:
        raise ValueError("Калорийность не может быть отрицательной.")

    if entry_date is None:
        entry_date = str(date.today())

    total = round(weight_g * calories_per_100g / 100, 2)
    rows = load_all()
    row = {
        "id": _next_id(rows),
        "date": entry_date,
        "product": product.strip(),
        "weight_g": weight_g,
        "calories_per_100g": calories_per_100g,
        "total_calories": total,
    }
    rows.append(row)
    save_all(rows)
    return row


def get_all_entries() -> list:
    return load_all()


def get_by_date(target_date: str) -> list:
    return [r for r in load_all() if r["date"] == target_date]


def delete_entry(entry_id: int) -> bool:
    rows = load_all()
    new_rows = [r for r in rows if int(r["id"]) != entry_id]
    if len(new_rows) == len(rows):
        return False
    save_all(new_rows)
    return True


def update_entry(entry_id: int, product: str = None, weight_g: float = None,
                 calories_per_100g: float = None) -> dict:
    rows = load_all()
    updated = None
    for row in rows:
        if int(row["id"]) == entry_id:
            if product is not None:
                if not product.strip():
                    raise ValueError("Название продукта не может быть пустым.")
                row["product"] = product.strip()
            if weight_g is not None:
                if weight_g <= 0:
                    raise ValueError("Вес должен быть положительным числом.")
                row["weight_g"] = weight_g
            if calories_per_100g is not None:
                if calories_per_100g < 0:
                    raise ValueError("Калорийность не может быть отрицательной.")
                row["calories_per_100g"] = calories_per_100g
            row["total_calories"] = round(
                float(row["weight_g"]) * float(row["calories_per_100g"]) / 100, 2
            )
            updated = row
            break
    if updated:
        save_all(rows)
    return updated


def clear_all():
    save_all([])
