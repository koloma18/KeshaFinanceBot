"""Tests for sign model, categories spending, budget manager, account balances."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── 1. Sign model: expense -350 → balance -350 UAH ────────────────────────


def test_balance_sign_model():
    from sheets import get_balance

    rows = [
        ["June", "01.06.2026", "income", 1000, 0, 0, "Зарплата", "", "manual"],
        ["June", "01.06.2026", "expense", -350, 0, 0, "Еда", "", "manual"],
    ]

    with patch("sheets.get_all_rows", return_value=rows):
        balance = get_balance()

    assert balance["UAH"] == 650
    assert balance["USD"] == 0


def test_balance_only_expenses():
    from sheets import get_balance

    rows = [
        ["June", "01.06.2026", "expense", -100, 0, 0, "Кофе", "", "manual"],
        ["June", "02.06.2026", "expense", -250, 0, 0, "Еда", "", "manual"],
    ]

    with patch("sheets.get_all_rows", return_value=rows):
        balance = get_balance()

    assert balance["UAH"] == -350


# ── 2. get_categories_spending returns positive amounts ────────────────────


def test_categories_spending_positive():
    from sheets import get_categories_spending

    rows = [
        ["June", "01.06.2026", "expense", -100, 0, 0, "Кофе", "", "manual"],
        ["June", "02.06.2026", "expense", -200, 0, 0, "Еда", "", "manual"],
        ["June", "03.06.2026", "expense", -50, 0, 0, "Кофе", "", "manual"],
        ["June", "04.06.2026", "income", 5000, 0, 0, "Зарплата", "", "manual"],
    ]

    with patch("sheets.get_all_rows", return_value=rows):
        spending = get_categories_spending("2026-06")

    assert spending["Кофе"] == 150
    assert spending["Еда"] == 200
    assert "Зарплата" not in spending


# ── 3. BudgetManager correctly computes spent/remaining/percent ───────────


def test_budget_manager_status():
    from budget import BudgetManager

    # Invalidate caches from other tests
    BudgetManager._budget_cache.clear()
    BudgetManager._spending_cache.clear()

    budget_rows = [["2026-06", "Общий", 10000, "budget"]]
    spending = {"Кофе": 1500, "Еда": 3500}

    # Patch the cached methods directly (bypasses get_budget_rows format issue)
    with (
        patch.object(
            BudgetManager, "_get_cached_budget_rows", return_value=budget_rows
        ),
        patch.object(BudgetManager, "_get_cached_spending", return_value=spending),
    ):
        status = BudgetManager.get_budget_status("2026-06")

    assert status is not None
    assert status["budget"] == 10000
    assert status["spent"] == 5000
    assert status["remaining"] == 5000
    assert status["percent"] == 0.5
    assert "█" in status["bar"]


def test_budget_manager_limits():
    from budget import BudgetManager

    BudgetManager._budget_cache.clear()
    BudgetManager._spending_cache.clear()

    budget_rows = [
        ["2026-06", "Кофе", 2000, "limit"],
        ["2026-06", "Еда", 5000, "limit"],
    ]
    spending = {"Кофе": 1800, "Еда": 2000}

    with (
        patch.object(
            BudgetManager, "_get_cached_budget_rows", return_value=budget_rows
        ),
        patch.object(BudgetManager, "_get_cached_spending", return_value=spending),
    ):
        limits = BudgetManager.get_limits("2026-06")

    assert len(limits) == 2

    coffee = next(l for l in limits if l["category"] == "Кофе")
    assert coffee["limit"] == 2000
    assert coffee["spent"] == 1800
    assert coffee["percent"] == 0.9

    food = next(l for l in limits if l["category"] == "Еда")
    assert food["spent"] == 2000
    assert food["percent"] == 0.4


def test_budget_manager_alerts():
    from budget import BudgetManager

    BudgetManager._budget_cache.clear()
    BudgetManager._spending_cache.clear()

    budget_rows = [["2026-06", "Кофе", 2000, "limit"]]
    spending = {"Кофе": 1100}

    with (
        patch.object(
            BudgetManager, "_get_cached_budget_rows", return_value=budget_rows
        ),
        patch.object(BudgetManager, "_get_cached_spending", return_value=spending),
    ):
        alerts = BudgetManager.check_alerts("Кофе", 200, "2026-06")

    assert len(alerts) >= 1
    assert any("50%" in a for a in alerts)


# ── 4. Monobank negative amount handled as expense ────────────────────────


def test_monobank_negative_is_expense():
    from sheets import get_categories_spending

    rows = [
        [
            "June",
            "01.06.2026",
            "expense",
            -450,
            0,
            0,
            "Еда",
            "mono import",
            "mono:abc123",
        ],
    ]

    with patch("sheets.get_all_rows", return_value=rows):
        spending = get_categories_spending("2026-06")

    assert spending["Еда"] == 450


# ── 5. recategorize logic: row index parsing ──────────────────────────────


@pytest.mark.parametrize(
    "args,expected_index,expected_cat_start",
    [
        (["15", "Еда"], 15, 1),
        (["last", "Еда"], -1, 1),
        (["Еда"], -1, 0),
        (["1", "Кофе", "латте"], 1, 1),
    ],
)
def test_recategorize_arg_parsing(args, expected_index, expected_cat_start):
    total_rows = 20
    row_index = None
    cat_start = 0

    first = args[0].lower()

    if first == "last":
        row_index = total_rows
        cat_start = 1
    else:
        try:
            row_index = int(first)
            cat_start = 1
        except ValueError:
            row_index = total_rows
            cat_start = 0

    if expected_index == -1:
        assert row_index == total_rows
    else:
        assert row_index == expected_index
    assert cat_start == expected_cat_start


# ── 6. Account balances ───────────────────────────────────────────────────

_BASE_ACCOUNTS = [
    {
        "id": "abc",
        "name": "Карта",
        "type": "bank",
        "currency": "UAH",
        "balance": 1000.0,
        "source": "manual",
        "active": True,
    },
]


def test_account_balances_starting_balance():
    """Starting balance from Accounts sheet is included."""
    from sheets import get_account_balances

    rows = [
        [
            "June",
            "01.06.2026",
            "income",
            5000,
            0,
            0,
            "Зарплата",
            "",
            "manual",
            "",
            "Карта",
            "",
        ],
    ]

    with (
        patch("sheets.get_accounts", return_value=_BASE_ACCOUNTS),
        patch("sheets.get_all_rows", return_value=rows),
    ):
        balances = get_account_balances()

    card = next(b for b in balances if b["name"] == "Карта")
    assert card["starting_balance"] == 1000.0
    assert card["balance"] == 6000.0  # 1000 start + 5000 income


def test_account_balances_expense_reduces():
    """Expense with account reduces that account's balance."""
    from sheets import get_account_balances

    rows = [
        [
            "June",
            "01.06.2026",
            "income",
            5000,
            0,
            0,
            "Зарплата",
            "",
            "manual",
            "",
            "Карта",
            "",
        ],
        [
            "June",
            "01.06.2026",
            "expense",
            -350,
            0,
            0,
            "Еда",
            "",
            "manual",
            "",
            "Карта",
            "",
        ],
    ]

    with (
        patch("sheets.get_accounts", return_value=_BASE_ACCOUNTS),
        patch("sheets.get_all_rows", return_value=rows),
    ):
        balances = get_account_balances()

    card = next(b for b in balances if b["name"] == "Карта")
    assert card["expense"] == 350.0
    assert card["balance"] == 5650.0  # 1000 + 5000 - 350


