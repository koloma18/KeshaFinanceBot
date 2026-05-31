import html
from datetime import datetime, timedelta

from responses import get_balance_response, get_month_response, get_week_response
from sheets import COL, get_all_rows, get_balance
from telegram import Update
from telegram.ext import ContextTypes


def _filter_today(rows):
    today = datetime.now().strftime("%d.%m.%Y")
    return [r for r in rows if len(r) > COL["DATE"] and r[COL["DATE"]] == today]


def _filter_week(rows):
    now = datetime.now()
    start_of_week = now - timedelta(days=now.weekday())
    dates = {start_of_week.strftime("%d.%m.%Y")}
    for i in range(1, 7):
        dates.add((start_of_week + timedelta(days=i)).strftime("%d.%m.%Y"))
    return [r for r in rows if len(r) > COL["DATE"] and r[COL["DATE"]] in dates]


def _filter_month(rows):
    month = datetime.now().strftime("%B")
    return [r for r in rows if len(r) > COL["MONTH"] and r[COL["MONTH"]] == month]


def _summarize(rows):
    income = 0.0
    expense = 0.0
    cat_expense = {}
    for r in rows:
        if len(r) <= max(COL["AMOUNT_UAH"], COL["TYPE"]):
            continue
        try:
            amount = float(r[COL["AMOUNT_UAH"]]) if r[COL["AMOUNT_UAH"]] else 0
        except (ValueError, IndexError):
            continue
        t = str(r[COL["TYPE"]]).strip().lower()
        if t == "income":
            income += amount
        elif t == "expense":
            expense += abs(amount)
            cat = str(r[COL["CATEGORY"]]) if len(r) > COL["CATEGORY"] else "Другое"
            cat_expense[cat] = cat_expense.get(cat, 0) + abs(amount)
    return income, expense, cat_expense


def _format_cat_top(cat_expense, top=3):
    sorted_cats = sorted(cat_expense.items(), key=lambda x: -x[1])[:top]
    if not sorted_cats:
        return ""
    lines = []
    for cat, amt in sorted_cats:
        lines.append(f"  • {html.escape(cat)}: {amt:.0f} UAH")
    return "\n" + "\n".join(lines)


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = _filter_today(get_all_rows())
    income, expense, cat_expense = _summarize(rows)
    cat_block = _format_cat_top(cat_expense)
    text = (
        f"📅 <b>Сегодня</b>\n\n"
        f"💰 Доход: +{income:.0f} UAH\n"
        f"💸 Расход: -{expense:.0f} UAH\n"
        f"📊 Итого: {income - expense:+.0f} UAH"
    )
    if cat_block:
        text += f"\n\n<b>Топ трат:</b>{cat_block}"
    await update.message.reply_html(text)


async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = _filter_week(get_all_rows())
    income, expense, cat_expense = _summarize(rows)
    cat_block = _format_cat_top(cat_expense)
    text = (
        f"📆 <b>Эта неделя</b>\n\n"
        f"💰 Доход: +{income:.0f} UAH\n"
        f"💸 Расход: -{expense:.0f} UAH\n"
        f"📊 Итого: {income - expense:+.0f} UAH"
    )
    if cat_block:
        text += f"\n\n<b>Топ трат:</b>{cat_block}"
    text += f"\n\n<i>{get_week_response()}</i>"
    await update.message.reply_html(text)


async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = _filter_month(get_all_rows())
    income, expense, cat_expense = _summarize(rows)
    cat_block = _format_cat_top(cat_expense, top=5)
    text = (
        f"🗓 <b>Этот месяц</b>\n\n"
        f"💰 Доход: +{income:.0f} UAH\n"
        f"💸 Расход: -{expense:.0f} UAH\n"
        f"📊 Итого: {income - expense:+.0f} UAH"
    )
    if cat_block:
        text += f"\n\n<b>Топ трат:</b>{cat_block}"
    text += f"\n\n<i>{get_month_response()}</i>"
    await update.message.reply_html(text)


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    b = get_balance()
    uah = b.get("UAH", 0)
    usd = b.get("USD", 0)
    eur = b.get("EUR", 0)
    text = f"📊 <b>Общий баланс</b>\n\n"
    parts = []
    if uah:
        parts.append(f"🇺🇦 {uah:+.2f} UAH")
    if usd:
        parts.append(f"🇺🇸 {usd:+.2f} USD")
    if eur:
        parts.append(f"🇪🇺 {eur:+.2f} EUR")
    text += "\n".join(parts) if parts else "0.00 UAH"
    text += f"\n\n<i>{get_balance_response(uah)}</i>"
    await update.message.reply_html(text)
