"""Команда /set_currency — выбор основной валюты."""

from config import CURRENCIES, PRIMARY_CURRENCY
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from user_settings import persist_setting

CURRENCY_EMOJI = {
    "UAH": "🇺🇦",
    "USD": "🇺🇸",
    "EUR": "🇪🇺",
    "USDT": "💲",
}


async def set_currency_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Выбрать основную валюту.

    /set_currency UAH
    /set_currency USD
    /set_currency EUR
    /set_currency USDT
    """
    args = context.args
    available = list(CURRENCIES) if isinstance(CURRENCIES, list) else CURRENCIES.split()
    available_lower = [c.lower() for c in available]

    # Если передан аргумент — установить валюту
    if args:
        currency = args[0].upper()
        if currency.lower() in available_lower:
            context.user_data["currency"] = currency
            persist_setting("currency", currency)
            emoji = CURRENCY_EMOJI.get(currency, "")
            await update.message.reply_text(
                f"{emoji} Основная валюта: <b>{currency}</b>",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                f"❌ Неизвестная валюта: <b>{currency}</b>\n"
                f"Доступные: {', '.join(available)}",
                parse_mode="HTML",
            )
        return

    # Без аргументов — показать inline-кнопки
    user_currency = context.user_data.get("currency", PRIMARY_CURRENCY)
    text = f"💱 <b>Выбор валюты</b>\n\nТекущая: <b>{user_currency}</b>\nВыбери валюту:"

    keyboard = []
    row = []
    for i, cur in enumerate(available):
        emoji = CURRENCY_EMOJI.get(cur, "")
        current_mark = " ✅" if cur == user_currency else ""
        row.append(
            InlineKeyboardButton(
                f"{emoji} {cur}{current_mark}",
                callback_data=f"set_currency_{cur}",
            )
        )
        if len(row) == 3 or i == len(available) - 1:
            keyboard.append(row)
            row = []

    keyboard.append(
        [InlineKeyboardButton("🔙 Назад", callback_data="menu_settings_full")]
    )

    await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))
