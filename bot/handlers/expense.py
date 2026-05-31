import html
from datetime import datetime

from budget import BudgetManager
from categories import get_all_expense_categories, normalize_category
from responses import get_expense_response, get_toxicity_response
from sheets import add_row
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


async def expense_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split(maxsplit=2)

    if len(parts) < 2:
        context.user_data["expense_step"] = "amount"
        await update.message.reply_text(
            "Укажи сумму и категорию. Например:\n"
            "<code>/expense 350 кофе капучино</code>",
            parse_mode="HTML",
        )
        return

    try:
        amount = float(parts[1])
    except ValueError:
        await update.message.reply_text(
            "Сумму цифрами пиши. Например: <code>/expense 350 кофе</code>",
            parse_mode="HTML",
        )
        return

    context.user_data["expense_amount"] = amount

    # Try to parse category and comment from command
    if len(parts) >= 3:
        rest = parts[2]
        cat_parts = rest.split(maxsplit=1)
        context.user_data["expense_category"] = cat_parts[0]
        if len(cat_parts) > 1:
            context.user_data["expense_comment"] = cat_parts[1]
            return await _save_expense(update, context)
        # Only category, no comment — ask for comment
        context.user_data["expense_step"] = "comment"
        await update.message.reply_text(
            f"Категория: {cat_parts[0]}\nНапиши комментарий к расходу:"
        )
        return

    # No category — show keyboard
    context.user_data["expense_step"] = "category"
    keyboard = [
        [InlineKeyboardButton(cat, callback_data=f"exp_cat_{cat}")]
        for cat in get_all_expense_categories()
    ]
    await update.message.reply_text(
        "На что ушли деньги?", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def expense_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("exp_cat_"):
        context.user_data["expense_category"] = query.data.replace("exp_cat_", "")
        context.user_data["expense_step"] = "comment"
        await query.edit_message_text("Напиши комментарий к расходу:")


async def expense_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    step = context.user_data.get("expense_step")

    if step == "amount":
        try:
            context.user_data["expense_amount"] = float(text)
            context.user_data["expense_step"] = "category"
            keyboard = [
                [InlineKeyboardButton(cat, callback_data=f"exp_cat_{cat}")]
                for cat in get_all_expense_categories()
            ]
            await update.message.reply_text(
                "На что ушли деньги?", reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except ValueError:
            await update.message.reply_text("Сумму цифрами надо писать.")

    elif step == "comment":
        context.user_data["expense_comment"] = text
        await _save_expense(update, context)


async def _save_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = context.user_data.get("expense_amount", 0)
    raw_category = context.user_data.get("expense_category", "Другое")
    category = normalize_category(raw_category)
    comment = context.user_data.get("expense_comment", "")
    now = datetime.now()

    success = add_row(
        [
            now.strftime("%B"),
            now.strftime("%d.%m.%Y"),
            "expense",
            -amount,
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

    # Инвалидируем кэш BudgetManager — в Transactions новые данные
    BudgetManager.invalidate_after_transaction()

    # Проверяем только включённые пороги
    alert_text = ""
    alert_50 = context.user_data.get("alert_50", True)
    alert_80 = context.user_data.get("alert_80", True)
    alert_exceeded = context.user_data.get("alert_exceeded", True)
    if any([alert_50, alert_80, alert_exceeded]):
        alerts = BudgetManager.check_alerts(category, abs(amount))
        budget_alerts = BudgetManager.check_budget_alert(abs(amount))
        raw = alerts + budget_alerts
        filtered = []
        for a in raw:
            if alert_50 and ("50%" in a):
                filtered.append(a)
            elif alert_80 and ("80%" in a):
                filtered.append(a)
            elif alert_exceeded and (
                "100%" in a or "исчерпан" in a or "Превышение" in a
            ):
                filtered.append(a)
        if filtered:
            alert_text = "\n".join(filtered)

    # Track repeat categories per day
    today_key = now.strftime("%d.%m.%Y")
    today_cats = context.user_data.setdefault("today_categories", {})
    day_cats = today_cats.setdefault(today_key, {})
    repeat_count = day_cats.get(category, 0) + 1
    day_cats[category] = repeat_count
    today_cats[today_key] = day_cats
    context.user_data["today_categories"] = today_cats

    toxicity = context.user_data.get("toxicity", "grumpy")
    profanity = context.user_data.get("profanity_enabled", True)
    if toxicity == "random":
        import random as _rnd

        toxicity = _rnd.choice(["soft", "grumpy", "hard"])

    response = get_expense_response(amount, category, now.hour, repeat_count)
    toxicity_line = get_toxicity_response(toxicity, profanity)

    keyboard = [
        [
            InlineKeyboardButton("➖ Добавить ещё", callback_data="menu_expense"),
            InlineKeyboardButton(
                "↩️ Отменить последнюю", callback_data="menu_delete_last"
            ),
        ],
        [InlineKeyboardButton("📊 Показать день", callback_data="menu_today")],
    ]
    text = f"{toxicity_line}\n\n💸 Записал расход: -{amount:.0f} UAH\nКатегория: {html.escape(category)}\n\n{response}"
    if alert_text:
        text += f"\n\n{alert_text}"
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
    )

    context.user_data.pop("expense_step", None)
    context.user_data.pop("expense_amount", None)
    context.user_data.pop("expense_category", None)
    context.user_data.pop("expense_comment", None)
