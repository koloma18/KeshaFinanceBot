"""Обработчик команды /mono_sync — докачка пропущенных транзакций Monobank.

Формат: /mono_sync
Синхронизирует счета 5259 и 4454 с последней импортированной транзакции.
"""

import logging
from datetime import datetime, timezone

from mono import build_transaction_row
from mono.client import MonobankClient, MonobankError
from mono.mcc_categories import get_mcc_description
from sheets import add_row, find_row_by_source, get_last_mono_timestamp
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

MAX_STATEMENT_DAYS = 31
CHUNK_SECONDS = MAX_STATEMENT_DAYS * 86400

PRIORITY_MASKS = ["5259", "4454"]


async def mono_sync(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Синхронизация счетов 5259 и 4454."""
    last_ts = get_last_mono_timestamp()
    if last_ts is None:
        await update.message.reply_text(
            "ℹ️ Сначала сделай /mono_import — нет предыдущих импортов Monobank."
        )
        return

    await update.message.reply_chat_action("typing")
    status_msg = await update.message.reply_text("🔄 Синхронизирую Monobank...")

    async with MonobankClient() as client:
        try:
            client_info = await client.get_client_info()
        except MonobankError as e:
            await status_msg.edit_text(f"❌ Ошибка: {e.message}")
            return
        except Exception:
            await status_msg.edit_text("❌ Не удалось подключиться.")
            return

        accounts = client_info.get("accounts", [])
        if not accounts:
            await status_msg.edit_text("❌ Нет счетов.")
            return

        # Найти основные счета
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
        grand_total = 0
        grand_skipped = 0
        grand_errors = 0
        account_lines: list[str] = []

        for account in target_accounts:
            account_id = account.get("id")
            if not account_id:
                continue
            masked = (account.get("maskedPan", ["???"]) or ["???"])[0]

            await status_msg.edit_text(f"🔄 Счёт {masked}...")

            # Собрать все чанки
            chunks: list[tuple[int, int]] = []
            chunk_start = last_ts
            while chunk_start < now:
                chunk_end = min(chunk_start + CHUNK_SECONDS, now)
                chunks.append((chunk_start, chunk_end))
                chunk_start = chunk_end + 1

            all_statements: list[dict] = []
            for chunk_idx, (c_from, c_to) in enumerate(chunks, 1):
                await status_msg.edit_text(
                    f"🔄 {masked}: чанк {chunk_idx}/{len(chunks)}..."
                )
                try:
                    chunk_data = await client.get_statement(account_id, c_from, c_to)
                    all_statements.extend(chunk_data)
                except MonobankError as e:
                    await status_msg.edit_text(f"❌ {masked}: {e.message}")
                    return

            if not all_statements:
                account_lines.append(f"💳 {masked}: нет новых")
                continue

            total = 0
            skipped = 0
            errors = 0
            for tx in all_statements:
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

        last_date = datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime(
            "%d.%m.%Y"
        )
        lines = [
            f"✅ <b>Синхронизация завершена</b>",
            f"📅 С {last_date} по сегодня",
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
