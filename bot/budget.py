import calendar
from datetime import datetime
from typing import Any

from sheets import (
    delete_budget_row,
    get_budget_rows,
    get_categories_spending,
    upsert_budget_row,
)


class BudgetManager:
    """Управление месячным бюджетом и лимитами по категориям.

    Использует лист Budgets (Month, Category, Limit, Type) в Google Sheets.
    Type="budget" — общий бюджет на месяц.
    Type="limit" — лимит на категорию.
    """

    _budget_cache: dict[str, Any] = {}
    _spending_cache: dict[str, Any] = {}

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def current_month() -> str:
        """Вернуть "YYYY-MM" для текущего месяца."""
        now = datetime.now()
        return now.strftime("%Y-%m")

    @staticmethod
    def _month_name(ym: str) -> str:
        """Вернуть английское название месяца из "YYYY-MM" (напр. "June")."""
        try:
            parts = ym.split("-")
            return calendar.month_name[int(parts[1])]
        except (IndexError, ValueError):
            return ""

    @staticmethod
    def _format_progress_bar(pct: float, width: int = 10) -> str:
        """Прогресс-бар: ██████░░░░ (filled=█, empty=░).

        pct: 0.0–1.0 (допускается >1 для превышения).
        """
        filled = min(width, int(round(pct * width, 1)))
        return "█" * filled + "░" * (width - filled)

    @classmethod
    def _invalidate_cache(cls) -> None:
        """Сбросить кэши Budgets и spending."""
        cls._budget_cache.clear()
        cls._spending_cache.clear()

    @classmethod
    def invalidate_after_transaction(cls) -> None:
        """Вызвать после добавления транзакции в Transactions sheet.

        Сбрасывает только spending-кэш (категории и общий потрачено),
        но не трогает кэш строк Budgets (лимиты не менялись).
        """
        cls._spending_cache.clear()

    @classmethod
    def _get_cached_budget_rows(cls) -> list[list]:
        """Получить строки Budgets с кэшированием."""
        if "rows" not in cls._budget_cache:
            cls._budget_cache["rows"] = get_budget_rows()
        return cls._budget_cache["rows"]

    @classmethod
    def _get_cached_spending(cls, month: str) -> dict[str, float]:
        """Получить траты по категориям за месяц с кэшированием."""
        key = f"spending_{month}"
        if key not in cls._spending_cache:
            cls._spending_cache[key] = get_categories_spending(month)
        return cls._spending_cache[key]

    # ── общий бюджет ──────────────────────────────────────────────────

    @classmethod
    def get_budget(cls, month: str | None = None) -> float | None:
        """Вернуть общий бюджет на месяц или None, если не установлен."""
        month = month or cls.current_month()
        rows = cls._get_cached_budget_rows()
        for r in rows:
            if len(r) >= 4 and r[0] == month and r[3] == "budget":
                try:
                    return float(r[2])
                except (ValueError, TypeError):
                    return None
        return None

    @classmethod
    def set_budget(cls, amount: float, month: str | None = None) -> bool:
        """Установить общий бюджет на месяц. amount > 0."""
        if amount <= 0:
            return False
        month = month or cls.current_month()
        ok = upsert_budget_row(month, "Общий", amount, "budget")
        if ok:
            cls._invalidate_cache()
        return ok

    @classmethod
    def delete_budget(cls, month: str | None = None) -> bool:
        """Удалить общий бюджет на месяц."""
        month = month or cls.current_month()
        ok = delete_budget_row(month, "Общий")
        if ok:
            cls._invalidate_cache()
        return ok

    @classmethod
    def get_budget_status(cls, month: str | None = None) -> dict | None:
        """Вернуть статус бюджета:

        {
            "budget": 50000,
            "spent": 32450,
            "remaining": 17550,
            "percent": 0.649,
            "bar": "██████░░░░"
        }
        или None если бюджет не установлен.
        Spent = сумма всех expense за месяц (Amount UAH).
        """
        month = month or cls.current_month()
        budget = cls.get_budget(month)
        if budget is None:
            return None

        spending = cls._get_cached_spending(month)
        total_spent = sum(spending.values())

        percent = total_spent / budget if budget > 0 else 0.0
        remaining = budget - total_spent

        return {
            "budget": round(budget, 2),
            "spent": round(total_spent, 2),
            "remaining": round(remaining, 2),
            "percent": round(percent, 3),
            "bar": cls._format_progress_bar(percent),
        }

    # ── лимиты категорий ──────────────────────────────────────────────

    @classmethod
    def get_limits(cls, month: str | None = None) -> list[dict]:
        """Вернуть все лимиты категорий на месяц:

        [
            {
                "category": "Кофе",
                "limit": 3000,
                "spent": 2450,
                "percent": 0.817,
                "bar": "████████░░"
            },
            ...
        ]
        """
        month = month or cls.current_month()
        rows = cls._get_cached_budget_rows()
        spending = cls._get_cached_spending(month)

        result: list[dict] = []
        for r in rows:
            if len(r) < 4 or r[0] != month or r[3] != "limit":
                continue

            category = r[1]
            try:
                limit_val = float(r[2])
            except (ValueError, TypeError):
                continue

            spent = spending.get(category, 0.0)
            percent = spent / limit_val if limit_val > 0 else 0.0

            result.append(
                {
                    "category": category,
                    "limit": round(limit_val, 2),
                    "spent": round(spent, 2),
                    "percent": round(percent, 3),
                    "bar": cls._format_progress_bar(percent),
                }
            )

        return result

    @classmethod
    def set_limit(cls, category: str, amount: float, month: str | None = None) -> bool:
        """Установить лимит на категорию. amount > 0."""
        if amount <= 0:
            return False
        if not category:
            return False
        month = month or cls.current_month()
        ok = upsert_budget_row(month, category, amount, "limit")
        if ok:
            cls._invalidate_cache()
        return ok

    @classmethod
    def delete_limit(cls, category: str, month: str | None = None) -> bool:
        """Удалить лимит категории."""
        if not category:
            return False
        month = month or cls.current_month()
        ok = delete_budget_row(month, category)
        if ok:
            cls._invalidate_cache()
        return ok

    @classmethod
    def get_limit(cls, category: str, month: str | None = None) -> dict | None:
        """Вернуть лимит одной категории со spent/percent/bar."""
        month = month or cls.current_month()
        rows = cls._get_cached_budget_rows()
        spending = cls._get_cached_spending(month)

        for r in rows:
            if len(r) >= 4 and r[0] == month and r[1] == category and r[3] == "limit":
                try:
                    limit_val = float(r[2])
                except (ValueError, TypeError):
                    return None
                spent = spending.get(category, 0.0)
                percent = spent / limit_val if limit_val > 0 else 0.0
                return {
                    "category": category,
                    "limit": round(limit_val, 2),
                    "spent": round(spent, 2),
                    "percent": round(percent, 3),
                    "bar": cls._format_progress_bar(percent),
                }
        return None

    # ── алерты ────────────────────────────────────────────────────────

    @classmethod
    def check_alerts(
        cls,
        category: str,
        amount: float,
        month: str | None = None,
    ) -> list[str]:
        """Проверить пороги лимита категории после добавления траты.

        Возвращает список предупреждений (пустой если всё ок).
        Алерт срабатывает 1 раз при пересечении порога:
        - 50%: "50% лимита {category}: потрачено X из Y"
        - 80%: "80% лимита {category}: осталось всего Z"
        - 100%: "100% лимита {category}: лимит исчерпан!"
        - превышение: "Превышение лимита {category}: перерасход на Z"
        """
        month = month or cls.current_month()
        limit_info = cls.get_limit(category, month)
        if limit_info is None:
            return []

        limit_val = limit_info["limit"]
        old_spent = limit_info["spent"] - amount  # spent ДО этой траты
        new_spent = limit_info["spent"]

        alerts: list[str] = []

        # Пороги
        thresholds = [
            (
                0.50,
                lambda: (
                    f"⚠️ 50% лимита <b>{category}</b>: потрачено {cls._fmt(new_spent)} из {cls._fmt(limit_val)}"
                ),
            ),
            (
                0.80,
                lambda: (
                    f"⚠️ 80% лимита <b>{category}</b>: осталось всего {cls._fmt(limit_val - new_spent)}"
                ),
            ),
            (1.00, lambda: f"🚫 100% лимита <b>{category}</b>: лимит исчерпан!"),
        ]

        for pct, msg_fn in thresholds:
            if old_spent < pct * limit_val <= new_spent:
                alerts.append(msg_fn())

        # Превышение
        if new_spent > limit_val and old_spent <= limit_val:
            over = new_spent - limit_val
            alerts.append(
                f"‼️ Превышение лимита <b>{category}</b>: перерасход на {cls._fmt(over)}"
            )

        return alerts

    @classmethod
    def check_budget_alert(
        cls,
        amount: float,
        month: str | None = None,
    ) -> list[str]:
        """Проверить пороги общего бюджета после добавления траты.

        Аналогично check_alerts, но для общего бюджета.
        """
        month = month or cls.current_month()
        status = cls.get_budget_status(month)
        if status is None:
            return []

        budget_val = status["budget"]
        old_spent = status["spent"] - amount
        new_spent = status["spent"]

        alerts: list[str] = []

        thresholds = [
            (
                0.50,
                lambda: (
                    f"⚠️ 50% бюджета: потрачено {cls._fmt(new_spent)} из {cls._fmt(budget_val)}"
                ),
            ),
            (
                0.80,
                lambda: (
                    f"⚠️ 80% бюджета: осталось всего {cls._fmt(budget_val - new_spent)}"
                ),
            ),
            (
                1.00,
                lambda: (
                    f"🚫 Бюджет исчерпан: потрачено {cls._fmt(new_spent)} из {cls._fmt(budget_val)}"
                ),
            ),
        ]

        for pct, msg_fn in thresholds:
            if old_spent < pct * budget_val <= new_spent:
                alerts.append(msg_fn())

        if new_spent > budget_val and old_spent <= budget_val:
            over = new_spent - budget_val
            alerts.append(f"‼️ Превышение бюджета: перерасход на {cls._fmt(over)}")

        return alerts

    @staticmethod
    def _fmt(value: float) -> str:
        """Форматировать число: 32450 → "32 450 грн"."""
        return f"{value:,.0f} грн".replace(",", " ")
