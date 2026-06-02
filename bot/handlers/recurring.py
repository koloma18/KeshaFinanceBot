"""Telegram-хендлеры для регулярных платежей и подписок.

/recurring_add  — добавить регулярный платёж (fixed / variable / fx)
/recurring_list  — список активных и paused платежей
/recurring_pause  — поставить на паузу
/recurring_resume — возобновить
/recurring_delete — удалить (soft-delete)
/recurring_due   — интерактивный флоу оплаты с кнопками
"""

import logging
import re
from datetime import datetime

from account_aliases import resolve_account
from sheets import (
    add_recurring_item,
    add_row,
    calculate_initial_next_run_date,
    calculate_next_run_date,
    get_accounts,
    get_due_recurring_items,
    get_recurring_item,
    get_recurring_items,
    mark_recurring_deleted,
    pause_recurring_item,
    resume_recurring_item,
    update_recurring_item,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


# ── Account display mapping ────────────────────────────────────────────────

_ACCOUNT_DISPLAY = {
    "cash-uah": ("\U0001f4b5", "Наличными"),
    "card-office": ("\U0001f3e2", "Офисная карта"),
    "card-main": ("\U0001f4b3", "Личная Monobank"),
}

# Fallback canonical names when Accounts sheet is unreachable.
# These match the canonical names in account_aliases.py.
_CANONICAL_ACCOUNT_NAMES = {
    "cash-uah": "Наличка",
    "card-office": "4441...4454",
    "card-main": "4441...5259",
}


def _resolve_canonical_account_name(account_id: str) -> str:
    """Resolve canonical account name from Accounts sheet by ID.

    Returns the 'name' field from Accounts, or a hardcoded fallback,
    or the account_id itself if nothing found.
    """
    if not account_id:
        return ""
    # Priority 1: Accounts sheet
    accounts = get_accounts()
    for acc in accounts:
        if acc.get("id", "").lower() == account_id.lower():
            return acc.get("name", account_id)
    # Priority 2: Hardcoded fallback
    canonical = _CANONICAL_ACCOUNT_NAMES.get(account_id.lower())
    if canonical:
        return canonical
    # Priority 3: account_id itself
    return account_id


def _parse_date_to_period(date_val) -> str | None:
    """Parse a Date value from Google Sheets into YYYY-MM period.

    Handles various formats GS may return:
      - Serial date number (e.g. 46179.0)
      - String "02.06.2026", "2026-06-02", "02/06/2026"
      - datetime/date object
      - String with whitespace

    Returns "YYYY-MM" or None if unparseable.
    """
    if date_val is None:
        return None

    # ── Numeric: Google Sheets serial date ──────────────────────────
    if isinstance(date_val, (int, float)):
        try:
            from datetime import timedelta

            base = datetime(1899, 12, 30)
            dt = base + timedelta(days=int(float(date_val)))
            return f"{dt.year}-{dt.month:02d}"
        except Exception:
            pass

    # ── datetime/date object ────────────────────────────────────────
    if hasattr(date_val, "year") and hasattr(date_val, "month"):
        try:
            return f"{date_val.year}-{date_val.month:02d}"
        except Exception:
            pass

    # ── String ──────────────────────────────────────────────────────
    date_str = str(date_val).strip()
    if not date_str:
        return None

    # DD.MM.YYYY or D.M.YYYY or similar
    for sep in (".", "/"):
        parts = date_str.split(sep)
        if len(parts) == 3:
            try:
                if len(parts[0]) == 4:  # YYYY-MM-DD
                    return f"{parts[0]}-{int(parts[1]):02d}"
                else:  # DD.MM.YYYY
                    return f"{parts[2]}-{int(parts[1]):02d}"
            except (ValueError, IndexError):
                pass

    # ISO 8601 fallback
    try:
        dt = datetime.fromisoformat(date_str)
        return f"{dt.year}-{dt.month:02d}"
    except Exception:
        pass

    return None


def _find_recurring_transaction(item_id: str, period: str | None = None) -> bool:
    """Check if a recurring payment already has a transaction this period.

    Args:
        item_id: Recurring item ID.
        period: YYYY-MM string to check (default: current YYYY-MM).

    Returns True if a row with Source = 'recurring:<item_id>' and
    Date within the given YYYY-MM period already exists in Transactions.
    """
    from sheets import COL, get_all_rows

    if period is None:
        now = datetime.now()
        period = f"{now.year}-{now.month:02d}"

    source = f"recurring:{item_id}"
    try:
        rows = get_all_rows()
        for r in rows:
            if len(r) <= COL["SOURCE"]:
                continue
            row_source = str(r[COL["SOURCE"]]).strip() if r[COL["SOURCE"]] else ""
            if row_source != source:
                continue

            # Parse Date column
            if len(r) > COL["DATE"] and r[COL["DATE"]] is not None:
                raw_date = r[COL["DATE"]]
                row_period = _parse_date_to_period(raw_date)
                if row_period is None:
                    logger.warning(
                        "recurring dup check: unparseable Date=%r for source=%s",
                        raw_date, source,
                    )
                    continue
                if row_period == period:
                    logger.debug(
                        "recurring dup check: source=%s date=%r "
                        "parsed_period=%s target_period=%s duplicate=True",
                        source, raw_date, row_period, period,
                    )
                    return True
    except Exception:
        pass
    return False


def _resolve_account_display(account_id: str) -> tuple[str, str]:
    """Resolve (emoji, display_name) for an account ID — for UI button labels.

    Uses hardcoded mapping first, falls back to Accounts sheet.
    """
    known = _ACCOUNT_DISPLAY.get(account_id.lower())
    if known:
        return known
    # Fallback: lookup in Accounts sheet
    accounts = get_accounts()
    for acc in accounts:
        if acc.get("id", "").lower() == account_id.lower():
            return ("\U0001f4b3", acc.get("name", account_id))
    return ("\U0001f4b3", account_id)


# ── Helpers ────────────────────────────────────────────────────────────────


def _generate_id(title: str) -> str:
    """Generate a safe ID from title: lowercase, spaces->dashes, only word chars."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-") or "recurring"


def _parse_recurring_args(
    args: list[str],
) -> dict | None:
    """Parse /recurring_add arguments into a recurring item dict.

    Supported formats:
      A) Fixed UAH:
         expense 20000 UAH fixed Дом "Аренда квартиры" monthly 3 --grace 4 --pay a,b,c
      B) Variable:
         expense variable UAH Дом "Коммунальные" monthly 4 --grace 4 --pay a,b,c
      C) FX subscription:
         expense 2.49 USD fx Подписки "Apple" monthly 27 карта --estimate 110.64

    Returns dict ready for add_recurring_item(), or None on parse error.
    """
    flags = {
        "grace": None,
        "pay": None,
        "estimate": None,
        "id": None,
    }

    # Extract --flags
    positional = []
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            key = a[2:]
            if key in flags:
                if i + 1 < len(args) and not args[i + 1].startswith("--"):
                    flags[key] = args[i + 1]
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        else:
            positional.append(a)
            i += 1

    if len(positional) < 7:
        return None

    item_type = positional[0].lower()
    if item_type not in ("expense", "income"):
        return None

    amount_mode = None
    original_amount = 0.0
    original_currency = ""
    amount = 0.0
    currency = "UAH"

    if positional[1].lower() == "variable":
        amount_mode = "variable"
        currency = positional[2].upper()
        cat_start = 3
        title_tokens_start = 4
    else:
        try:
            amt = float(positional[1])
            curr = positional[2].upper()
            mode_token = positional[3].lower()
            if mode_token in ("fixed", "fx"):
                amount_mode = mode_token
                if amount_mode == "fixed":
                    amount = amt
                    currency = curr
                else:
                    original_amount = amt
                    original_currency = curr
                    currency = "UAH"
                cat_start = 4
                title_tokens_start = 5
            else:
                return None
        except ValueError:
            return None

    if amount_mode is None:
        return None

    account_alias = positional[-1].lower()
    account_resolved = resolve_account(account_alias)
    has_account_alias = account_resolved is not None

    if has_account_alias:
        freq_token = positional[-3]
        day_token = positional[-2]
        title_tokens_end = -3
    else:
        freq_token = positional[-2]
        day_token = positional[-1]
        title_tokens_end = -2

    freq_map = {
        "monthly": "monthly",
        "month": "monthly",
        "weekly": "weekly",
        "week": "weekly",
        "daily": "daily",
        "day": "daily",
    }
    frequency = freq_map.get(freq_token.lower(), "monthly")

    try:
        day_of_month = int(day_token)
    except ValueError:
        day_of_month = 1

    title_tokens = positional[title_tokens_start:title_tokens_end]
    title = " ".join(title_tokens).strip().strip('"').strip("'").strip()
    if not title:
        return None

    category = positional[cat_start]

    now = datetime.now().strftime("%Y-%m-%d")

    item = {
        "id": flags.get("id") or _generate_id(title),
        "title": title,
        "type": item_type,
        "amount": amount,
        "currency": currency,
        "original_amount": original_amount,
        "original_currency": original_currency,
        "estimated_uah": 0,
        "amount_mode": amount_mode,
        "category": category,
        "frequency": frequency,
        "day_of_month": day_of_month,
        "due_day": day_of_month,
        "grace_until_day": day_of_month,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }

    if amount_mode == "fixed":
        item["estimated_uah"] = amount
    if flags.get("estimate"):
        try:
            item["estimated_uah"] = float(flags["estimate"])
        except ValueError:
            pass

    if flags.get("grace"):
        try:
            item["grace_until_day"] = int(flags["grace"])
        except ValueError:
            pass
    if amount_mode == "fx" and not flags.get("grace"):
        item["grace_until_day"] = day_of_month

    if has_account_alias and account_resolved:
        acc_id, acc_name = account_resolved
        item["default_account_id"] = acc_id
        item["default_account_name"] = acc_name
        item["payment_options"] = acc_id

    if flags.get("pay"):
        item["payment_options"] = flags["pay"]

    if amount_mode == "fx":
        item["notes"] = f"original {original_amount} {original_currency}"

    item["next_run_date"] = calculate_initial_next_run_date(
        now, frequency, day_of_month
    )

    return item


# ── Transaction creation helper ────────────────────────────────────────────


def _create_transaction_from_recurring(
    item: dict,
    amount: float,
    account_id: str,
    account_name: str,
    estimated: bool = False,
) -> list:
    """Create a Transactions row list from a recurring item.

    Returns a list matching Transactions A:L columns ready for add_row().

    Args:
        item: Recurring item dict.
        amount: Transaction amount in UAH (positive, will be negated for expense).
        account_id: Account ID for col J.
        account_name: Canonical account name for col K.
        estimated: If True, append ' · estimated' to AI Comment for fx items.
    """
    mode = item.get("amount_mode", "fixed")
    now = datetime.now()
    month = now.strftime("%B")
    date_str = now.strftime("%d.%m.%Y")

    sign = -1 if item.get("type", "expense") == "expense" else 1
    amount_uah = sign * abs(amount)

    title = item.get("title", "")
    if mode == "fx":
        orig_amt = item.get("original_amount", 0)
        orig_cur = item.get("original_currency", "")
        comment = f"{title} · {orig_amt:.2f} {orig_cur}"
        if estimated:
            comment += " · estimated"
    else:
        comment = title

    return [
        month,
        date_str,
        item.get("type", "expense"),
        amount_uah,
        0,
        0,
        item.get("category", ""),
        comment,
        f"recurring:{item.get('id', '')}",
        account_id or "",
        account_name or "",
        "",
    ]


# ── Internal helper: save recurring transaction + update run dates ─────────


def _save_and_update(
    item: dict,
    amount: float,
    account_id: str,
    today_str: str,
    estimated: bool = False,
) -> tuple[bool, str]:
    """Save transaction row and update recurring run dates.

    Returns (success, warning_message).
    warning_message is empty on success, or a non-empty warning string.
    """
    item_id = item.get("id", "")

    # ── Duplicate protection ─────────────────────────────────────────
    period = today_str[:7]  # YYYY-MM
    if _find_recurring_transaction(item_id, period):
        return False, (
            f"\u26a0\ufe0f Платёж <b>{item['title']}</b> уже записан в этом месяце."
        )

    # Resolve canonical account name
    canonical_name = _resolve_canonical_account_name(account_id)

    row = _create_transaction_from_recurring(
        item,
        amount,
        account_id,
        canonical_name,
        estimated=estimated,
    )
    success = add_row(row)

    if not success:
        return False, ""

    from budget import BudgetManager

    BudgetManager.invalidate_after_transaction()

    next_run = calculate_next_run_date(
        today_str,
        item.get("frequency", "monthly"),
        item.get("day_of_month"),
    )

    updated = update_recurring_item(
        item_id,
        {
            "last_run_date": today_str,
            "next_run_date": next_run,
            "last_action": "paid",
        },
    )

    warning = ""
    if not updated:
        warning = (
            "\u26a0\ufe0f Транзакция записана, но не удалось обновить "
            "NextRunDate в Recurring. Проверь /recurring_list."
        )

    return True, warning


# ── Handlers ───────────────────────────────────────────────────────────────


async def recurring_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Добавить регулярный платёж."""
    args = context.args
    if not args or len(args) < 7:
        await update.message.reply_html(
            "\U0001f501 <b>Добавление регулярного платежа</b>\n\n"
            "<b>Fixed UAH:</b>\n"
            "<code>/recurring_add expense 20000 UAH fixed Дом "
            '"Аренда квартиры" monthly 3 --grace 4 '
            "--pay cash-uah,card-office,card-main</code>\n\n"
            "<b>Variable:</b>\n"
            "<code>/recurring_add expense variable UAH Дом "
            '"Коммунальные" monthly 4 --grace 4 '
            "--pay cash-uah,card-office,card-main</code>\n\n"
            "<b>FX subscription:</b>\n"
            '<code>/recurring_add expense 2.49 USD fx Подписки "Apple" '
            "monthly 27 карта --estimate 110.64</code>\n\n"
            "Опции: <code>--id</code> <code>--grace</code> "
            "<code>--pay</code> <code>--estimate</code>",
        )
        return

    item = _parse_recurring_args(args)
    if item is None:
        await update.message.reply_text(
            "\u274c Не удалось разобрать команду. Проверь формат:\n"
            "/recurring_add expense 20000 UAH fixed Дом "
            '"Аренда квартиры" monthly 3 --grace 4 --pay cash-uah,card-office,card-main'
        )
        return

    result = add_recurring_item(item)
    if result:
        mode_icon = {
            "fixed": "\U0001f4b0",
            "variable": "\U0001f4a1",
            "fx": "\U0001f4b1",
        }.get(item["amount_mode"], "\U0001f501")
        amount_str = _format_amount_display(item)

        lines = [
            f"\u2705 {mode_icon} <b>{item['title']}</b> добавлен",
            f"   {amount_str}",
            f"   Категория: {item['category']}",
            f"   Период: {item['frequency']}, {item['day_of_month']} число",
        ]
        if item.get("grace_until_day") and item["grace_until_day"] != item.get(
            "day_of_month"
        ):
            lines.append(f"   Можно до {item['grace_until_day']} числа")
        if item.get("payment_options"):
            lines.append(f"   Оплата: {item['payment_options']}")
        if item.get("id"):
            lines.append(f"   ID: <code>{item['id']}</code>")

        await update.message.reply_html("\n".join(lines))
    else:
        await update.message.reply_text("\u274c Ошибка при сохранении. Проверь данные.")


