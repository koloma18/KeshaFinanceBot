from responses import HELP_TEXT, get_greeting
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from user_settings import DEFAULTS, load_user_settings, should_reset_alerts


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Загружаем сохранённые настройки из Sheets
    saved = load_user_settings()
    for key, value in saved.items():
        context.user_data[key] = value

    # Устанавливаем defaults для отсутствующих ключей
    for key, value in DEFAULTS.items():
        context.user_data.setdefault(key, value)

    # Сбрасываем alert-флаги если начался новый месяц
    should_reset_alerts(context.user_data)

    keyboard = [
        [
            InlineKeyboardButton("➕ Доход", callback_data="menu_income"),
            InlineKeyboardButton("➖ Расход", callback_data="menu_expense"),
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="menu_stats_full"),
            InlineKeyboardButton("📋 Последние", callback_data="menu_last"),
        ],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="menu_settings_full")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_greeting(), reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(HELP_TEXT)
