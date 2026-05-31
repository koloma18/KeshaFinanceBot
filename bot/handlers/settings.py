from config import CURRENCIES, PRIMARY_CURRENCY
from responses import TOXICITY_LEVELS
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from user_settings import persist_setting


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_currency = context.user_data.get("currency", PRIMARY_CURRENCY)
    currency_list = ", ".join(CURRENCIES)
    toxicity = context.user_data.get("toxicity", "grumpy")
    profanity_enabled = context.user_data.get("profanity_enabled", True)
    toxicity_label = TOXICITY_LEVELS.get(toxicity, TOXICITY_LEVELS["grumpy"])
    profanity_label = "Вкл 🤬" if profanity_enabled else "Выкл 😇"

    text = (
        "⚙️ <b>Настройки</b>\n\n"
        f"💱 Основная валюта: <b>{user_currency}</b>\n"
        f"📋 Доступные: {currency_list}\n\n"
        f"😈 Токсичность: <b>{toxicity_label}</b>\n"
        f"🤬 Мат: <b>{profanity_label}</b>"
    )

    keyboard = [
        [
            InlineKeyboardButton("🇺🇦 UAH", callback_data="set_currency_UAH"),
            InlineKeyboardButton("🇺🇸 USD", callback_data="set_currency_USD"),
            InlineKeyboardButton("🇪🇺 EUR", callback_data="set_currency_EUR"),
        ],
        [
            InlineKeyboardButton("😇 Мягкий", callback_data="toxicity_soft"),
            InlineKeyboardButton("😤 Бурчливый", callback_data="toxicity_grumpy"),
        ],
        [
            InlineKeyboardButton("🤬 Жёсткий", callback_data="toxicity_hard"),
            InlineKeyboardButton("🎲 Случайно", callback_data="toxicity_random"),
        ],
        [
            InlineKeyboardButton(
                "🤬 Мат: ВЫКЛ" if profanity_enabled else "🤬 Мат: ВКЛ",
                callback_data="profanity_toggle",
            ),
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")],
    ]
    await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("set_currency_"):
        currency = query.data.replace("set_currency_", "")
        context.user_data["currency"] = currency
        persist_setting("currency", currency)
        await query.edit_message_text(
            f"✅ Валюта изменена на <b>{currency}</b>", parse_mode="HTML"
        )

    elif query.data.startswith("toxicity_"):
        level = query.data.replace("toxicity_", "")
        context.user_data["toxicity"] = level
        persist_setting("toxicity", level)
        label = TOXICITY_LEVELS.get(level, level)
        await query.edit_message_text(
            f"✅ Уровень токсичности: <b>{label}</b>", parse_mode="HTML"
        )

    elif query.data == "profanity_toggle":
        current = context.user_data.get("profanity_enabled", True)
        context.user_data["profanity_enabled"] = not current
        persist_setting("profanity_enabled", not current)
        label = "Выкл 😇" if current else "Вкл 🤬"
        await query.edit_message_text(f"✅ Мат: <b>{label}</b>", parse_mode="HTML")