def _format_amount_display(item: dict) -> str:
    """Format amount for display in list/due."""
    mode = item.get("amount_mode", "fixed")
    if mode == "fixed":
        return f"{item['amount']:,.0f} {item['currency']}"
    elif mode == "fx":
        return (
            f"{item['original_amount']:.2f} {item['original_currency']}"
            f" · ориентир ~{item['estimated_uah']:,.0f} {item['currency']}"
        )
    else:
        est = item.get("estimated_uah", 0)
        if est:
            return f"Сумма: переменная (~{est:,.0f} {item['currency']})"
        return "Сумма: переменная"


def _format_recurring_item(item: dict, index: int | None = None) -> str:
    """Format a single recurring item for display in list."""
    mode = item.get("amount_mode", "fixed")
    icon = {"fixed": "\U0001f4b0", "variable": "\U0001f4a1", "fx": "\U0001f4b1"}.get(
        mode, "\U0001f501"
    )
    title = item.get("title", "Без названия")
    category = item.get("category", "")

    num_prefix = f"{index}. " if index is not None else ""

    lines = [f"{icon} {num_prefix}<b>{title}</b>"]

    amount_str = _format_amount_display(item)
    if category:
        lines.append(f"{amount_str} · {category}")
    else:
        lines.append(amount_str)

    freq = item.get("frequency", "monthly")
    dom = item.get("day_of_month", 1)
    grace = item.get("grace_until_day", dom)
    grace_str = ""
    if grace and grace != dom:
        grace_str = f", можно до {grace}"

    freq_display = {
        "monthly": "Каждый месяц",
        "weekly": "Каждую неделю",
        "daily": "Каждый день",
    }.get(freq, freq)

    if mode == "variable":
        lines.append(f"{freq_display}: до {dom} числа{grace_str}")
    else:
        lines.append(f"{freq_display}: {dom} число{grace_str}")

    pay = item.get("payment_options", "")
    if pay:
        lines.append(f"Оплата: {pay}")

    status = item.get("status", "active")
    status_display = {
        "active": "\U0001f7e2 active",
        "paused": "\u23f8 paused",
        "deleted": "\U0001f5d1 deleted",
    }.get(status, status)
    lines.append(f"Статус: {status_display}")

    next_run = item.get("next_run_date", "")
    if next_run and status == "active":
        lines.append(f"Следующий запуск: {next_run}")

    return "\n".join(lines)


