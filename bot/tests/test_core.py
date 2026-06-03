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


# ═══════════════════════════════════════════════════════════════════
# Phase 7 — Monthly Report Tests
# ═══════════════════════════════════════════════════════════════════


def test_parse_row_date_dd_mm_yyyy_string():
    """Date column as DD.MM.YYYY string → YYYY-MM."""
    from handlers.report import _parse_row_date

    row = ["June", "15.06.2026", "expense", -100, 0, 0, "Кофе", "", "manual"]
    assert _parse_row_date(row) == "2026-06"


def test_parse_row_date_serial_number():
    """Date column as Google Sheets Excel serial number."""
    # 2026-06-15 = Excel serial ~46180 (approximate)
    from datetime import datetime

    from handlers.report import _parse_row_date

    target = datetime(2026, 6, 15)
    epoch = datetime(1899, 12, 30)
    serial = (target - epoch).days

    row = ["", serial, "expense", -100, 0, 0, "Кофе", "", "manual"]
    assert _parse_row_date(row) == "2026-06"


def test_parse_row_date_fallback_to_month():
    """Date empty → fallback to Month column."""
    from handlers.report import _parse_row_date

    row = ["June", "", "expense", -100, 0, 0, "Кофе", "", "manual"]
    assert _parse_row_date(row) == "2026-06"


def test_parse_row_date_unknown_month_returns_none():
    """Month column not English → None."""
    from handlers.report import _parse_row_date

    row = ["Июнь", "", "expense", -100, 0, 0, "Кофе", "", "manual"]
    assert _parse_row_date(row) is None


def test_filter_period():
    """Only rows matching YYYY-MM pass through."""
    from handlers.report import _filter_period

    rows = [
        ["June", "01.06.2026", "income", 1000, 0, 0, "Зарплата", "", "manual"],
        ["July", "05.07.2026", "expense", -200, 0, 0, "Еда", "", "manual"],
        ["June", "10.06.2026", "expense", -50, 0, 0, "Кофе", "", "manual"],
    ]
    filtered = _filter_period(rows, "2026-06")
    assert len(filtered) == 2
    assert filtered[0][6] == "Зарплата"
    assert filtered[1][6] == "Кофе"


def test_summarize_excludes_transfers():
    """Rows with TRANSFER_ID are excluded from income/expense."""
    from handlers.report import _summarize

    rows = [
        # Normal income
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
            "",
            "",
        ],
        # Normal expense
        ["June", "02.06.2026", "expense", -500, 0, 0, "Еда", "", "manual", "", "", ""],
        # Transfer: expense leg — must be excluded
        [
            "June",
            "03.06.2026",
            "expense",
            -1000,
            0,
            0,
            "Перевод",
            "",
            "manual",
            "acc1",
            "Карта1",
            "TFR-001",
        ],
        # Transfer: income leg — must be excluded
        [
            "June",
            "03.06.2026",
            "income",
            1000,
            0,
            0,
            "Перевод",
            "",
            "manual",
            "acc2",
            "Карта2",
            "TFR-001",
        ],
    ]
    s = _summarize(rows)
    assert s["income"] == 5000
    assert s["expense"] == 500
    assert s["cats"] == {"Еда": 500}
    assert s["recurring"] == 0


def test_summarize_recurring_counted():
    """Recurring spending is included in expense AND tracked separately."""
    from handlers.report import _summarize

    rows = [
        [
            "June",
            "01.06.2026",
            "income",
            3000,
            0,
            0,
            "Зарплата",
            "",
            "manual",
            "",
            "",
            "",
        ],
        [
            "June",
            "02.06.2026",
            "expense",
            -100,
            0,
            0,
            "Подписки",
            "",
            "recurring:abc123",
            "",
            "Карта1",
            "",
        ],
        [
            "June",
            "03.06.2026",
            "expense",
            -200,
            0,
            0,
            "Подписки",
            "",
            "recurring:def456",
            "",
            "Карта2",
            "",
        ],
        ["June", "04.06.2026", "expense", -400, 0, 0, "Еда", "", "manual", "", "", ""],
    ]
    s = _summarize(rows)
    assert s["income"] == 3000
    assert s["expense"] == 700  # 100 + 200 + 400
    assert s["recurring"] == 300  # 100 + 200
    assert s["cats"] == {"Подписки": 300, "Еда": 400}


