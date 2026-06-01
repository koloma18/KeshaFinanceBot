"""Обработчик команды /mono_import — импорт выписки из Monobank.

Формат: /mono_import [days=7]
Импортирует операции за указанное количество дней и сохраняет в Google Sheets.
"""

import logging

from mono import build_transaction_row
from mono.client import MonobankClient, MonobankError, currency_code_to_name
from mono.mcc_categories import get_mcc_description
from sheets import COL, add_row, find_row_by_source
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

MAX_DAYS = 31
DEFAULT_DAYS = 7
PROGRESS_INTERVAL = 10


def _parse_days(args: list[str]) -> int:
    """Распарсить аргумент days из команды."""
    if not args:
        return DEFAULT_DAYS
    raw = args[0].strip()
    if not raw.isdigit():
        raise ValueError(
            f"«{raw}» — это не число. Укажи количество дней от 1 до {MAX_DAYS}."
        )
    days = int(raw)
    if days < 1 or days > MAX_DAYS:
        raise ValueError(
            f"Количество дней должно быть от 1 до {MAX_DAYS}. Получено: {days}."
        )
    return days


async def mono_import(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Импорт выписки из Monobank. Формат: /mono_import [days=7]"""
    try:
        days = _parse_days(context.args)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return

    await update.message.reply_chat_action("typing")
    status_msg = await update.message.reply_text(
        f"🔄 Подключаюсь к Monobank...\nЗапрошу выписку за последние {days} дн."
    )

    async with MonobankClient() as client:
        try:
            client_info = await client.get_client_info()
        except MonobankError as e:
            logger.error("Monobank client info error: %s", e)
            await status_msg.edit_text(
                f"❌ Ошибка Monobank: {e.message}\n\nПроверь X-Token в настройках."
            )
            return
        except Exception as e:
            logger.error(
                "Unexpected error getting client info: %s (type: %s)",
                e,
                type(e).__name__,
            )
            await status_msg.edit_text(
                f"❌ Не удалось подключиться: {type(e).__name__}"
            )
            return

        accounts = client_info.get("accounts", [])
        if not accounts:
            await status_msg.edit_text("❌ У тебя нет счетов в Monobank.")
            return

        # Основные счета: 5259 и 4454
        PRIORITY_MASKS = ["5259"]
        target_accounts = []
        for mask in PRIORITY_MASKS:
            for acc in accounts:
                masked = (acc.get("maskedPan", [""]) or [""])[0]
                if masked.endswith(mask):
                    target_accounts.append(acc)
                    break

        if not target_accounts:
            await status_msg.edit_text("❌ Счета 5259 и 4454 не найдены.")
            return

        now = int(datetime.now(timezone.utc).timestamp())
        from_ts = now - days * 86400

        grand_total = 0
        grand_skipped = 0
        grand_errors = 0
        account_lines: list[str] = []

        for account in target_accounts:
            account_id = account.get("id")
            if not account_id:
                continue
            masked = (account.get("maskedPan", ["???"]) or ["???"])[0]

            await status_msg.edit_text(f"🔄 Загружаю {masked}...")

            try:
                statements = await client.get_statement(account_id, from_ts, now)
            except MonobankError as e:
                account_lines.append(f"💳 {masked}: ❌ {e.message}")
                continue
            except Exception:
                account_lines.append(f"💳 {masked}: ❌ ошибка")
                continue

            if not statements:
                account_lines.append(f"💳 {masked}: нет транзакций")
                continue

            total = 0
            skipped = 0
            errors = 0
            for tx in statements:
                if tx.get("amount", 0) == 0:
                    skipped += 1
                    continue
                source_key = f"mono:{tx['id']}"
                try:
                    existing = find_row_by_source(source_key)
                except Exception:
                    existing = None
                if existing is not None:
                    skipped += 1
                    continue
                row = build_transaction_row(tx)
                if row is None:
                    skipped += 1
                    continue
                try:
                    ok = add_row(row)
                except Exception:
                    ok = False
                if ok:
                    total += 1
                else:
                    errors += 1

            account_lines.append(
                f"💳 {masked}: +{total}" + (f" (⏭{skipped})" if skipped else "")
            )
            grand_total += total
            grand_skipped += skipped
            grand_errors += errors

        lines = [
            f"✅ <b>Импорт завершён</b>",
            f"📅 Период: последние {days} дн.",
            f"",
            *account_lines,
            f"",
            f"📥 Всего: <b>{grand_total}</b>",
        ]
        if grand_skipped:
            lines.append(f"⏭ Пропущено: {grand_skipped}")
        if grand_errors:
            lines.append(f"❌ Ошибок: {grand_errors}")

        await status_msg.edit_text("\n".join(lines), parse_mode="HTML")