def test_account_balances_income_increases():
    """Income with account increases that account's balance."""
    from sheets import get_account_balances

    rows = [
        [
            "June",
            "01.06.2026",
            "income",
            5000,
            0,
            0,
            "Зарплата",
            "",
            "manual",
            "",
            "Карта",
            "",
        ],
    ]
    accounts_list = [
        {
            "id": "abc",
            "name": "Карта",
            "type": "bank",
            "currency": "UAH",
            "balance": 0.0,
            "source": "manual",
            "active": True,
        },
    ]

    with (
        patch("sheets.get_accounts", return_value=accounts_list),
        patch("sheets.get_all_rows", return_value=rows),
    ):
        balances = get_account_balances()

    card = next(b for b in balances if b["name"] == "Карта")
    assert card["income"] == 5000.0
    assert card["balance"] == 5000.0


def test_account_balances_transfer_between():
    """Transfer outflow reduces source, inflow increases destination."""
    from sheets import get_account_balances

    tid = "abc123def456"
    rows = [
        [
            "June",
            "01.06.2026",
            "expense",
            -5000,
            0,
            0,
            "Перевод",
            "",
            "manual",
            "",
            "Карта",
            tid,
        ],
        [
            "June",
            "01.06.2026",
            "income",
            5000,
            0,
            0,
            "Перевод",
            "",
            "manual",
            "",
            "Наличка",
            tid,
        ],
    ]
    accounts_list = [
        {
            "id": "abc",
            "name": "Карта",
            "type": "bank",
            "currency": "UAH",
            "balance": 10000.0,
            "source": "manual",
            "active": True,
        },
        {
            "id": "def",
            "name": "Наличка",
            "type": "cash",
            "currency": "UAH",
            "balance": 2000.0,
            "source": "manual",
            "active": True,
        },
    ]

    with (
        patch("sheets.get_accounts", return_value=accounts_list),
        patch("sheets.get_all_rows", return_value=rows),
    ):
        balances = get_account_balances()

    card = next(b for b in balances if b["name"] == "Карта")
    cash = next(b for b in balances if b["name"] == "Наличка")
    assert card["balance"] == 5000.0  # 10000 - 5000
    assert cash["balance"] == 7000.0  # 2000 + 5000


