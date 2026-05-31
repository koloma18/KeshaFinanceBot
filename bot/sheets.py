import calendar
from datetime import datetime, timezone

from config import GOOGLE_PRIVATE_KEY, GOOGLE_SERVICE_ACCOUNT_EMAIL, SPREADSHEET_ID
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_service():
    """Returns Google Sheets service. Returns None on auth failure."""
    try:
        if (
            not GOOGLE_SERVICE_ACCOUNT_EMAIL
            or not GOOGLE_PRIVATE_KEY
            or not SPREADSHEET_ID
        ):
            return None
        creds = service_account.Credentials.from_service_account_info(
            {
                "type": "service_account",
                "client_email": GOOGLE_SERVICE_ACCOUNT_EMAIL,
                "private_key": GOOGLE_PRIVATE_KEY,
                "token_uri": "https://oauth2.googleapis.com/token",
            },
            scopes=SCOPES,
        )
        return build("sheets", "v4", credentials=creds)
    except Exception:
        return None


COL = {
    "MONTH": 0,
    "DATE": 1,
    "TYPE": 2,
    "AMOUNT_UAH": 3,
    "AMOUNT_USD": 4,
    "AMOUNT_EUR": 5,
    "CATEGORY": 6,
    "COMMENT": 7,
    "SOURCE": 8,
}
HEADERS = [
    "Month",
    "Date",
    "Type",
    "Amount UAH",
    "Amount USD",
    "Amount EUR",
    "Category",
    "AI Comment",
    "Source",
]


def get_all_rows():
    service = get_service()
    if not service:
        return []
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range="Transactions!A:I",
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )
        values = result.get("values", [])
        return values[1:] if len(values) > 1 else []
    except HttpError:
        return []
    except Exception:
        return []


def add_row(row_data):
    service = get_service()
    if not service:
        return False
    try:
        body = {"values": [row_data]}
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=SPREADSHEET_ID,
                range="Transactions!A:I",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )
        return True
    except HttpError as e:
        print(f"Google Sheets API error: {e}")
        return False
    except Exception as e:
        print(f"Unknown Sheets error: {e}")
        return False


def delete_row_by_index(row_index: int) -> bool:
    """Удалить строку по 1-based индексу.
    row_index=1 → первая строка после заголовка.
    Использует batchUpdate deleteDimension.
    """
    service = get_service()
    if not service:
        return False
    sheet_id = _get_sheet_id("Transactions")
    if sheet_id is None:
        return False
    try:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "requests": [
                    {
                        "deleteDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": row_index,
                                "endIndex": row_index + 1,
                            }
                        }
                    }
                ]
            },
        ).execute()
        return True
    except (HttpError, Exception):
        return False


def delete_last_row():
    rows = get_all_rows()
    if not rows:
        return False
    last_row_num = len(rows) + 1  # +1 for header
    service = get_service()
    if not service:
        return False
    sheet_id = _get_sheet_id("Transactions")
    if sheet_id is None:
        return False
    try:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "requests": [
                    {
                        "deleteDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": last_row_num - 1,
                                "endIndex": last_row_num,
                            }
                        }
                    }
                ]
            },
        ).execute()
        return True
    except (HttpError, Exception):
        return False


def update_row_category(row_index: int, new_category: str) -> bool:
    """Update category in a Transactions row by 1-based index.

    row_index: 1-based index of the data row (1 = first row after header).
    """
    service = get_service()
    if not service:
        return False
    try:
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"Transactions!G{row_index + 1}",
            valueInputOption="RAW",
            body={"values": [[new_category]]},
        ).execute()
        return True
    except Exception as e:
        print(f"Failed to update row category: {e}")
        return False


def find_row_by_source(source: str) -> int | None:
    """Search for a row by Source column value. Returns 1-based row index or None."""
    service = get_service()
    if not service:
        return None
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range="Transactions!A:I",
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )
        values = result.get("values", [])
        for i, row in enumerate(values[1:], start=2):  # skip header, 1-based
            if len(row) > COL["SOURCE"] and str(row[COL["SOURCE"]]) == source:
                return i
        return None
    except Exception:
        return None


def get_last_mono_timestamp() -> int | None:
    """Return max Unix timestamp among mono-sourced transactions, or None."""
    rows = get_all_rows()
    max_ts: int | None = None
    for r in rows:
        if len(r) <= max(COL["SOURCE"], COL["DATE"]):
            continue
        source = str(r[COL["SOURCE"]]) if r[COL["SOURCE"]] else ""
        if not source.startswith("mono:"):
            continue
        date_str = str(r[COL["DATE"]]) if r[COL["DATE"]] else ""
        if not date_str:
            continue
        try:
            dt = datetime.strptime(date_str, "%d.%m.%Y")
            ts = int(dt.replace(tzinfo=timezone.utc).timestamp())
            if max_ts is None or ts > max_ts:
                max_ts = ts
        except (ValueError, IndexError):
            continue
    return max_ts


