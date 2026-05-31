"""Обработчик команды /mono_sync — докачка пропущенных транзакций Monobank.

Формат: /mono_sync
Импортирует транзакции начиная с даты последней импортированной операции.
Если разрыв больше 31 дня — разбивает на чанки.
"""

import logging
from datetime import datetime, timezone

from mono import build_transaction_row
from mono.client import MonobankClient, MonobankError
from mono.mcc_categories import get_mcc_description
from sheets import COL, add_row, find_row_by_source, get_last_mono_timestamp
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

MAX_STATEMENT_DAYS = 31
PROGRESS_INTERVAL = 10
CHUNK_SECONDS = MAX_STATEMENT_DAYS * 86400


async def mono_sync(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Докачка пропущенных транзакций Monobank."""
    last_ts = get_last_mono_timestamp()
    if last_ts is None:
        await update.message.reply_text(
            "ℹ️ Сначала сделай /mono_import — нет предыдущих импортов Monobank."
        )
        return

    await update.message.reply_chat_action("typing")
    status_msg = await update.message.reply_text(
        "🔄 Синхронизирую транзакции Monobank..."
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
            await status_msg.edit_text("❌ Не удалось подключиться к Monobank.")
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
        from_ts = last_ts
        to_ts = now

        chunks: list[tuple[int, int]] = []
        chunk_start = from_ts
        while chunk_start < to_ts:
            chunk_end = min(chunk_start + CHUNK_SECONDS, to_ts)
            chunks.append((chunk_start, chunk_end))
            chunk_start = chunk_end + 1

        all_statements: list[dict] = []
        for chunk_idx, (c_from, c_to) in enumerate(chunks, start=1):
            c_from_dt = datetime.fromtimestamp(c_from, tz=timezone.utc).strftime(
                "%d.%m.%Y"
            )
            c_to_dt = datetime.fromtimestamp(c_to, tz=timezone.utc).strftime("%d.%m.%Y")

            await status_msg.edit_text(
                f"🔄 Загружаю чанк {chunk_idx}/{len(chunks)}: {c_from_dt} — {c_to_dt}"
            )

            try:
                chunk_data = await client.get_statement(account_id, c_from, c_to)
                all_statements.extend(chunk_data)
            except MonobankError as e:
                logger.error("Monobank statement error (chunk %s): %s", chunk_idx, e)
                await status_msg.edit_text(
                    f"❌ Ошибка при загрузке чанка {c_from_dt} — {c_to_dt}: {e.message}"
                )
                return
            except Exception as e:
                logger.error("Unexpected error getting statement chunk: %s", e)
                await status_msg.edit_text(
                    "❌ Не удалось получить выписку. Попробуй позже."
                )
                return

        if not all_statements:
            last_date = datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime(
                "%d.%m.%Y"
            )
            await status_msg.edit_text(f"ℹ️ Новых транзакций с {last_date} нет.")
            return

        total = 0
        skipped = 0
        errors = 0
        processed = 0

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

            processed += 1

            if processed % PROGRESS_INTERVAL == 0:
                mcc_desc = get_mcc_description(tx.get("mcc", 0))
                try:
                    await status_msg.edit_text(
                        f"🔄 Синхронизирую...\n"
                        f"✅ Добавлено: {total}\n"
                        f"⏭ Пропущено: {skipped}\n"
                        f"❌ Ошибок: {errors}\n"
                        f"\nПоследняя: {mcc_desc}"
                    )
                except Exception:
                    pass

        last_date = datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime(
            "%d.%m.%Y"
        )
        lines = [
            f"✅ <b>Синхронизация завершена</b>",
            f"",
            f"📅 Период: с {last_date} по сегодня",
            f"📦 Чанков загружено: {len(chunks)}",
            f"",
            f"📥 Добавлено: <b>{total}</b>",
            f"⏭ Пропущено (дубликаты/нулевые): {skipped}",
        ]
        if errors:
            lines.append(f"❌ Ошибок записи: {errors}")

        await status_msg.edit_text("\n".join(lines), parse_mode="HTML")