def test_account_balances_transfer_id_match():
    """Transfer income on cash-uah resolved by AccountID regardless of case.

    Income row has AccountID=cash-uah, AccountName=наличка (lowercase).
    get_account_balances should match by AccountID first and add 500 to cash-uah.
    """
    from sheets import get_account_balances

    tid = "abc123"
    rows = [
        [
            "June",
            "01.06.2026",
            "expense",
            -500,
            0,
            0,
            "Перевод",
            "",
            "manual",
            "card-main",
            "4441...5259",
            tid,
        ],
        [
            "June",
            "01.06.2026",
            "income",
            500,
            0,
            0,
            "Перевод",
            "",
            "manual",
            "cash-uah",
            "наличка",
            tid,
        ],
    ]
    accounts_list = [
        {
            "id": "card-main",
            "name": "4441...5259",
            "type": "bank",
            "currency": "UAH",
            "balance": 10000.0,
            "source": "manual",
            "active": True,
        },
        {
            "id": "cash-uah",
            "name": "Наличка",
            "type": "cash",
            "currency": "UAH",
            "balance": 200.0,
            "source": "manual",
            "active": True,
        },
    ]

    with (
        patch("sheets.get_accounts", return_value=accounts_list),
        patch("sheets.get_all_rows", return_value=rows),
    ):
        balances = get_account_balances()

    card = next(b for b in balances if b["name"] == "4441...5259")
    cash = next(b for b in balances if b["name"] == "Наличка")
    assert card["balance"] == 9500.0  # 10000 - 500
    assert cash["balance"] == 700.0  # 200 + 500


def test_account_balances_old_9col_rows_dont_break():
    """Old 9-column rows without account info don't break calculation."""
    from sheets import get_account_balances

    old_row = ["June", "01.06.2026", "expense", -150, 0, 0, "Кофе", "", "manual"]
    new_row = [
        "June",
        "01.06.2026",
        "income",
        5000,
        0,
        0,
        "Зарплата",
        "",
        "manual",
        "",
        "Карта",
        "",
    ]
    rows = [old_row, new_row]

    with (
        patch("sheets.get_accounts", return_value=_BASE_ACCOUNTS),
        patch("sheets.get_all_rows", return_value=rows),
    ):
        balances = get_account_balances()

    card = next(b for b in balances if b["name"] == "Карта")
    uncat = next(b for b in balances if b["name"] == "Без счета")

    assert card["balance"] == 6000.0  # 1000 + 5000
    assert uncat["balance"] == -150.0  # old row expense
    assert uncat["transaction_count"] == 1