# ────────────────────────────── Budgets sheet ──────────────────────────────

BUDGET_HEADERS = ["Month", "Category", "Limit", "Type"]
# Type: "budget" (общий бюджет) или "limit" (лимит категории)


def _get_sheet_id(sheet_name: str) -> int | None:
    """Get internal sheet ID by name or None if sheet doesn't exist."""
    service = get_service()
    if not service:
        return None
    try:
        meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        for s in meta.get("sheets", []):
            props = s.get("properties", {})
            if props.get("title") == sheet_name:
                return props.get("sheetId")
        return None
    except Exception:
        return None


def get_budget_rows() -> list[list]:
    """All rows from Budgets sheet (without header). Returns [] if sheet missing."""
    service = get_service()
    if not service:
        return []
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range="Budgets!A:D",
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )
        values = result.get("values", [])
        return values[1:] if len(values) > 1 else []
    except Exception:
        return []


def upsert_budget_row(
    month: str, category: str, limit_value: float, limit_type: str
) -> bool:
    """Add or update a row in Budgets.
    Searches by Month+Category+Type; if found updates Limit, otherwise appends.
    """
    service = get_service()
    if not service:
        return False
    get_or_create_sheet("Budgets", BUDGET_HEADERS)
    try:
        # Read existing rows with header
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range="Budgets!A:D",
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )
        all_rows = result.get("values", [])

        # Find matching row (1-based, including header)
        target_row = None
        for i, row in enumerate(all_rows, start=1):
            if len(row) >= 3:
                if row[0] == month and row[1] == category and row[3] == limit_type:
                    target_row = i
                    break

        if target_row:
            # Update existing row — rewrite Month, Category, Limit, Type
            body = {"values": [[month, category, limit_value, limit_type]]}
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"Budgets!A{target_row}:D{target_row}",
                valueInputOption="RAW",
                body=body,
            ).execute()
        else:
            # Append new row
            body = {"values": [[month, category, limit_value, limit_type]]}
            service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range="Budgets!A:D",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body,
            ).execute()
        return True
    except HttpError as e:
        print(f"Google Sheets API error (upsert): {e}")
        return False
    except Exception as e:
        print(f"Unknown error (upsert): {e}")
        return False


def delete_budget_row(month: str, category: str) -> bool:
    """Delete a row from Budgets by Month+Category.
    Returns True if deleted, False if not found or error.
    """
    service = get_service()
    if not service:
        return False
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range="Budgets!A:D",
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )
        all_rows = result.get("values", [])

        # Find matching row (1-based, including header)
        target_row = None
        for i, row in enumerate(all_rows, start=1):
            if len(row) >= 2 and row[0] == month and row[1] == category:
                target_row = i
                break

        if not target_row:
            return False

        sheet_id = _get_sheet_id("Budgets")
        if sheet_id is None:
            return False

        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "requests": [
                    {
                        "deleteDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": target_row - 1,
                                "endIndex": target_row,
                            }
                        }
                    }
                ]
            },
        ).execute()
        return True
    except HttpError as e:
        print(f"Google Sheets API error (delete): {e}")
        return False
    except Exception as e:
        print(f"Unknown error (delete): {e}")
        return False


def get_categories_spending(month: str) -> dict[str, float]:
    """Sum expenses per category for a given month.
    Month format: "YYYY-MM". Filters by month name and Type == "expense".
    Returns {category: total_spent_in_uah}.
    """
    rows = get_all_rows()
    if not rows:
        return {}

    # Convert "2026-06" to month name (e.g. "June")
    try:
        parts = month.split("-")
        month_num = int(parts[1])
        month_name = calendar.month_name[month_num]
    except (IndexError, ValueError):
        return {}

    spending: dict[str, float] = {}
    for r in rows:
        if len(r) <= max(COL["MONTH"], COL["CATEGORY"], COL["AMOUNT_UAH"], COL["TYPE"]):
            continue

        row_month = str(r[COL["MONTH"]] or "").strip()
        row_type = str(r[COL["TYPE"]] or "").strip().lower()
        row_cat = str(r[COL["CATEGORY"]] or "").strip()

        if row_type != "expense":
            continue
        if row_month != month_name:
            continue

        try:
            amount = float(r[COL["AMOUNT_UAH"]]) if r[COL["AMOUNT_UAH"]] else 0
        except (ValueError, TypeError):
            continue

        spending[row_cat] = spending.get(row_cat, 0.0) + amount

    return spending


