"""Account aliases — maps everyday words to real account IDs and names.

Used by parser to detect account hints in transaction messages.
Keys are lowercase; values are (account_id, account_name) tuples.

Mappings come from the Accounts sheet (bot/sheets.py).
"""

# Each alias maps to (account_id, account_name)
# account_id matches the 'ID' column in Accounts sheet
# account_name is the display name (masked card number or label)
ACCOUNT_ALIASES: dict[str, tuple[str, str]] = {
    # ── Основная карта (Monobank card-main) ────────────────────────────
    "карта": ("card-main", "4441...5259"),
    "карты": ("card-main", "4441...5259"),
    "картой": ("card-main", "4441...5259"),
    "карточка": ("card-main", "4441...5259"),
    "карточкой": ("card-main", "4441...5259"),
    "основная карта": ("card-main", "4441...5259"),
    "основной карты": ("card-main", "4441...5259"),
    "основной картой": ("card-main", "4441...5259"),
    "mono": ("card-main", "4441...5259"),
    "моно": ("card-main", "4441...5259"),
    "монобанк": ("card-main", "4441...5259"),
    "монобанка": ("card-main", "4441...5259"),
    "monobank": ("card-main", "4441...5259"),
    # ── Офисная карта (business card) ──────────────────────────────────
    "офисная": ("card-office", "4441...4454"),
    "офисной": ("card-office", "4441...4454"),
    "офисная карта": ("card-office", "4441...4454"),
    "офисной карты": ("card-office", "4441...4454"),
    "офисной картой": ("card-office", "4441...4454"),
    # ── Приват24 ───────────────────────────────────────────────────────
    "приват": ("privat24", "5457...8762"),
    "приват24": ("privat24", "5457...8762"),
    "привата": ("privat24", "5457...8762"),
    "privat": ("privat24", "5457...8762"),
    # ── Sense Bank ─────────────────────────────────────────────────────
    "sense": ("sense", "5472...6562"),
    "сенс": ("sense", "5472...6562"),
    # ── Наличка UAH ────────────────────────────────────────────────────
    "cash": ("cash-uah", "Наличка"),
    "кеш": ("cash-uah", "Наличка"),
    "нал": ("cash-uah", "Наличка"),
    "наличка": ("cash-uah", "Наличка"),
    "наличку": ("cash-uah", "Наличка"),
    "наличные": ("cash-uah", "Наличка"),
    "наличными": ("cash-uah", "Наличка"),
    "наличкой": ("cash-uah", "Наличка"),
    # ── Наличка EUR ────────────────────────────────────────────────────
    "наличка eur": ("cash-eur", "наличка EUR"),
    "наличка евро": ("cash-eur", "наличка EUR"),
    "cash eur": ("cash-eur", "наличка EUR"),
    "наличные eur": ("cash-eur", "наличка EUR"),
    "наличные евро": ("cash-eur", "наличка EUR"),
    # ── Legacy (keep old canonical names for backward compat) ──────────
    "google pay": ("card-main", "4441...5259"),
    "apple pay": ("card-main", "4441...5259"),
    "gpay": ("card-main", "4441...5259"),
}

# Sorted by length descending for greedy multi-word matching
_MULTI_WORD_ALIASES = sorted(
    [(k, v) for k, v in ACCOUNT_ALIASES.items() if " " in k],
    key=lambda x: -len(x[0]),
)


def resolve_account(raw: str) -> tuple[str, str] | None:
    """Resolve a single raw account keyword to (account_id, account_name).

    Returns (account_id, account_name) or None.
    """
    return ACCOUNT_ALIASES.get(raw.lower())


def resolve_account_multi(
    tokens: list[str], max_words: int = 3
) -> tuple[str, str] | None:
    """Try to match consecutive tokens against multi-word account aliases.

    Returns (account_id, account_name) or None.
    """
    if not tokens or len(tokens) < 2:
        return None

    for alias_key, value in _MULTI_WORD_ALIASES:
        alias_tokens = alias_key.split()
        if len(alias_tokens) > len(tokens):
            continue
        for start in range(len(tokens) - len(alias_tokens) + 1):
            match = True
            for j, at in enumerate(alias_tokens):
                if tokens[start + j] != at:
                    match = False
                    break
            if match:
                # Remove matched tokens in reverse order
                for j in range(len(alias_tokens) - 1, -1, -1):
                    del tokens[start + j]
                return value

    return None