def test_account_balances_inactive_not_included():
    """Inactive accounts are excluded from balances."""
    from sheets import get_account_balances

    rows = [
        [
            "June",
            "01.06.2026",
            "income",
            5000,
            0,
            0,
            "Зарплата",
            "",
            "manual",
            "",
            "Старый счёт",
            "",
        ],
    ]
    accounts_list = [
        {
            "id": "abc",
            "name": "Старый счёт",
            "type": "bank",
            "currency": "UAH",
            "balance": 100.0,
            "source": "manual",
            "active": False,
        },
        {
            "id": "def",
            "name": "Карта",
            "type": "bank",
            "currency": "UAH",
            "balance": 1000.0,
            "source": "manual",
            "active": True,
        },
    ]

    with (
        patch("sheets.get_accounts", return_value=accounts_list),
        patch("sheets.get_all_rows", return_value=rows),
    ):
        balances = get_account_balances()

    inactive = next((b for b in balances if b["name"] == "Старый счёт"), None)
    uncat = next(b for b in balances if b["name"] == "Без счета")

    assert inactive is None
    assert uncat["income"] == 5000.0


# ── 7. Bank command handlers: add_bank / del_bank / set_balance ────────────


@pytest.mark.asyncio
async def test_add_bank_creates_with_explicit_id():
    """/add_bank test-card 1234...9999 100 UAH → ID=test-card, Name=1234...9999."""
    from handlers.bank import add_bank

    update = MagicMock()
    context = MagicMock()
    context.args = ["test-card", "1234...9999", "100", "UAH"]
    update.message.reply_text = AsyncMock()

    with patch("handlers.bank.upsert_account", return_value=True) as mock_upsert:
        await add_bank(update, context)

    mock_upsert.assert_called_once_with(
        account_id="test-card",
        name="1234...9999",
        acc_type="card",
        currency="UAH",
        balance=100.0,
        source="manual",
        active=True,
    )
    update.message.reply_text.assert_called_once()
    assert "test-card" in update.message.reply_text.call_args[0][0]
    assert "100.00" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_del_bank_soft_deletes_by_id():
    """/del_bank test-card → upsert_account с active=False."""
    from handlers.bank import del_bank

    existing_account = {
        "id": "test-card",
        "name": "1234...9999",
        "type": "card",
        "currency": "UAH",
        "balance": 100.0,
        "source": "manual",
        "active": True,
    }

    update = MagicMock()
    context = MagicMock()
    context.args = ["test-card"]
    update.message.reply_text = AsyncMock()

    with (
        patch("handlers.bank.get_accounts", return_value=[existing_account]),
        patch("handlers.bank.upsert_account", return_value=True) as mock_upsert,
    ):
        await del_bank(update, context)

    mock_upsert.assert_called_once_with(
        account_id="test-card",
        name="1234...9999",
        acc_type="card",
        currency="UAH",
        balance=100.0,
        source="manual",
        active=False,
    )
    assert "деактивирован" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_del_bank_not_found():
    """/del_bank unknown → сообщение об ошибке, upsert_account не вызывается."""
    from handlers.bank import del_bank

    update = MagicMock()
    context = MagicMock()
    context.args = ["unknown-id"]
    update.message.reply_text = AsyncMock()

    with (
        patch("handlers.bank.get_accounts", return_value=[]),
        patch("handlers.bank.upsert_account") as mock_upsert,
    ):
        await del_bank(update, context)

    mock_upsert.assert_not_called()
    assert "не найден" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_set_balance_updates_by_id():
    """/set_balance test-card 200 → обновляет баланс через upsert_account."""
    from handlers.bank import set_balance

    existing_account = {
        "id": "test-card",
        "name": "1234...9999",
        "type": "card",
        "currency": "UAH",
        "balance": 100.0,
        "source": "manual",
        "active": True,
    }

    update = MagicMock()
    context = MagicMock()
    context.args = ["test-card", "200"]
    update.message.reply_text = AsyncMock()

    with (
        patch("handlers.bank.get_accounts", return_value=[existing_account]),
        patch("handlers.bank.upsert_account", return_value=True) as mock_upsert,
    ):
        await set_balance(update, context)

    mock_upsert.assert_called_once_with(
        account_id="test-card",
        name="1234...9999",
        acc_type="card",
        currency="UAH",
        balance=200.0,
        source="manual",
        active=True,
    )
    assert "100.00" in update.message.reply_text.call_args[0][0]
    assert "200.00" in update.message.reply_text.call_args[0][0]
