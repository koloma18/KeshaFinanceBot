import html

from categories import (
    EXPENSE_CATEGORIES_DISPLAY,
    INCOME_CATEGORIES_DISPLAY,
    _get_custom_by_type,
    get_all_expense_categories,
    get_all_income_categories,
    invalidate_category_cache,
)
from sheets import add_custom_category
from telegram import Update
from telegram.ext import ContextTypes


async def add_category_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавить новую категорию.

    /add_category expense Кофе — добавить в расходы
    /add_category income Премия — добавить в доходы
    /add_category list — показать кастомные категории
    """
    text = update.message.text.strip()
    parts = text.split(maxsplit=2)

    if len(parts) < 2:
        await update.message.reply_html(
            "📂 <b>Добавление категории</b>\n\n"
            "Использование:\n"
            "<code>/add_category expense Название</code> — добавить в расходы\n"
            "<code>/add_category income Название</code> — добавить в доходы\n"
            "<code>/add_category list</code> — показать кастомные категории"
        )
        return

    sub = parts[1].strip().lower()

    # ── list ──
    if sub == "list":
        custom_by_type = _get_custom_by_type()
        custom_exp = custom_by_type.get("expense", [])
        custom_inc = custom_by_type.get("income", [])

        if not custom_exp and not custom_inc:
            await update.message.reply_html(
                "✨ Кастомных категорий пока нет.\n"
                "Добавь через <code>/add_category expense Название</code>"
            )
            return

        lines: list[str] = ["✨ <b>Кастомные категории</b>\n"]
        if custom_exp:
            lines.append("<b>Расходы:</b>")
            for name in custom_exp:
                lines.append(f"  • {html.escape(name)}")
        if custom_inc:
            if custom_exp:
                lines.append("")
            lines.append("<b>Доходы:</b>")
            for name in custom_inc:
                lines.append(f"  • {html.escape(name)}")

        await update.message.reply_html("\n".join(lines))
        return

    # ── expense / income ──
    if sub not in ("expense", "income"):
        await update.message.reply_text(
            "Укажи тип: expense или income.\nНапример: /add_category expense Книги"
        )
        return

    if len(parts) < 3:
        await update.message.reply_text(
            f"Укажи название категории.\nПример: /add_category {sub} Книги"
        )
        return

    raw_name = parts[2].strip()

    # Require at least 2 characters
    if len(raw_name) < 2:
        await update.message.reply_text(
            "Название должно быть хотя бы из двух символов."
        )
        return

    # Capitalise first letter
    name = raw_name[0].upper() + raw_name[1:]

    # Check against built-in
    builtin = (
        EXPENSE_CATEGORIES_DISPLAY if sub == "expense" else INCOME_CATEGORIES_DISPLAY
    )
    for cat in builtin:
        if cat.lower() == name.lower():
            await update.message.reply_text(
                f"«{cat}» — уже есть во встроенных категориях.\n"
                f"Придумай что-то новое, зачем плодить дубликаты."
            )
            return

    # Check against existing custom
    all_for_type = (
        get_all_expense_categories()
        if sub == "expense"
        else get_all_income_categories()
    )
    for cat in all_for_type:
        if cat.lower() == name.lower():
            await update.message.reply_text(
                f"«{cat}» уже есть в категориях. Дубликаты — это для бухгалтеров, а не для Кеши."
            )
            return

    # Add to sheets
    success = add_custom_category(sub, name)
    if not success:
        await update.message.reply_text(
            "Не могу сохранить категорию. Google Sheets не отвечает.\n"
            "Проверь доступы и наличие листа «Categories»."
        )
        return

    # Invalidate cache so next /expense /income picks it up
    invalidate_category_cache()

    type_label = "расходов" if sub == "expense" else "доходов"

    responses = {
        "expense": [
            f"📂 Добавил категорию: {name}.\n\n"
            "Надеюсь, это реальная статья расходов, а не очередное «саморазвитие» за 999 грн, которое ты не откроешь.",
            f"📂 Категория «{name}» в расходах. Теперь у тебя есть официальное место для слива денег.",
            f"📂 Добавил «{name}» в расходы. Ещё одна строчка для отчёта «куда делась зарплата».",
        ],
        "income": [
            f"📂 Добавил категорию: {name}.\n\n"
            "Новый источник дохода? Надеюсь, не криптовалюта и не MLM.",
            f"📂 Категория «{name}» в доходах. Звучит многообещающе. Посмотрим, как часто она будет появляться.",
            f"📂 Добавил «{name}» в доходы. Если это пассивный доход — я официально завидую.",
        ],
    }

    import random

    await update.message.reply_text(random.choice(responses[sub]))
