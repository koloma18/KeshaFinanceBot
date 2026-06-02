"""Natural language parser for transaction messages.

Pure functions — no Telegram dependency. Takes a string, returns a
structured ParsedTransaction or None if the message isn't a transaction.

Supported patterns:
    кофе 85                  → expense, category from known expense cats
    такси 230 вчера          → expense with date override
    зарплата 40000           → income, category from known income cats
    +5000 фриланс            → explicit income
    -1200 продукты           → explicit expense
    обед 340 карта           → expense with account hint (resolved to real account)
    кофе 85 mono             → expense with account hint
    перевод 5000 с mono на cash     → transfer between accounts
    перевод 1000 с карты в наличку  → transfer between accounts
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Sequence

from account_aliases import ACCOUNT_ALIASES, resolve_account, resolve_account_multi
from categories_aliases import CATEGORY_ALIASES, resolve_alias

# ── Date keywords ──────────────────────────────────────────────────────────

_DATE_KEYWORDS: dict[str, str] = {
    "сегодня": "today",
    "вчера": "yesterday",
    "позавчера": "day_before_yesterday",
}

_DATE_OVERRIDE_MAP: dict[str, str] = {
    "today": "today",
    "yesterday": "yesterday",
    "day_before_yesterday": "yesterday",  # mapped to relative for simplicity
}

# ── Transfer detection pattern ─────────────────────────────────────────────

_TRANSFER_PATTERN = re.compile(
    r"перевод\s+(\d+(?:[.,]\d+)?)\s+с\s+(\S+(?:\s+\S+)?)\s+(?:на|в)\s+(\S+(?:\s+\S+)?)",
    re.IGNORECASE,
)


# ── Result type ────────────────────────────────────────────────────────────


@dataclass
class ParsedTransaction:
    type: str  # "income" | "expense" | "transfer"
    amount: float
    category: str | None = None
    comment: str = ""
    date: str | None = None  # "today" | "yesterday" | None (use now)
    raw: str = ""  # original input

    # Account fields — resolved from aliases to real Accounts sheet entries
    account_id: str | None = None  # column J — matches Accounts!A (ID)
    account_name: str | None = None  # column K — display name (masked card)

    # Backward-compat: legacy code may access .account for display name
    account: str | None = None  # deprecated alias, kept for old callers

    # Transfer-specific fields
    transfer_from: str | None = None
    transfer_to: str | None = None
    # Structured transfer
    transfer_from_id: str | None = None
    transfer_to_id: str | None = None
    transfer_id: str = ""

    def is_transfer(self) -> bool:
        return self.type == "transfer"

    def to_row(self) -> tuple[list, str | None]:
        """Convert to sheets row and optional date override.

        Returns ([month, date_str, type, amount_uah, 0, 0, category, comment, source,
                  account_id, account_name, transfer_id], date_override).
        date_override is "today" or "yesterday" — caller decides how to map.
        """
        now = datetime.now()
        month = now.strftime("%B")
        date_str = now.strftime("%d.%m.%Y")

        sign = 1 if self.type == "income" else -1
        category = self.category or "Другое"

        return (
            [
                month,
                date_str,
                self.type if self.type != "transfer" else "expense",
                sign * abs(self.amount),
                0,
                0,
                category,
                self.comment,  # чистый комментарий, без [Account]
                "manual",
                self.account_id or "",  # J — AccountID
                self.account_name or self.account or "",  # K — AccountName
                self.transfer_id or "",  # L — TransferID
            ],
            self.date,
        )

    def to_transfer_rows(self) -> tuple[list, list, str]:
        """Generate TWO linked rows for a transfer: outflow + inflow.

        Returns (outflow_row, inflow_row, transfer_id).
        Both rows share the same TransferID so total balance is unchanged.
        """
        tid = self.transfer_id or uuid.uuid4().hex[:12]
        now = datetime.now()
        month = now.strftime("%B")
        date_str = now.strftime("%d.%m.%Y")

        comment_out = (
            f"Перевод: {self.transfer_from or '?'} → {self.transfer_to or '?'}"
        )
        comment_in = f"Перевод: {self.transfer_from or '?'} → {self.transfer_to or '?'}"

        outflow = [
            month,
            date_str,
            "expense",
            -abs(self.amount),
            0,
            0,
            "Перевод",
            comment_out,
            "manual",
            self.transfer_from_id or "",
            self.transfer_from or "",
            tid,
        ]

        inflow = [
            month,
            date_str,
            "income",
            abs(self.amount),
            0,
            0,
            "Перевод",
            comment_in,
            "manual",
            self.transfer_to_id or "",
            self.transfer_to or "",
            tid,
        ]

        return outflow, inflow, tid


# ── Public API ─────────────────────────────────────────────────────────────


def parse_message(
    text: str,
    expense_categories: Sequence[str] | None = None,
    income_categories: Sequence[str] | None = None,
    user_rules: Sequence[dict] | None = None,
) -> ParsedTransaction | None:
    """Parse a natural-language message into a ParsedTransaction.

    Returns None if the message doesn't look like a transaction.
    """
    original = text.strip()
    if not original:
        return None

    lower = original.lower()

    # ── 0. Detect transfer ─────────────────────────────────────────────

    transfer_match = _TRANSFER_PATTERN.search(original)
    if transfer_match:
        amount_val = float(transfer_match.group(1).replace(",", "."))
        from_raw = transfer_match.group(2).strip()
        to_raw = transfer_match.group(3).strip()

        from_resolved = resolve_account(from_raw)
        to_resolved = resolve_account(to_raw)

        from_id = from_resolved[0] if from_resolved else ""
        from_name = from_resolved[1] if from_resolved else from_raw
        to_id = to_resolved[0] if to_resolved else ""
        to_name = to_resolved[1] if to_resolved else to_raw

        return ParsedTransaction(
            type="transfer",
            amount=amount_val,
            category="Перевод",
            comment=f"{from_name} → {to_name}",
            raw=original,
            transfer_from=from_name,
            transfer_to=to_name,
            transfer_from_id=from_id,
            transfer_to_id=to_id,
            transfer_id=uuid.uuid4().hex[:12],
        )

    # ── 1. Extract amount ──────────────────────────────────────────────

    amount_match = _find_amount(original)
    if not amount_match:
        return None

    amount_val = amount_match["value"]

    # ── 2. Determine type ──────────────────────────────────────────────

    if amount_match["explicit_sign"]:
        tx_type = "income" if amount_match["explicit_sign"] == "+" else "expense"
    else:
        tx_type = _infer_type_from_text(lower, expense_categories, income_categories)

    # ── 3. Extract remaining tokens (split around amount) ──────────────

    before = original[: amount_match["start"]].strip()
    after = original[amount_match["end"] :].strip()

    tokens_before = _tokenize(before) if before else []
    tokens_after = _tokenize(after) if after else []

    # ── 4. Extract date keyword ───────────────────────────────────────

    date_override = None
    for tokens in (tokens_after, tokens_before):
        for t in tokens:
            if t in _DATE_KEYWORDS:
                date_override = _DATE_KEYWORDS[t]
                tokens.remove(t)
                break

    # ── 5. Extract account hint via aliases ───────────────────────────
    # Try multi-word first (e.g. "основная карта", "наличка eur"),
    # then single-word.

    account_id = None
    account_name = None

    for tokens in (tokens_after, tokens_before):
        # Multi-word match
        multi = resolve_account_multi(tokens)
        if multi:
            account_id, account_name = multi
            break
        # Single-word match
        for t in list(tokens):
            resolved = resolve_account(t)
            if resolved:
                account_id, account_name = resolved
                tokens.remove(t)
                break
        if account_id:
            break

    # ── 6. Extract category from remaining tokens ─────────────────────
    # Priority: user rules → CATEGORY_ALIASES → built-in categories → None

    all_tokens = tokens_before + tokens_after

    category = _match_user_rules(all_tokens, user_rules)
    if category is None:
        category = _match_aliases(all_tokens)
    if category is None:
        category = _match_category(all_tokens, expense_categories, income_categories)

    # ── 7. Remaining tokens become comment ────────────────────────────

    comment_tokens = [t for t in all_tokens if t]
    comment = " ".join(comment_tokens)

    return ParsedTransaction(
        type=tx_type,
        amount=amount_val,
        category=category,
        comment=comment,
        date=date_override,
        account_id=account_id,
        account_name=account_name,
        account=account_name,  # backward-compat
        raw=original,
    )


# ── Internal helpers ───────────────────────────────────────────────────────


def _find_amount(text: str) -> dict | None:
    """Find the first number in text and detect explicit sign.

    Returns dict with: value, start, end, explicit_sign (None | '+' | '-').
    Matches:
        +5000, -1200, 5000, 85
        ушло 340  (NOT matched — no explicit sign context)
    """
    # Look for explicit sign: +NNN or -NNN
    m = re.search(r"([+-])\s*(\d+(?:[.,]\d+)?)", text)
    if m:
        sign = m.group(1)
        val_str = m.group(2).replace(",", ".")
        return {
            "value": float(val_str),
            "start": m.start(),
            "end": m.end(),
            "explicit_sign": sign,
        }

    # Look for any number (no sign)
    m = re.search(r"\b(\d+(?:[.,]\d+)?)\b", text)
    if m:
        val_str = m.group(1).replace(",", ".")
        return {
            "value": float(val_str),
            "start": m.start(),
            "end": m.end(),
            "explicit_sign": None,
        }

    return None


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens, preserving multi-word phrases."""
    return [t.strip() for t in text.lower().split() if t.strip()]


