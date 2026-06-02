"""Tests for natural language parser."""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parser import ParsedTransaction, parse_message

EXPENSE_CATS = [
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
INCOME_CATS = [
    "Зарплата",
    "Фриланс",
    "Подарок",
    "Инвестиции",
    "Возврат долга",
    "Другое",
]


# ── Basic parsing ──────────────────────────────────────────────────────────


def test_coffee_expense():
    r = parse_message("кофе 85", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.type == "expense"
    assert r.amount == 85
    assert r.category == "Кофе"
    assert r.date is None


def test_taxi_yesterday():
    r = parse_message("такси 230 вчера", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.type == "expense"
    assert r.amount == 230
    assert r.category == "Такси"
    assert r.date == "yesterday"


def test_salary_income():
    r = parse_message("зарплата 40000", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.type == "income"
    assert r.amount == 40000
    assert r.category == "Зарплата"


def test_explicit_plus():
    r = parse_message("+5000 фриланс", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.type == "income"
    assert r.amount == 5000
    assert r.category == "Фриланс"


def test_explicit_minus():
    r = parse_message("-1200 продукты", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.type == "expense"
    assert r.amount == 1200
    assert r.category == "Еда"  # alias продуктов -> Еда


def test_with_account():
    r = parse_message("обед 340 карта", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.type == "expense"
    assert r.amount == 340
    assert r.account_name == "4441...5259"
    assert r.account_id == "card-main"
    assert r.account == "4441...5259"  # backward-compat
    assert r.category == "Еда"  # alias обед -> Еда


# ── Edge cases ─────────────────────────────────────────────────────────────


def test_no_number():
    r = parse_message("просто текст без цифр", EXPENSE_CATS, INCOME_CATS)
    assert r is None


def test_empty_string():
    r = parse_message("", EXPENSE_CATS, INCOME_CATS)
    assert r is None


def test_whitespace_only():
    r = parse_message("   ", EXPENSE_CATS, INCOME_CATS)
    assert r is None


def test_decimal_amount():
    r = parse_message("кофе 85.50", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.amount == 85.50
    assert r.category == "Кофе"


def test_comma_decimal():
    r = parse_message("еда 350,75", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.amount == 350.75
    assert r.category == "Еда"


def test_number_only():
    r = parse_message("500", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.amount == 500
    assert r.type == "expense"
    assert r.category is None


# ── Category detection ─────────────────────────────────────────────────────


def test_category_case_insensitive():
    r = parse_message("КОФЕ 100", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.category == "Кофе"


def test_explicit_sign_overrides_category():
    r = parse_message("-3000 зарплата", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.type == "expense"


def test_unknown_category():
    r = parse_message("бензин 2000", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.type == "expense"
    assert r.category is None
    assert "бензин" in r.comment


# ── to_row conversion ──────────────────────────────────────────────────────


def test_to_row_expense():
    p = ParsedTransaction(type="expense", amount=350, category="Еда", comment="обед")
    row, date_override = p.to_row()

    assert row[2] == "expense"
    assert row[3] < 0  # negative amount
    assert row[6] == "Еда"
    assert "обед" in row[7]
    assert row[8] == "manual"
    assert date_override is None


def test_to_row_income():
    p = ParsedTransaction(type="income", amount=50000, category="Зарплата")
    row, _ = p.to_row()

    assert row[2] == "income"
    assert row[3] > 0
    assert row[6] == "Зарплата"


def test_to_row_account_not_in_comment():
    """Account info goes to columns J/K, NOT to comment."""
    p = ParsedTransaction(
        type="expense",
        amount=340,
        category="Еда",
        account_id="card-main",
        account_name="4441...5259",
    )
    row, _ = p.to_row()
    # Comment (col H) should NOT contain account info
    assert "4441" not in row[7]
    assert "card-main" not in row[7]
    # Account info goes to dedicated columns
    assert row[9] == "card-main"  # AccountID
    assert row[10] == "4441...5259"  # AccountName


# ── Category aliases ───────────────────────────────────────────────────────


def test_alias_products_to_food():
    r = parse_message("продукты 1200", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.category == "Еда"
    assert r.amount == 1200
    assert r.type == "expense"


def test_alias_bolt_to_taxi():
    r = parse_message("bolt 230", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.category == "Такси"
    assert r.amount == 230
    assert r.type == "expense"


def test_alias_apteka_to_health():
    r = parse_message("аптека 400", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.category == "Здоровье"
    assert r.amount == 400
    assert r.type == "expense"


def test_alias_netflix_to_subscriptions():
    r = parse_message("netflix 299", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.category == "Подписки"
    assert r.amount == 299
    assert r.type == "expense"


def test_alias_rozetka_to_marketplaces():
    r = parse_message("розетка 1500", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.category == "Маркетплейсы"
    assert r.amount == 1500
    assert r.type == "expense"


# ── User rules (override aliases) ──────────────────────────────────────────


def test_user_rule_overrides_alias():
    """User rule 'продукты -> Развлечения' should win over alias 'продукты -> Еда'."""
    rules = [
        {
            "pattern": "продукты",
            "category": "Развлечения",
            "type": "expense",
            "priority": 1,
        }
    ]
    r = parse_message("продукты 500", EXPENSE_CATS, INCOME_CATS, user_rules=rules)
    assert r is not None
    assert r.category == "Развлечения"


def test_user_rule_no_match_when_pattern_absent():
    """User rule should not match when pattern isn't in text."""
    rules = [
        {"pattern": "xyz", "category": "Развлечения", "type": "expense", "priority": 1}
    ]
    r = parse_message("кофе 100", EXPENSE_CATS, INCOME_CATS, user_rules=rules)
    assert r is not None
    assert r.category == "Кофе"  # falls through to built-in


def test_user_rule_priority_order():
    """Lower priority number = checked first."""
    rules = [
        {
            "pattern": "обед",
            "category": "Развлечения",
            "type": "expense",
            "priority": 3,
        },
        {"pattern": "обед", "category": "Дом", "type": "expense", "priority": 1},
    ]
    r = parse_message("обед 300", EXPENSE_CATS, INCOME_CATS, user_rules=rules)
    assert r is not None
    assert r.category == "Дом"  # priority 1 wins over priority 3


def test_alias_multi_word():
    """Multi-word aliases like 'доставка еды' should match."""
    r = parse_message("доставка еды 600", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.category == "Еда"


# ── Account detection ────────────────────────────────────────────────────


def test_account_card_resolves_to_real():
    """кофе 85 карта → account_id=card-main, account_name=4441...5259"""
    r = parse_message("кофе 85 карта", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.type == "expense"
    assert r.amount == 85
    assert r.account_id == "card-main"
    assert r.account_name == "4441...5259"
    assert r.category == "Кофе"


def test_account_mono_resolves_to_card_main():
    """кофе 85 mono → account_id=card-main"""
    r = parse_message("кофе 85 mono", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.type == "expense"
    assert r.amount == 85
    assert r.account_id == "card-main"
    assert r.account_name == "4441...5259"
    assert r.category == "Кофе"


def test_account_cash():
    r = parse_message("обед 340 наличка", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.account_id == "cash-uah"
    assert r.account_name == "Наличка"


def test_account_privat():
    r = parse_message("кофе 100 приват", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.account_id == "privat24"
    assert r.account_name == "5457...8762"


def test_account_sense():
    r = parse_message("кофе 100 сенс", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.account_id == "sense"
    assert r.account_name == "5472...6562"


def test_no_account():
    r = parse_message("кофе 85", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.account_id is None
    assert r.account_name is None


def test_account_in_to_row():
    """Account info fills columns J (ID) and K (Name) correctly."""
    p = ParsedTransaction(
        type="expense",
        amount=340,
        category="Еда",
        account_id="card-main",
        account_name="4441...5259",
    )
    row, _ = p.to_row()
    assert len(row) == 12
    assert row[9] == "card-main"  # AccountID
    assert row[10] == "4441...5259"  # AccountName
    assert row[11] == ""  # no TransferID


def test_account_alias_not_in_comment():
    """When account is resolved via alias, it should NOT appear as [Account] in comment."""
    r = parse_message("кофе 85 карта", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert "карта" not in r.comment
    assert "4441" not in r.comment
    assert "card-main" not in r.comment
    assert r.comment == ""  # all tokens consumed by category/account extraction


def test_comment_preserved_without_account():
    """When no account hint, comment becomes remaining tokens."""
    r = parse_message("кофе 85 в Старбаксе", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert "в" in r.comment or "Старбаксе" in r.comment


# ── Multi-word account aliases ────────────────────────────────────────────


def test_account_multi_word_osnovnaya_karta():
    """основная карта → card-main"""
    r = parse_message("кофе 85 основная карта", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.account_id == "card-main"
    assert r.account_name == "4441...5259"


def test_account_multi_word_ofisnaya_karta():
    """офисная карта → card-office"""
    r = parse_message("обед 500 офисная карта", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.account_id == "card-office"
    assert r.account_name == "4441...4454"


def test_account_multi_word_cash_eur():
    """наличка eur → cash-eur"""
    r = parse_message("кофе 5 наличка eur", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.account_id == "cash-eur"
    assert r.account_name == "наличка EUR"


def test_account_multi_word_cash_evro():
    """наличка евро → cash-eur"""
    r = parse_message("кофе 5 наличка евро", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.account_id == "cash-eur"
    assert r.account_name == "наличка EUR"


# ── Transfer detection ────────────────────────────────────────────────────


def test_transfer_mono_to_cash():
    r = parse_message("перевод 5000 с mono на cash", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.type == "transfer"
    assert r.amount == 5000
    assert r.transfer_from == "4441...5259"  # resolved from mono alias
    assert r.transfer_to == "Наличка"  # resolved from cash alias
    assert r.transfer_from_id == "card-main"
    assert r.transfer_to_id == "cash-uah"
    assert r.is_transfer()


def test_transfer_card_to_cash_russian_style():
    r = parse_message("перевод 1000 с карты в наличку", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.type == "transfer"
    assert r.amount == 1000
    assert r.transfer_from == "4441...5259"  # карты alias → card-main
    assert r.transfer_to == "Наличка"  # наличку alias → cash-uah
    assert r.transfer_from_id == "card-main"
    assert r.transfer_to_id == "cash-uah"


def test_transfer_generates_two_linked_rows():
    r = parse_message("перевод 500 с карта на mono", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    outflow, inflow, tid = r.to_transfer_rows()

    # Both rows share the same TransferID
    assert outflow[11] == tid
    assert inflow[11] == tid

    # Outflow is expense (negative), inflow is income (positive)
    assert outflow[2] == "expense"
    assert float(outflow[3]) == -500
    assert inflow[2] == "income"
    assert float(inflow[3]) == 500

    # Category is "Перевод" for both
    assert outflow[6] == "Перевод"
    assert inflow[6] == "Перевод"

    # Account names with real IDs
    assert outflow[9] == "card-main"  # from account ID
    assert outflow[10] == "4441...5259"  # from account name
    assert inflow[9] == "card-main"  # to account ID (mono → card-main)
    assert inflow[10] == "4441...5259"  # to account name


def test_transfer_balance_neutral():
    """Transfer outflow + inflow = net zero UAH balance change."""
    r = parse_message("перевод 3000 с mono на cash", EXPENSE_CATS, INCOME_CATS)
    outflow, inflow, _ = r.to_transfer_rows()

    assert float(outflow[2 + 1]) + float(inflow[2 + 1]) == 0


def test_transfer_from_card_to_cash():
    """перевод 500 с карты в наличку → from card-main, to cash-uah"""
    r = parse_message("перевод 500 с карты в наличку", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.transfer_from_id == "card-main"
    assert r.transfer_to_id == "cash-uah"
    assert r.transfer_from == "4441...5259"
    assert r.transfer_to == "Наличка"


# ── Old transactions without AccountID don't break balance ────────────────


def test_balance_with_old_and_new_rows():
    """Old rows (9 columns) and new rows (12 columns) compute balance correctly."""
    from sheets import get_balance

    # 9-column old row
    rows = [
        ["June", "01.06.2026", "income", 1000, 0, 0, "Зарплата", "", "manual"],
        # 12-column new row with account
        [
            "June",
            "01.06.2026",
            "expense",
            -350,
            0,
            0,
            "Еда",
            "обед",
            "manual",
            "card-main",
            "4441...5259",
            "",
        ],
    ]

    with patch("sheets.get_all_rows", return_value=rows):
        balance = get_balance()

    assert balance["UAH"] == 650


# ── TransferID field is empty for non-transfer rows ───────────────────────


def test_regular_transaction_no_transfer_id():
    r = parse_message("кофе 85 карта", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert r.transfer_id == ""

    row, _ = r.to_row()
    assert row[11] == ""  # TransferID column is empty


def test_transfer_has_transfer_id():
    r = parse_message("перевод 500 с mono на cash", EXPENSE_CATS, INCOME_CATS)
    assert r is not None
    assert len(r.transfer_id) > 0
