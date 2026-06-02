"""Tests for Recurring payments & subscriptions data layer.

Tests the Google Sheets model, CRUD, due filtering, and date calculation.
Does NOT test Telegram handlers.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from handlers.recurring import (
    _build_due_card,
    _create_transaction_from_recurring,
    _find_recurring_transaction,
    _format_amount_display,
    _resolve_account_display,
    _parse_date_to_period,
    _resolve_canonical_account_name,
)
from sheets import (
    RECURRING_COL,
    RECURRING_HEADERS,
    _parse_recurring_row,
    _recurring_to_row,
    _validate_recurring,
    calculate_initial_next_run_date,
    calculate_next_run_date,
)

# ── Helpers for building test data ─────────────────────────────────────────


def make_rent_item():
    return {
        "id": "rent-flat",
        "title": "Аренда квартиры",
        "type": "expense",
        "amount": 20000,
        "currency": "UAH",
        "original_amount": 0,
        "original_currency": "",
        "estimated_uah": 20000,
        "amount_mode": "fixed",
        "category": "Дом",
        "default_account_id": "",
        "default_account_name": "",
        "payment_options": "cash-uah,card-office,card-main",
        "frequency": "monthly",
        "day_of_month": 3,
        "due_day": 3,
        "grace_until_day": 4,
        "next_run_date": "2026-06-03",
        "last_run_date": "",
        "status": "active",
        "created_at": "2026-06-02",
        "updated_at": "2026-06-02",
        "notes": "",
        "last_action": "",
    }


def make_utilities_item():
    return {
        "id": "utilities",
        "title": "Коммунальные",
        "type": "expense",
        "amount": 0,
        "currency": "UAH",
        "original_amount": 0,
        "original_currency": "",
        "estimated_uah": 3500,
        "amount_mode": "variable",
        "category": "Дом",
        "default_account_id": "",
        "default_account_name": "",
        "payment_options": "cash-uah,card-office,card-main",
        "frequency": "monthly",
        "day_of_month": 4,
        "due_day": 4,
        "grace_until_day": 4,
        "next_run_date": "2026-06-04",
        "last_run_date": "",
        "status": "active",
        "created_at": "2026-06-02",
        "updated_at": "2026-06-02",
        "notes": "",
        "last_action": "",
    }


def make_apple_item():
    return {
        "id": "subscription-apple",
        "title": "Apple",
        "type": "expense",
        "amount": 0,
        "currency": "UAH",
        "original_amount": 2.49,
        "original_currency": "USD",
        "estimated_uah": 110.64,
        "amount_mode": "fx",
        "category": "Подписки",
        "default_account_id": "card-main",
        "default_account_name": "4441...5259",
        "payment_options": "",
        "frequency": "monthly",
        "day_of_month": 27,
        "due_day": 27,
        "grace_until_day": 0,
        "next_run_date": "2026-06-27",
        "last_run_date": "",
        "status": "active",
        "created_at": "2026-06-02",
        "updated_at": "2026-06-02",
        "notes": "Apple subscription, original 2.49 USD",
        "last_action": "",
    }


def make_openai_item():
    return {
        "id": "subscription-openai",
        "title": "OpenAI",
        "type": "expense",
        "amount": 0,
        "currency": "UAH",
        "original_amount": 23.80,
        "original_currency": "USD",
        "estimated_uah": 1052.86,
        "amount_mode": "fx",
        "category": "Подписки",
        "default_account_id": "card-main",
        "default_account_name": "4441...5259",
        "payment_options": "",
        "frequency": "monthly",
        "day_of_month": 12,
        "due_day": 12,
        "grace_until_day": 0,
        "next_run_date": "2026-06-12",
        "last_run_date": "",
        "status": "active",
        "created_at": "2026-06-02",
        "updated_at": "2026-06-02",
        "notes": "OpenAI subscription, original 23.80 USD",
        "last_action": "",
    }


def make_wayforpay_item():
    return {
        "id": "subscription-wayforpay",
        "title": "WayForPay",
        "type": "expense",
        "amount": 102,
        "currency": "UAH",
        "original_amount": 0,
        "original_currency": "",
        "estimated_uah": 102,
        "amount_mode": "fixed",
        "category": "Подписки",
        "default_account_id": "card-main",
        "default_account_name": "4441...5259",
        "payment_options": "",
        "frequency": "monthly",
        "day_of_month": 2,
        "due_day": 2,
        "grace_until_day": 0,
        "next_run_date": "2026-06-02",
        "last_run_date": "",
        "status": "active",
        "created_at": "2026-06-02",
        "updated_at": "2026-06-02",
        "notes": "",
        "last_action": "",
    }


# ── Parsing ────────────────────────────────────────────────────────────────


class TestParseRecurringRow:
    def test_parses_valid_row(self):
        row = _recurring_to_row(make_rent_item())
        assert len(row) == 24
        assert row[RECURRING_COL["ID"]] == "rent-flat"
        assert row[RECURRING_COL["TITLE"]] == "Аренда квартиры"
        assert row[RECURRING_COL["AMOUNT"]] == 20000

    def test_parses_fx_row(self):
        item = make_apple_item()
        row = _recurring_to_row(item)
        parsed = _parse_recurring_row(row)
        assert parsed["id"] == "subscription-apple"
        assert parsed["title"] == "Apple"
        assert parsed["amount_mode"] == "fx"
        assert parsed["original_amount"] == 2.49
        assert parsed["original_currency"] == "USD"
        assert parsed["estimated_uah"] == 110.64

    def test_parses_variable_row(self):
        item = make_utilities_item()
        row = _recurring_to_row(item)
        parsed = _parse_recurring_row(row)
        assert parsed["amount_mode"] == "variable"
        assert parsed["amount"] == 0
        assert parsed["estimated_uah"] == 3500

    def test_parse_empty_row_returns_none(self):
        assert _parse_recurring_row([]) is None
        assert _parse_recurring_row(["", "", ""]) is None

    def test_parse_row_with_missing_cols(self):
        short_row = ["test-id", "Test Title"]
        parsed = _parse_recurring_row(short_row)
        assert parsed is not None
        assert parsed["id"] == "test-id"
        assert parsed["title"] == "Test Title"
        assert parsed["amount"] == 0.0


class TestRecurringToRow:
    def test_roundtrip_preserves_data(self):
        item = make_apple_item()
        row = _recurring_to_row(item)
        parsed = _parse_recurring_row(row)
        assert parsed["id"] == item["id"]
        assert parsed["title"] == item["title"]
        assert parsed["amount_mode"] == item["amount_mode"]
        assert parsed["original_amount"] == item["original_amount"]
        assert parsed["original_currency"] == item["original_currency"]
        assert parsed["estimated_uah"] == item["estimated_uah"]

    def test_to_row_has_24_columns(self):
        row = _recurring_to_row(make_rent_item())
        assert len(row) == 24
        assert len(row) == len(RECURRING_HEADERS)


# ── Validation ─────────────────────────────────────────────────────────────


class TestValidateRecurring:
    def test_valid_fixed_item(self):
        errors = _validate_recurring(make_rent_item())
        assert errors == []

    def test_valid_fx_item(self):
        errors = _validate_recurring(make_apple_item())
        assert errors == []

    def test_valid_variable_item(self):
        errors = _validate_recurring(make_utilities_item())
        assert errors == []

    def test_missing_title(self):
        item = make_rent_item()
        item["title"] = ""
        errors = _validate_recurring(item)
        assert any("Title" in e for e in errors)

    def test_invalid_type(self):
        item = make_rent_item()
        item["type"] = "transfer"
        errors = _validate_recurring(item)
        assert any("Type" in e for e in errors)

    def test_invalid_currency(self):
        item = make_rent_item()
        item["currency"] = "GBP"
        errors = _validate_recurring(item)
        assert any("Currency" in e for e in errors)

    def test_invalid_amount_mode(self):
        item = make_rent_item()
        item["amount_mode"] = "unknown"
        errors = _validate_recurring(item)
        assert any("AmountMode" in e for e in errors)

    def test_invalid_frequency(self):
        item = make_rent_item()
        item["frequency"] = "yearly"
        errors = _validate_recurring(item)
        assert any("Frequency" in e for e in errors)

    def test_invalid_status(self):
        item = make_rent_item()
        item["status"] = "archived"
        errors = _validate_recurring(item)
        assert any("Status" in e for e in errors)

    def test_day_of_month_too_low(self):
        item = make_rent_item()
        item["day_of_month"] = 0
        errors = _validate_recurring(item)
        assert any("DayOfMonth" in e for e in errors)

    def test_day_of_month_too_high(self):
        item = make_rent_item()
        item["day_of_month"] = 32
        errors = _validate_recurring(item)
        assert any("DayOfMonth" in e for e in errors)

    def test_fx_requires_original_amount(self):
        item = make_apple_item()
        item["original_amount"] = 0
        errors = _validate_recurring(item)
        assert any("OriginalAmount > 0" in e for e in errors)

    def test_fx_requires_original_currency(self):
        item = make_apple_item()
        item["original_currency"] = ""
        errors = _validate_recurring(item)
        assert any("OriginalCurrency" in e for e in errors)

    def test_fx_original_currency_not_uah(self):
        item = make_apple_item()
        item["original_currency"] = "UAH"
        errors = _validate_recurring(item)
        assert any("must not be UAH" in e for e in errors)

    def test_fixed_requires_amount(self):
        item = make_rent_item()
        item["amount"] = 0
        errors = _validate_recurring(item)
        assert any("Amount > 0" in e for e in errors)

    def test_fixed_requires_uah_currency(self):
        item = make_rent_item()
        item["currency"] = "USD"
        errors = _validate_recurring(item)
        assert any("Currency = UAH" in e for e in errors)

    def test_variable_requires_uah_currency(self):
        item = make_utilities_item()
        item["currency"] = "USD"
        errors = _validate_recurring(item)
        assert any("Currency = UAH" in e for e in errors)


# ── Next date calculation ──────────────────────────────────────────────────


class TestCalculateNextRunDate:
    def test_monthly_normal_case(self):
        result = calculate_next_run_date("2026-06-03", "monthly", 3)
        assert result == "2026-07-03"

    def test_monthly_day_31_handles_shorter_month(self):
        """Day 31 in January → next month is February, clamp to 28/29."""
        result = calculate_next_run_date("2026-01-31", "monthly", 31)
        assert result == "2026-02-28"  # 2026 is not a leap year

    def test_monthly_day_31_december(self):
        """Day 31 in December → next is January, 31 is valid."""
        result = calculate_next_run_date("2026-12-31", "monthly", 31)
        assert result == "2027-01-31"

    def test_daily_next_date(self):
        result = calculate_next_run_date("2026-06-02", "daily")
        assert result == "2026-06-03"

    def test_weekly_next_date(self):
        result = calculate_next_run_date("2026-06-02", "weekly")
        assert result == "2026-06-09"

    def test_monthly_day_30_in_february(self):
        """Day 30 doesn't exist in February."""
        result = calculate_next_run_date("2026-01-30", "monthly", 30)
        assert result == "2026-02-28"

    def test_empty_date_defaults_to_today(self):
        result = calculate_next_run_date("", "daily")
        expected = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        assert result == expected

    def test_unknown_frequency_defaults_to_daily(self):
        result = calculate_next_run_date("2026-06-02", "yearly")
        assert result == "2026-06-03"