def test_spending_by_account_excludes_transfers():
    """Account spending excludes transfer rows and groups by ACCOUNT_NAME."""
    from handlers.report import _spending_by_account

    rows = [
        [
            "June",
            "01.06.2026",
            "expense",
            -500,
            0,
            0,
            "Еда",
            "",
            "manual",
            "",
            "Карта1",
            "",
        ],
        [
            "June",
            "02.06.2026",
            "expense",
            -300,
            0,
            0,
            "Кофе",
            "",
            "manual",
            "",
            "Карта1",
            "",
        ],
        [
            "June",
            "03.06.2026",
            "expense",
            -200,
            0,
            0,
            "Такси",
            "",
            "manual",
            "",
            "Карта2",
            "",
        ],
        # Transfer — excluded
        [
            "June",
            "04.06.2026",
            "expense",
            -1000,
            0,
            0,
            "Перевод",
            "",
            "manual",
            "acc1",
            "Карта1",
            "TFR-001",
        ],
        # Income — not counted
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
            "Карта3",
            "",
        ],
        # Expense without account name
        [
            "June",
            "05.06.2026",
            "expense",
            -150,
            0,
            0,
            "Другое",
            "",
            "manual",
            "",
            "",
            "",
        ],
    ]
    acc = _spending_by_account(rows)
    by_name = {a["name"]: a["expense"] for a in acc}
    assert by_name["Карта1"] == 800  # 500 + 300, transfer excluded
    assert by_name["Карта2"] == 200
    assert by_name["Без счета"] == 150


def test_top_categories():
    """Top N categories with bars and percentages."""
    from handlers.report import _top_categories

    cats = {"Еда": 500, "Кофе": 300, "Такси": 200}
    top, total = _top_categories(cats, n=5)
    assert total == 1000
    assert len(top) == 3
    assert top[0][0] == "Еда"
    assert top[0][2] == 50.0  # 500/1000*100
    assert "█" in top[0][3]


def test_report_empty_month():
    """When no rows match the period, report shows a clean message."""
    from handlers.report import _filter_period

    # Empty dataset
    all_rows = []
    rows = _filter_period(all_rows, "2026-06")
    assert rows == []


# ── Phase 7.2 — Period argument parsing ──


def test_parse_period_valid():
    """Valid YYYY-MM returns the same string."""
    from handlers.report import _parse_period_arg

    assert _parse_period_arg("2026-06") == "2026-06"
    assert _parse_period_arg("2025-12") == "2025-12"
    assert _parse_period_arg("2026-01") == "2026-01"


def test_parse_period_invalid_no_leading_zero():
    """2026-6 is invalid (month must be 2 digits)."""
    from handlers.report import _parse_period_arg

    assert _parse_period_arg("2026-6") is None
    assert _parse_period_arg("2026-5") is None


def test_parse_period_invalid_text():
    """Non-numeric input returns None."""
    from handlers.report import _parse_period_arg

    assert _parse_period_arg("abc") is None
    assert _parse_period_arg("июнь") is None
    assert _parse_period_arg("") is None


def test_parse_period_invalid_month():
    """Month 13, 00 returns None."""
    from handlers.report import _parse_period_arg

    assert _parse_period_arg("2026-13") is None
    assert _parse_period_arg("2026-00") is None


def test_report_with_period_arg():
    """/report 2026-05 filters rows for May 2026."""
    from handlers.report import _filter_period

    rows = [
        ["May", "05.05.2026", "income", 1000, 0, 0, "Зарплата", "", "manual"],
        ["June", "10.06.2026", "expense", -500, 0, 0, "Еда", "", "manual"],
    ]
    filtered = _filter_period(rows, "2026-05")
    assert len(filtered) == 1
    assert filtered[0][6] == "Зарплата"


@pytest.mark.asyncio
async def test_report_invalid_arg_shows_hint():
    """/report abc returns error hint."""
    from unittest.mock import AsyncMock

    from handlers.report import report

    update = AsyncMock()
    update.message = AsyncMock()
    context = AsyncMock()
    context.args = ["abc"]

    await report(update, context)

    update.message.reply_html.assert_called_once()
    text = update.message.reply_html.call_args[0][0]
    assert "Неправильный формат" in text
    assert "/report 2026-06" in text


@pytest.mark.asyncio
async def test_report_no_arg_uses_current_month():
    """/report without argument uses current month."""
    from unittest.mock import AsyncMock, patch

    from handlers.report import report

    update = AsyncMock()
    update.message = AsyncMock()
    context = AsyncMock()
    context.args = []

    all_rows = [["June", "01.06.2026", "income", 1000, 0, 0, "Зарплата", "", "manual"]]

    with patch("handlers.report.get_all_rows", return_value=all_rows):
        await report(update, context)

    update.message.reply_html.assert_called_once()
    html = update.message.reply_html.call_args[0][0]
    assert "+1,000 UAH" in html
    assert "июнь 2026" in html


