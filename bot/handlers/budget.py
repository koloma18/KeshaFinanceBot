"""Хендлеры бюджета и лимитов: /budget, /set_limit, /limits, /limit_alerts."""

import logging
from decimal import Decimal, InvalidOperation

from budget import BudgetManager
from categories import normalize_category
from responses import (
    get_budget_deleted_response,
    get_budget_set_response,
    get_limit_deleted_response,
    get_limit_set_response,
    get_no_budget_response,
    get_no_limits_response,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from user_settings import persist_setting

logger = logging.getLogger(__name__)

MONTH_NAMES_RU = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "октябрь",
    11: "ноябрь",
    12: "декабрь",
}


def _month_name_ru(ym: str) -> str:
    """'2026-06' -> 'июнь 2026'."""
    try:
        parts = ym.split("-")
        year = parts[0]
        month_num = int(parts[1])
        name = MONTH_NAMES_RU.get(month_num, "")
        return f"{name} {year}"
    except (IndexError, ValueError):
        return ym


def _parse_amount(text: str) -> Decimal | None:
    """Парсит число из строки. Умеет "50000", "50 000", "50000.50"."""
    try:
        cleaned = text.replace(" ", "").replace(",", ".")
        return Decimal(cleaned)
    except InvalidOperation:
        return None


async def budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Управление общим бюджетом.

    /budget           — показать статус
    /budget 50000     — установить бюджет на месяц
    /budget delete    — удалить бюджет
    """
    args = context.args
    month = BudgetManager.current_month()
    month_display = _month_name_ru(month)

    if not args:
        status = BudgetManager.get_budget_status(month)
        if status is None:
            text = f"📊 <b>Бюджет на {month_display}</b>\n\n{get_no_budget_response()}"
        else:
            budget_fmt = f"{status['budget']:,.0f}".replace(",", " ")
            spent_fmt = f"{status['spent']:,.0f}".replace(",", " ")
            remain_fmt = f"{status['remaining']:,.0f}".replace(",", " ")
            text = (
                f"📊 <b>Бюджет на {month_display}</b>\n\n"
                f"▸ Всего: {budget_fmt} UAH\n"
                f"▸ Потрачено: {spent_fmt} UAH\n"
                f"▸ Осталось: {remain_fmt} UAH\n\n"
                f"{status['bar']} {status['percent'] * 100:.0f}%\n\n"
                f"<i>Бюджет есть. Смотри не просри.</i>"
            )
        await update.message.reply_html(text)
        return

    # /budget delete
    if args[0].lower() == "delete":
        ok = BudgetManager.delete_budget(month)
        if ok:
            text = f"🗑 {get_budget_deleted_response()}"
        else:
            text = "Бюджет не был установлен. Нечего удалять."
        await update.message.reply_text(text)
        return

    # /budget <amount>
    amount = _parse_amount(args[0])
    if amount is None or amount <= 0:
        await update.message.reply_text(
            "Некорректная сумма. Пример: <code>/budget 50000</code>",
            parse_mode="HTML",
        )
        return

    ok = BudgetManager.set_budget(float(amount), month)
    if ok:
        amt_fmt = f"{amount:,.0f}".replace(",", " ")
        text = (
            f"💰 {get_budget_set_response()}\n\n"
            f"▸ Бюджет на {month_display}: <b>{amt_fmt} UAH</b>"
        )
        await update.message.reply_html(text)
    else:
        await update.message.reply_text("Что-то пошло не так. Попробуй ещё раз.")


async def set_limit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Установить лимит категории.

    /set_limit Кофе 3000
    /set_limit Кофе delete  — удалить лимит
    """
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Формат: <code>/set_limit Категория 3000</code>\n"
            "Или: <code>/set_limit Категория delete</code>",
            parse_mode="HTML",
        )
        return

    # Первый аргумент — категория (может быть из нескольких слов, если это delete)
    # Ищем, где заканчивается название категории
    if args[-1].lower() == "delete":
        category_raw = " ".join(args[:-1])
        category = normalize_category(category_raw)

        ok = BudgetManager.delete_limit(category)
        if ok:
            text = f"🗑 {get_limit_deleted_response(category)}"
        else:
            text = f"Лимит на «{category}» не был установлен."
        await update.message.reply_text(text)
        return

    # category = всё кроме последнего аргумента
    category_raw = " ".join(args[:-1])
    category = normalize_category(category_raw)

    amount = _parse_amount(args[-1])
    if amount is None or amount <= 0:
        await update.message.reply_text(
            "Некорректная сумма. Пример: <code>/set_limit Кофе 3000</code>",
            parse_mode="HTML",
        )
        return

    month = BudgetManager.current_month()
    ok = BudgetManager.set_limit(category, float(amount), month)
    if ok:
        text = get_limit_set_response(category, float(amount))
        await update.message.reply_text(text)
    else:
        await update.message.reply_text("Что-то пошло не так. Попробуй ещё раз.")


