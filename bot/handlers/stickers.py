"""Настройка стикеров и эмодзи."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from user_settings import persist_setting

logger = logging.getLogger(__name__)

STICKER_STATES = {
    "always": "🔊 Всегда",
    "large_only": "🔉 Только крупные",
    "off": "🔇 Выключены",
}


def _build_sticker_keyboard(user_data: dict) -> InlineKeyboardMarkup:
    """Построить inline-клавиатуру на основе текущих настроек."""
    stickers_enabled = user_data.get("stickers_enabled", True)
    sticker_freq = user_data.get("sticker_frequency", "always")
    emoji_enabled = user_data.get("emoji_enabled", True)

    freq_label = STICKER_STATES.get(sticker_freq, "🔊 Всегда")
    stickers_status = "✅ Включены" if stickers_enabled else "❌ Отключены"
    emoji_status = "✅ Включены" if emoji_enabled else "❌ Отключены"

    keyboard = [
        [
            InlineKeyboardButton(
                f"🎭 Стикеры: {stickers_status}", callback_data="sticker_toggle"
            )
        ],
        [
            InlineKeyboardButton(
                f"📊 Частота: {freq_label}", callback_data="sticker_freq_cycle"
            )
        ],
        [
            InlineKeyboardButton("🔊 Всегда", callback_data="sticker_freq_always"),
            InlineKeyboardButton("🔉 Крупные", callback_data="sticker_freq_large"),
            InlineKeyboardButton("🔇 Выкл", callback_data="sticker_freq_off"),
        ],
        [
            InlineKeyboardButton(
                f"😊 Эмодзи: {emoji_status}", callback_data="emoji_toggle"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 Выбрать стикер-пак", callback_data="sticker_pack_info"
            )
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def stickers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать и изменить настройки стикеров.

    Использует inline-кнопки для переключения опций.
    """
    user_data = context.user_data
    keyboard = _build_sticker_keyboard(user_data)

    text = (
        "🎭 <b>Настройки стикеров и эмодзи</b>\n\n"
        "Кеша может отправлять стикеры в ответ на твои действия.\n"
        "Настраивай как хочешь:\n\n"
        "• <b>Стикеры</b> — включить/выключить полностью\n"
        "• <b>Частота</b> — когда отправлять\n"
        "• <b>Эмодзи</b> — эмоциональные реакции\n\n"
        "Выбери опцию ниже:"
    )
    await update.message.reply_html(text, reply_markup=keyboard)


async def stickers_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback для inline-кнопок стикеров.

    patterns: "sticker_toggle", "sticker_freq_always", "sticker_freq_large",
              "sticker_freq_off", "sticker_freq_cycle", "emoji_toggle"
    """
    query = update.callback_query
    await query.answer()

    user_data = context.user_data
    data = query.data

    if data == "sticker_toggle":
        current = user_data.get("stickers_enabled", True)
        user_data["stickers_enabled"] = not current
        persist_setting("stickers_enabled", not current)

    elif data == "sticker_freq_always":
        user_data["sticker_frequency"] = "always"
        user_data["stickers_enabled"] = True
        persist_setting("sticker_frequency", "always")
        persist_setting("stickers_enabled", True)

    elif data == "sticker_freq_large":
        user_data["sticker_frequency"] = "large_only"
        user_data["stickers_enabled"] = True
        persist_setting("sticker_frequency", "large_only")
        persist_setting("stickers_enabled", True)

    elif data == "sticker_freq_off":
        user_data["sticker_frequency"] = "off"
        user_data["stickers_enabled"] = False
        persist_setting("sticker_frequency", "off")
        persist_setting("stickers_enabled", False)

    elif data == "sticker_freq_cycle":
        cycle = ["always", "large_only", "off"]
        current = user_data.get("sticker_frequency", "always")
        next_idx = (cycle.index(current) + 1) % len(cycle) if current in cycle else 0
        new_freq = cycle[next_idx]
        user_data["sticker_frequency"] = new_freq
        persist_setting("sticker_frequency", new_freq)
        if new_freq == "off":
            user_data["stickers_enabled"] = False
            persist_setting("stickers_enabled", False)
        else:
            user_data["stickers_enabled"] = True
            persist_setting("stickers_enabled", True)

    elif data == "emoji_toggle":
        current = user_data.get("emoji_enabled", True)
        user_data["emoji_enabled"] = not current
        persist_setting("emoji_enabled", not current)

    elif data == "sticker_pack_info":
        from stickers import STICKER_POOL

        has_stickers = bool(STICKER_POOL)
        await query.edit_message_text(
            "Чтобы добавить стикеры Кеши:\n\n"
            "1. Создай стикер-пак в @Stickers боте\n"
            "2. Добавь стикеры с эмоциями\n"
            "3. Пришли мне любой стикер из пака\n"
            "4. Я запомню его ID и буду использовать\n\n"
            "Пока стикеры не добавлены — я использую эмодзи.\n\n"
            f"Сейчас стикер-пак: {'✅ настроен' if has_stickers else '❌ не настроен (использую эмодзи)'}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Назад", callback_data="menu_back")]]
            ),
        )
        return

    # Обновляем клавиатуру
    keyboard = _build_sticker_keyboard(user_data)

    await query.edit_message_text(
        "🎭 <b>Настройки стикеров и эмодзи</b>\n\n"
        "Настройки обновлены. Выбери опцию ниже:",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