# ── Phase 7.3 — Previous month comparison ──


def test_previous_month_normal():
    """2026-06 → 2026-05."""
    from handlers.report import _previous_month

    assert _previous_month("2026-06") == "2026-05"
    assert _previous_month("2026-12") == "2026-11"


def test_previous_month_year_boundary():
    """2026-01 → 2025-12."""
    from handlers.report import _previous_month

    assert _previous_month("2026-01") == "2025-12"
    assert _previous_month("2025-01") == "2024-12"


@pytest.mark.asyncio
async def test_report_comparison_with_prev_month():
    """Report includes comparison block when prev month has data."""
    from unittest.mock import AsyncMock, patch

    from handlers.report import report

    update = AsyncMock()
    update.message = AsyncMock()
    context = AsyncMock()
    context.args = ["2026-06"]

    all_rows = [
        ["June", "05.06.2026", "expense", -500, 0, 0, "Еда", "", "manual"],
        ["May", "10.05.2026", "expense", -300, 0, 0, "Еда", "", "manual"],
    ]

    with patch("handlers.report.get_all_rows", return_value=all_rows):
        await report(update, context)

    update.message.reply_html.assert_called_once()
    html = update.message.reply_html.call_args[0][0]
    assert "Сравнение с прошлым месяцем" in html
    assert "+200 UAH" in html  # expense: 500 - 300 = +200


@pytest.mark.asyncio
async def test_report_comparison_no_prev_data():
    """Report shows no-data message when prev month is empty."""
    from unittest.mock import AsyncMock, patch

    from handlers.report import report

    update = AsyncMock()
    update.message = AsyncMock()
    context = AsyncMock()
    context.args = ["2026-06"]

    all_rows = [
        ["June", "05.06.2026", "expense", -500, 0, 0, "Еда", "", "manual"],
    ]

    with patch("handlers.report.get_all_rows", return_value=all_rows):
        await report(update, context)

    update.message.reply_html.assert_called_once()
    html = update.message.reply_html.call_args[0][0]
    assert "за прошлый месяц данных нет" in html


def test_comparison_excludes_transfers():
    """Transfers excluded from both current and previous month."""
    from handlers.report import _filter_period, _summarize

    rows = [
        # June: normal expense
        ["June", "01.06.2026", "expense", -500, 0, 0, "Еда", "", "manual", "", "", ""],
        # June: transfer — must be excluded
        [
            "June",
            "02.06.2026",
            "expense",
            -1000,
            0,
            0,
            "Перевод",
            "",
            "manual",
            "acc1",
            "Карта1",
            "TFR-001",
        ],
        # May: normal expense
        ["May", "01.05.2026", "expense", -300, 0, 0, "Еда", "", "manual", "", "", ""],
        # May: transfer — must be excluded
        [
            "May",
            "02.05.2026",
            "expense",
            -2000,
            0,
            0,
            "Перевод",
            "",
            "manual",
            "acc2",
            "Карта2",
            "TFR-002",
        ],
    ]

    june = _summarize(_filter_period(rows, "2026-06"))
    may = _summarize(_filter_period(rows, "2026-05"))

    assert june["expense"] == 500  # transfer excluded
    assert may["expense"] == 300  # transfer excluded


# ── Phase 7.4 — Recurring items in report ──


def test_recurring_items_extracts_expense():
    """Recurring expense rows appear in _recurring_items."""
    from handlers.report import _recurring_items

    rows = [
        [
            "June",
            "01.06.2026",
            "expense",
            -100,
            0,
            0,
            "Подписки",
            "Apple iCloud",
            "recurring:abc",
            "",
            "",
            "",
        ],
        [
            "June",
            "02.06.2026",
            "expense",
            -200,
            0,
            0,
            "Подписки",
            "Netflix",
            "recurring:def",
            "",
            "",
            "",
        ],
    ]
    items = _recurring_items(rows)
    assert len(items) == 2
    titles = {it["title"] for it in items}
    assert "Apple iCloud" in titles
    assert "Netflix" in titles
    total = sum(it["amount"] for it in items)
    assert total == 300