async def limits_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать все лимиты категорий с прогресс-баром."""
    month = BudgetManager.current_month()
    month_display = _month_name_ru(month)
    limits = BudgetManager.get_limits(month)

    if not limits:
        text = f"📋 <b>Лимиты на {month_display}</b>\n\n{get_no_limits_response()}"
        await update.message.reply_html(text)
        return

    lines = [f"📋 <b>Лимиты на {month_display}</b>\n"]
    emoji_map = {
        "кофе": "☕",
        "еда": "🍔",
        "такси": "🚕",
        "одежда": "👗",
        "красота": "💄",
        "подписки": "📡",
        "дом": "🏠",
        "подарки": "🎁",
        "маркетплейсы": "📦",
        "здоровье": "💊",
        "развлечения": "🎬",
        "другое": "📎",
    }

    for lim in limits:
        cat = lim["category"]
        emoji = "💰"
        for key, e in emoji_map.items():
            if key in cat.lower():
                emoji = e
                break

        pct = lim["percent"] * 100
        bar = lim["bar"]
        spent_fmt = f"{lim['spent']:,.0f}".replace(",", " ")
        limit_fmt = f"{lim['limit']:,.0f}".replace(",", " ")
        warning = " ⚠️" if pct > 100 else ""
        lines.append(
            f"{emoji} {cat}: {bar} {pct:.0f}% — {spent_fmt} / {limit_fmt}{warning}"
        )

    await update.message.reply_html("\n".join(lines))


async def limit_alerts_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Настройка порогов уведомлений.

    /limit_alerts — показать текущие настройки
    /limit_alerts on — включить все
    /limit_alerts off — выключить все
    """
    args = context.args

    # /limit_alerts on — включить все пороги
    if args and args[0].lower() in ("on", "вкл", "да", "yes"):
        context.user_data["alert_50"] = True
        context.user_data["alert_80"] = True
        context.user_data["alert_exceeded"] = True
        persist_setting("alert_50", True)
        persist_setting("alert_80", True)
        persist_setting("alert_exceeded", True)
        await update.message.reply_text(
            "🔔 Все уведомления о лимитах включены. Буду кошмарить по полной."
        )
        return

    # /limit_alerts off — выключить все пороги
    if args and args[0].lower() in ("off", "выкл", "нет", "no"):
        context.user_data["alert_50"] = False
        context.user_data["alert_80"] = False
        context.user_data["alert_exceeded"] = False
        persist_setting("alert_50", False)
        persist_setting("alert_80", False)
        persist_setting("alert_exceeded", False)
        await update.message.reply_text(
            "🔕 Все уведомления о лимитах выключены. Трать, не думая."
        )
        return

    # Показать текущие настройки с inline-кнопками
    alert_50 = context.user_data.get("alert_50", True)
    alert_80 = context.user_data.get("alert_80", True)
    alert_exceeded = context.user_data.get("alert_exceeded", True)
    profanity_enabled = context.user_data.get("profanity_enabled", True)
    stickers_enabled = context.user_data.get("stickers_enabled", True)

    text = (
        "🔔 <b>Настройки напоминаний по лимитам:</b>\n\n"
        f"✅ 50% лимита — {'✅ предупреждать' if alert_50 else '❌ молчать'}\n"
        f"✅ 80% лимита — {'✅ предупреждать' if alert_80 else '❌ молчать'}\n"
        f"✅ Превышение лимита — {'✅ предупреждать' if alert_exceeded else '❌ молчать'}\n"
        f"✅ Мат при превышении — {'✅' if profanity_enabled else '❌'}\n"
        f"✅ Стикер при превышении — {'✅' if stickers_enabled else '❌'}\n\n"
        "Выбери, насколько сильно мне тебя кошмарить."
    )

    keyboard = [
        [
            InlineKeyboardButton(
                f"{'✅' if alert_50 else '❌'} 50%",
                callback_data="alert_toggle_50",
            )
        ],
        [
            InlineKeyboardButton(
                f"{'⚠️' if alert_80 else '❌'} 80%",
                callback_data="alert_toggle_80",
            )
        ],
        [
            InlineKeyboardButton(
                f"{'🚫' if alert_exceeded else '❌'} Превышение",
                callback_data="alert_toggle_exceeded",
            )
        ],
        [
            InlineKeyboardButton(
                f"{'🤬' if profanity_enabled else '😇'} Мат при превышении",
                callback_data="alert_toggle_profanity",
            )
        ],
        [
            InlineKeyboardButton(
                f"{'😈' if stickers_enabled else '😐'} Стикер при превышении",
                callback_data="alert_toggle_sticker",
            )
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="menu_limits_full")],
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_html(
            text, reply_markup=InlineKeyboardMarkup(keyboard)
        )
