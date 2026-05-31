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


# ============================================================
# ИНТЕРАКТИВНЫЙ /help
# ============================================================

HELP_SECTIONS = {
    "income": (
        "💰 <b>Доход</b>\n\n"
        "Записать доход с категорией и комментарием:\n"
        "<code>/income 5000 зарплата аванс</code>\n\n"
        "Или через кнопки: ➕ Доход → сумма → категория → комментарий"
    ),
    "expense": (
        "💸 <b>Расход</b>\n\n"
        "Записать расход с категорией и комментарием:\n"
        "<code>/expense 350 кофе капучино</code>\n\n"
        "Или через кнопки: ➖ Расход → сумма → категория → комментарий"
    ),
    "stats": (
        "📊 <b>Статистика</b>\n\n"
        "<code>/today</code> — доходы/расходы за сегодня\n"
        "<code>/week</code> — за эту неделю\n"
        "<code>/month</code> — за этот месяц\n"
        "<code>/balance</code> — общий баланс (все валюты)\n"
        "<code>/top</code> — топ категорий расходов\n"
        "<code>/compare</code> — сравнить с прошлым месяцем"
    ),
    "budget": (
        "🎯 <b>Бюджет и лимиты</b>\n\n"
        "<code>/budget 30000</code> — установить общий бюджет\n"
        "<code>/budget</code> — посмотреть статус бюджета\n"
        "<code>/set_limit Кофе 2000</code> — лимит на категорию\n"
        "<code>/limits</code> — все лимиты с прогрессом\n"
        "<code>/limit_alerts</code> — настроить уведомления\n\n"
        "Алерты приходят при 50%, 80% и превышении лимита."
    ),
    "mono": (
        "🏦 <b>Monobank</b>\n\n"
        "<code>/mono_import 7</code> — импорт выписки за 7 дней\n"
        "<code>/mono_import 30</code> — за 30 дней (макс 31)\n"
        "<code>/mono_info</code> — счета и балансы\n"
        "<code>/mono_rates</code> — курсы валют\n"
        "<code>/mono_sync</code> — докачать пропущенные\n\n"
        "⚠️ Monobank API: 1 запрос в 60 секунд. Импорт небыстрый."
    ),
    "manage": (
        "📋 <b>Управление записями</b>\n\n"
        "<code>/last</code> — последние 5 операций\n"
        "<code>/delete_last</code> — удалить последнюю\n"
        "<code>/delete 15</code> — удалить по номеру\n"
        "<code>/recategorize Кофе</code> — сменить категорию\n"
        "<code>/categories</code> — список категорий\n"
        "<code>/add_category expense Книги</code> — своя категория\n"
        "<code>/export</code> — выгрузить в CSV или Google Sheets"
    ),
    "fun": (
        "🧠 <b>Цитаты, стикеры, напоминания</b>\n\n"
        "<code>/quote</code> — случайная цитата Кеши\n"
        "<code>/quote_time 09:00</code> — авто-цитата каждое утро\n"
        "<code>/reminder 21:00</code> — итог дня вечером\n"
        "<code>/stickers</code> — настроить стикеры и эмодзи\n\n"
        "Кеша может быть мягким 😇, бурчливым 😤, жёстким 🤬 или случайным 🎲.\n"
        "Стикеры и мат настраиваются в /settings."
    ),
    "settings": (
        "⚙️ <b>Настройки</b>\n\n"
        "<code>/settings</code> — все настройки\n"
        "<code>/set_currency UAH</code> — сменить валюту\n"
        "<code>/stickers</code> — стикеры и эмодзи\n\n"
        "Уровень токсичности: мягкий / бурчливый / жёсткий / случайный\n"
        "Мат: вкл / выкл\n"
        "Стикеры: всегда / только крупные / выкл"
    ),
}

HELP_EMOJI = {
    "income": "💰",
    "expense": "💸",
    "stats": "📊",
    "budget": "🎯",
    "mono": "🏦",
    "manage": "📋",
    "fun": "🧠",
    "settings": "⚙️",
}

HELP_LABELS = {
    "income": "Доход",
    "expense": "Расход",
    "stats": "Статистика",
    "budget": "Бюджет и лимиты",
    "mono": "Monobank",
    "manage": "Управление записями",
    "fun": "Цитаты и стикеры",
    "settings": "Настройки",
}


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    section = None
    if context.args and context.args[0] in HELP_SECTIONS:
        section = context.args[0]

    if section:
        text = HELP_SECTIONS[section]
        keyboard = [
            [InlineKeyboardButton("🔙 Ко всем разделам", callback_data="help_main")]
        ]
        await update.message.reply_html(
            text, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        text = (
            "🆘 <b>Что ты хочешь узнать?</b>\n\n"
            "Выбери раздел — покажу команды и примеры."
        )
        keyboard = []
        keys = list(HELP_SECTIONS.keys())
        for i in range(0, len(keys), 2):
            row = []
            for j in range(2):
                if i + j < len(keys):
                    k = keys[i + j]
                    row.append(
                        InlineKeyboardButton(
                            f"{HELP_EMOJI[k]} {HELP_LABELS[k]}",
                            callback_data=f"help_{k}",
                        )
                    )
            keyboard.append(row)
        keyboard.append(
            [InlineKeyboardButton("📖 Полный список команд", callback_data="help_full")]
        )
        await update.message.reply_html(
            text, reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "help_main":
        text = "🆘 <b>Что ты хочешь узнать?</b>\n\nВыбери раздел — покажу команды и примеры."
        keyboard = []
        keys = list(HELP_SECTIONS.keys())
        for i in range(0, len(keys), 2):
            row = []
            for j in range(2):
                if i + j < len(keys):
                    k = keys[i + j]
                    row.append(
                        InlineKeyboardButton(
                            f"{HELP_EMOJI[k]} {HELP_LABELS[k]}",
                            callback_data=f"help_{k}",
                        )
                    )
            keyboard.append(row)
        keyboard.append(
            [InlineKeyboardButton("📖 Полный список команд", callback_data="help_full")]
        )
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
        )

    elif data == "help_full":
        await query.edit_message_text(
            HELP_TEXT,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 К разделам", callback_data="help_main")]]
            ),
        )

    elif data.startswith("help_"):
        section = data.replace("help_", "")
        if section in HELP_SECTIONS:
            text = HELP_SECTIONS[section]
            keyboard = [
                [InlineKeyboardButton("🔙 Ко всем разделам", callback_data="help_main")]
            ]
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
            )