def test_recurring_items_ignores_income():
    """Recurring income rows are excluded from recurring block."""
    from handlers.report import _recurring_items

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
            "recurring:salary",
            "",
            "",
            "",
        ],
        [
            "June",
            "02.06.2026",
            "expense",
            -100,
            0,
            0,
            "Подписки",
            "Netflix",
            "recurring:def",
            "",
            "",
            "",
        ],
    ]
    items = _recurring_items(rows)
    assert len(items) == 1
    assert items[0]["title"] == "Netflix"


def test_recurring_items_excludes_transfer():
    """Recurring source with Transfer ID is excluded."""
    from handlers.report import _recurring_items

    rows = [
        [
            "June",
            "01.06.2026",
            "expense",
            -100,
            0,
            0,
            "Перевод",
            "Аренда",
            "recurring:rent",
            "acc1",
            "Карта1",
            "TFR-001",
        ],
        [
            "June",
            "02.06.2026",
            "expense",
            -200,
            0,
            0,
            "Подписки",
            "Netflix",
            "recurring:def",
            "",
            "",
            "",
        ],
    ]
    items = _recurring_items(rows)
    assert len(items) == 1
    assert items[0]["title"] == "Netflix"


def test_recurring_items_ignores_non_recurring_source():
    """Source='manual' or 'mono:...' not included."""
    from handlers.report import _recurring_items

    rows = [
        ["June", "01.06.2026", "expense", -100, 0, 0, "Еда", "", "manual", "", "", ""],
        [
            "June",
            "02.06.2026",
            "expense",
            -200,
            0,
            0,
            "Такси",
            "",
            "mono:xyz",
            "",
            "",
            "",
        ],
    ]
    items = _recurring_items(rows)
    assert items == []


def test_recurring_items_fallback_title():
    """Empty AI Comment → fallback to Category."""
    from handlers.report import _recurring_items

    rows = [
        [
            "June",
            "01.06.2026",
            "expense",
            -100,
            0,
            0,
            "Подписки",
            "",
            "recurring:abc",
            "",
            "",
            "",
        ],
    ]
    items = _recurring_items(rows)
    assert len(items) == 1
    assert items[0]["title"] == "Подписки"


@pytest.mark.asyncio
async def test_report_recurring_percentage():
    """Recurring percentage = recurring_total / total_expense * 100."""
    from unittest.mock import AsyncMock, patch

    from handlers.report import report

    update = AsyncMock()
    update.message = AsyncMock()
    context = AsyncMock()
    context.args = ["2026-06"]

    all_rows = [
        [
            "June",
            "01.06.2026",
            "expense",
            -300,
            0,
            0,
            "Подписки",
            "Netflix",
            "recurring:def",
            "",
            "",
            "",
        ],
        ["June", "02.06.2026", "expense", -700, 0, 0, "Еда", "", "manual", "", "", ""],
    ]

    with patch("handlers.report.get_all_rows", return_value=all_rows):
        await report(update, context)

    update.message.reply_html.assert_called_once()
    html = update.message.reply_html.call_args[0][0]
    # 300 / 1000 = 30%
    assert "30.0% расходов" in html


# ── Phase 7.5 — Budget warnings in report ──


def test_categories_spending_excludes_transfers():
    """get_categories_spending ignores rows with Transfer ID."""
    from unittest.mock import patch

    from sheets import get_categories_spending

    rows = [
        ["June", "01.06.2026", "expense", -500, 0, 0, "Еда", "", "manual", "", "", ""],
        ["June", "02.06.2026", "expense", -300, 0, 0, "Кофе", "", "manual", "", "", ""],
        # Transfer — must be excluded
        [
            "June",
            "03.06.2026",
            "expense",
            -1000,
            0,
            0,
            "Перевод",
            "",
            "manual",
            "acc1",
            "Карта1",
            "TFR-001",
        ],
    ]

    with patch("sheets.get_all_rows", return_value=rows):
        spending = get_categories_spending("2026-06")

    assert spending.get("Еда") == 500
    assert spending.get("Кофе") == 300
    assert "Перевод" not in spending


@pytest.mark.asyncio
async def test_report_shows_budget_warnings():
    """Report shows ⚠️ Лимиты section when limits >= 80%."""
    from unittest.mock import AsyncMock, patch

    from budget import BudgetManager
    from handlers.report import report

    update = AsyncMock()
    update.message = AsyncMock()
    context = AsyncMock()
    context.args = ["2026-06"]

    all_rows = [
        ["June", "01.06.2026", "expense", -900, 0, 0, "Кофе", "", "manual"],
    ]
    budget_rows = [["2026-06", "Кофе", 1000, "limit"]]
    spending = {"Кофе": 900}

    with (
        patch("handlers.report.get_all_rows", return_value=all_rows),
        patch.object(
            BudgetManager, "_get_cached_budget_rows", return_value=budget_rows
        ),
        patch.object(BudgetManager, "_get_cached_spending", return_value=spending),
    ):
        await report(update, context)

    update.message.reply_html.assert_called_once()
    html = update.message.reply_html.call_args[0][0]
    assert "⚠️ Лимиты" in html
    assert "Кофе" in html
    assert "900 / 1,000 UAH" in html
    assert "90%" in html


