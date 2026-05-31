"""Сравнение и топ категорий. /top — топ категорий, /compare — сравнение месяцев."""

import logging
import random
from datetime import datetime

from responses import COMPARE_LESS, COMPARE_MORE
from sheets import COL, get_all_rows
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Топ категорий расходов.

    /top     — топ-5 за текущий месяц
    /top 10  — топ-10

    Показывает: место, категория, сумма, процент от всех трат.
    """
    n = 5
    if context.args and context.args[0].isdigit():
        n = int(context.args[0])

    rows = _filter_month_rows(get_all_rows())
    if not rows:
        await update.message.reply_text(
            "🫙 За этот месяц трат нет. Идеальный финансовый отчёт."
        )
        return

    top, total_expense = _top_categories(rows, n)
    if not top:
        await update.message.reply_text(
            "💰 Расходов не нашлось. Только доходы? Ты ли это?"
        )
        return

    lines = [f"🏆 <b>Топ-{len(top)} категорий трат</b>\n"]
    for i, (cat, amt, pct) in enumerate(top, start=1):
        bar_len = max(1, int(pct // 5))
        bar = "█" * bar_len + "░" * (20 - bar_len)
        amt_fmt = f"{amt:,.0f}".replace(",", " ")
        lines.append(
            f"{i}. <b>{cat}</b>\n   {amt_fmt} UAH — {pct:.1f}%\n   <code>{bar}</code>"
        )
    total_fmt = f"{total_expense:,.0f}".replace(",", " ")
    lines.append(f"\n💸 Всего расходов: {total_fmt} UAH")
    lines.append(f"\n<i>{random.choice(COMPARE_MORE)}</i>")

    await update.message.reply_html("\n".join(lines))


async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сравнить текущий месяц с предыдущим.

    Показывает:
    📊 Текущий месяц vs Прошлый месяц
    Доход: +X vs +Y (+Z%)
    Расход: -X vs -Y (Z%)
    Итого: X vs Y
    Персонаж комментирует.
    """
    now = datetime.now()
    current_month = now.strftime("%B")

    if now.month == 1:
        prev_month = "December"
    else:
        prev_month = datetime(now.year, now.month - 1, 1).strftime("%B")

    all_rows = get_all_rows()
    current_rows = _filter_month_rows(all_rows, current_month)
    prev_rows = _filter_month_rows(all_rows, prev_month)

    current = _month_summary(current_rows)
    prev = _month_summary(prev_rows)

    if current["total"] == 0 and prev["total"] == 0:
        await update.message.reply_text(
            "📊 Сравнивать нечего. Ни в этом, ни в прошлом месяце данных нет. "
            "Или ты не тратила, или я что-то пропустил."
        )
        return

    def pct_str(this: float, that: float) -> str:
        if that == 0:
            return "—" if this == 0 else "+∞"
        return f"{((this - that) / abs(that)) * 100:+.1f}%"

    expense_diff = current["expense"] - prev["expense"]
    if expense_diff > 0:
        comment = random.choice(COMPARE_MORE)
    elif expense_diff < 0:
        comment = random.choice(COMPARE_LESS)
    else:
        comment = "Как в прошлом месяце. Стабильность — признак мастерства. Или застоя."

    lines = [
        "📊 <b>Сравнение месяцев</b>\n",
        f"📅 {current_month} vs {prev_month}\n",
        f"💰 Доход:",
        f"   {current_month}: +{current['income']:,.0f} UAH",
        f"   {prev_month}: +{prev['income']:,.0f} UAH "
        f"(<code>{pct_str(current['income'], prev['income'])}</code>)\n",
        f"💸 Расход:",
        f"   {current_month}: -{current['expense']:,.0f} UAH",
        f"   {prev_month}: -{prev['expense']:,.0f} UAH "
        f"(<code>{pct_str(current['expense'], prev['expense'])}</code>)\n",
        f"📊 Итого:",
        f"   {current_month}: {current['total']:+,.0f} UAH",
        f"   {prev_month}: {prev['total']:+,.0f} UAH",
        f"",
        f"<i>{comment}</i>",
    ]

    await update.message.reply_html("\n".join(lines))


def _top_categories(
    rows: list[list], n: int = 5
) -> tuple[list[tuple[str, float, float]], float]:
    """Вернуть (топ N категорий, общая сумма всех расходов).

    [(category, amount, percent_of_total), ...], total_expense
    percent_of_total = category_amount / total_expense * 100
    """
    cat_totals: dict[str, float] = {}
    total_expense = 0.0

    for r in rows:
        if len(r) <= max(COL["AMOUNT_UAH"], COL["TYPE"], COL["CATEGORY"]):
            continue
        t = str(r[COL["TYPE"]]).strip().lower()
        if t != "expense":
            continue
        try:
            amount = float(r[COL["AMOUNT_UAH"]]) if r[COL["AMOUNT_UAH"]] else 0
        except (ValueError, IndexError):
            continue
        total_expense += abs(amount)
        cat = str(r[COL["CATEGORY"]]) if r[COL["CATEGORY"]] else "Другое"
        cat_totals[cat] = cat_totals.get(cat, 0) + abs(amount)

    sorted_cats = sorted(cat_totals.items(), key=lambda x: -x[1])
    result: list[tuple[str, float, float]] = []
    for cat, amt in sorted_cats[:n]:
        pct = (amt / total_expense * 100) if total_expense > 0 else 0
        result.append((cat, amt, pct))
    return result, total_expense


def _month_summary(rows: list[list]) -> dict:
    """Сводка за месяц: {"income": float, "expense": float, "total": float}"""
    income = 0.0
    expense = 0.0
    for r in rows:
        if len(r) <= COL["TYPE"]:
            continue
        t = str(r[COL["TYPE"]]).strip().lower()
        if t not in ("income", "expense"):
            continue
        try:
            amount = float(r[COL["AMOUNT_UAH"]]) if r[COL["AMOUNT_UAH"]] else 0
        except (ValueError, IndexError):
            continue
        if t == "income":
            income += amount
        else:
            expense += abs(amount)
    return {"income": income, "expense": expense, "total": income - expense}


def _filter_month_rows(rows: list[list], month: str | None = None) -> list[list]:
    """Отфильтровать строки по названию месяца.

    Если month не передан — берётся текущий месяц.
    """
    if month is None:
        month = datetime.now().strftime("%B")
    return [r for r in rows if len(r) > COL["MONTH"] and r[COL["MONTH"]] == month]
