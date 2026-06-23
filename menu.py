from datetime import date
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from data_service import add_entry, get_all_entries, delete_entry, update_entry, clear_all
from logic import (calculate_daily_norm, daily_summary, search_by_product,
                   period_stats, top_products_by_day, ACTIVITY_COEFFICIENTS, GOALS)

VERSION = "1.0.2"

BANNER = f"  УЧЁТ КАЛОРИЙ  v{VERSION}"

MAIN_MENU = """
[1] Добавить продукт
[2] Посмотреть записи за день
[3] Удалить запись
[4] Редактировать запись
[5] Рассчитать дневную норму калорий
[6] Поиск по продукту
[7] Статистика за период
[8] Все записи
[0] Выход
"""


def normalize_decimal(s: str) -> float:
    return float(s.replace(",", "."))


def _input(prompt: str) -> str:
    return input(prompt).strip()


def _float_input(prompt: str) -> float:
    while True:
        try:
            return normalize_decimal(_input(prompt))
        except ValueError:
            print("  Введите число (можно использовать , или .).")


def _int_input(prompt: str) -> int:
    while True:
        try:
            return int(_input(prompt))
        except ValueError:
            print("  Введите целое число.")


def _date_input(prompt: str, default: str = None) -> str:
    val = _input(prompt + (f" [{default}]: " if default else ": "))
    if not val and default:
        return default
    try:
        parts = val.split("-")
        assert len(parts) == 3
        date(int(parts[0]), int(parts[1]), int(parts[2]))
        return val
    except Exception:
        print("  Неверный формат даты. Используйте YYYY-MM-DD.")
        return _date_input(prompt, default)


def action_add():
    print("\nДобавить продукт")
    product = _input("Название продукта: ")
    if not product:
        print("  Название не может быть пустым.")
        return
    weight = _float_input("Вес (г): ")
    cal100 = _float_input("Калорийность на 100 г (ккал): ")
    today = str(date.today())
    d = _date_input("Дата", default=today)
    try:
        row = add_entry(product, weight, cal100, entry_date=d)
        print(f"  Добавлено: {row['product']} - {row['total_calories']} ккал (ID {row['id']})")
    except ValueError as e:
        print(f"  Ошибка: {e}")


def action_day():
    print("\nЗаписи за день")
    today = str(date.today())
    d = _date_input("Дата", default=today)
    print("Введите вашу норму (Enter - пропустить): ", end="")
    norm_str = input().strip()
    norm = float(norm_str) if norm_str else None

    summary = daily_summary(d, norm)
    if not summary["entries"]:
        print("  Нет записей за этот день.")
        return

    print(f"\n  Дата: {d}")
    print(f"  {'ID':<5} {'Продукт':<20} {'Вес (г)':<10} {'Кал/100г':<12} {'Итого ккал'}")
    print("  " + "-" * 60)
    for e in summary["entries"]:
        print(f"  {e['id']:<5} {e['product']:<20} {float(e['weight_g']):<10.1f} "
              f"{float(e['calories_per_100g']):<12.1f} {float(e['total_calories']):.1f}")
    print("  " + "-" * 60)
    print(f"  Итого за день: {summary['total_calories']} ккал")
    if norm is not None:
        status = "ПРЕВЫШЕНО" if summary["over_norm"] else "В норме"
        print(f"  Норма: {norm} ккал  |  Остаток: {summary['remaining']} ккал  |  {status}")
        if summary["over_norm"]:
            print(f"  Превышение: {summary['over_norm_pct']}%")

    if summary["entries"]:
        top = top_products_by_day(d, n=3)
        print("\n  Топ-3 по калориям за день:")
        for i, e in enumerate(top, 1):
            print(f"    {i}. {e['product']} - {float(e['total_calories']):.1f} ккал")


def action_delete():
    print("\nУдалить запись")
    eid = _int_input("ID записи: ")
    confirm = _input(f"Удалить запись #{eid}? (да/нет): ").lower()
    if confirm not in ("да", "yes", "y"):
        print("  Отменено.")
        return
    if delete_entry(eid):
        print(f"  Запись #{eid} удалена.")
    else:
        print(f"  Запись #{eid} не найдена.")