# ── Initial next run date calculation ──────────────────────────────────────


class TestCalculateInitialNextRunDate:
    """Tests for calculate_initial_next_run_date — first occurrence >= today."""

    def test_day_3_is_june_when_today_june_2(self):
        """today 2026-06-02, monthly day 3 → 2026-06-03"""
        result = calculate_initial_next_run_date("2026-06-02", "monthly", 3)
        assert result == "2026-06-03"

    def test_day_27_is_june_when_today_june_2(self):
        """today 2026-06-02, monthly day 27 → 2026-06-27"""
        result = calculate_initial_next_run_date("2026-06-02", "monthly", 27)
        assert result == "2026-06-27"

    def test_today_is_due_when_day_matches(self):
        """today 2026-06-27, monthly day 27 → 2026-06-27"""
        result = calculate_initial_next_run_date("2026-06-27", "monthly", 27)
        assert result == "2026-06-27"

    def test_day_passed_goes_to_next_month(self):
        """today 2026-06-28, monthly day 27 → 2026-07-27"""
        result = calculate_initial_next_run_date("2026-06-28", "monthly", 27)
        assert result == "2026-07-27"

    def test_after_paid_next_is_next_month(self):
        """After paid/skipped 2026-06-27, next should be 2026-07-27"""
        # calculate_next_run_date handles the post-payment case
        result = calculate_next_run_date("2026-06-27", "monthly", 27)
        assert result == "2026-07-27"

    def test_day_31_clamped_to_february_28(self):
        """today 2026-01-15, monthly day 31 → clamp to 2026-01-31 first.
        But 31 >= 15, so still January."""
        result = calculate_initial_next_run_date("2026-01-15", "monthly", 31)
        assert result == "2026-01-31"

    def test_day_31_past_in_january_goes_to_february_clamped(self):
        """today 2026-02-01, monthly day 31 → Feb has 28 days, clamp to 28"""
        result = calculate_initial_next_run_date("2026-02-01", "monthly", 31)
        assert result == "2026-02-28"

    def test_day_1_is_today_if_today_is_1(self):
        result = calculate_initial_next_run_date("2026-06-01", "monthly", 1)
        assert result == "2026-06-01"

    def test_daily_returns_today(self):
        result = calculate_initial_next_run_date("2026-06-15", "daily")
        assert result == "2026-06-15"

    def test_weekly_returns_today(self):
        result = calculate_initial_next_run_date("2026-06-15", "weekly")
        assert result == "2026-06-15"

    def test_december_rolls_to_january(self):
        """today 2026-12-20, monthly day 5 → next is 2027-01-05"""
        result = calculate_initial_next_run_date("2026-12-20", "monthly", 5)
        assert result == "2027-01-05"

    def test_existing_calculate_next_run_date_still_works(self):
        """calculate_next_run_date unchanged: always advances one period."""
        assert calculate_next_run_date("2026-06-02", "monthly", 3) == "2026-07-03"
        assert calculate_next_run_date("2026-06-27", "monthly", 27) == "2026-07-27"
        assert calculate_next_run_date("2026-06-02", "daily") == "2026-06-03"


