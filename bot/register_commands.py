"""Регистрация команд бота в Telegram. Запускать при деплое или вручную."""

import asyncio

from config import BOT_TOKEN
from telegram import Bot, BotCommand

COMMANDS = [
    BotCommand("start", "🚀 Главное меню"),
    BotCommand("help", "🆘 Помощь и примеры"),
    BotCommand("income", "💰 Добавить доход"),
    BotCommand("expense", "💸 Добавить расход"),
    BotCommand("today", "📍 Статистика за сегодня"),
    BotCommand("week", "📅 Статистика за неделю"),
    BotCommand("month", "📆 Статистика за месяц"),
    BotCommand("balance", "🧾 Текущий баланс"),
    BotCommand("categories", "📂 Список категорий"),
    BotCommand("add_category", "➕ Добавить категорию"),
    BotCommand("budget", "🎯 Бюджет на месяц"),
    BotCommand("set_limit", "⚙️ Лимит по категории"),
    BotCommand("limits", "🚦 Лимиты и остатки"),
    BotCommand("limit_alerts", "🔔 Настройки уведомлений"),
    BotCommand("top", "🏆 Топ расходов"),
    BotCommand("compare", "📈 Сравнить с прошлым месяцем"),
    BotCommand("last", "📋 Последние операции"),
    BotCommand("delete_last", "↩️ Отменить последнюю"),
    BotCommand("delete", "🗑 Удалить по номеру"),
    BotCommand("recategorize", "🔄 Сменить категорию"),
    BotCommand("export", "📤 Экспорт данных"),
    BotCommand("settings", "⚙️ Настройки"),
    BotCommand("set_currency", "💱 Сменить валюту"),
    BotCommand("reminder", "⏰ Ежедневное напоминание"),
    BotCommand("quote", "🧠 Цитата дня"),
    BotCommand("quote_time", "🕙 Время цитаты"),
    BotCommand("stickers", "😈 Стикеры и эмодзи"),
    BotCommand("mono_import", "🏦 Импорт из Monobank"),
    BotCommand("mono_rates", "💱 Курсы валют Monobank"),
    BotCommand("mono_sync", "🔄 Синхронизация Monobank"),
    BotCommand("mono_day", "📅 Выписка за день Monobank"),
    BotCommand("mono_info", "💳 Счета Monobank"),
]


async def main():
    bot = Bot(token=BOT_TOKEN)
    await bot.set_my_commands(COMMANDS)
    print(f"✅ {len(COMMANDS)} команд зарегистрировано")


if __name__ == "__main__":
    asyncio.run(main())
