import html
from datetime import datetime

from budget import BudgetManager
from categories import get_all_income_categories, normalize_category
from responses import get_income_response, get_toxicity_response
from sheets import add_row
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


async def income_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split(maxsplit=2)

    if len(parts) < 2:
        context.user_data["income_step"] = "amount"
        await update.message.reply_text(
            "Укажи сумму. Например:\n<code>/income 5000 зарплата аванс</code>",
            parse_mode="HTML",
        )
        return

    try:
        amount = float(parts[1])
    except ValueError:
        await update.message.reply_text(
            "Сумму цифрами пиши. Например: <code>/income 5000 зарплата</code>",
            parse_mode="HTML",
        )
        return

    context.user_data["income_amount"] = amount

    # Try to parse category and comment from command
    if len(parts) >= 3:
        rest = parts[2]
        cat_parts = rest.split(maxsplit=1)
        context.user_data["income_category"] = cat_parts[0]
        if len(cat_parts) > 1:
            context.user_data["income_comment"] = cat_parts[1]
            return await _save_income(update, context)
        # Only category, no comment — ask for comment
        context.user_data["income_step"] = "comment"
        await update.message.reply_text(
            f"Категория: {cat_parts[0]}\nНапиши комментарий к доходу:"
        )
        return

    # No category — show keyboard
    context.user_data["income_step"] = "category"
    keyboard = [
        [InlineKeyboardButton(cat, callback_data=f"inc_cat_{cat}")]
        for cat in get_all_income_categories()
    ]
    await update.message.reply_text(
        "Откуда это счастье?", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def income_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("inc_cat_"):
        context.user_data["income_category"] = query.data.replace("inc_cat_", "")
        context.user_data["income_step"] = "comment"
        await query.edit_message_text("Напиши комментарий к доходу:")


async def income_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    step = context.user_data.get("income_step")

    if step == "amount":
        try:
            context.user_data["income_amount"] = float(text)
            context.user_data["income_step"] = "category"
            keyboard = [
                [InlineKeyboardButton(cat, callback_data=f"inc_cat_{cat}")]
                for cat in get_all_income_categories()
            ]
            await update.message.reply_text(
                "Откуда это счастье?", reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except ValueError:
            await update.message.reply_text("Сумму цифрами надо писать.")

    elif step == "comment":
        context.user_data["income_comment"] = text
        await _save_income(update, context)


async def _save_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = context.user_data.get("income_amount", 0)
    raw_category = context.user_data.get("income_category", "Другое")
    category = normalize_category(raw_category)
    comment = context.user_data.get("income_comment", "")
    now = datetime.now()

    success = add_row(
        [
            now.strftime("%B"),
            now.strftime("%d.%m.%Y"),
            "income",
            amount,
            0,
            0,
            category,
            comment,
            "manual",
        ]
    )

    if not success:
        await update.message.reply_text(
            "Не могу записать в таблицу. Google Sheets не отвечает.\n"
            "Проверь: 1) доступ у service account к таблице  2) лист называется 'Transactions'"
        )
        return

    BudgetManager.invalidate_after_transaction()

    toxicity = context.user_data.get("toxicity", "grumpy")
    profanity = context.user_data.get("profanity_enabled", True)
    if toxicity == "random":
        import random as _rnd

        toxicity = _rnd.choice(["soft", "grumpy", "hard"])

    toxicity_line = get_toxicity_response(toxicity, profanity)

    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить ещё", callback_data="menu_income"),
            InlineKeyboardButton("📊 Баланс", callback_data="menu_balance"),
        ],
    ]
    text = (
        f"{toxicity_line}\n\n"
        f"💰 Записал доход: +{amount:.0f} UAH\n"
        f"Категория: {html.escape(category)}\n\n"
        f"{get_income_response()}"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    context.user_data.pop("income_step", None)
    context.user_data.pop("income_amount", None)
    context.user_data.pop("income_category", None)
    context.user_data.pop("income_comment", None)