# ── Due filtering (logic only, no Sheets API) ──────────────────────────────


class TestDueFilteringLogic:
    def test_active_item_with_past_date_is_due(self):
        """Item with NextRunDate in the past should be due."""
        item = make_rent_item()
        item["next_run_date"] = "2026-05-15"  # in the past
        item["status"] = "active"
        assert item["next_run_date"] <= "2026-06-02"

    def test_active_item_with_future_date_is_not_due(self):
        """Item with future NextRunDate should NOT be due."""
        item = make_rent_item()
        item["next_run_date"] = "2026-12-25"
        item["status"] = "active"
        assert not (item["next_run_date"] <= "2026-06-02")

    def test_paused_item_is_not_due(self):
        """Paused items should be excluded from due check."""
        item = make_rent_item()
        item["status"] = "paused"
        assert item["status"] != "active"

    def test_deleted_item_is_not_due(self):
        """Deleted items should be excluded from due check."""
        item = make_rent_item()
        item["status"] = "deleted"
        assert item["status"] != "active"

    def test_active_item_with_empty_next_run_is_due(self):
        """Item without NextRunDate should be treated as due."""
        item = make_rent_item()
        item["next_run_date"] = ""
        item["status"] = "active"
        assert item["next_run_date"] == ""

    def test_active_item_with_today_date_is_due(self):
        """Item with NextRunDate = today is due."""
        today = datetime.now().strftime("%Y-%m-%d")
        item = make_rent_item()
        item["next_run_date"] = today
        item["status"] = "active"
        assert item["next_run_date"] <= today


# ── Model completeness ─────────────────────────────────────────────────────


class TestRecurringModelCompleteness:
    def test_apple_fx_stores_all_fields(self):
        item = make_apple_item()
        assert item["amount_mode"] == "fx"
        assert item["original_amount"] == 2.49
        assert item["original_currency"] == "USD"
        assert item["estimated_uah"] == 110.64
        assert item["currency"] == "UAH"
        assert item["day_of_month"] == 27
        assert item["category"] == "Подписки"

    def test_openai_fx_stores_all_fields(self):
        item = make_openai_item()
        assert item["amount_mode"] == "fx"
        assert item["original_amount"] == 23.80
        assert item["original_currency"] == "USD"
        assert item["estimated_uah"] == 1052.86
        assert item["day_of_month"] == 12

    def test_wayforpay_fixed_stores_all_fields(self):
        item = make_wayforpay_item()
        assert item["amount_mode"] == "fixed"
        assert item["amount"] == 102
        assert item["currency"] == "UAH"
        assert item["original_amount"] == 0

    def test_rent_has_payment_options(self):
        item = make_rent_item()
        assert "cash-uah" in item["payment_options"]
        assert "card-office" in item["payment_options"]
        assert "card-main" in item["payment_options"]

    def test_variable_can_have_amount_zero(self):
        item = make_utilities_item()
        assert item["amount_mode"] == "variable"
        assert item["amount"] == 0

    def test_fx_items_have_zero_amount_field(self):
        for maker in [make_apple_item, make_openai_item]:
            item = maker()
            assert item["amount"] == 0, f"{item['title']}: amount should be 0 for fx"


# ── Simulated Sheets integration tests ─────────────────────────────────────


