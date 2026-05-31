import html
from datetime import datetime

from sheets import COL, delete_last_row, get_all_rows
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


async def last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = get_all_rows()
    if not rows:
        await update.message.reply_text("История пуста. Даже тратить ничего не умеешь?")
        return

    last_five = rows[:5]
    lines = ["<b>📋 Последние операции</b>\n"]
    for r in last_five:
        date = r[COL["DATE"]] if len(r) > COL["DATE"] else "??"
        t = str(r[COL["TYPE"]]).strip().lower() if len(r) > COL["TYPE"] else ""
        try:
            amount = float(r[COL["AMOUNT_UAH"]]) if r[COL["AMOUNT_UAH"]] else 0
        except (ValueError, IndexError):
            amount = 0
        category = r[COL["CATEGORY"]] if len(r) > COL["CATEGORY"] else ""
        comment = r[COL["COMMENT"]] if len(r) > COL["COMMENT"] else ""

        sign = "+" if t == "income" else "−"
        emoji = "💰" if t == "income" else "💸"
        cat_str = f" · {html.escape(category)}" if category else ""
        cmt_str = f" — {html.escape(comment)}" if comment else ""
        lines.append(
            f"{emoji} {date} <code>{sign}{amount:.0f}</code>{cat_str}{cmt_str}"
        )

    text = "\n".join(lines)
    await update.message.reply_html(text)


async def delete_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deleted = delete_last_row()
    if deleted:
        await update.message.reply_text(
            "🗑 Удалил последнюю запись.\n"
            "/last — проверить\n"
            "/delete_last — отменить ещё одну"
        )
    else:
        await update.message.reply_text("Нечего удалять. История пуста.")
