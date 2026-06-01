import html
import logging
from datetime import datetime

from config import BOT_TOKEN
from handlers.add_category import add_category_command
from handlers.budget import (
    budget_command,
    limit_alerts_command,
    limits_command,
    set_limit_command,
)
from handlers.categories import categories
from handlers.compare import compare_command, top_command
from handlers.delete_command import delete_command
from handlers.expense import expense_callback, expense_command, expense_text
from handlers.export_data import export_command
from handlers.income import income_callback, income_command, income_text
from handlers.last import delete_last, last
from handlers.mono_day import mono_day
from handlers.mono_import import mono_import
from handlers.mono_info import mono_info
from handlers.mono_rates import mono_rates
from handlers.mono_sync import mono_sync
from handlers.quotes import quote_command, quote_time_command
from handlers.recategorize import recategorize_command
from handlers.reminder import reminder_command
from handlers.set_currency import set_currency_command
from handlers.settings import settings, settings_callback
from handlers.start import help_callback, help_command, start
from handlers.statistics import balance, month, today, week
from handlers.stickers import stickers_callback, stickers_command
from register_commands import COMMANDS as BOT_COMMANDS
from sheets import COL, get_all_rows
from sheets import get_balance as sheets_balance
from telegram import (
    BotCommandScopeDefault,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from user_settings import persist_setting

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Не логировать токены в httpx (пишет полный URL с BOT_TOKEN)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

TOXICITY_LABELS = {
    "soft": "🧸 Мягкий",
    "grumpy": "🧂 Бурчливый",
    "hard": "😈 Жёсткий",
    "random": "🎲 Случайный",
}


async def menu_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── Главное меню ──
    if data == "menu_income":
        context.user_data["income_step"] = "amount"
        await query.edit_message_text("Сколько денег пришло? Давай, порадуй меня.")

    elif data == "menu_expense":
        context.user_data["expense_step"] = "amount"
        await query.edit_message_text("Сколько опять потратила?")

    elif data == "menu_last":
        rows = get_all_rows()
        if not rows:
            text = "История пуста. Даже тратить ничего не умеешь?"
        else:
            lines = ["<b>📋 Последние операции</b>\n"]
            for r in rows[:5]:
                date = r[COL["DATE"]] if len(r) > COL["DATE"] else "??"
                t = str(r[COL["TYPE"]]).strip().lower() if len(r) > COL["TYPE"] else ""
                try:
                    amount = float(r[COL["AMOUNT_UAH"]]) if r[COL["AMOUNT_UAH"]] else 0
                except (ValueError, IndexError):
                    amount = 0
                cat = r[COL["CATEGORY"]] if len(r) > COL["CATEGORY"] else ""
                cmt = r[COL["COMMENT"]] if len(r) > COL["COMMENT"] else ""
                sign = "+" if t == "income" else "−"
                emoji = "💰" if t == "income" else "💸"
                cat_str = f" · {html.escape(cat)}" if cat else ""
                cmt_str = f" — {html.escape(cmt)}" if cmt else ""
                lines.append(
                    f"{emoji} {date} <code>{sign}{amount:.0f}</code>{cat_str}{cmt_str}"
                )
            text = "\n".join(lines)
        await query.edit_message_text(text, parse_mode="HTML")

    elif data == "menu_balance":
        b = sheets_balance()
        uah = b.get("UAH", 0)
        usd = b.get("USD", 0)
        eur = b.get("EUR", 0)
        parts = []
        if uah:
            parts.append(f"🇺🇦 {uah:+.2f} UAH")
        if usd:
            parts.append(f"🇺🇸 {usd:+.2f} USD")
        if eur:
            parts.append(f"🇪🇺 {eur:+.2f} EUR")
        text = f"📊 <b>Общий баланс</b>\n\n" + (
            "\n".join(parts) if parts else "0.00 UAH"
        )
        await query.edit_message_text(text, parse_mode="HTML")

    elif data == "menu_delete_last":
        from sheets import delete_last_row

        deleted = delete_last_row()
        text = "🗑 Удалил последнюю запись." if deleted else "Нечего удалять."
        await query.edit_message_text(text)

    elif data == "menu_today":
        rows = get_all_rows()
        from handlers.statistics import _filter_today, _format_cat_top, _summarize

        filtered = _filter_today(rows)
        income, expense, cat_expense = _summarize(filtered)
        cat_block = _format_cat_top(cat_expense)
        text = (
            f"📅 <b>Сегодня</b>\n\n"
            f"💰 Доход: +{income:.0f} UAH\n"
            f"💸 Расход: -{expense:.0f} UAH\n"
            f"📊 Итого: {income - expense:+.0f} UAH"
        )
        if cat_block:
            text += f"\n\n<b>Топ трат:</b>{cat_block}"
        await query.edit_message_text(text, parse_mode="HTML")

    elif data == "menu_settings":
        from config import CURRENCIES, PRIMARY_CURRENCY

        user_currency = context.user_data.get("currency", PRIMARY_CURRENCY)
        currency_list = ", ".join(CURRENCIES)
        text = (
            f"⚙️ <b>Настройки</b>\n\n"
            f"💱 Основная валюта: <b>{user_currency}</b>\n"
            f"📋 Доступные: {currency_list}"
        )
        keyboard = [
            [
                InlineKeyboardButton("🇺🇦 UAH", callback_data="set_currency_UAH"),
                InlineKeyboardButton("🇺🇸 USD", callback_data="set_currency_USD"),
                InlineKeyboardButton("🇪🇺 EUR", callback_data="set_currency_EUR"),
            ],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")],
        ]
        await query.edit_message_text(
            text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "menu_budget":
        await query.edit_message_text(
            "💰 <b>Бюджет</b>\n\n"
            "/budget — общий бюджет на месяц\n"
            "/limits — лимиты по категориям\n"
            "/set_limit — установить лимит\n"
            "/limit_alerts — уведомления\n\n"
            "Используй команды выше или вернись в меню.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]],
            ),
        )

    # ── Статистика (под-меню) ──
    elif data == "menu_stats_full":
        keyboard = [
            [InlineKeyboardButton("📍 Сегодня", callback_data="menu_today")],
            [InlineKeyboardButton("📅 Неделя", callback_data="menu_week")],
            [InlineKeyboardButton("📆 Месяц", callback_data="menu_month")],
            [InlineKeyboardButton("🏆 Топ расходов", callback_data="menu_top")],
            [
                InlineKeyboardButton(
                    "📈 Сравнить с прошлым месяцем", callback_data="menu_compare"
                )
            ],
            [InlineKeyboardButton("💰 Баланс", callback_data="menu_balance")],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")],
        ]
        await query.edit_message_text(
            "📊 Статистика:", reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── Лимиты (под-меню) ──
    elif data == "menu_limits_full":
        keyboard = [
            [InlineKeyboardButton("🚦 Показать лимиты", callback_data="menu_limits")],
            [
                InlineKeyboardButton(
                    "⚙️ Установить лимит", callback_data="menu_set_limit"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔔 Напоминания по лимитам", callback_data="menu_limit_alerts"
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 Расходы по категориям", callback_data="menu_cat_spending"
                )
            ],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")],
        ]
        await query.edit_message_text(
            "🚦 Лимиты:", reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── Настройки (под-меню) ──
    elif data == "menu_settings_full":
        keyboard = [
            [InlineKeyboardButton("💰 Валюта", callback_data="menu_settings")],
            [InlineKeyboardButton("📂 Категории", callback_data="menu_categories")],
            [InlineKeyboardButton("🎯 Бюджет", callback_data="menu_budget")],
            [InlineKeyboardButton("🚦 Лимиты", callback_data="menu_limits_full")],
            [InlineKeyboardButton("🔔 Напоминания", callback_data="menu_reminder")],
            [InlineKeyboardButton("🧠 Цитата дня", callback_data="menu_quote")],
            [InlineKeyboardButton("🧂 Стиль ответов", callback_data="menu_toxicity")],
            [InlineKeyboardButton("🤬 Мат", callback_data="menu_profanity")],
            [
                InlineKeyboardButton(
                    "😈 Стикеры и эмодзи", callback_data="menu_stickers"
                )
            ],
            [InlineKeyboardButton("📤 Экспорт", callback_data="menu_export")],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")],
        ]
        await query.edit_message_text(
            "⚙️ Настройки:", reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── Делегирование в хендлеры ──
    elif data == "menu_week":
        await query.delete_message()
        await week(update, context)

    elif data == "menu_month":
        await query.delete_message()
        await month(update, context)

    elif data == "menu_top":
        await query.delete_message()
        await top_command(update, context)

    elif data == "menu_compare":
        await query.delete_message()
        await compare_command(update, context)

    elif data == "menu_limits":
        await query.delete_message()
        await limits_command(update, context)

    elif data == "menu_set_limit":
        await query.edit_message_text(
            "⚙️ <b>Установить лимит</b>\n\n"
            "Формат: <code>/set_limit Категория 3000</code>\n"
            "Удалить: <code>/set_limit Категория delete</code>\n\n"
            "Примеры:\n"
            "<code>/set_limit Кофе 3000</code>\n"
            "<code>/set_limit Такси 5000</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Назад", callback_data="menu_limits_full")]],
            ),
        )

    elif data == "menu_limit_alerts":
        await query.delete_message()
        await limit_alerts_command(update, context)

    elif data == "menu_cat_spending":
        await query.delete_message()
        await top_command(update, context)

    elif data == "menu_quote":
        await query.delete_message()
        await quote_command(update, context)

    elif data == "menu_reminder":
        await query.delete_message()
        await reminder_command(update, context)

    elif data == "menu_stickers":
        await query.delete_message()
        await stickers_command(update, context)

    elif data == "menu_export":
        await query.delete_message()
        await export_command(update, context)

    elif data == "menu_categories":
        await query.delete_message()
        await categories(update, context)

    # ── Стиль ответов (токсичность) ──
    elif data == "menu_toxicity":
        await _show_toxicity_menu(update, context)

    elif data.startswith("toxicity_"):
        level = data.replace("toxicity_", "")
        context.user_data["toxicity"] = level
        persist_setting("toxicity", level)
        await query.answer(f"Стиль: {TOXICITY_LABELS.get(level, level)}")
        await _show_toxicity_menu(update, context)

    # ── Мат ──
    elif data == "menu_profanity":
        await _show_profanity_menu(update, context)

    elif data == "profanity_on":
        context.user_data["profanity_enabled"] = True
        persist_setting("profanity_enabled", True)
        await query.answer("Мат включен")
        await _show_profanity_menu(update, context)

    elif data == "profanity_off":
        context.user_data["profanity_enabled"] = False
        persist_setting("profanity_enabled", False)
        await query.answer("Мат выключен")
        await _show_profanity_menu(update, context)

    # ── alert_toggle_*: индивидуальные пороги алертов ──
    elif data.startswith("alert_toggle_"):
        key = data.replace("alert_toggle_", "")
        if key == "50":
            new_val = not context.user_data.get("alert_50", True)
            context.user_data["alert_50"] = new_val
            persist_setting("alert_50", new_val)
        elif key == "80":
            new_val = not context.user_data.get("alert_80", True)
            context.user_data["alert_80"] = new_val
            persist_setting("alert_80", new_val)
        elif key == "exceeded":
            new_val = not context.user_data.get("alert_exceeded", True)
            context.user_data["alert_exceeded"] = new_val
            persist_setting("alert_exceeded", new_val)
        elif key == "profanity":
            new_val = not context.user_data.get("profanity_enabled", True)
            context.user_data["profanity_enabled"] = new_val
            persist_setting("profanity_enabled", new_val)
        elif key == "sticker":
            new_val = not context.user_data.get("stickers_enabled", True)
            context.user_data["stickers_enabled"] = new_val
            persist_setting("stickers_enabled", new_val)
        await limit_alerts_command(update, context)

    # ── Назад в главное меню ──
    elif data == "menu_back":
        keyboard = [
            [
                InlineKeyboardButton("➕ Доход", callback_data="menu_income"),
                InlineKeyboardButton("➖ Расход", callback_data="menu_expense"),
            ],
            [
                InlineKeyboardButton("📊 Статистика", callback_data="menu_stats_full"),
                InlineKeyboardButton("🚦 Лимиты", callback_data="menu_limits_full"),
            ],
            [
                InlineKeyboardButton("🧠 Цитата дня", callback_data="menu_quote"),
                InlineKeyboardButton(
                    "📋 Последние операции", callback_data="menu_last"
                ),
            ],
            [
                InlineKeyboardButton("⚙️ Настройки", callback_data="menu_settings_full"),
            ],
        ]
        await query.edit_message_text(
            "Выбери действие:", reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def _show_toxicity_menu(update: Update, context) -> None:
    """Показать/обновить меню выбора стиля ответов."""
    query = update.callback_query
    toxicity = context.user_data.get("toxicity", "grumpy")
    current = TOXICITY_LABELS.get(toxicity, "🧂 Бурчливый")

    keyboard = [
        [
            InlineKeyboardButton("🧸 Мягкий", callback_data="toxicity_soft"),
            InlineKeyboardButton("🧂 Бурчливый", callback_data="toxicity_grumpy"),
        ],
        [
            InlineKeyboardButton("😈 Жёсткий", callback_data="toxicity_hard"),
            InlineKeyboardButton("🎲 Случайный", callback_data="toxicity_random"),
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="menu_settings_full")],
    ]
    await query.edit_message_text(
        f"🧂 Стиль ответов: <b>{current}</b>\n\nВыбери уровень токсичности:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _show_profanity_menu(update: Update, context) -> None:
    """Показать/обновить меню включения/выключения мата."""
    query = update.callback_query
    profanity = context.user_data.get("profanity_enabled", True)
    status = "✅ Включен" if profanity else "❌ Выключен"

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Включить" if not profanity else "✅ Вкл",
                callback_data="profanity_on",
            ),
            InlineKeyboardButton(
                "❌ Выключить" if profanity else "❌ Выкл",
                callback_data="profanity_off",
            ),
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="menu_settings_full")],
    ]
    await query.edit_message_text(
        f"🤬 Мат: <b>{status}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_text(update: Update, context):
    if context.user_data.get("income_step"):
        await income_text(update, context)
    elif context.user_data.get("expense_step"):
        await expense_text(update, context)
    else:
        await update.message.reply_text("Не понял. Напиши /help чтобы увидеть команды.")


async def register_bot_commands(app):
    """Зарегистрировать команды бота при старте."""
    try:
        await app.bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeDefault())
        logging.info(f"✅ {len(BOT_COMMANDS)} bot commands registered")
    except Exception as e:
        logging.warning(f"Failed to register commands: {e}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("income", income_command))
    app.add_handler(CommandHandler("expense", expense_command))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("month", month))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("categories", categories))
    app.add_handler(CommandHandler("add_category", add_category_command))
    app.add_handler(CommandHandler("last", last))
    app.add_handler(CommandHandler("delete_last", delete_last))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CommandHandler("set_currency", set_currency_command))

    # Monobank commands
    app.add_handler(CommandHandler("mono_import", mono_import))
    app.add_handler(CommandHandler("mono_rates", mono_rates))
    app.add_handler(CommandHandler("mono_sync", mono_sync))
    app.add_handler(CommandHandler("mono_day", mono_day))
    app.add_handler(CommandHandler("mono_info", mono_info))

    # ── Phase 2 — Budget ──
    app.add_handler(CommandHandler("budget", budget_command))
    app.add_handler(CommandHandler("set_limit", set_limit_command))
    app.add_handler(CommandHandler("limits", limits_command))
    app.add_handler(CommandHandler("limit_alerts", limit_alerts_command))

    # ── Phase 2 — Quotes & Stickers & Reminder ──
    app.add_handler(CommandHandler("quote", quote_command))
    app.add_handler(CommandHandler("quote_time", quote_time_command))
    app.add_handler(CommandHandler("stickers", stickers_command))
    app.add_handler(CommandHandler("reminder", reminder_command))

    # ── Recategorize ──
    app.add_handler(CommandHandler("recategorize", recategorize_command))

    # ── Phase 2 — Export & Compare ──
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("compare", compare_command))

    app.add_handler(CallbackQueryHandler(income_callback, pattern="^inc_cat_"))
    app.add_handler(CallbackQueryHandler(expense_callback, pattern="^exp_cat_"))
    app.add_handler(
        CallbackQueryHandler(settings_callback, pattern="^(set_|toxicity_|profanity_)")
    )
    app.add_handler(CallbackQueryHandler(stickers_callback, pattern="^sticker_"))
    app.add_handler(CallbackQueryHandler(help_callback, pattern="^help_"))
    app.add_handler(
        CallbackQueryHandler(menu_callback, pattern="^(menu_|alert_toggle_)")
    )

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Авто-регистрация команд при старте
    app.post_init = register_bot_commands

    logging.info("🚀 Kesha запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