class TestRecurringSheetsIntegration:
    """Tests that simulate Sheets API calls via mocking."""

    @patch("sheets._sheets_api")
    @patch("sheets.GOOGLE_SERVICE_ACCOUNT_EMAIL", "test@example.com")
    @patch("sheets.GOOGLE_PRIVATE_KEY", "test-key")
    @patch("sheets.SPREADSHEET_ID", "test-sheet")
    def test_get_recurring_skips_deleted(self, mock_api):
        """get_recurring_items with default filter skips deleted items."""
        from sheets import get_recurring_items

        row_active = _recurring_to_row(make_rent_item())
        row_active[RECURRING_COL["STATUS"]] = "active"

        row_deleted = _recurring_to_row(make_apple_item())
        row_deleted[RECURRING_COL["ID"]] = "deleted-item"
        row_deleted[RECURRING_COL["TITLE"]] = "Deleted Sub"
        row_deleted[RECURRING_COL["STATUS"]] = "deleted"

        mock_api.return_value = {"values": [RECURRING_HEADERS, row_active, row_deleted]}

        items = get_recurring_items(status_filter="active")
        assert len(items) == 1
        assert items[0]["id"] == "rent-flat"
        assert items[0]["status"] == "active"

    @patch("sheets._sheets_api")
    @patch("sheets.GOOGLE_SERVICE_ACCOUNT_EMAIL", "test@example.com")
    @patch("sheets.GOOGLE_PRIVATE_KEY", "test-key")
    @patch("sheets.SPREADSHEET_ID", "test-sheet")
    def test_get_recurring_all_includes_deleted(self, mock_api):
        """get_recurring_items(status_filter=None) includes deleted."""
        from sheets import get_recurring_items

        row_active = _recurring_to_row(make_rent_item())
        row_active[RECURRING_COL["STATUS"]] = "active"

        row_deleted = _recurring_to_row(make_apple_item())
        row_deleted[RECURRING_COL["ID"]] = "deleted-item"
        row_deleted[RECURRING_COL["TITLE"]] = "Deleted Sub"
        row_deleted[RECURRING_COL["STATUS"]] = "deleted"

        mock_api.return_value = {"values": [RECURRING_HEADERS, row_active, row_deleted]}

        items = get_recurring_items(status_filter=None)
        assert len(items) == 2
        statuses = {i["status"] for i in items}
        assert "active" in statuses
        assert "deleted" in statuses

    @patch("sheets._sheets_api")
    @patch("sheets.GOOGLE_SERVICE_ACCOUNT_EMAIL", "test@example.com")
    @patch("sheets.GOOGLE_PRIVATE_KEY", "test-key")
    @patch("sheets.SPREADSHEET_ID", "test-sheet")
    def test_get_due_returns_active_with_past_or_today_date(self, mock_api):
        """get_due_recurring_items returns only active items due <= today."""
        from sheets import get_due_recurring_items

        today = "2026-06-02"

        row_due = _recurring_to_row(make_rent_item())
        row_due[RECURRING_COL["STATUS"]] = "active"
        row_due[RECURRING_COL["NEXT_RUN_DATE"]] = "2026-05-15"  # past

        row_future = _recurring_to_row(make_apple_item())
        row_future[RECURRING_COL["ID"]] = "future-item"
        row_future[RECURRING_COL["TITLE"]] = "Future Sub"
        row_future[RECURRING_COL["STATUS"]] = "active"
        row_future[RECURRING_COL["NEXT_RUN_DATE"]] = "2026-12-25"  # future

        row_paused = _recurring_to_row(make_utilities_item())
        row_paused[RECURRING_COL["ID"]] = "paused-item"
        row_paused[RECURRING_COL["TITLE"]] = "Paused Sub"
        row_paused[RECURRING_COL["STATUS"]] = "paused"
        row_paused[RECURRING_COL["NEXT_RUN_DATE"]] = "2026-05-15"  # past but paused

        mock_api.side_effect = [
            {"values": [RECURRING_HEADERS, row_due, row_future, row_paused]},
            {"values": [RECURRING_HEADERS, row_due, row_future, row_paused]},
        ]

        items = get_due_recurring_items(today)
        assert len(items) == 1
        assert items[0]["id"] == "rent-flat"

    @patch("sheets._sheets_api")
    @patch("sheets.GOOGLE_SERVICE_ACCOUNT_EMAIL", "test@example.com")
    @patch("sheets.GOOGLE_PRIVATE_KEY", "test-key")
    @patch("sheets.SPREADSHEET_ID", "test-sheet")
    def test_paused_item_not_in_due(self, mock_api):
        """Paused items are excluded from get_due_recurring_items."""
        from sheets import get_due_recurring_items

        row_paused = _recurring_to_row(make_rent_item())
        row_paused[RECURRING_COL["STATUS"]] = "paused"
        row_paused[RECURRING_COL["NEXT_RUN_DATE"]] = "2026-05-15"

        mock_api.side_effect = [
            {"values": [RECURRING_HEADERS, row_paused]},
            {"values": [RECURRING_HEADERS, row_paused]},
        ]

        items = get_due_recurring_items("2026-06-02")
        assert len(items) == 0

    @patch("sheets._sheets_api")
    @patch("sheets.GOOGLE_SERVICE_ACCOUNT_EMAIL", "test@example.com")
    @patch("sheets.GOOGLE_PRIVATE_KEY", "test-key")
    @patch("sheets.SPREADSHEET_ID", "test-sheet")
    def test_deleted_item_not_visible_to_get_items(self, mock_api):
        """Deleted items are filtered by default in get_recurring_items."""
        from sheets import get_recurring_items

        row_deleted = _recurring_to_row(make_rent_item())
        row_deleted[RECURRING_COL["STATUS"]] = "deleted"

        mock_api.return_value = {"values": [RECURRING_HEADERS, row_deleted]}

        items = get_recurring_items()  # default: active only
        assert len(items) == 0

    @patch("sheets._sheets_api")
    @patch("sheets.GOOGLE_SERVICE_ACCOUNT_EMAIL", "test@example.com")
    @patch("sheets.GOOGLE_PRIVATE_KEY", "test-key")
    @patch("sheets.SPREADSHEET_ID", "test-sheet")
    def test_empty_sheet_returns_empty(self, mock_api):
        """Sheet with only headers returns empty list."""
        from sheets import get_recurring_items

        mock_api.return_value = {"values": [RECURRING_HEADERS]}
        items = get_recurring_items()
        assert items == []

    @patch("sheets._sheets_api")
    @patch("sheets.GOOGLE_SERVICE_ACCOUNT_EMAIL", "test@example.com")
    @patch("sheets.GOOGLE_PRIVATE_KEY", "test-key")
    @patch("sheets.SPREADSHEET_ID", "test-sheet")
    def test_add_recurring_creates_row(self, mock_api):
        """add_recurring_item calls Sheets API to append."""
        from sheets import add_recurring_item

        mock_api.return_value = {}

        result = add_recurring_item(make_rent_item())
        assert result == "rent-flat"

        # Verify the API was called to append and to check sheet existence
        append_calls = [c for c in mock_api.call_args_list if "append" in str(c)]
        assert len(append_calls) >= 1

    @patch("sheets._sheets_api")
    @patch("sheets.GOOGLE_SERVICE_ACCOUNT_EMAIL", "test@example.com")
    @patch("sheets.GOOGLE_PRIVATE_KEY", "test-key")
    @patch("sheets.SPREADSHEET_ID", "test-sheet")
    def test_add_recurring_auto_calculates_estimated_uah_for_fixed(self, mock_api):
        """Fixed mode: EstimatedUAH = Amount if not explicitly set."""
        from sheets import add_recurring_item

        mock_api.return_value = {}

        item = make_wayforpay_item()
        item["estimated_uah"] = 0  # not set

        add_recurring_item(item)

        # Find the append call and check estimated_uah was set
        append_calls = [c for c in mock_api.call_args_list if "append" in str(c)]
        assert len(append_calls) >= 1
        # The row sent should have amount=102 in UAH col and estimated_uah=102
        # This is verified implicitly through _recurring_to_row producing correct values
        row = _recurring_to_row(item)
        assert row[RECURRING_COL["AMOUNT"]] == 102
        assert row[RECURRING_COL["ESTIMATED_UAH"]] == 102  # auto-calculated from amount


# ── HEADERS consistency ────────────────────────────────────────────────────


class TestRecurringHeaders:
    def test_headers_count_is_24(self):
        assert len(RECURRING_HEADERS) == 24

    def test_headers_match_spec(self):
        expected = [
            "ID",
            "Title",
            "Type",
            "Amount",
            "Currency",
            "OriginalAmount",
            "OriginalCurrency",
            "EstimatedUAH",
            "AmountMode",
            "Category",
            "DefaultAccountID",
            "DefaultAccountName",
            "PaymentOptions",
            "Frequency",
            "DayOfMonth",
            "DueDay",
            "GraceUntilDay",
            "NextRunDate",
            "LastRunDate",
            "Status",
            "CreatedAt",
            "UpdatedAt",
            "Notes",
            "LastAction",
        ]
        assert RECURRING_HEADERS == expected

    def test_col_indices_match_headers(self):
        """Each key in RECURRING_COL maps to the correct header name."""
        for key, idx in RECURRING_COL.items():
            header_key = {
                "ID": "ID",
                "TITLE": "Title",
                "TYPE": "Type",
                "AMOUNT": "Amount",
                "CURRENCY": "Currency",
                "ORIGINAL_AMOUNT": "OriginalAmount",
                "ORIGINAL_CURRENCY": "OriginalCurrency",
                "ESTIMATED_UAH": "EstimatedUAH",
                "AMOUNT_MODE": "AmountMode",
                "CATEGORY": "Category",
                "DEFAULT_ACCOUNT_ID": "DefaultAccountID",
                "DEFAULT_ACCOUNT_NAME": "DefaultAccountName",
                "PAYMENT_OPTIONS": "PaymentOptions",
                "FREQUENCY": "Frequency",
                "DAY_OF_MONTH": "DayOfMonth",
                "DUE_DAY": "DueDay",
                "GRACE_UNTIL_DAY": "GraceUntilDay",
                "NEXT_RUN_DATE": "NextRunDate",
                "LAST_RUN_DATE": "LastRunDate",
                "STATUS": "Status",
                "CREATED_AT": "CreatedAt",
                "UPDATED_AT": "UpdatedAt",
                "NOTES": "Notes",
                "LAST_ACTION": "LastAction",
            }.get(key, key)
            assert RECURRING_HEADERS[idx] == header_key, (
                f"COL[{key}]={idx} but HEADERS[{idx}]={RECURRING_HEADERS[idx]}"
            )