def get_balance():
    rows = get_all_rows()
    balance = {"UAH": 0.0, "USD": 0.0, "EUR": 0.0}
    for r in rows:
        if len(r) <= max(COL["AMOUNT_EUR"], COL["TYPE"]):
            continue
        try:
            amount_uah = float(r[COL["AMOUNT_UAH"]]) if r[COL["AMOUNT_UAH"]] else 0
            amount_usd = float(r[COL["AMOUNT_USD"]]) if r[COL["AMOUNT_USD"]] else 0
            amount_eur = float(r[COL["AMOUNT_EUR"]]) if r[COL["AMOUNT_EUR"]] else 0
        except (ValueError, IndexError):
            continue
        t = str(r[COL["TYPE"]]).strip().lower() if len(r) > COL["TYPE"] else ""
        sign = 1 if t == "income" else -1
        balance["UAH"] += sign * amount_uah
        balance["USD"] += sign * amount_usd
        balance["EUR"] += sign * amount_eur
    return balance


# ────────────────────────────── Categories sheet ──────────────────────────────


def get_custom_categories(type_filter: str | None = None) -> list[tuple[str, str]]:
    """Get custom categories from Categories sheet.

    Returns list of (type, name) tuples.
    If type_filter is 'expense' or 'income', filters by type.
    """
    service = get_service()
    if not service:
        return []
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range="Categories!A:B",
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )
        values = result.get("values", [])
        rows = values[1:] if len(values) > 1 else []
        cats: list[tuple[str, str]] = []
        for r in rows:
            if len(r) >= 2:
                t = str(r[0]).strip().lower()
                name = str(r[1]).strip()
                if type_filter is None or t == type_filter:
                    cats.append((t, name))
        return cats
    except HttpError:
        return []
    except Exception:
        return []


def add_custom_category(cat_type: str, name: str) -> bool:
    """Add a custom category to the Categories sheet.

    cat_type: 'expense' or 'income'
    name: display name (should be normalised with capital first letter)
    """
    service = get_service()
    if not service:
        return False
    get_or_create_sheet("Categories", ["Type", "Name"])
    try:
        body = {"values": [[cat_type, name]]}
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Categories!A:B",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        return True
    except Exception:
        return False


# ────────────────────────────── Settings sheet ──────────────────────────────

SETTINGS_HEADERS = ["Key", "Value"]


def get_or_create_sheet(sheet_name: str, headers: list[str]) -> bool:
    """Ensure a sheet exists. If not, create it with headers row.

    Returns True if sheet already existed or was created successfully.
    """
    service = get_service()
    if not service:
        return False
    try:
        meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        for s in meta.get("sheets", []):
            if s.get("properties", {}).get("title") == sheet_name:
                return True

        # Sheet not found — create it
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]},
        ).execute()

        # Write headers
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            body={"values": [headers]},
        ).execute()
        return True
    except Exception:
        return False


def get_settings_rows() -> list[list]:
    """All rows from Settings sheet (without header). Returns [] if sheet missing."""
    service = get_service()
    if not service:
        return []
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range="Settings!A:B",
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )
        values = result.get("values", [])
        return values[1:] if len(values) > 1 else []
    except Exception:
        return []


def upsert_setting(key: str, value: str) -> bool:
    """Add or update a key-value pair in Settings sheet.

    Searches for existing key; updates if found, appends if new.
    """
    service = get_service()
    if not service:
        return False
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range="Settings!A:B",
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )
        all_rows = result.get("values", [])

        target_row = None
        for i, row in enumerate(all_rows, start=1):
            if len(row) >= 1 and str(row[0]).strip() == key:
                target_row = i
                break

        if target_row:
            body = {"values": [[key, value]]}
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"Settings!A{target_row}:B{target_row}",
                valueInputOption="RAW",
                body=body,
            ).execute()
        else:
            body = {"values": [[key, value]]}
            service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range="Settings!A:B",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body,
            ).execute()
        return True
    except Exception:
        return False


def delete_setting(key: str) -> bool:
    """Delete a setting row by key. Returns True if deleted, False if not found."""
    service = get_service()
    if not service:
        return False
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range="Settings!A:B",
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )
        all_rows = result.get("values", [])

        target_row = None
        for i, row in enumerate(all_rows, start=1):
            if len(row) >= 1 and str(row[0]).strip() == key:
                target_row = i
                break

        if not target_row:
            return False

        sheet_id = _get_sheet_id("Settings")
        if sheet_id is None:
            return False

        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "requests": [
                    {
                        "deleteDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": target_row - 1,
                                "endIndex": target_row,
                            }
                        }
                    }
                ]
            },
        ).execute()
        return True
    except Exception:
        return False
