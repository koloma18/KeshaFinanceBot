from sheets import COL, delete_row_by_index, get_all_rows
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удалить операцию по ID с подтверждением.

    /delete 15 — запросить подтверждение удаления строки 15
    /delete — показать последние 5 с номерами
    """
    text = update.message.text.strip()
    parts = text.split(maxsplit=1)

    rows = get_all_rows()
    if not rows:
        await update.message.reply_text("История пуста. Нечего удалять.")
        return

    if len(parts) < 2:
        total_rows = len(rows)
        last_rows = rows[-5:]
        lines = ["<b>📋 Последние 5 с номерами:</b>\n"]
        for i, r in enumerate(last_rows):
            idx = total_rows - len(last_rows) + i + 1
            date = r[COL["DATE"]] if len(r) > COL["DATE"] else "??"
            t = str(r[COL["TYPE"]]).strip().lower() if len(r) > COL["TYPE"] else ""
            try:
                amount = float(r[COL["AMOUNT_UAH"]]) if r[COL["AMOUNT_UAH"]] else 0
            except (ValueError, IndexError):
                amount = 0
            cat = r[COL["CATEGORY"]] if len(r) > COL["CATEGORY"] else ""
            sign = "+" if t == "income" else "\u2212"
            emoji = "\U0001f4b0" if t == "income" else "\U0001f4b8"
            cat_str = f" \u00b7 {cat}" if cat else ""
            lines.append(
                f"<b>#{idx}</b> {emoji} {date} <code>{sign}{amount:.0f}</code>{cat_str}"
            )

        text_out = (
            "\n".join(lines) + "\n\nИспользуй <code>/delete НОМЕР</code> для удаления."
        )
        await update.message.reply_html(text_out)
        return

    try:
        delete_id = int(parts[1])
    except ValueError:
        await update.message.reply_text("Номер должен быть числом. Например: /delete 5")
        return

    if delete_id < 1 or delete_id > len(rows):
        await update.message.reply_text(
            f"Нет операции с номером {delete_id}. Доступны: 1\u2013{len(rows)}"
        )
        return

    # Show confirmation with inline buttons
    r = rows[delete_id - 1]
    date = r[COL["DATE"]] if len(r) > COL["DATE"] else "??"
    t = str(r[COL["TYPE"]]).strip().lower() if len(r) > COL["TYPE"] else ""
    try:
        amount = float(r[COL["AMOUNT_UAH"]]) if r[COL["AMOUNT_UAH"]] else 0
    except (ValueError, IndexError):
        amount = 0
    cat = r[COL["CATEGORY"]] if len(r) > COL["CATEGORY"] else ""
    sign = "+" if t == "income" else "\u2212"
    emoji = "\U0001f4b0" if t == "income" else "\U0001f4b8"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "\u2705 Да, удалить",
                    callback_data=f"delete_confirm_{delete_id}",
                ),
                InlineKeyboardButton(
                    "\u274c Отмена",
                    callback_data="delete_cancel",
                ),
            ]
        ]
    )

    await update.message.reply_html(
        f"\u2757 <b>Удалить операцию?</b>\n\n"
        f"#{delete_id} {emoji} {date} <code>{sign}{abs(amount):.0f}</code>"
        + (f" \u00b7 {cat}" if cat else ""),
        reply_markup=keyboard,
    )


async def delete_confirm_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обработка подтверждения/отмены удаления."""
    query = update.callback_query
    await query.answer()

    if query.data == "delete_cancel":
        await query.edit_message_text("\u2705 Удаление отменено. Живём дальше.")
        return

    # Extract row index from callback data: delete_confirm_N
    try:
        delete_id = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        await query.edit_message_text("\u274c Ошибка: некорректный ID операции.")
        return

    success = delete_row_by_index(delete_id)
    if success:
        await query.edit_message_text(
            f"\U0001f5d1 Удалил операцию \u2116{delete_id}. "
            "Финансовая история переписана."
        )
    else:
        await query.edit_message_text(
            "Не получилось удалить. Google Sheets не отвечает."
        )