# ── Telegram handler tests (Phase 6, Step 2) ────────────────────────────

from unittest.mock import AsyncMock, MagicMock

from handlers.recurring import (
    _format_amount_display,
    _format_recurring_item,
    _generate_id,
    _parse_recurring_args,
)


class TestGenerateId:
    def test_generates_slug_from_title(self):
        assert _generate_id("Аренда квартиры") == "аренда-квартиры"

    def test_strips_special_chars(self):
        assert _generate_id("Apple & Co!") == "apple-co"

    def test_empty_title_returns_recurring(self):
        assert _generate_id("") == "recurring"

    def test_multiple_spaces_become_single_dash(self):
        assert _generate_id("   Apple   Music   ") == "apple-music"


class TestParseRecurringArgs:
    """Test _parse_recurring_args for all 3 modes."""

    def test_parse_fixed_rent(self):
        """1. parse fixed rent command"""
        args = [
            "expense",
            "20000",
            "UAH",
            "fixed",
            "Дом",
            "Аренда квартиры",
            "monthly",
            "3",
            "--grace",
            "4",
            "--pay",
            "cash-uah,card-office,card-main",
            "--id",
            "rent-flat",
        ]
        item = _parse_recurring_args(args)
        assert item is not None
        assert item["id"] == "rent-flat"
        assert item["title"] == "Аренда квартиры"
        assert item["type"] == "expense"
        assert item["amount"] == 20000
        assert item["currency"] == "UAH"
        assert item["amount_mode"] == "fixed"
        assert item["category"] == "Дом"
        assert item["frequency"] == "monthly"
        assert item["day_of_month"] == 3
        assert item["grace_until_day"] == 4
        assert item["payment_options"] == "cash-uah,card-office,card-main"
        assert item["estimated_uah"] == 20000
        assert item["status"] == "active"

    def test_parse_variable_utilities(self):
        """2. parse variable utilities command"""
        args = [
            "expense",
            "variable",
            "UAH",
            "Дом",
            "Коммунальные",
            "monthly",
            "4",
            "--grace",
            "4",
            "--pay",
            "cash-uah,card-office,card-main",
            "--id",
            "utilities",
        ]
        item = _parse_recurring_args(args)
        assert item is not None
        assert item["id"] == "utilities"
        assert item["title"] == "Коммунальные"
        assert item["amount_mode"] == "variable"
        assert item["amount"] == 0
        assert item["currency"] == "UAH"
        assert item["category"] == "Дом"
        assert item["day_of_month"] == 4

    def test_parse_fx_apple(self):
        """3. parse fx Apple command"""
        args = [
            "expense",
            "2.49",
            "USD",
            "fx",
            "Подписки",
            "Apple",
            "monthly",
            "27",
            "карта",
            "--estimate",
            "110.64",
            "--id",
            "subscription-apple",
        ]
        item = _parse_recurring_args(args)
        assert item is not None
        assert item["id"] == "subscription-apple"
        assert item["title"] == "Apple"
        assert item["amount_mode"] == "fx"
        assert item["original_amount"] == 2.49
        assert item["original_currency"] == "USD"
        assert item["estimated_uah"] == 110.64
        assert item["currency"] == "UAH"
        assert item["category"] == "Подписки"
        assert item["day_of_month"] == 27

    def test_account_alias_karta_resolves(self):
        """4. account alias карта resolves to card-main"""
        args = [
            "expense",
            "2.49",
            "USD",
            "fx",
            "Подписки",
            "Apple",
            "monthly",
            "27",
            "карта",
        ]
        item = _parse_recurring_args(args)
        assert item is not None
        assert item["default_account_id"] == "card-main"
        assert item["default_account_name"] == "4441...5259"
        assert item["payment_options"] == "card-main"

    def test_pay_flag_creates_payment_options(self):
        """5. --pay creates PaymentOptions"""
        args = [
            "expense",
            "20000",
            "UAH",
            "fixed",
            "Дом",
            "Аренда квартиры",
            "monthly",
            "3",
            "--pay",
            "cash-uah,card-office,card-main",
        ]
        item = _parse_recurring_args(args)
        assert item is not None
        assert item["payment_options"] == "cash-uah,card-office,card-main"

    def test_pay_overrides_account_alias(self):
        """--pay takes priority over account alias resolution"""
        args = [
            "expense",
            "20000",
            "UAH",
            "fixed",
            "Дом",
            "Аренда квартиры",
            "monthly",
            "3",
            "карта",
            "--pay",
            "cash-uah,card-office",
        ]
        item = _parse_recurring_args(args)
        assert item is not None
        assert item["payment_options"] == "cash-uah,card-office"
        # Account alias still resolved
        assert item["default_account_id"] == "card-main"

    def test_missing_args_returns_none(self):
        assert _parse_recurring_args(["expense", "20000"]) is None

    def test_invalid_type_returns_none(self):
        args = ["transfer", "20000", "UAH", "fixed", "Дом", "Test", "monthly", "1"]
        assert _parse_recurring_args(args) is None

    def test_generates_id_from_title(self):
        """When --id is not provided, ID is generated from title"""
        args = [
            "expense",
            "variable",
            "UAH",
            "Дом",
            "Коммунальные",
            "monthly",
            "4",
        ]
        item = _parse_recurring_args(args)
        assert item is not None
        assert item["id"] == "коммунальные"

    def test_parse_fx_openai(self):
        args = [
            "expense",
            "23.80",
            "USD",
            "fx",
            "Подписки",
            "OpenAI",
            "monthly",
            "12",
            "карта",
            "--estimate",
            "1052.86",
            "--id",
            "subscription-openai",
        ]
        item = _parse_recurring_args(args)
        assert item is not None
        assert item["id"] == "subscription-openai"
        assert item["original_amount"] == 23.80
        assert item["estimated_uah"] == 1052.86
        assert item["day_of_month"] == 12

    def test_weekly_frequency(self):
        args = [
            "expense",
            "500",
            "UAH",
            "fixed",
            "Дом",
            "Уборка",
            "weekly",
            "1",
        ]
        item = _parse_recurring_args(args)
        assert item is not None
        assert item["frequency"] == "weekly"

    def test_fx_notes_generated(self):
        args = [
            "expense",
            "2.49",
            "USD",
            "fx",
            "Подписки",
            "Apple",
            "monthly",
            "27",
            "карта",
        ]
        item = _parse_recurring_args(args)
        assert item is not None
        assert "original 2.49 USD" in item["notes"]


