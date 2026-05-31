"""Обработчик команды /mono_rates — курсы валют Monobank.

Получает актуальные курсы из публичного API Monobank (/bank/currency)
и показывает USD/UAH, EUR/UAH, EUR/USD.
"""

import logging

from mono.client import MonobankClient
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Коды валют ISO 4217
UAH = 980
USD = 840
EUR = 978

# Какие cross-курсы показываем: (from, to, label)
_RATE_PAIRS = [
    (USD, UAH, "🇺🇸 USD → 🇺🇦 UAH"),
    (EUR, UAH, "🇪🇺 EUR → 🇺🇦 UAH"),
    (EUR, USD, "🇪🇺 EUR → 🇺🇸 USD"),
]


def _find_rate(
    rates: list[dict], currency_code_a: int, currency_code_b: int
) -> dict | None:
    """Найти cross-курс в списке курсов Monobank."""
    for r in rates:
        if (
            r.get("currencyCodeA") == currency_code_a
            and r.get("currencyCodeB") == currency_code_b
        ):
            return r
    return None


async def mono_rates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать актуальные курсы валют Monobank."""
    await update.message.reply_chat_action("typing")

    async with MonobankClient() as client:
        try:
            rates = await client.get_currency_rates()
        except Exception as e:
            logger.error("Ошибка получения курсов Monobank: %s", e)
            await update.message.reply_text(
                "❌ Не удалось получить курсы валют Monobank.\n"
                "Попробуй позже или проверь подключение к интернету."
            )
            return

    lines = ["💱 <b>Курсы Monobank</b>\n"]
    found_any = False

    for code_a, code_b, label in _RATE_PAIRS:
        rate = _find_rate(rates, code_a, code_b)
        if rate is None:
            # Иногда Monobank отдаёт обратную пару — пробуем инвертировать
            rate = _find_rate(rates, code_b, code_a)
            if rate and "rateBuy" in rate and "rateSell" in rate:
                rate_sell = round(1 / rate["rateBuy"], 4)
                rate_buy = round(1 / rate["rateSell"], 4)
            else:
                lines.append(f"{label}: <i>нет данных</i>")
                continue
        else:
            rate_buy = rate.get("rateBuy")
            rate_sell = rate.get("rateSell")
            if rate_buy is None or rate_sell is None:
                lines.append(f"{label}: <i>нет данных</i>")
                continue

        lines.append(f"{label}: <b>{rate_buy:.2f}</b> / <b>{rate_sell:.2f}</b>")
        found_any = True

    if not found_any:
        lines.append("\n<i>Курсы временно недоступны.</i>")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
