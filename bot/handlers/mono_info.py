"""Обработчик команды /mono_info — информация о счетах и клиенте Monobank.

Формат: /mono_info
Показывает имя клиента, список счетов с маскированными номерами,
балансами и типами.
"""

import logging

from mono.client import (
    MonobankClient,
    MonobankError,
    _convert_amount,
    currency_code_to_name,
)
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Типы счетов Monobank → эмодзи + русское название
_ACCOUNT_TYPE_LABELS: dict[str, tuple[str, str]] = {
    "black": ("⬛", "Black"),
    "white": ("⬜", "White"),
    "platinum": ("💎", "Platinum"),
    "iron": ("⚫", "Iron"),
    "fop": ("🏢", "FOP"),
    "yellow": ("💛", "Yellow"),
    "eAid": ("💚", "eAid"),
}


def _format_account_type(acc_type: str) -> str:
    """Форматировать тип счёта с эмодзи."""
    emoji, label = _ACCOUNT_TYPE_LABELS.get(acc_type.lower(), ("🏦", acc_type))
    return f"{emoji} {label}"


def _mask_pan(masked_pan: str) -> str:
    """Привести маскированный PAN к читаемому виду.

    Monobank отдаёт уже маскированные номера, например 537541******1234.
    Форматируем как 5375 41** **** 1234.
    """
    if len(masked_pan) == 16:
        return f"{masked_pan[:4]} {masked_pan[4:6]}** **** {masked_pan[-4:]}"
    return masked_pan


def _format_balance(balance: int, currency_code: int) -> str:
    """Форматировать баланс из копеек/центов в читаемый вид."""
    converted = _convert_amount(balance, currency_code)
    currency = currency_code_to_name(currency_code)
    return f"{converted:,.2f} {currency}"


async def mono_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать информацию о клиенте и счетах Monobank."""
    await update.message.reply_chat_action("typing")

    async with MonobankClient() as client:
        try:
            info = await client.get_client_info()
        except MonobankError as e:
            logger.error("Monobank client info error: %s", e)
            await update.message.reply_text(
                f"❌ Ошибка Monobank: {e.message}\n\nПроверь X-Token в настройках."
            )
            return
        except Exception as e:
            logger.error("Unexpected error getting client info: %s", e)
            await update.message.reply_text(
                "❌ Не удалось получить информацию из Monobank. Попробуй позже."
            )
            return

    # --- Сортируем счета: основные первыми ---
    accounts = info.get("accounts", [])

    # Приоритетные маски: 5259 → #1, 4454 → #2
    PRIORITY_MASKS = ["5259", "4454"]

    def _account_priority(acc: dict) -> int:
        masked = (acc.get("maskedPan", [""]) or [""])[0]
        for i, suffix in enumerate(PRIORITY_MASKS):
            if masked.endswith(suffix):
                return i
        return len(PRIORITY_MASKS)

    accounts = sorted(accounts, key=_account_priority)

    client_name = info.get("name", "—")

    lines = [
        f"👤 <b>Клиент:</b> {client_name}",
        f"💳 <b>Счетов:</b> {len(accounts)}",
        f"",
    ]

    for i, acc in enumerate(accounts, start=1):
        acc_type = acc.get("type", "unknown")
        currency_code = acc.get("currencyCode", 980)
        balance = acc.get("balance", 0)
        credit_limit = acc.get("creditLimit", 0)

        total_balance = balance - credit_limit  # доступный остаток

        masked_pans = acc.get("maskedPan", [])
        pan_str = _mask_pan(masked_pans[0]) if masked_pans else "—"

        type_label = _format_account_type(acc_type)
        currency_name = currency_code_to_name(currency_code)
        balance_str = _format_balance(total_balance, currency_code)

        lines.append(f"<b>Счёт {i}:</b> {type_label} ({currency_name})")
        lines.append(f"   💳 {pan_str}")
        lines.append(f"   💰 Баланс: {balance_str}")

        # Если есть кредитный лимит — показываем отдельно
        if credit_limit > 0:
            credit_str = _format_balance(credit_limit, currency_code)
            lines.append(f"   🏦 Кредитный лимит: {credit_str}")

        # Пустая строка между счетами (кроме последнего)
        if i < len(accounts):
            lines.append(f"")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