async def recurring_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать список регулярных платежей (active + paused)."""
    items = get_recurring_items(status_filter=None)
    visible = [i for i in items if i.get("status") in ("active", "paused")]

    if not visible:
        await update.message.reply_text(
            "\U0001f501 Регулярных платежей пока нет.\nДобавь через /recurring_add"
        )
        return

    lines = ["<b>\U0001f501 Регулярные платежи</b>\n"]
    for idx, item in enumerate(visible, 1):
        lines.append(_format_recurring_item(item, index=idx))
        lines.append("")

    await update.message.reply_html("\n".join(lines))


async def recurring_pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Поставить регулярный платёж на паузу: /recurring_pause <id>"""
    args = context.args
    if not args:
        await update.message.reply_text(
            "\u274c Укажи ID платежа: /recurring_pause rent-flat"
        )
        return

    item_id = args[0]
    item = get_recurring_item(item_id)

    if item is None:
        await update.message.reply_text(
            f"\u274c Платёж с ID <code>{item_id}</code> не найден.", parse_mode="HTML"
        )
        return

    if item.get("status") == "paused":
        await update.message.reply_text(
            f"\u23f8 Платёж <b>{item['title']}</b> уже на паузе.", parse_mode="HTML"
        )
        return

    ok = pause_recurring_item(item_id)
    if ok:
        await update.message.reply_text(
            f"\u23f8 Платёж <b>{item['title']}</b> поставлен на паузу.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text("\u274c Ошибка при обновлении.")


async def recurring_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Возобновить регулярный платёж: /recurring_resume <id>"""
    args = context.args
    if not args:
        await update.message.reply_text(
            "\u274c Укажи ID платежа: /recurring_resume rent-flat"
        )
        return

    item_id = args[0]
    item = get_recurring_item(item_id)

    if item is None:
        await update.message.reply_text(
            f"\u274c Платёж с ID <code>{item_id}</code> не найден.", parse_mode="HTML"
        )
        return

    if item.get("status") == "active":
        await update.message.reply_text(
            f"\u25b6\ufe0f Платёж <b>{item['title']}</b> уже активен.",
            parse_mode="HTML",
        )
        return

    ok = resume_recurring_item(item_id)
    if ok:
        await update.message.reply_text(
            f"\u25b6\ufe0f Платёж <b>{item['title']}</b> возобновлён.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text("\u274c Ошибка при обновлении.")


async def recurring_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удалить регулярный платёж: /recurring_delete <id>"""
    args = context.args
    if not args:
        await update.message.reply_text(
            "\u274c Укажи ID платежа: /recurring_delete rent-flat"
        )
        return

    item_id = args[0]
    item = get_recurring_item(item_id)

    if item is None:
        await update.message.reply_text(
            f"\u274c Платёж с ID <code>{item_id}</code> не найден.", parse_mode="HTML"
        )
        return

    ok = mark_recurring_deleted(item_id)
    if ok:
        await update.message.reply_text(
            f"\U0001f5d1 Платёж <b>{item['title']}</b> удалён.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text("\u274c Ошибка при удалении.")


# ── Interactive /recurring_due ─────────────────────────────────────────────


def _build_due_card(item: dict, today_str: str) -> tuple[str, InlineKeyboardMarkup]:
    """Build a message card and inline keyboard for one due item.

    Returns (html_text, InlineKeyboardMarkup).
    """
    mode = item.get("amount_mode", "fixed")
    item_id = item.get("id", "")
    title = item.get("title", "Без названия")
    category = item.get("category", "")
    dom = item.get("day_of_month", 1)
    grace = item.get("grace_until_day", dom)
    frequency = item.get("frequency", "monthly")

    overdue = False
    try:
        today_dom = int(today_str.split("-")[2])
        if today_dom > grace and grace and grace > 0:
            overdue = True
    except (ValueError, IndexError):
        pass

    freq_display = {
        "monthly": "ежемесячно",
        "weekly": "еженедельно",
        "daily": "ежедневно",
    }.get(frequency, frequency)

    lines = []

    if mode == "fixed":
        icon = "\U0001f3e0" if "аренд" in title.lower() else "\U0001f4b0"
        amount = item.get("amount", 0)
        lines.append(f"{icon} <b>Плановый платёж:</b> {title}")
        lines.append(f"<b>Сумма:</b> {amount:,.0f} {item.get('currency', 'UAH')}")
        if category:
            lines.append(f"<b>Категория:</b> {category}")
        lines.append(f"<b>Оплатить:</b> {dom}-го числа ({freq_display})")
        if grace and grace != dom:
            lines.append(f"<b>Можно до:</b> {grace}-го числа")

    elif mode == "variable":
        lines.append(f"\U0001f4a1 <b>{title}</b>")
        lines.append("Сумма каждый месяц разная.")
        lines.append(f"Нужно оплатить до {dom}-го числа ({freq_display}).")
        if category:
            lines.append(f"<b>Категория:</b> {category}")

    elif mode == "fx":
        orig_amt = item.get("original_amount", 0)
        orig_cur = item.get("original_currency", "")
        est_uah = item.get("estimated_uah", 0)
        lines.append(f"\U0001f4f1 <b>Подписка:</b> {title}")
        lines.append(f"<b>Оригинал:</b> {orig_amt:.2f} {orig_cur}")
        lines.append(f"<b>Ориентир:</b> ~{est_uah:,.0f} UAH")
        lines.append("Курс может отличаться.")
        if category:
            lines.append(f"<b>Категория:</b> {category}")

    if overdue:
        if grace and grace != dom:
            lines.insert(0, f"\u26a0\ufe0f <b>Просрочено с {grace}-го числа</b>")
        else:
            lines.insert(0, "\u26a0\ufe0f <b>Просрочено</b>")

    text = "\n".join(lines)

    keyboard = []

    if mode == "fixed":
        pay_opts_str = item.get("payment_options", "")
        if pay_opts_str:
            pay_ids = [p.strip() for p in pay_opts_str.split(",") if p.strip()]
            for pid in pay_ids:
                emoji, name = _resolve_account_display(pid)
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"{emoji} {name}",
                            callback_data=f"rec_pay|{item_id}|{pid}",
                        )
                    ]
                )
        if not keyboard:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "\u2705 Оплатить",
                        callback_data=f"rec_pay|{item_id}|",
                    )
                ]
            )

    elif mode == "variable":
        keyboard.append(
            [
                InlineKeyboardButton(
                    "\u270d\ufe0f Ввести сумму",
                    callback_data=f"rec_amount|{item_id}",
                )
            ]
        )

    elif mode == "fx":
        keyboard.append(
            [
                InlineKeyboardButton(
                    "\u2705 Записать по ориентиру",
                    callback_data=f"rec_est|{item_id}",
                )
            ]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "\u270d\ufe0f Ввести фактическую UAH",
                    callback_data=f"rec_actual|{item_id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                "\u23ed Пропустить",
                callback_data=f"rec_skip|{item_id}",
            )
        ]
    )

    return text, InlineKeyboardMarkup(keyboard)


