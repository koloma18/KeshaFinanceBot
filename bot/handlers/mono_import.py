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
            logger.error("Unexpected error getting client info: %s", e)
            await status_msg.edit_text(
                "❌ Не удалось подключиться к Monobank. Попробуй позже."
            )
            return

        accounts = client_info.get("accounts", [])
        if not accounts:
            await status_msg.edit_text("❌ У тебя нет счетов в Monobank.")
            return

        account = accounts[0]
        account_id = account.get("id")
        if not account_id:
            await status_msg.edit_text("❌ Не удалось получить ID счёта.")
            return

        now = int(datetime.now(timezone.utc).timestamp())
        from_ts = now - days * 86400

        masked = account.get("maskedPan", ["???"])
        await status_msg.edit_text(
            f"🔄 Загружаю выписку за {days} дн.\nСчёт: {masked[0]}"
        )

        try:
            statements = await client.get_statement(account_id, from_ts, now)
        except MonobankError as e:
            logger.error("Monobank statement error: %s", e)
            await status_msg.edit_text(f"❌ Ошибка при получении выписки: {e.message}")
            return
        except Exception as e:
            logger.error("Unexpected error getting statement: %s", e)
            await status_msg.edit_text(
                "❌ Не удалось получить выписку. Попробуй позже."
            )
            return

        if not statements:
            await status_msg.edit_text(f"ℹ️ За последние {days} дн. транзакций нет.")
            return

        total = 0
        skipped = 0
        errors = 0
        processed = 0

        for tx in statements:
            if tx.get("amount", 0) == 0:
                skipped += 1
                continue

            source_key = f"mono:{tx['id']}"

            try:
                existing = find_row_by_source(source_key)
            except Exception as e:
                logger.warning("Ошибка проверки дубликата для %s: %s", source_key, e)
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
            except Exception as e:
                logger.error("Ошибка добавления строки в Sheets: %s", e)
                ok = False

            if ok:
                total += 1
            else:
                errors += 1

            processed += 1

            if processed % PROGRESS_INTERVAL == 0:
                mcc_desc = get_mcc_description(tx.get("mcc", 0))
                try:
                    await status_msg.edit_text(
                        f"🔄 Импортирую...\n"
                        f"✅ Добавлено: {total}\n"
                        f"⏭ Пропущено: {skipped}\n"
                        f"❌ Ошибок: {errors}\n"
                        f"\nПоследняя: {mcc_desc}"
                    )
                except Exception:
                    pass

        currency_name = currency_code_to_name(account.get("currencyCode", 980))
        masked_pan = account.get("maskedPan", [""])[0]
        lines = [
            f"✅ <b>Импорт завершён</b>",
            f"",
            f"📅 Период: последние {days} дн.",
            f"💳 Счёт: {masked_pan} ({currency_name})",
            f"",
            f"📥 Добавлено: <b>{total}</b>",
            f"⏭ Пропущено (дубликаты/нулевые): {skipped}",
        ]
        if errors:
            lines.append(f"❌ Ошибок записи: {errors}")

        await status_msg.edit_text("\n".join(lines), parse_mode="HTML")
