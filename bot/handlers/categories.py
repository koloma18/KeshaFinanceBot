from categories import (
    EXPENSE_CATEGORIES_DISPLAY,
    INCOME_CATEGORIES_DISPLAY,
    _get_custom_by_type,
    is_builtin_category,
)
from telegram import Update
from telegram.ext import ContextTypes

INCOME_CATEGORIES = [
    ("Зарплата", "💼"),
    ("Фриланс", "💻"),
    ("Подарок", "🎁"),
    ("Инвестиции", "📈"),
    ("Возврат долга", "🔄"),
    ("Другое", "❓"),
]

EXPENSE_CATEGORIES = [
    ("Кофе", "☕️"),
    ("Еда", "🍔"),
    ("Такси", "🚕"),
    ("Одежда", "👗"),
    ("Красота", "💅"),
    ("Подписки", "📺"),
    ("Дом", "🏠"),
    ("Подарки", "🎀"),
    ("Маркетплейсы", "📦"),
    ("Здоровье", "🏥"),
    ("Развлечения", "🎮"),
    ("Другое", "❓"),
]


async def categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    custom_by_type = _get_custom_by_type()

    inc_lines = [f"  {emoji} {name}" for name, emoji in INCOME_CATEGORIES]
    for name in custom_by_type.get("income", []):
        inc_lines.append(f"  ✨ {name}")

    exp_lines = [f"  {emoji} {name}" for name, emoji in EXPENSE_CATEGORIES]
    for name in custom_by_type.get("expense", []):
        exp_lines.append(f"  ✨ {name}")

    custom_suffix = ""
    if custom_by_type.get("expense") or custom_by_type.get("income"):
        custom_suffix = "\n\n✨ — кастомные категории"

    text = (
        "📂 <b>Категории доходов</b>\n"
        + "\n".join(inc_lines)
        + "\n\n📂 <b>Категории расходов</b>\n"
        + "\n".join(exp_lines)
        + custom_suffix
    )
    await update.message.reply_html(text)