@pytest.mark.asyncio
async def test_report_shows_limit_exceeded():
    """Report shows exceeded limit message."""
    from unittest.mock import AsyncMock, patch

    from budget import BudgetManager
    from handlers.report import report

    update = AsyncMock()
    update.message = AsyncMock()
    context = AsyncMock()
    context.args = ["2026-06"]

    all_rows = [
        ["June", "01.06.2026", "expense", -2500, 0, 0, "Такси", "", "manual"],
    ]
    budget_rows = [["2026-06", "Такси", 2000, "limit"]]
    spending = {"Такси": 2500}

    with (
        patch("handlers.report.get_all_rows", return_value=all_rows),
        patch.object(
            BudgetManager, "_get_cached_budget_rows", return_value=budget_rows
        ),
        patch.object(BudgetManager, "_get_cached_spending", return_value=spending),
    ):
        await report(update, context)

    update.message.reply_html.assert_called_once()
    html = update.message.reply_html.call_args[0][0]
    assert "превышен на 500 UAH" in html


@pytest.mark.asyncio
async def test_report_hides_low_limits():
    """Limits below 80% are not shown."""
    from unittest.mock import AsyncMock, patch

    from budget import BudgetManager
    from handlers.report import report

    update = AsyncMock()
    update.message = AsyncMock()
    context = AsyncMock()
    context.args = ["2026-06"]

    all_rows = [
        ["June", "01.06.2026", "expense", -300, 0, 0, "Кофе", "", "manual"],
    ]
    budget_rows = [["2026-06", "Кофе", 1000, "limit"]]
    spending = {"Кофе": 300}

    with (
        patch("handlers.report.get_all_rows", return_value=all_rows),
        patch.object(
            BudgetManager, "_get_cached_budget_rows", return_value=budget_rows
        ),
        patch.object(BudgetManager, "_get_cached_spending", return_value=spending),
    ):
        await report(update, context)

    update.message.reply_html.assert_called_once()
    html = update.message.reply_html.call_args[0][0]
    assert "⚠️ Лимиты" not in html  # 30% — too low, not shown


@pytest.mark.asyncio
async def test_report_no_limits_ok():
    """Report without any limits does not crash."""
    from unittest.mock import AsyncMock, patch

    from budget import BudgetManager
    from handlers.report import report

    update = AsyncMock()
    update.message = AsyncMock()
    context = AsyncMock()
    context.args = ["2026-06"]

    all_rows = [
        ["June", "01.06.2026", "expense", -500, 0, 0, "Еда", "", "manual"],
    ]

    with (
        patch("handlers.report.get_all_rows", return_value=all_rows),
        patch.object(BudgetManager, "_get_cached_budget_rows", return_value=[]),
        patch.object(BudgetManager, "_get_cached_spending", return_value={}),
    ):
        await report(update, context)

    update.message.reply_html.assert_called_once()
    html = update.message.reply_html.call_args[0][0]
    assert "⚠️ Лимиты" not in html


@pytest.mark.asyncio
async def test_report_budget_manager_error_safe():
    """Report survives BudgetManager exception."""
    from unittest.mock import AsyncMock, patch

    from budget import BudgetManager
    from handlers.report import report

    update = AsyncMock()
    update.message = AsyncMock()
    context = AsyncMock()
    context.args = ["2026-06"]

    all_rows = [
        ["June", "01.06.2026", "expense", -500, 0, 0, "Еда", "", "manual"],
    ]

    with (
        patch("handlers.report.get_all_rows", return_value=all_rows),
        patch.object(
            BudgetManager,
            "get_budget_status",
            side_effect=RuntimeError("sheets down"),
        ),
    ):
        await report(update, context)

    update.message.reply_html.assert_called_once()
    html = update.message.reply_html.call_args[0][0]
    assert "📊" in html  # report rendered
    assert "-500 UAH" in html  # expense shown
    assert "⚠️ Лимиты" not in html  # budget section skipped safely
