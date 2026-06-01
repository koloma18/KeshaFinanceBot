"""Обработчик команды /mono_day — выгрузка транзакций за конкретный день.

Формат: /mono_day <день>[.<месяц>] <номер_счёта>
Например: /mono_day 1 2 — 1-е число, второй счёт
          /mono_day 25.05 1 — 25 мая, первый счёт

Счета:
  1 = 4441 **** 5259 (основная)
  2 = 4441 **** 4454
"""

import logging
from datetime import datetime, timezone

from mono import build_transaction_row
from mono.client import MonobankClient, MonobankError, currency_code_to_name
from mono.mcc_categories import get_mcc_description
from sheets import add_row, find_row_by_source
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

PROGRESS_INTERVAL = 10


def _parse_day(args: list[str]) -> tuple[int, int, int]:
    """Разобрать аргументы: день[.месяц] и номер счёта. Возвращает (day, month, account_num)."""
    if len(args) < 2:
        raise ValueError(
            "Укажи день и номер счёта. Например:\n"
            "/mono_day 1 1 — 1-е число, счёт 5259\n"
            "/mono_day 25.05 2 — 25 мая, счёт 4454"
        )

    date_raw = args[0].strip()
    account_raw = args[1].strip()
    now = datetime.now(timezone.utc)

    if "." in date_raw:
        parts = date_raw.split(".")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError(
                f"Формат даты: день.месяц (например 25.05). Получено: {date_raw}"
            )
        day = int(parts[0])
        month = int(parts[1])
    else:
        if not date_raw.isdigit():
            raise ValueError(f"«{date_raw}» — не число. Укажи день: /mono_day 25 1")
        day = int(date_raw)
        month = now.month

    if not account_raw.isdigit():
        raise ValueError(f"«{account_raw}» — не номер счёта. Укажи 1 или 2.")
    account_num = int(account_raw)
    if account_num < 1 or account_num > 2:
        raise ValueError(f"Номер счёта должен быть 1 или 2. Получено: {account_num}")

    if day < 1 or day > 31:
        raise ValueError(f"День должен быть от 1 до 31. Получено: {day}")
    if month < 1 or month > 12:
        raise ValueError(f"Месяц должен быть от 1 до 12. Получено: {month}")

    return day, month, account_num


async def mono_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выгрузка транзакций Monobank за конкретный день.
    /mono_day <дата> <номер_счёта>"""
    try:
        day, month, account_num = _parse_day(context.args)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return

    # Маски счетов: 1 = 5259, 2 = 4454
    TARGET_MASKS: dict[int, str] = {1: "5259", 2: "4454"}
    target_suffix = TARGET_MASKS[account_num]

    now = datetime.now(timezone.utc)
    year = now.year
    if month > now.month:
        year -= 1

    # Транзакции за день: с 00:00 до 23:59
    from_dt = datetime(year, month, day, 0, 0, 0, tzinfo=timezone.utc)
    to_dt = datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc)
    from_ts = int(from_dt.timestamp())
    to_ts = int(to_dt.timestamp())

    date_label = f"{day:02d}.{month:02d}.{year}"

    await update.message.reply_chat_action("typing")
    status_msg = await update.message.reply_text(
        f"⏳ Жду очередь Monobank API (до 60 сек)..."
    )

    async with MonobankClient() as client:
        # Обновим статус перед запросом
        await status_msg.edit_text(f"🔄 Загружаю транзакции за {date_label}...")
        try:
            client_info = await client.get_client_info()
        except MonobankError as e:
            await status_msg.edit_text(
                f"❌ Ошибка Monobank: {e.message}\n\nПроверь X-Token."
            )
            return
        except Exception as e:
            logger.error("Client info error: %s", e)
            await status_msg.edit_text("❌ Не удалось подключиться к Monobank.")
            return

        accounts = client_info.get("accounts", [])
        if not accounts:
            await status_msg.edit_text("❌ Нет счетов в Monobank.")
            return

        # Найти счёт по последним 4 цифрам maskedPan
        account = None
        for acc in accounts:
            masked = acc.get("maskedPan", [""])[0]
            if masked.endswith(target_suffix):
                account = acc
                break

        if account is None:
            acc_list = "\n".join(
                f"  • {a.get('maskedPan', ['???'])[0]} ({a.get('type', '?')})"
                for a in accounts
            )
            await status_msg.edit_text(
                f"❌ Счёт *{target_suffix} не найден.\n\nДоступные счета:\n{acc_list}",
                parse_mode="HTML",
            )
            return
        account_id = account.get("id")
        if not account_id:
            await status_msg.edit_text("❌ Не удалось получить ID счёта.")
            return

        try:
            statements = await client.get_statement(account_id, from_ts, to_ts)
        except MonobankError as e:
            await status_msg.edit_text(f"❌ Ошибка выписки: {e.message}")
            return
        except Exception as e:
            logger.error("Statement error: %s", e)
            await status_msg.edit_text("❌ Не удалось получить выписку.")
            return

        if not statements:
            masked = account.get("maskedPan", ["???"])[0]
            await status_msg.edit_text(
                f"ℹ️ За {date_label} транзакций нет.\nСчёт: {masked}"
            )
            return

        total = 0
        skipped = 0
        errors = 0
        income_total = 0.0
        expense_total = 0.0
        tx_list: list[str] = []

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

            amount = tx.get("amount", 0) / 100.0
            mcc_desc = get_mcc_description(tx.get("mcc", 0))

            if ok:
                total += 1
                if amount > 0:
                    income_total += amount
                else:
                    expense_total += abs(amount)

                sign = "+" if amount > 0 else ""
                tx_list.append(
                    f"  {sign}{amount:.2f} — {tx.get('description', '')[:25]}"
                )
                if mcc_desc:
                    tx_list[-1] += f" ({mcc_desc})"
            else:
                errors += 1

        currency = "UAH"
        lines = [
            f"📅 <b>{date_label}</b> — выгрузка из Monobank",
            "",
            f"📥 Добавлено: <b>{total}</b>",
            f"💰 Доход: <b>+{income_total:,.2f} {currency}</b>",
            f"💸 Расход: <b>-{expense_total:,.2f} {currency}</b>",
            f"⏭ Пропущено: {skipped}",
        ]
        if errors:
            lines.append(f"❌ Ошибок: {errors}")

        if tx_list:
            lines.append("")
            lines.append("📋 <b>Детали:</b>")
            lines.extend(tx_list[:15])
            if len(tx_list) > 15:
                lines.append(f"  ... и ещё {len(tx_list) - 15}")

        await status_msg.edit_text("\n".join(lines), parse_mode="HTML")