def _infer_type_from_text(
    lower_text: str,
    expense_categories: Sequence[str] | None,
    income_categories: Sequence[str] | None,
) -> str:
    """Infer income vs expense from category keywords in text.

    Default expense categories are checked for substring matches.
    If an income category keyword appears, it's income.
    Otherwise, expense.
    """
    # Default income keywords (can be matched out of context)
    income_keywords = {"зарплата", "зарплату", "зп", "аванс", "премия", "подарок"}

    # If we have explicit income categories, check them
    if income_categories:
        for cat in income_categories:
            if cat.lower() in lower_text:
                return "income"

    # Check income keywords
    for kw in income_keywords:
        if kw in lower_text:
            return "income"

    return "expense"


def _match_user_rules(
    tokens: list[str],
    user_rules: Sequence[dict] | None,
):
    """Check tokens against user-defined rules (highest priority).

    Sorted by priority (lower number = higher priority).
    Returns category name on first match, or None.
    """
    if not user_rules or not tokens:
        return None

    text = " ".join(tokens)
    text_lower = text.lower()

    # Sort by priority ascending (lower = more important)
    sorted_rules = sorted(user_rules, key=lambda r: r.get("priority", 999))

    for rule in sorted_rules:
        pattern = str(rule.get("pattern", "")).lower()
        if not pattern:
            continue
        if pattern in text_lower:
            cat = str(rule.get("category", "")) or None
            if cat:
                # Remove matched tokens
                pattern_tokens = pattern.split()
                for pt in pattern_tokens:
                    for t in list(tokens):
                        if t == pt:
                            tokens.remove(t)
                            break
                return cat

    return None


