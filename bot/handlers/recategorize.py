"""Manual recategorization. /recategorize — change a transaction's category.

/recategorize                  — show last 5 rows for selection
/recategorize Категория        — change category of the LAST transaction (backward compat)
/recategorize last Категория   — change category of the LAST transaction
/recategorize 15 Категория     — change category of row 15
"""

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
    args = context.args
    rows = get_all_rows()

    if not rows:
        await update.message.reply_text("Нечего перекатегоризировать. База пуста.")
        return

    if not args:
        await _show_recategorize_list(update, rows)
        return

    # Parse: /recategorize [N|last] Категория
    row_index: int | None = None
    cat_start = 0

    first = args[0].lower()

    if first == "last":
        row_index = len(rows)  # 1-based last data row
        cat_start = 1
    else:
        try:
            row_index = int(first)
            cat_start = 1
        except ValueError:
            # No number/last — all args are category, target = last row (backward compat)
            row_index = len(rows)
            cat_start = 0

    if row_index < 1 or row_index > len(rows):
        await update.message.reply_text(
            f"Нет операции с номером {row_index}. Доступны: 1–{len(rows)}"
        )
        return

    if cat_start >= len(args):
        await update.message.reply_text(
            f"Укажи категорию. Например:\n<code>/recategorize {row_index} Еда</code>",
            parse_mode="HTML",
        )
        return

    new_cat_raw = " ".join(args[cat_start:])
    new_category = normalize_category(new_cat_raw)

    success = update_row_category(row_index, new_category)

    if success:
        old_cat = (
            rows[row_index - 1][COL["CATEGORY"]]
            if len(rows[row_index - 1]) > COL["CATEGORY"]
            else "?"
        )
        await update.message.reply_text(
            f"✅ Строка #{row_index}: <b>{html.escape(old_cat)}</b> → <b>{html.escape(new_category)}</b>\n"
            f"Кеша: «Уже лучше. Хотя мог бы и сам догадаться.»",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            "❌ Не удалось обновить категорию. Google Sheets не отвечает."
        )


async def _show_recategorize_list(update: Update, rows: list) -> None:
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

    lines.append("\nНапиши номер строки и категорию:")
    lines.append("<code>/recategorize 2 Еда</code>")
    lines.append("<code>/recategorize last Еда</code> — последняя")

    await update.message.reply_html("\n".join(lines), disable_web_page_preview=True)