def action_update():
    print("\nРедактировать запись")
    eid = _int_input("ID записи: ")
    print("  Оставьте поле пустым, чтобы не менять его.")
    product_new = _input("Новое название продукта (Enter - пропустить): ") or None
    weight_str = _input("Новый вес (г) (Enter - пропустить): ")
    weight_new = float(weight_str) if weight_str else None
    cal_str = _input("Новая калорийность на 100 г (Enter - пропустить): ")
    cal_new = float(cal_str) if cal_str else None

    try:
        updated = update_entry(eid, product=product_new, weight_g=weight_new,
                               calories_per_100g=cal_new)
        if updated:
            print(f"  Обновлено: {updated['product']} - {updated['total_calories']} ккал")
        else:
            print(f"  Запись #{eid} не найдена.")
    except ValueError as e:
        print(f"  Ошибка: {e}")


def action_norm():
    print("\nРасчёт дневной нормы")
    weight = _float_input("Вес (кг): ")
    height = _float_input("Рост (см): ")
    age = _int_input("Возраст (лет): ")
    gender = ""
    while gender not in ("м", "ж", "m", "f"):
        gender = _input("Пол (м/ж): ").lower()
    gender_en = "male" if gender in ("м", "m") else "female"

    print("\nУровень активности:")
    labels = {
        "sedentary":   "Малоподвижный",
        "light":       "Лёгкая активность",
        "moderate":    "Умеренная активность",
        "active":      "Высокая активность",
        "very_active": "Очень высокая активность",
    }
    for k in ACTIVITY_COEFFICIENTS:
        print(f"  {k:<15} - {labels[k]}")
    activity = _input("Уровень [moderate]: ") or "moderate"

    print("\nЦель:")
    print("  loss - похудение  |  keep - поддержание  |  gain - набор")
    goal = _input("Цель [keep]: ") or "keep"

    try:
        norm = calculate_daily_norm(weight, height, age, gender_en, activity, goal)
        print(f"\n  Ваша дневная норма: {norm} ккал")
    except ValueError as e:
        print(f"  Ошибка: {e}")


def action_search():
    print("\nПоиск по продукту")
    kw = _input("Ключевое слово: ")
    try:
        results = search_by_product(kw)
        if not results:
            print("  Ничего не найдено.")
            return
        print(f"\n  Найдено записей: {len(results)}")
        print(f"  {'ID':<5} {'Дата':<12} {'Продукт':<20} {'Итого ккал'}")
        print("  " + "-" * 55)
        for e in results:
            print(f"  {e['id']:<5} {e['date']:<12} {e['product']:<20} {float(e['total_calories']):.1f}")
    except ValueError as e:
        print(f"  Ошибка: {e}")


def action_period():
    print("\nСтатистика за период")
    start = _date_input("Начало периода (YYYY-MM-DD)")
    end = _date_input("Конец периода (YYYY-MM-DD)")
    stats = period_stats(start, end)
    if not stats["entries"]:
        print("  Нет данных за выбранный период.")
        return
    print(f"\n  Период: {start} - {end}")
    print(f"  Дней с записями: {stats['days']}")
    print(f"  Всего калорий:   {stats['total_calories']} ккал")
    print(f"  Среднее в день:  {stats['avg_per_day']} ккал")


def action_all():
    print("\nВсе записи")
    entries = get_all_entries()
    if not entries:
        print("  Нет записей.")
        return
    print(f"\n  {'ID':<5} {'Дата':<12} {'Продукт':<20} {'Вес (г)':<10} {'Кал/100г':<12} {'Итого'}")
    print("  " + "-" * 68)
    for e in entries:
        print(f"  {e['id']:<5} {e['date']:<12} {e['product']:<20} {float(e['weight_g']):<10.1f} "
              f"{float(e['calories_per_100g']):<12.1f} {float(e['total_calories']):.1f}")
    print(f"\n  Всего записей: {len(entries)}")


def main():
    print(BANNER)
    actions = {
        "1": action_add,
        "2": action_day,
        "3": action_delete,
        "4": action_update,
        "5": action_norm,
        "6": action_search,
        "7": action_period,
        "8": action_all,
    }
    while True:
        print(MAIN_MENU)
        choice = _input("Выберите действие: ")
        if choice == "0":
            print("  До свидания!")
            break
        action = actions.get(choice)
        if action:
            action()
        else:
            print("  Неверный пункт меню.")


if __name__ == "__main__":
    main()