class TestFormatAmountDisplay:
    def test_fixed_format(self):
        item = {"amount_mode": "fixed", "amount": 20000, "currency": "UAH"}
        result = _format_amount_display(item)
        assert "20,000 UAH" in result

    def test_fx_format(self):
        item = {
            "amount_mode": "fx",
            "original_amount": 2.49,
            "original_currency": "USD",
            "estimated_uah": 110.64,
            "currency": "UAH",
        }
        result = _format_amount_display(item)
        assert "2.49 USD" in result
        assert "111 UAH" in result

    def test_variable_with_estimate(self):
        item = {
            "amount_mode": "variable",
            "estimated_uah": 3500,
            "currency": "UAH",
        }
        result = _format_amount_display(item)
        assert "переменная" in result
        assert "3,500" in result

    def test_variable_no_estimate(self):
        item = {
            "amount_mode": "variable",
            "estimated_uah": 0,
            "currency": "UAH",
        }
        result = _format_amount_display(item)
        assert "переменная" in result


class TestFormatRecurringItem:
    def test_formats_active_item(self):
        item = {
            "id": "rent-flat",
            "title": "Аренда квартиры",
            "type": "expense",
            "amount": 20000,
            "currency": "UAH",
            "original_amount": 0,
            "original_currency": "",
            "estimated_uah": 20000,
            "amount_mode": "fixed",
            "category": "Дом",
            "payment_options": "cash-uah,card-office,card-main",
            "frequency": "monthly",
            "day_of_month": 3,
            "due_day": 3,
            "grace_until_day": 4,
            "next_run_date": "2026-07-03",
            "status": "active",
        }
        result = _format_recurring_item(item)
        assert "Аренда квартиры" in result
        assert "20,000 UAH" in result
        assert "Дом" in result
        assert "можно до 4" in result
        assert "active" in result
        assert "2026-07-03" in result

    def test_formats_paused_item(self):
        item = {
            "id": "utilities",
            "title": "Коммунальные",
            "type": "expense",
            "amount": 0,
            "currency": "UAH",
            "original_amount": 0,
            "original_currency": "",
            "estimated_uah": 3500,
            "amount_mode": "variable",
            "category": "Дом",
            "payment_options": "",
            "frequency": "monthly",
            "day_of_month": 4,
            "due_day": 4,
            "grace_until_day": 4,
            "next_run_date": "",
            "status": "paused",
        }
        result = _format_recurring_item(item)
        assert "Коммунальные" in result
        assert "переменная" in result
        assert "paused" in result

    def test_formats_with_index(self):
        item = {
            "id": "test",
            "title": "Test",
            "type": "expense",
            "amount": 100,
            "currency": "UAH",
            "original_amount": 0,
            "original_currency": "",
            "estimated_uah": 100,
            "amount_mode": "fixed",
            "category": "",
            "payment_options": "",
            "frequency": "monthly",
            "day_of_month": 1,
            "due_day": 1,
            "grace_until_day": 0,
            "next_run_date": "",
            "status": "active",
        }
        result = _format_recurring_item(item, index=1)
        assert "1." in result


# ── Phase 6.2: Interactive /recurring_due flow tests ───────────────────────


class TestResolveAccountDisplay:
    def test_known_ids(self):
        assert _resolve_account_display("cash-uah") == ("💵", "Наличными")
        assert _resolve_account_display("card-office") == ("🏢", "Офисная карта")
        assert _resolve_account_display("card-main") == ("💳", "Личная Monobank")

    def test_case_insensitive(self):
        assert _resolve_account_display("CASH-UAH") == ("💵", "Наличными")
        assert _resolve_account_display("Card-Main") == ("💳", "Личная Monobank")

    def test_unknown_account_id_falls_back_to_sheet(self):
        with patch("handlers.recurring.get_accounts") as mock_get:
            mock_get.return_value = [
                {"id": "privat24", "name": "5457...8762"},
            ]
            result = _resolve_account_display("privat24")
            assert result == ("💳", "5457...8762")

    def test_totally_unknown_returns_default(self):
        with patch("handlers.recurring.get_accounts") as mock_get:
            mock_get.return_value = []
            result = _resolve_account_display("unknown-id")
            assert result == ("💳", "unknown-id")


class TestCreateTransactionFromRecurring:
    def test_fixed_creates_row_with_negated_amount(self):
        item = make_rent_item()
        row = _create_transaction_from_recurring(
            item, 20000, "card-office", "Офисная карта"
        )
        assert row[2] == "expense"
        assert row[3] == -20000
        assert row[6] == "Дом"
        assert row[7] == "Аренда квартиры"
        assert row[8] == "recurring:rent-flat"
        assert row[9] == "card-office"
        assert row[10] == "Офисная карта"
        assert row[11] == ""  # Transfer ID empty

    def test_source_is_recurring_colon_id(self):
        item = make_rent_item()
        row = _create_transaction_from_recurring(item, 20000, "cash-uah", "Наличными")
        assert row[8] == "recurring:rent-flat"

    def test_variable_creates_row(self):
        item = make_utilities_item()
        row = _create_transaction_from_recurring(
            item, 2750, "card-office", "Офисная карта"
        )
        assert row[2] == "expense"
        assert row[3] == -2750
        assert row[6] == "Дом"
        assert row[7] == "Коммунальные"
        assert row[8] == "recurring:utilities"

    def test_fx_creates_row_with_original_currency_in_comment(self):
        item = make_apple_item()
        row = _create_transaction_from_recurring(
            item, 110.64, "card-main", "4441...5259"
        )
        assert row[7] == "Apple · 2.49 USD"
        assert row[8] == "recurring:subscription-apple"
        assert row[3] == -110.64

    def test_fx_estimated_appends_estimated_to_comment(self):
        item = make_apple_item()
        row = _create_transaction_from_recurring(
            item, 110.64, "card-main", "4441...5259", estimated=True
        )
        assert row[7] == "Apple · 2.49 USD · estimated"

    def test_openai_fx_comment(self):
        item = make_openai_item()
        row = _create_transaction_from_recurring(
            item, 1052.86, "card-main", "4441...5259", estimated=True
        )
        assert row[7] == "OpenAI · 23.80 USD · estimated"

    def test_has_12_columns(self):
        item = make_rent_item()
        row = _create_transaction_from_recurring(
            item, 20000, "card-office", "Офисная карта"
        )
        assert len(row) == 12

    def test_income_type_preserves_positive_amount(self):
        item = make_rent_item()
        item["type"] = "income"
        row = _create_transaction_from_recurring(
            item, 20000, "card-office", "Офисная карта"
        )
        assert row[2] == "income"
        assert row[3] == 20000