def _match_aliases(tokens: list[str]):
    """Resolve tokens via CATEGORY_ALIASES (medium priority).

    Tries multi-word phrases first, then single tokens.
    Returns canonical category name on first match, or None.
    """
    if not tokens:
        return None

    text = " ".join(tokens)
    text_lower = text.lower()

    # Try longest alias first (multi-word phrases)
    sorted_aliases = sorted(CATEGORY_ALIASES.items(), key=lambda x: -len(x[0].split()))

    for alias, category in sorted_aliases:
        if alias in text_lower:
            # Remove matched tokens
            alias_tokens = alias.split()
            for at in alias_tokens:
                for t in list(tokens):
                    if t == at:
                        tokens.remove(t)
                        break
            return category

    return None


def _match_category(
    tokens: list[str],
    expense_categories: Sequence[str] | None,
    income_categories: Sequence[str] | None,
) -> str | None:
    """Find the best matching category from tokens.

    Tries exact multi-word match first, then single token match.
    Removes consumed tokens from the list.
    """
    if not tokens:
        return None

    text = " ".join(tokens)

    # Collect all known categories
    all_cats: list[tuple[str, str]] = []  # (lowercase, original)

    if expense_categories:
        for c in expense_categories:
            all_cats.append((c.lower(), c))
    if income_categories:
        for c in income_categories:
            all_cats.append((c.lower(), c))

    if not all_cats:
        return None

    # Try longest match first (multi-word categories)
    all_cats.sort(key=lambda x: -len(x[0].split()))

    for cat_lower, cat_original in all_cats:
        if cat_lower in text:
            # Remove matched tokens
            cat_tokens = cat_lower.split()
            for ct in cat_tokens:
                for t in list(tokens):
                    if t == ct:
                        tokens.remove(t)
                        break
            return cat_original

    return None
