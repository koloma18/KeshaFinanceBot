"""Управление счетами (лист Accounts).

/add_bank <id> <name_or_pan> <balance> <currency> — добавить/обновить счёт
/del_bank <id> — деактивировать счёт (soft-delete)
/set_balance <id> <balance> — обновить баланс
/banks — показать все счета с балансами из транзакций
"""

import logging

from sheets import get_account_balances, get_accounts, upsert_account
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def add_bank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Добавить или обновить счёт в листе Accounts.

    /add_bank test-card 5457082516868762 114.43 UAH
    ── создаёт строку: ID=test-card, Name=5457...8762
    """
    args = context.args
    if len(args) < 4:
        await update.message.reply_text(
            "❌ Формат: /add_bank ID PAN баланс UAH\n"
            "Пример: /add_bank test-card 5457082516868762 114.43 UAH"
        )
        return

    account_id = args[0]
    name = args[1]
    try:
        balance = float(args[2])
    except ValueError:
        await update.message.reply_text("❌ Баланс должен быть числом.")
        return
    currency = args[3].upper()

    ok = upsert_account(
        account_id=account_id,
        name=name,
        acc_type="card",
        currency=currency,
        balance=balance,
        source="manual",
        active=True,
    )
    if ok:
        await update.message.reply_text(
            f"✅ Счёт «{account_id}» сохранён: {balance:,.2f} {currency}\n"
            f"   PAN: {name}"
        )
    else:
        await update.message.reply_text(
            "❌ Не удалось сохранить. Проверь Google Sheets."
        )


async def del_bank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Деактивировать счёт (soft-delete через Active = FALSE).

    /del_bank test-card
    """
    if not context.args:
        await update.message.reply_text("❌ Укажи ID счёта: /del_bank test-card")
        return

    account_id = context.args[0]
    existing = get_accounts()

    target = None
    for acc in existing:
        if acc["id"].lower() == account_id.lower():
            target = acc
            break

    if not target:
        await update.message.reply_text(
            f"❌ Счёт с ID «{account_id}» не найден в Accounts."
        )
        return

    ok = upsert_account(
        account_id=target["id"],
        name=target["name"],
        acc_type=target.get("type", "bank"),
        currency=target.get("currency", "UAH"),
        balance=target.get("balance", 0.0),
        source=target.get("source", "manual"),
        active=False,
    )
    if ok:
        await update.message.reply_text(
            f"🗑 Счёт «{target['id']}» деактивирован (Active = FALSE)."
        )
    else:
        await update.message.reply_text("❌ Не удалось деактивировать.")


async def set_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обновить баланс счёта в Accounts.

    /set_balance test-card 200
    """
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Формат: /set_balance ID 150.00\nПример: /set_balance test-card 150.00"
        )
        return

    account_id = context.args[0]
    try:
        new_balance = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Баланс должен быть числом.")
        return

    existing = get_accounts()
    target = None
    for acc in existing:
        if acc["id"].lower() == account_id.lower():
            target = acc
            break

    if not target:
        await update.message.reply_text(
            f"❌ Счёт с ID «{account_id}» не найден в Accounts. Сначала /add_bank"
        )
        return

    old_balance = target["balance"]
    ok = upsert_account(
        account_id=target["id"],
        name=target["name"],
        acc_type=target.get("type", "bank"),
        currency=target.get("currency", "UAH"),
        balance=new_balance,
        source=target.get("source", "manual"),
        active=target.get("active", True),
    )
    if ok:
        await update.message.reply_text(
            f"✅ «{target['id']}»: {old_balance:,.2f}"
            f" → {new_balance:,.2f} {target['currency']}"
        )
    else:
        await update.message.reply_text("❌ Не удалось обновить.")


async def banks_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать все счета с балансами из транзакций (только Accounts)."""
    account_balances = get_account_balances()

    if not account_balances:
        await update.message.reply_text("💳 Счетов нет. Добавь через /add_bank")
        return

    lines = ["📊 <b>Счета</b>", ""]

    total = sum(a["balance"] for a in account_balances)
    for acc in account_balances:
        sign = "+" if acc["balance"] >= 0 else ""
        extra = ""
        if acc["name"] == "Без счета":
            extra = f" ({acc['transaction_count']} оп.)"
        else:
            extra = (
                f" | +{acc['income']:,.0f} / -{acc['expense']:,.0f}"
                if acc["income"] or acc["expense"]
                else ""
            )
        lines.append(
            f"  • {acc['name']} — {sign}{acc['balance']:,.2f} {acc['currency']}{extra}"
        )

    lines.append("")
    total_sign = "+" if total >= 0 else ""
    lines.append(f"  📌 <b>Итого: {total_sign}{total:,.2f} UAH</b>")

    await update.message.reply_html("\n".join(lines))