async def recurring_due(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать регулярные платежи к оплате сегодня — с кнопками действий."""
    due = get_due_recurring_items()

    if not due:
        await update.message.reply_text("\u2705 На сегодня регулярных платежей нет.")
        return

    today_str = datetime.now().strftime("%Y-%m-%d")

    for item in due:
        text, markup = _build_due_card(item, today_str)
        await update.message.reply_html(text, reply_markup=markup)


# ── Callback handler for recurring due actions ─────────────────────────────


async def recurring_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle inline button callbacks from /recurring_due cards.

    Patterns:
      rec_pay|<item_id>|<account_id>   — pay with specific account
      rec_skip|<item_id>               — skip this payment
      rec_amount|<item_id>             — enter amount for variable
      rec_actual|<item_id>             — enter actual UAH for fx
      rec_est|<item_id>                — record by estimated UAH (fx)
      rec_acct|<item_id>|<account_id>  — select account after entering amount
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    parts = data.split("|")
    if len(parts) < 2:
        return

    action = parts[0]
    item_id = parts[1]

    item = get_recurring_item(item_id)
    if item is None:
        await query.edit_message_text(
            f"\u274c Платёж <code>{item_id}</code> не найден.", parse_mode="HTML"
        )
        return

    today_str = datetime.now().strftime("%Y-%m-%d")

    # ── rec_skip: skip this occurrence ──────────────────────────────────
    if action == "rec_skip":
        next_run = calculate_next_run_date(
            today_str,
            item.get("frequency", "monthly"),
            item.get("day_of_month"),
        )
        update_recurring_item(
            item_id,
            {
                "last_run_date": today_str,
                "next_run_date": next_run,
                "last_action": "skipped",
            },
        )
        await query.edit_message_text(
            f"\u23ed Пропущено. Следующее напоминание: <b>{next_run}</b>",
            parse_mode="HTML",
        )
        return

    # ── rec_amount: variable — ask for amount ───────────────────────────
    if action == "rec_amount":
        context.user_data["pending_recurring"] = {
            "item_id": item_id,
            "mode": "variable",
        }
        await query.edit_message_text(
            f"\U0001f4a1 <b>{item['title']}</b>\nВведи сумму в UAH числом (например, 2750):",
            parse_mode="HTML",
        )
        return

    # ── rec_actual: fx — ask for actual UAH ─────────────────────────────
    if action == "rec_actual":
        context.user_data["pending_recurring"] = {
            "item_id": item_id,
            "mode": "fx_actual",
        }
        await query.edit_message_text(
            f"\U0001f4f1 <b>{item['title']}</b>\n"
            f"Оригинал: {item.get('original_amount', 0):.2f} "
            f"{item.get('original_currency', '')}\n\n"
            "Введи фактическую сумму в UAH:",
            parse_mode="HTML",
        )
        return

    # ── rec_est: fx — record by estimated UAH ───────────────────────────
    if action == "rec_est":
        estimated_uah = item.get("estimated_uah", 0)
        if estimated_uah <= 0:
            await query.edit_message_text(
                "\u274c Нет ориентировочной суммы. Введи вручную через кнопку ниже."
            )
            return

        acc_id = item.get("default_account_id", "")

        ok, warning = _save_and_update(
            item,
            estimated_uah,
            acc_id,
            today_str,
            estimated=True,
        )

        if not ok:
            if warning:
                await query.edit_message_text(warning, parse_mode="HTML")
            else:
                await query.edit_message_text("\u274c Ошибка при записи в таблицу.")
            return

        msg = (
            f"\u2705 Записано по ориентиру: <code>-{estimated_uah:,.0f} UAH</code>\n"
            f"\U0001f4f1 {item['title']} · {item.get('original_amount', 0):.2f} "
            f"{item.get('original_currency', '')} · estimated"
        )
        if warning:
            msg += f"\n\n{warning}"

        await query.edit_message_text(msg, parse_mode="HTML")
        return

    # ── rec_pay: fixed — pay with selected account ──────────────────────
    if action == "rec_pay":
        account_id = parts[2] if len(parts) > 2 else ""
        amount = item.get("amount", 0)

        if amount <= 0:
            await query.edit_message_text("\u274c Сумма платежа не задана.")
            return

        ok, warning = _save_and_update(item, amount, account_id, today_str)

        if not ok:
            if warning:
                await query.edit_message_text(warning, parse_mode="HTML")
            else:
                await query.edit_message_text("\u274c Ошибка при записи в таблицу.")
            return

        emoji, display_name = (
            _resolve_account_display(account_id) if account_id else ("", "")
        )
        canonical = _resolve_canonical_account_name(account_id)

        msg = (
            f"\u2705 Оплачено: <code>-{amount:,.0f} UAH</code> · {item['title']}\n"
            f"{emoji} {display_name} ({canonical})"
        )
        if warning:
            msg += f"\n\n{warning}"

        await query.edit_message_text(msg, parse_mode="HTML")
        return

    # ── rec_acct: account chosen after amount entry ─────────────────────
    if action == "rec_acct":
        pending = context.user_data.get("pending_recurring")
        if not pending or pending.get("item_id") != item_id:
            await query.edit_message_text(
                "\u23f3 Сессия истекла. Запусти /recurring_due снова."
            )
            return

        amount_val = pending.get("amount", 0)
        if amount_val <= 0:
            await query.edit_message_text("\u274c Сумма не задана.")
            return

        account_id = parts[2] if len(parts) > 2 else ""

        ok, warning = _save_and_update(item, amount_val, account_id, today_str)

        context.user_data.pop("pending_recurring", None)

        if not ok:
            if warning:
                await query.edit_message_text(warning, parse_mode="HTML")
            else:
                await query.edit_message_text("\u274c Ошибка при записи в таблицу.")
            return

        emoji, display_name = (
            _resolve_account_display(account_id) if account_id else ("", "")
        )
        canonical = _resolve_canonical_account_name(account_id)

        msg = (
            f"\u2705 Оплачено: <code>-{amount_val:,.0f} UAH</code> · {item['title']}\n"
            f"{emoji} {display_name} ({canonical})"
        )
        if warning:
            msg += f"\n\n{warning}"

        await query.edit_message_text(msg, parse_mode="HTML")
        return


# ── Pending amount text handler (called from handle_text in main.py) ───────


async def handle_recurring_amount(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """Process text input as a recurring payment amount.

    Called when context.user_data has 'pending_recurring'.
    Returns True if the message was handled, False otherwise.
    """
    pending = context.user_data.get("pending_recurring")
    if not pending:
        return False

    text = update.message.text.strip()
    item_id = pending.get("item_id")
    mode = pending.get("mode")

    try:
        amount = float(text.replace(",", ".").replace(" ", ""))
    except ValueError:
        await update.message.reply_text(
            "\u274c Введи число (например, 2750). Попробуй ещё раз:"
        )
        return True

    if amount <= 0:
        await update.message.reply_text(
            "\u274c Сумма должна быть больше нуля. Попробуй ещё раз:"
        )
        return True

    pending["amount"] = amount

    item = get_recurring_item(item_id)
    if item is None:
        context.user_data.pop("pending_recurring", None)
        await update.message.reply_text(
            "\u274c Платёж не найден. Запусти /recurring_due снова."
        )
        return True

    if mode == "variable":
        pay_opts_str = item.get("payment_options", "")
        if pay_opts_str:
            pay_ids = [p.strip() for p in pay_opts_str.split(",") if p.strip()]
            keyboard = []
            row_buttons = []
            for pid in pay_ids:
                emoji, name = _resolve_account_display(pid)
                row_buttons.append(
                    InlineKeyboardButton(
                        f"{emoji} {name}",
                        callback_data=f"rec_acct|{item_id}|{pid}",
                    )
                )
                if len(row_buttons) == 2:
                    keyboard.append(row_buttons)
                    row_buttons = []
            if row_buttons:
                keyboard.append(row_buttons)
        else:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "\u2705 Сохранить",
                        callback_data=f"rec_acct|{item_id}|{item.get('default_account_id', '')}",
                    )
                ]
            ]

        await update.message.reply_html(
            f"\U0001f4a1 <b>{item['title']}</b>\n"
            f"Сумма: <b>{amount:,.0f} UAH</b>\n\n"
            "Выбери способ оплаты:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return True

    if mode == "fx_actual":
        acc_id = item.get("default_account_id", "")
        today_str = datetime.now().strftime("%Y-%m-%d")

        ok, warning = _save_and_update(item, amount, acc_id, today_str)

        context.user_data.pop("pending_recurring", None)

        if not ok:
            if warning:
                await update.message.reply_text(warning, parse_mode="HTML")
            else:
                await update.message.reply_text("\u274c Ошибка при записи в таблицу.")
            return True

        msg = (
            f"\u2705 Записано: <code>-{amount:,.0f} UAH</code>\n"
            f"\U0001f4f1 {item['title']} · {item.get('original_amount', 0):.2f} "
            f"{item.get('original_currency', '')}"
        )
        if warning:
            msg += f"\n\n{warning}"

        await update.message.reply_html(msg)
        return True

    return False
