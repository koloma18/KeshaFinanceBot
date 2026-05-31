"""Экспорт данных. /export csv — выгрузить в CSV."""

import csv
import io
import logging
from datetime import datetime, timedelta

from config import SPREADSHEET_ID
from sheets import COL, get_all_rows
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

CSV_FIELDS = [
    "Date",
    "Type",
    "Amount UAH",
    "Amount USD",
    "Amount EUR",
    "Category",
    "Comment",
    "Source",
]
COL_MAP = [
    COL["DATE"],
    COL["TYPE"],
    COL["AMOUNT_UAH"],
    COL["AMOUNT_USD"],
    COL["AMOUNT_EUR"],
    COL["CATEGORY"],
    COL["COMMENT"],
    COL["SOURCE"],
]


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Экспорт транзакций.

    /export csv         — все транзакции
    /export csv 30      — последние 30 дней
    /export csv month   — этот месяц
    /export sheets      — ссылка на Google Sheets
    """
    if not context.args:
        await update.message.reply_html(
            "📤 <b>Экспорт</b>\n\n"
            "<code>/export csv</code> — все транзакции\n"
            "<code>/export csv 30</code> — последние N дней\n"
            "<code>/export csv month</code> — этот месяц\n"
            "<code>/export sheets</code> — открыть Google Sheets"
        )
        return

    cmd = context.args[0].lower()

    if cmd == "sheets":
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
        await update.message.reply_html(
            f'📊 <a href="{url}">Открыть Google Sheets</a>\n\n'
            f"Там живут все твои траты. Можешь посмотреть и ужаснуться."
        )
        return

    if cmd != "csv":
        await update.message.reply_text(
            "❌ Непонятная команда. Пиши /export csv или /export sheets."
        )
        return

    all_rows = get_all_rows()
    if not all_rows:
        await update.message.reply_text("🫙 База пуста. Тратить нечего экспортировать.")
        return

    rows = all_rows
    filter_label = "все"

    if len(context.args) >= 2:
        arg2 = context.args[1].lower()
        if arg2 == "month":
            rows = _filter_month(all_rows)
            filter_label = "текущий месяц"
        elif arg2.isdigit():
            rows = _filter_days(all_rows, int(arg2))
            filter_label = f"последние {arg2} дней"

    if not rows:
        await update.message.reply_text(
            f"ℹ️ За период «{filter_label}» ничего не нашлось. Живи."
        )
        return

    csv_io = _build_csv(rows)
    filename = f"kesha_export_{datetime.now().strftime('%Y-%m-%d')}.csv"

    await update.message.reply_document(
        document=csv_io.getvalue().encode("utf-8-sig"),
        filename=filename,
        caption=f"📤 Экспорт: {filter_label} ({len(rows)} записей)\n"
        f"Бот Кеша — твой финансовый надзиратель.",
    )


def _build_csv(rows: list[list]) -> io.StringIO:
    """Конвертировать строки Sheets в CSV (StringIO).

    Колонки: Date, Type, Amount UAH, Amount USD, Amount EUR, Category, Comment, Source
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_FIELDS)
    for r in rows:
        row_out = []
        for col_idx in COL_MAP:
            val = r[col_idx] if len(r) > col_idx else ""
            row_out.append(val)
        writer.writerow(row_out)
    output.seek(0)
    return output


def _filter_days(rows: list[list], days: int) -> list[list]:
    """Оставить только строки за последние N дней."""
    cutoff = datetime.now() - timedelta(days=days)
    result = []
    for r in rows:
        if len(r) <= COL["DATE"]:
            continue
        try:
            row_date = datetime.strptime(str(r[COL["DATE"]]), "%d.%m.%Y")
        except (ValueError, IndexError):
            continue
        if row_date >= cutoff:
            result.append(r)
    return result


def _filter_month(rows: list[list]) -> list[list]:
    """Оставить только строки за текущий месяц."""
    month = datetime.now().strftime("%B")
    return [r for r in rows if len(r) > COL["MONTH"] and r[COL["MONTH"]] == month]