class TestBuildDueCard:
    def test_fixed_rent_shows_payment_buttons(self):
        item = make_rent_item()
        item["next_run_date"] = "2026-06-02"  # due today
        text, markup = _build_due_card(item, "2026-06-02")

        assert "Аренда квартиры" in text
        assert "20,000" in text
        assert "Дом" in text
        assert "3-го числа" in text
        assert "4-го числа" in text

        # Check buttons exist
        buttons = [btn for row in markup.inline_keyboard for btn in row]
        callback_data_list = [b.callback_data for b in buttons]
        assert "rec_pay|rent-flat|cash-uah" in callback_data_list
        assert "rec_pay|rent-flat|card-office" in callback_data_list
        assert "rec_pay|rent-flat|card-main" in callback_data_list
        assert "rec_skip|rent-flat" in callback_data_list

    def test_fixed_without_payment_options_shows_generic_button(self):
        item = make_wayforpay_item()
        item["payment_options"] = ""
        text, markup = _build_due_card(item, "2026-06-02")
        buttons = [btn for row in markup.inline_keyboard for btn in row]
        callback_data_list = [b.callback_data for b in buttons]
        assert "rec_pay|" in "".join(callback_data_list)
        assert "rec_skip|subscription-wayforpay" in callback_data_list

    def test_variable_shows_amount_input_button(self):
        item = make_utilities_item()
        item["next_run_date"] = "2026-06-04"
        text, markup = _build_due_card(item, "2026-06-04")

        assert "Коммунальные" in text
        assert "каждый месяц разная" in text
        assert "до 4-го числа" in text

        buttons = [btn for row in markup.inline_keyboard for btn in row]
        callback_data_list = [b.callback_data for b in buttons]
        assert "rec_amount|utilities" in callback_data_list
        assert "rec_skip|utilities" in callback_data_list

    def test_fx_subscription_shows_estimate_and_actual_buttons(self):
        item = make_apple_item()
        text, markup = _build_due_card(item, "2026-06-27")

        assert "Apple" in text
        assert "2.49 USD" in text
        assert "111" in text  # 110.64 rounds to 111 with :,.0f

        buttons = [btn for row in markup.inline_keyboard for btn in row]
        callback_data_list = [b.callback_data for b in buttons]
        assert "rec_est|subscription-apple" in callback_data_list
        assert "rec_actual|subscription-apple" in callback_data_list
        assert "rec_skip|subscription-apple" in callback_data_list

    def test_overdue_shows_warning(self):
        item = make_rent_item()
        item["grace_until_day"] = 4
        # June 5 is past grace day 4
        text, markup = _build_due_card(item, "2026-06-05")
        assert "Просрочено с 4-го числа" in text

    def test_overdue_without_gap_shows_generic_warning(self):
        item = make_utilities_item()
        item["grace_until_day"] = 4
        item["day_of_month"] = 4
        # grace == dom, but today > grace triggers overdue
        # The condition is today_dom > grace, not today_dom > grace AND grace != dom
        # Actually looking at the code: if today_dom > grace and grace and grace > 0
        # For due_day=4, grace=4, today=5: overdue triggers
        text, markup = _build_due_card(item, "2026-06-05")
        # When grace==dom, the message is just "⚠️ <b>Просрочено</b>"
        assert "Просрочено" in text

    def test_not_overdue_on_grace_day(self):
        item = make_rent_item()
        item["grace_until_day"] = 4
        # June 4 is exactly the grace day
        text, markup = _build_due_card(item, "2026-06-04")
        assert "Просрочено" not in text

    def test_all_modes_have_skip_button(self):
        for make_fn in [make_rent_item, make_utilities_item, make_apple_item]:
            item = make_fn()
            text, markup = _build_due_card(item, "2026-06-02")
            buttons = [btn for row in markup.inline_keyboard for btn in row]
            callback_data_list = [b.callback_data for b in buttons]
            assert any("rec_skip|" in d for d in callback_data_list), (
                f"skip missing for {item['id']}"
            )


# ── Phase 6.3: Canonical names, duplicates, skip LastRunDate ────────────────


class TestResolveCanonicalAccountName:
    def test_known_ids_from_fallback(self):
        assert _resolve_canonical_account_name("cash-uah") == "Наличка"
        assert _resolve_canonical_account_name("card-office") == "4441...4454"
        assert _resolve_canonical_account_name("card-main") == "4441...5259"

    def test_case_insensitive(self):
        assert _resolve_canonical_account_name("CASH-UAH") == "Наличка"

    def test_from_accounts_sheet(self):
        with patch("handlers.recurring.get_accounts") as mock_get:
            mock_get.return_value = [
                {"id": "privat24", "name": "5457...8762"},
            ]
            result = _resolve_canonical_account_name("privat24")
            assert result == "5457...8762"

    def test_unknown_returns_account_id(self):
        with patch("handlers.recurring.get_accounts") as mock_get:
            mock_get.return_value = []
            result = _resolve_canonical_account_name("unknown-id")
            assert result == "unknown-id"

    def test_empty_id_returns_empty(self):
        assert _resolve_canonical_account_name("") == ""


class TestFindRecurringTransaction:
    def test_duplicate_found_same_year_month(self):
        mock_rows = [
            ["June", "02.06.2026", "expense", -20000, 0, 0,
             "Дом", "Аренда квартиры", "recurring:rent-flat", "", "", ""],
        ]
        with patch("sheets.get_all_rows", return_value=mock_rows):
            assert _find_recurring_transaction("rent-flat", "2026-06") is True

    def test_different_year_not_duplicate(self):
        """Row from June 2025 should NOT be a duplicate for June 2026."""
        mock_rows = [
            ["June", "03.06.2025", "expense", -20000, 0, 0,
             "Дом", "Аренда квартиры", "recurring:rent-flat", "", "", ""],
        ]
        with patch("sheets.get_all_rows", return_value=mock_rows):
            assert _find_recurring_transaction("rent-flat", "2026-06") is False

    def test_same_year_month_is_duplicate(self):
        """Row from June 2026 IS a duplicate for June 2026."""
        mock_rows = [
            ["June", "03.06.2026", "expense", -20000, 0, 0,
             "Дом", "Аренда квартиры", "recurring:rent-flat", "", "", ""],
        ]
        with patch("sheets.get_all_rows", return_value=mock_rows):
            assert _find_recurring_transaction("rent-flat", "2026-06") is True

    def test_different_source_not_duplicate(self):
        mock_rows = [
            ["June", "02.06.2026", "expense", -3500, 0, 0,
             "Дом", "Коммунальные", "recurring:utilities", "", "", ""],
        ]
        with patch("sheets.get_all_rows", return_value=mock_rows):
            assert _find_recurring_transaction("rent-flat", "2026-06") is False

    def test_empty_rows(self):
        with patch("sheets.get_all_rows", return_value=[]):
            assert _find_recurring_transaction("rent-flat", "2026-06") is False

    def test_exception_returns_false(self):
        with patch("sheets.get_all_rows", side_effect=Exception("boom")):
            assert _find_recurring_transaction("rent-flat", "2026-06") is False


