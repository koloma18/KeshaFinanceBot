"""Manual recategorization. /recategorize — change a transaction's category."""

import html
import logging

from categories import (
    EXPENSE_CATEGORIES_DISPLAY,
    INCOME_CATEGORIES_DISPLAY,
    normalize_category,
)
from sheets import COL, get_all_rows, update_row_category
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def recategorize_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Change the category of a transaction.

    /recategorize             — show last 5 rows for selection
    /recategorize Категория   — change category of the LAST transaction
    """
    args = context.args
    rows = get_all_rows()

    if not rows:
        await update.message.reply_text("Нечего перекатегоризировать. База пуста.")
        return

    if args:
        new_cat_raw = " ".join(args)
        new_category = normalize_category(new_cat_raw)

        last_index = len(rows)  # 1-based, rows has no header
        success = update_row_category(last_index, new_category)

        if success:
            old_cat = (
                rows[-1][COL["CATEGORY"]] if len(rows[-1]) > COL["CATEGORY"] else "?"
            )
            await update.message.reply_text(
                f"✅ Категория изменена: <b>{html.escape(old_cat)}</b> → <b>{html.escape(new_category)}</b>\n"
                f"Кеша: «Уже лучше. Хотя мог бы и сам догадаться.»",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                "❌ Не удалось обновить категорию. Google Sheets не отвечает."
            )
        return

    await _show_recategorize_list(update, rows)


async def _show_recategorize_list(update: Update, rows: list) -> None:
    """Show the last 5 transactions so the user can pick one to recategorize."""
    lines = ["📋 <b>Выбери операцию для перекатегоризации:</b>\n"]

    last_five = rows[-5:] if len(rows) >= 5 else rows
    for i, r in enumerate(last_five):
        idx = len(rows) - len(last_five) + i + 1
        date = r[COL["DATE"]] if len(r) > COL["DATE"] else "??"
        t = str(r[COL["TYPE"]]).strip().lower() if len(r) > COL["TYPE"] else ""
        try:
            amount = float(r[COL["AMOUNT_UAH"]]) if r[COL["AMOUNT_UAH"]] else 0
        except (ValueError, IndexError):
            amount = 0
        cat = r[COL["CATEGORY"]] if len(r) > COL["CATEGORY"] else ""
        cmt = r[COL["COMMENT"]] if len(r) > COL["COMMENT"] else ""

        sign = "+" if t == "income" else "−"
        emoji = "💰" if t == "income" else "💸"
        cmt_str = f" — {html.escape(cmt)}" if cmt else ""

        lines.append(
            f"{i + 1}. {emoji} {date} <code>{sign}{abs(amount):.0f}</code> · {html.escape(cat)}{cmt_str}"
        )

    lines.append("\nНапиши номер операции (1–{}) и категорию:")
    lines.append(f"<code>/recategorize НоваяКатегория</code> — для последней")

    await update.message.reply_html("\n".join(lines), disable_web_page_preview=True)
