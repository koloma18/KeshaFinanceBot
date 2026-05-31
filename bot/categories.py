# Normalized category names — matches Google Sheets dropdown exactly

EXPENSE_CATEGORIES_DISPLAY = [
    "Кофе",
    "Еда",
    "Такси",
    "Одежда",
    "Красота",
    "Подписки",
    "Дом",
    "Подарки",
    "Маркетплейсы",
    "Здоровье",
    "Развлечения",
    "Другое",
]

INCOME_CATEGORIES_DISPLAY = [
    "Зарплата",
    "Фриланс",
    "Подарок",
    "Инвестиции",
    "Возврат долга",
    "Другое",
]

ALL_CATEGORIES = EXPENSE_CATEGORIES_DISPLAY + INCOME_CATEGORIES_DISPLAY

# Cache for custom categories to avoid API call on every keyboard render.
# Invalidate with invalidate_category_cache().
_custom_cache: dict[str, list[str]] | None = None


def invalidate_category_cache() -> None:
    """Clear cached custom categories so next call re-fetches from sheets."""
    global _custom_cache
    _custom_cache = None


def _get_custom_by_type() -> dict[str, list[str]]:
    """Lazy-load custom categories from sheets. Cached until invalidated."""
    global _custom_cache
    if _custom_cache is not None:
        return _custom_cache
    from sheets import get_custom_categories

    raw = get_custom_categories()
    result: dict[str, list[str]] = {"expense": [], "income": []}
    for t, name in raw:
        if t in result:
            result[t].append(name)
    _custom_cache = result
    return result


def get_all_expense_categories() -> list[str]:
    """Built-in + custom expense categories."""
    custom = _get_custom_by_type()["expense"]
    return EXPENSE_CATEGORIES_DISPLAY + custom


def get_all_income_categories() -> list[str]:
    """Built-in + custom income categories."""
    custom = _get_custom_by_type()["income"]
    return INCOME_CATEGORIES_DISPLAY + custom


def is_builtin_category(name: str) -> bool:
    """Check if a category name is a built-in (not custom)."""
    return name in EXPENSE_CATEGORIES_DISPLAY or name in INCOME_CATEGORIES_DISPLAY


def normalize_category(raw: str) -> str:
    """Match user input to proper category name (case-insensitive).

    Checks built-in first, then custom.
    """
    raw_lower = raw.strip().lower()
    for cat in ALL_CATEGORIES:
        if cat.lower() == raw_lower:
            return cat
    # Check custom categories too
    custom = _get_custom_by_type()
    for cat in custom["expense"] + custom["income"]:
        if cat.lower() == raw_lower:
            return cat
    return raw.strip()  # fallback