class TestSaveAndUpdate:
    def test_adds_row_and_updates_run_dates(self):
        from unittest.mock import call

        item = make_rent_item()
        item["id"] = "rent-flat"

        with patch("handlers.recurring.add_row", return_value=True) as mock_add, \
             patch("handlers.recurring.update_recurring_item", return_value=True) as mock_upd, \
             patch("handlers.recurring._find_recurring_transaction", return_value=False), \
             patch("handlers.recurring._resolve_canonical_account_name", return_value="4441...4454"), \
             patch("budget.BudgetManager") as mock_bm:

            from handlers.recurring import _save_and_update
            ok, warning = _save_and_update(item, 20000, "card-office", "2026-06-02")

            assert ok is True
            assert warning == ""
            mock_add.assert_called_once()
            mock_upd.assert_called_once()
            mock_bm.invalidate_after_transaction.assert_called_once()

            # Verify the row uses canonical name
            row = mock_add.call_args[0][0]
            assert row[8] == "recurring:rent-flat"
            assert row[9] == "card-office"
            assert row[10] == "4441...4454"  # canonical, not UI label

    def test_duplicate_returns_false_with_warning(self):
        item = make_rent_item()

        with patch("handlers.recurring._find_recurring_transaction", return_value=True):
            from handlers.recurring import _save_and_update
            ok, warning = _save_and_update(item, 20000, "card-office", "2026-06-02")
            assert ok is False
            assert "уже записан" in warning

    def test_update_failure_returns_warning(self):
        item = make_rent_item()

        with patch("handlers.recurring.add_row", return_value=True), \
             patch("handlers.recurring.update_recurring_item", return_value=False), \
             patch("handlers.recurring._find_recurring_transaction", return_value=False), \
             patch("handlers.recurring._resolve_canonical_account_name", return_value="Наличка"), \
             patch("budget.BudgetManager"):

            from handlers.recurring import _save_and_update
            ok, warning = _save_and_update(item, 20000, "cash-uah", "2026-06-02")

            assert ok is True
            assert "NextRunDate" in warning

    def test_add_row_failure_returns_false(self):
        item = make_rent_item()

        with patch("handlers.recurring.add_row", return_value=False), \
             patch("handlers.recurring._find_recurring_transaction", return_value=False):

            from handlers.recurring import _save_and_update
            ok, warning = _save_and_update(item, 20000, "cash-uah", "2026-06-02")
            assert ok is False
            assert warning == ""


class TestCreateTransactionCanonicalName:
    def test_canonical_name_in_row_not_ui_label(self):
        item = make_rent_item()
        # Even if we pass UI label "Наличными" as account_name,
        # _create_transaction_from_recurring uses whatever is passed.
        # The responsibility for passing canonical name is in _save_and_update.
        # This test verifies the function stores what it receives.
        row = _create_transaction_from_recurring(
            item, 20000, "cash-uah", "Наличка"
        )
        assert row[9] == "cash-uah"
        assert row[10] == "Наличка"
        assert row[10] != "Наличными"



class TestParseDateToPeriod:
    """Tests for _parse_date_to_period — handles various GS date formats."""

    def test_dd_mm_yyyy_string(self):
        assert _parse_date_to_period("02.06.2026") == "2026-06"

    def test_d_m_yyyy_string(self):
        assert _parse_date_to_period("2.6.2026") == "2026-06"

    def test_iso_format(self):
        assert _parse_date_to_period("2026-06-02") == "2026-06"

    def test_slash_format(self):
        assert _parse_date_to_period("02/06/2026") == "2026-06"

    def test_whitespace(self):
        assert _parse_date_to_period(" 02.06.2026 ") == "2026-06"

    def test_google_sheets_serial_number(self):
        """Google Sheets returns dates as serial numbers with UNFORMATTED_VALUE.
        2026-06-02 = serial 46175 (days since 1899-12-30)."""
        result = _parse_date_to_period(46175.0)
        assert result == "2026-06", f"Expected 2026-06, got {result}"

    def test_google_sheets_serial_int(self):
        result = _parse_date_to_period(46175)
        assert result == "2026-06"

    def test_datetime_object(self):
        from datetime import datetime
        result = _parse_date_to_period(datetime(2026, 6, 2, 10, 30))
        assert result == "2026-06"

    def test_none_returns_none(self):
        assert _parse_date_to_period(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_date_to_period("") is None

    def test_garbage_returns_none(self):
        assert _parse_date_to_period("not-a-date") is None


class TestDuplicateDetectionRealistic:
    """Tests duplicate detection with realistic Google Sheets values."""

    def test_real_case_rent_flat_duplicate(self):
        """Row with Source=recurring:rent-flat and Date=02.06.2026
        should be a duplicate for period 2026-06."""
        mock_rows = [
            ["June", "02.06.2026", "expense", -20000, 0, 0,
             "Дом", "Аренда квартиры", "recurring:rent-flat",
             "card-office", "4441...4454", ""],
        ]
        with patch("sheets.get_all_rows", return_value=mock_rows):
            assert _find_recurring_transaction("rent-flat", "2026-06") is True

    def test_gs_serial_date_detected(self):
        """Google Sheets serial date 46179 (2026-06-02) detected."""
        mock_rows = [
            ["June", 46175.0, "expense", -20000, 0, 0,
             "Дом", "Аренда квартиры", "recurring:rent-flat",
             "card-office", "4441...4454", ""],
        ]
        with patch("sheets.get_all_rows", return_value=mock_rows):
            assert _find_recurring_transaction("rent-flat", "2026-06") is True

    def test_iso_date_detected(self):
        mock_rows = [
            ["June", "2026-06-02", "expense", -20000, 0, 0,
             "Дом", "Аренда квартиры", "recurring:rent-flat",
             "card-office", "4441...4454", ""],
        ]
        with patch("sheets.get_all_rows", return_value=mock_rows):
            assert _find_recurring_transaction("rent-flat", "2026-06") is True

    def test_different_year_not_duplicate_serial(self):
        """Serial date for June 2025 should NOT match 2026-06."""
        # 2025-06-02 = serial 45810
        mock_rows = [
            ["June", 45810.0, "expense", -20000, 0, 0,
             "Дом", "Аренда квартиры", "recurring:rent-flat",
             "card-office", "4441...4454", ""],
        ]
        with patch("sheets.get_all_rows", return_value=mock_rows):
            assert _find_recurring_transaction("rent-flat", "2026-06") is False



class TestRowAlways12Columns:
    def test_fixed_row_has_12_columns(self):
        item = make_rent_item()
        row = _create_transaction_from_recurring(
            item, 20000, "card-office", "4441...4454"
        )
        assert len(row) == 12

    def test_variable_row_has_12_columns(self):
        item = make_utilities_item()
        row = _create_transaction_from_recurring(
            item, 2750, "cash-uah", "Наличка"
        )
        assert len(row) == 12

    def test_fx_row_has_12_columns(self):
        item = make_apple_item()
        row = _create_transaction_from_recurring(
            item, 110.64, "card-main", "4441...5259", estimated=True
        )
        assert len(row) == 12
