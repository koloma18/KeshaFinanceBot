"""Хендлеры пользовательских правил автокатегоризации.

/rules — показать все правила
/add_rule <паттерн> <категория> — добавить правило
/delete_rule <паттерн> — удалить правило

Приоритет: user rules → CATEGORY_ALIASES → built-in → fallback.
"""

from categories import get_all_expense_categories, get_all_income_categories
from sheets import add_rule, delete_rule, get_rules
from telegram import Update
from telegram.ext import ContextTypes


async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rules = get_rules()

    if not rules:
        await update.message.reply_text(
            "📋 <b>Правил нет.</b>\n\n"
            "Добавь правило через <code>/add_rule &lt;паттерн&gt; &lt;категория&gt;</code>\n"
            "Пример: <code>/add_rule Bolt Такси</code>\n\n"
            "Приоритет обработки:\n"
            "1. Пользовательские правила\n"
            "2. Встроенные синонимы (аптека→Здоровье, netflix→Подписки...)\n"
            "3. Стандартные категории",
            parse_mode="HTML",
        )
        return

    lines = ["<b>📋 Правила автокатегоризации:</b>\n"]
    for r in sorted(rules, key=lambda r: r.get("priority", 10)):
        p = r["pattern"]
        c = r["category"]
        t = r.get("type", "expense")
        prio = r.get("priority", 10)
        type_icon = "💰" if t == "income" else "💸"
        lines.append(f"  {type_icon} <code>{p}</code> → <b>{c}</b> (приоритет {prio})")
    lines.append(f"\nВсего правил: {len(rules)}")

    await update.message.reply_html("\n".join(lines))


async def add_rule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    parts = text.split(maxsplit=2)

    if len(parts) < 3:
        await update.message.reply_html(
            "📝 <b>Использование:</b> <code>/add_rule &lt;паттерн&gt; &lt;категория&gt;</code>\n\n"
            "Примеры:\n"
            "  <code>/add_rule Bolt Такси</code>\n"
            "  <code>/add_rule зарплата Зарплата</code>\n\n"
            "Доступные категории:\n"
            + "\n".join(f"  💸 {c}" for c in get_all_expense_categories())
            + "\n"
            + "\n".join(f"  💰 {c}" for c in get_all_income_categories()),
        )
        return

    pattern = parts[1].strip()
    category = parts[2].strip()

    # Validate category exists
    all_cats = set(
        c.lower() for c in get_all_expense_categories() + get_all_income_categories()
    )
    if category.lower() not in all_cats:
        await update.message.reply_html(
            f"❌ Категория <b>{category}</b> не найдена.\n"
            f"Используй существующие категории. Проверь через /categories."
        )
        return

    success = add_rule(pattern, category)
    if success:
        await update.message.reply_html(
            f"✅ Правило добавлено: <code>{pattern}</code> → <b>{category}</b>"
        )
    else:
        await update.message.reply_text(
            "❌ Не получилось добавить правило. Google Sheets не отвечает."
        )


async def delete_rule_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    text = update.message.text.strip()
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await update.message.reply_html(
            "🗑 <b>Использование:</b> <code>/delete_rule &lt;паттерн&gt;</code>\n\n"
            "Пример: <code>/delete_rule Bolt</code>\n\n"
            "Посмотреть все правила: /rules"
        )
        return

    pattern = parts[1].strip()
    count = delete_rule(pattern)

    if count > 0:
        await update.message.reply_html(
            f"🗑 Удалено правил: <b>{count}</b> (паттерн: <code>{pattern}</code>)"
        )
    else:
        await update.message.reply_text(
            f'❓ Нет правил с паттерном "{pattern}". Проверь через /rules.'
        )
