"""Google Sheets client via raw HTTP (no google-api-python-client).

Uses only google-auth (JWT) + httpx. Saves ~50MB RAM vs googleapiclient.
All existing functions keep identical signatures and behaviour.
"""

from __future__ import annotations

import calendar
import json
import time
import uuid
from datetime import datetime, timezone

import httpx
from config import GOOGLE_PRIVATE_KEY, GOOGLE_SERVICE_ACCOUNT_EMAIL, SPREADSHEET_ID
from google.auth.transport.requests import Request
from google.oauth2 import service_account

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TOKEN_URI = "https://oauth2.googleapis.com/token"

# ------------------------------------------------------------------
# Lightweight Sheets HTTP client
# ------------------------------------------------------------------

_client: httpx.Client | None = None
_token: str | None = None
_token_expiry: float = 0.0


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    return _client


def _get_token() -> str | None:
    global _token, _token_expiry
    if _token and time.time() < _token_expiry - 60:
        return _token

    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY:
        return None

    try:
        creds = service_account.Credentials.from_service_account_info(
            {
                "type": "service_account",
                "client_email": GOOGLE_SERVICE_ACCOUNT_EMAIL,
                "private_key": GOOGLE_PRIVATE_KEY,
                "token_uri": TOKEN_URI,
            },
            scopes=SCOPES,
        )
        creds.refresh(Request())
        _token = creds.token
        _token_expiry = time.time() + 3500  # 1h minus buffer
        return _token
    except Exception:
        return None


def _sheets_api(method: str, path: str, body: dict | None = None) -> dict:
    """Make a Google Sheets API v4 request. Returns parsed JSON dict."""
    token = _get_token()
    if not token:
        raise RuntimeError("No Google credentials")

    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    client = _get_client()
    if method == "GET":
        resp = client.get(url, headers=headers)
    elif method == "POST":
        resp = client.post(
            url, headers=headers, content=json.dumps(body) if body else None
        )
    elif method == "PUT":
        resp = client.put(
            url, headers=headers, content=json.dumps(body) if body else None
        )
    else:
        raise ValueError(f"Unknown method: {method}")

    if not resp.is_success:
        raise RuntimeError(
            f"Sheets API {method} {path}: {resp.status_code} {resp.text[:200]}"
        )

    return resp.json()


# ------------------------------------------------------------------
# Public API (same signatures as before)
# ------------------------------------------------------------------

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
    "ACCOUNT_ID": 9,
    "ACCOUNT_NAME": 10,
    "TRANSFER_ID": 11,
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
    "Account ID",
    "Account Name",
    "Transfer ID",
]


def get_all_rows():
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return []
    try:
        result = _sheets_api(
            "GET",
            "/values/Transactions!A:L?valueRenderOption=UNFORMATTED_VALUE",
        )
        values = result.get("values", [])
        return values[1:] if len(values) > 1 else []
    except Exception:
        return []


def add_row(row_data):
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return False
    try:
        num_cols = len(row_data)
        col_letter = chr(ord("A") + num_cols - 1) if num_cols <= 26 else "L"
        _sheets_api(
            "POST",
            f"/values/Transactions!A:{col_letter}:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
            {"values": [row_data]},
        )
        return True
    except Exception as e:
        print(f"Sheets error: {e}")
        return False


def delete_row_by_index(row_index: int) -> bool:
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY:
        return False
    sheet_id = _get_sheet_id("Transactions")
    if sheet_id is None:
        return False
    try:
        _sheets_api(
            "POST",
            ":batchUpdate",
            {
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
        )
        return True
    except Exception:
        return False


def delete_last_row():
    rows = get_all_rows()
    if not rows:
        return False
    last_row_num = len(rows) + 1
    return delete_row_by_index(last_row_num - 1)


def update_row_category(row_index: int, new_category: str) -> bool:
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY:
        return False
    try:
        _sheets_api(
            "PUT",
            f"/values/Transactions!G{row_index + 1}?valueInputOption=RAW",
            {"values": [[new_category]]},
        )
        return True
    except Exception as e:
        print(f"Failed to update row category: {e}")
        return False


def find_row_by_source(source: str) -> int | None:
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return None
    try:
        result = _sheets_api(
            "GET", "/values/Transactions!A:L?valueRenderOption=UNFORMATTED_VALUE"
        )
        values = result.get("values", [])
        for i, row in enumerate(values[1:], start=2):
            if len(row) > COL["SOURCE"] and str(row[COL["SOURCE"]]) == source:
                return i
        return None
    except Exception:
        return None


def get_existing_source_keys() -> set[str]:
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return set()
    try:
        result = _sheets_api(
            "GET", "/values/Transactions!I:I?valueRenderOption=UNFORMATTED_VALUE"
        )
        values = result.get("values", [])
        return {str(row[0]) for row in values[1:] if row}
    except Exception:
        return set()


def get_last_mono_timestamp() -> int | None:
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


def get_budget_rows():
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return []
    try:
        result = _sheets_api(
            "GET", "/values/Budgets!A:D?valueRenderOption=UNFORMATTED_VALUE"
        )
        values = result.get("values", [])
        if not values or len(values) <= 1:
            return []
        rows = []
        for row in values[1:]:
            rows.append(
                {
                    "month": str(row[0]) if len(row) > 0 else "",
                    "category": str(row[1]) if len(row) > 1 else "",
                    "limit": float(row[2]) if len(row) > 2 and row[2] else 0.0,
                    "type": str(row[3]) if len(row) > 3 else "",
                }
            )
        return rows
    except Exception:
        return []


def upsert_budget_row(month: str, category: str, limit: float, type_: str) -> bool:
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return False
    try:
        _ensure_sheet("Budgets", BUDGET_HEADERS)
        existing = get_budget_rows()
        row_idx = None
        for i, r in enumerate(existing):
            if r["month"] == month and r["category"] == category and r["type"] == type_:
                row_idx = i + 2
                break
        row_data = [month, category, limit, type_]
        if row_idx:
            _sheets_api(
                "PUT",
                f"/values/Budgets!A{row_idx}:D{row_idx}?valueInputOption=RAW",
                {"values": [row_data]},
            )
        else:
            _sheets_api(
                "POST",
                "/values/Budgets!A:D:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
                {"values": [row_data]},
            )
        return True
    except Exception:
        return False


def delete_budget_row(month: str, category: str, type_: str = "") -> bool:
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY:
        return False
    try:
        result = _sheets_api(
            "GET", "/values/Budgets!A:D?valueRenderOption=UNFORMATTED_VALUE"
        )
        values = result.get("values", [])
        target = None
        for i, row in enumerate(values, start=1):
            if len(row) < 3:
                continue
            if (
                str(row[0]) == month
                and str(row[1]) == category
                and (len(row) < 4 or str(row[3]) == type_)
            ):
                target = i
                break
        if not target:
            return False
        sheet_id = _get_sheet_id("Budgets")
        if sheet_id is None:
            return False
        _sheets_api(
            "POST",
            ":batchUpdate",
            {
                "requests": [
                    {
                        "deleteDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": target - 1,
                                "endIndex": target,
                            }
                        }
                    }
                ]
            },
        )
        return True
    except Exception:
        return False


def get_categories_spending(month: str = "") -> dict[str, float]:
    """Sum expenses per category for a given month (format: YYYY-MM)."""
    rows = get_all_rows()
    if not rows:
        return {}

    month_name = ""
    if month:
        try:
            parts = month.split("-")
            month_num = int(parts[1])
            month_name = calendar.month_name[month_num]
        except (IndexError, ValueError):
            pass

    spending: dict[str, float] = {}
    for r in rows:
        if len(r) <= max(COL["MONTH"], COL["CATEGORY"], COL["AMOUNT_UAH"], COL["TYPE"]):
            continue
        row_month = str(r[COL["MONTH"]] or "").strip()
        row_type = str(r[COL["TYPE"]] or "").strip().lower()
        row_cat = str(r[COL["CATEGORY"]] or "").strip()
        if row_type != "expense":
            continue
        # Exclude transfers (bounds-safe — Google Sheets may trim trailing empty columns)
        if (
            len(r) > COL["TRANSFER_ID"]
            and r[COL["TRANSFER_ID"]]
            and str(r[COL["TRANSFER_ID"]]).strip()
        ):
            continue
        if month_name and row_month != month_name:
            continue
        try:
            amount = float(r[COL["AMOUNT_UAH"]]) if r[COL["AMOUNT_UAH"]] else 0
        except (ValueError, TypeError):
            continue
        spending[row_cat] = spending.get(row_cat, 0.0) + abs(amount)
    return spending


def get_balance():
    """Calculate total balance per currency from all transactions."""
    rows = get_all_rows()
    balance = {"UAH": 0.0, "USD": 0.0, "EUR": 0.0}
    currency_cols = [
        ("UAH", COL["AMOUNT_UAH"]),
        ("USD", COL["AMOUNT_USD"]),
        ("EUR", COL["AMOUNT_EUR"]),
    ]
    for r in rows:
        if len(r) <= COL["AMOUNT_EUR"]:
            continue
        t = str(r[COL["TYPE"]]).strip().lower() if len(r) > COL["TYPE"] else ""
        if t not in ("income", "expense"):
            continue
        sign = 1 if t == "income" else -1
        for cur, col in currency_cols:
            if len(r) > col and r[col] and str(r[col]).strip():
                try:
                    balance[cur] += sign * abs(float(r[col]))
                except (ValueError, IndexError):
                    pass
    return balance


# ────────────────────────────── Categories sheet ──────────────────────────────


def get_custom_categories(type_filter: str | None = None) -> list[tuple[str, str]]:
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return []
    try:
        result = _sheets_api(
            "GET", "/values/Categories!A:B?valueRenderOption=UNFORMATTED_VALUE"
        )
        values = result.get("values", [])
        categories = []
        for row in values[1:]:
            if len(row) < 2:
                continue
            t = str(row[0]).strip().lower()
            name = str(row[1]).strip()
            if type_filter and t != type_filter:
                continue
            categories.append((t, name))
        return categories
    except Exception:
        return []


def add_custom_category(type_: str, name: str) -> bool:
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return False
    try:
        _ensure_sheet("Categories", ["Type", "Name"])
        _sheets_api(
            "POST",
            "/values/Categories!A:B:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
            {"values": [[type_, name]]},
        )
        return True
    except Exception:
        return False


# ────────────────────────────── Settings sheet ──────────────────────────────


def get_settings_rows() -> list[tuple[str, str]]:
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return []
    try:
        result = _sheets_api(
            "GET", "/values/Settings!A:B?valueRenderOption=UNFORMATTED_VALUE"
        )
        values = result.get("values", [])
        return [(str(r[0]), str(r[1]) if len(r) > 1 else "") for r in values[1:] if r]
    except Exception:
        return []


def upsert_setting(key: str, value: str) -> bool:
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return False
    try:
        _ensure_sheet("Settings", ["Key", "Value"])
        existing = get_settings_rows()
        row_idx = None
        for i, (k, v) in enumerate(existing):
            if k == key:
                row_idx = i + 2
                break
        row_data = [key, value]
        if row_idx:
            _sheets_api(
                "PUT",
                f"/values/Settings!A{row_idx}:B{row_idx}?valueInputOption=RAW",
                {"values": [row_data]},
            )
        else:
            _sheets_api(
                "POST",
                "/values/Settings!A:B:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
                {"values": [row_data]},
            )
        return True
    except Exception:
        return False


def delete_setting(key: str) -> bool:
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY:
        return False
    try:
        result = _sheets_api(
            "GET", "/values/Settings!A:A?valueRenderOption=UNFORMATTED_VALUE"
        )
        values = result.get("values", [])
        target = None
        for i, row in enumerate(values, start=1):
            if row and str(row[0]).strip() == key:
                target = i
                break
        if not target:
            return False
        sheet_id = _get_sheet_id("Settings")
        if sheet_id is None:
            return False
        _sheets_api(
            "POST",
            ":batchUpdate",
            {
                "requests": [
                    {
                        "deleteDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": target - 1,
                                "endIndex": target,
                            }
                        }
                    }
                ]
            },
        )
        return True
    except Exception:
        return False


# ────────────────────────────── Internal helpers ──────────────────────────────


def _get_sheet_id(sheet_name: str) -> int | None:
    """Get the internal sheet ID (gid) for a named sheet."""
    try:
        result = _sheets_api("GET", "")
        sheets = result.get("sheets", [])
        for s in sheets:
            props = s.get("properties", {})
            if props.get("title") == sheet_name:
                return props.get("sheetId")
        return None
    except Exception:
        return None


def _ensure_sheet(sheet_name: str, headers: list[str]) -> None:
    """Create sheet with headers if it doesn't exist."""
    sheet_id = _get_sheet_id(sheet_name)
    if sheet_id is not None:
        return
    try:
        _sheets_api(
            "POST",
            ":batchUpdate",
            {"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]},
        )
    except Exception:
        pass
    # Write headers
    try:
        _sheets_api(
            "PUT",
            f"/values/{sheet_name}!A1?valueInputOption=RAW",
            {"values": [headers]},
        )
    except Exception:
        pass


# ── Accounts sheet (manual accounts registry) ──────────────────────────────

ACCOUNTS_HEADERS = [
    "ID",
    "Name",
    "Type",
    "Currency",
    "Balance",
    "Source",
    "Active",
    "CreatedAt",
    "UpdatedAt",
]

# ── Recurring sheet ───────────────────────────────────────────────────────

RECURRING_HEADERS = [
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


def get_accounts() -> list[dict]:
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return []
    try:
        result = _sheets_api(
            "GET",
            "/values/Accounts!A:I?valueRenderOption=UNFORMATTED_VALUE",
        )
        values = result.get("values", [])
        accounts = []
        for row in values[1:]:
            if not row or not any(row):
                continue
            accounts.append(
                {
                    "id": str(row[0]).strip() if len(row) > 0 else "",
                    "name": str(row[1]).strip() if len(row) > 1 else "",
                    "type": str(row[2]).strip() if len(row) > 2 else "",
                    "currency": str(row[3]).strip().upper() if len(row) > 3 else "UAH",
                    "balance": float(row[4]) if len(row) > 4 and row[4] else 0.0,
                    "source": str(row[5]).strip() if len(row) > 5 else "manual",
                    "active": str(row[6]).strip().lower() != "false"
                    if len(row) > 6
                    else True,
                    "created_at": str(row[7]).strip() if len(row) > 7 else "",
                    "updated_at": str(row[8]).strip() if len(row) > 8 else "",
                }
            )
        return accounts
    except Exception:
        return []


def upsert_account(
    name: str,
    acc_type: str = "bank",
    currency: str = "UAH",
    balance: float = 0.0,
    source: str = "manual",
    active: bool = True,
    account_id: str | None = None,
) -> bool:
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return False
    try:
        _ensure_sheet("Accounts", ACCOUNTS_HEADERS)
        existing = get_accounts()
        now_str = datetime.now().isoformat(timespec="seconds")

        row_idx = None
        if account_id is not None:
            for i, acc in enumerate(existing):
                if acc["id"].lower() == account_id.lower():
                    row_idx = i + 2
                    break
        else:
            for i, acc in enumerate(existing):
                if acc["name"].lower() == name.lower():
                    row_idx = i + 2
                    break

        acc_id = account_id
        if row_idx:
            acc_id = existing[row_idx - 2].get("id", "") or account_id
        if not acc_id:
            acc_id = uuid.uuid4().hex[:8]

        row_data = [
            acc_id,
            name,
            acc_type,
            currency,
            balance,
            source,
            str(active).lower(),
            existing[row_idx - 2]["created_at"] if row_idx else now_str,
            now_str,
        ]

        if row_idx:
            _sheets_api(
                "PUT",
                f"/values/Accounts!A{row_idx}:I{row_idx}?valueInputOption=RAW",
                {"values": [row_data]},
            )
        else:
            _sheets_api(
                "POST",
                "/values/Accounts!A:I:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
                {"values": [row_data]},
            )
        return True
    except Exception as e:
        print(f"upsert_account error: {e}")
        return False


def delete_account(name: str) -> bool:
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY:
        return False
    try:
        result = _sheets_api(
            "GET", "/values/Accounts!A:A?valueRenderOption=UNFORMATTED_VALUE"
        )
        values = result.get("values", [])
        target = None
        all_rows = _sheets_api(
            "GET", "/values/Accounts!A:B?valueRenderOption=UNFORMATTED_VALUE"
        ).get("values", [])
        for i, row in enumerate(all_rows, start=1):
            if row and len(row) > 1 and str(row[1]).strip().lower() == name.lower():
                target = i
                break
        if not target:
            return False
        sheet_id = _get_sheet_id("Accounts")
        if sheet_id is None:
            return False
        _sheets_api(
            "POST",
            ":batchUpdate",
            {
                "requests": [
                    {
                        "deleteDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": target - 1,
                                "endIndex": target,
                            }
                        }
                    }
                ]
            },
        )
        return True
    except Exception as e:
        print(f"delete_account error: {e}")
        return False


# ── Transfer support (two linked rows) ─────────────────────────────────────


def get_account_balances() -> list[dict]:
    """Calculate per-account balances: starting balance + all transactions.

    Returns list of dicts with keys: name, currency, starting_balance,
    income, expense, balance, transaction_count, active.
    Includes a synthetic "Без счета" entry for transactions without accounts.
    """
    accounts = {a["name"]: a for a in get_accounts() if a["active"]}
    rows = get_all_rows()

    result: dict[str, dict] = {}

    for name, acc in accounts.items():
        result[name] = {
            "name": name,
            "currency": acc.get("currency", "UAH"),
            "starting_balance": acc.get("balance", 0.0),
            "income": 0.0,
            "expense": 0.0,
            "balance": acc.get("balance", 0.0),
            "transaction_count": 0,
            "active": True,
        }

    result["Без счета"] = {
        "name": "Без счета",
        "currency": "UAH",
        "starting_balance": 0.0,
        "income": 0.0,
        "expense": 0.0,
        "balance": 0.0,
        "transaction_count": 0,
        "active": True,
    }

    for r in rows:
        if len(r) <= COL["TYPE"]:
            continue
        t = str(r[COL["TYPE"]]).strip().lower()
        if t not in ("income", "expense"):
            continue

        amount_uah = 0.0
        if (
            len(r) > COL["AMOUNT_UAH"]
            and r[COL["AMOUNT_UAH"]]
            and str(r[COL["AMOUNT_UAH"]]).strip()
        ):
            try:
                amount_uah = float(r[COL["AMOUNT_UAH"]])
            except (ValueError, IndexError):
                pass

        account_name = _resolve_account_from_row(r)

        entry = result.get(account_name) if account_name else None
        if entry is None and account_name:
            name_lower = account_name.lower()
            for key in result:
                if key.lower() == name_lower:
                    entry = result[key]
                    break
        if entry is None:
            entry = result["Без счета"]

        entry["transaction_count"] += 1
        if t == "income":
            entry["income"] += abs(amount_uah)
            entry["balance"] += abs(amount_uah)
        else:
            entry["expense"] += abs(amount_uah)
            entry["balance"] -= abs(amount_uah)

    return [
        v
        for v in result.values()
        if v["transaction_count"] > 0 or v["name"] != "Без счета"
    ]


def _resolve_account_from_row(row: list) -> str | None:
    """Resolve canonical account name from a transaction row.

    Priority:
      1. AccountID (col J) → lookup canonical name in Accounts sheet.
      2. AccountName (col K) → case-insensitive match in Accounts sheet.

    Returns the canonical name from Accounts, or the raw name as fallback.
    """
    # Priority 1: AccountID → canonical name
    if len(row) > COL["ACCOUNT_ID"] and row[COL["ACCOUNT_ID"]]:
        acc_id = str(row[COL["ACCOUNT_ID"]]).strip()
        if acc_id:
            accounts = get_accounts()
            for acc in accounts:
                if acc.get("id") == acc_id:
                    return acc["name"]

    # Priority 2: AccountName → case-insensitive lookup
    if len(row) > COL["ACCOUNT_NAME"] and row[COL["ACCOUNT_NAME"]]:
        raw_name = str(row[COL["ACCOUNT_NAME"]]).strip()
        if raw_name:
            accounts = get_accounts()
            name_lower = raw_name.lower()
            for acc in accounts:
                if acc["name"].lower() == name_lower:
                    return acc["name"]
            # No canonical match — return raw name as fallback
            return raw_name

    return None


def add_transfer_rows(outflow_row: list, inflow_row: list, transfer_id: str) -> bool:
    """Write two linked rows for a transfer between accounts.

    Both rows share the same TransferID so balance remains neutral.
    """
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return False
    try:
        _sheets_api(
            "POST",
            "/values/Transactions!A:L:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
            {"values": [outflow_row, inflow_row]},
        )
        return True
    except Exception as e:
        print(f"add_transfer_rows error: {e}")
        return False


# ── Rules sheet (auto-categorization rules) ────────────────────────────────


def get_rules() -> list[dict]:
    """Read all rules from Rules sheet.

    Columns: Pattern | Category | Type | Priority
    Returns list of dicts with keys: pattern, category, type, priority.
    """
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return []
    try:
        result = _sheets_api(
            "GET",
            "/values/Rules!A:D?valueRenderOption=UNFORMATTED_VALUE",
        )
        values = result.get("values", [])
        rules = []
        for i, row in enumerate(values):
            if i == 0:
                continue  # skip header
            if not row or not any(row):
                continue
            pattern = str(row[0]).strip() if len(row) > 0 and row[0] else ""
            category = str(row[1]).strip() if len(row) > 1 and row[1] else ""
            rule_type = str(row[2]).strip() if len(row) > 2 and row[2] else "expense"
            try:
                priority = int(row[3]) if len(row) > 3 and row[3] else 10
            except (ValueError, TypeError):
                priority = 10
            if pattern and category:
                rules.append(
                    {
                        "pattern": pattern,
                        "category": category,
                        "type": rule_type,
                        "priority": priority,
                        "row_index": i + 1,  # 1-based sheets row
                    }
                )
        return rules
    except Exception:
        return []


def add_rule(
    pattern: str, category: str, rule_type: str = "expense", priority: int = 10
) -> bool:
    """Add a rule to Rules sheet."""
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return False
    try:
        _ensure_sheet("Rules", ["Pattern", "Category", "Type", "Priority"])
        _sheets_api(
            "POST",
            "/values/Rules!A:D:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
            {"values": [[pattern, category, rule_type, priority]]},
        )
        return True
    except Exception:
        return False


def delete_rule(pattern: str) -> int:
    """Delete all rules matching pattern. Returns count of deleted rules."""
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return 0
    rules = get_rules()
    pattern_lower = pattern.strip().lower()
    to_delete = [r for r in rules if r["pattern"].lower() == pattern_lower]

    if not to_delete:
        return 0

    # Get sheet ID for batch delete
    sheet_id = _get_sheet_id("Rules")
    if sheet_id is None:
        return 0

    # Sort rows descending so deletion doesn't shift indices
    sorted_rows = sorted([r["row_index"] for r in to_delete], reverse=True)

    requests = [
        {
            "deleteDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": row - 1,
                    "endIndex": row,
                }
            }
        }
        for row in sorted_rows
    ]

    try:
        _sheets_api("POST", ":batchUpdate", {"requests": requests})
        return len(to_delete)
    except Exception:
        return 0


# ── Recurring sheet (recurring payments & subscriptions) ───────────────────

RECURRING_COL = {
    "ID": 0,
    "TITLE": 1,
    "TYPE": 2,
    "AMOUNT": 3,
    "CURRENCY": 4,
    "ORIGINAL_AMOUNT": 5,
    "ORIGINAL_CURRENCY": 6,
    "ESTIMATED_UAH": 7,
    "AMOUNT_MODE": 8,
    "CATEGORY": 9,
    "DEFAULT_ACCOUNT_ID": 10,
    "DEFAULT_ACCOUNT_NAME": 11,
    "PAYMENT_OPTIONS": 12,
    "FREQUENCY": 13,
    "DAY_OF_MONTH": 14,
    "DUE_DAY": 15,
    "GRACE_UNTIL_DAY": 16,
    "NEXT_RUN_DATE": 17,
    "LAST_RUN_DATE": 18,
    "STATUS": 19,
    "CREATED_AT": 20,
    "UPDATED_AT": 21,
    "NOTES": 22,
    "LAST_ACTION": 23,
}

_VALID_TYPES = {"expense", "income"}
_VALID_CURRENCIES = {"UAH", "USD", "EUR", "USDT"}
_VALID_AMOUNT_MODES = {"fixed", "variable", "fx"}
_VALID_FREQUENCIES = {"monthly", "weekly", "daily"}
_VALID_STATUSES = {"active", "paused", "deleted"}


def _parse_recurring_row(row: list) -> dict | None:
    """Parse a raw sheets row into a recurring item dict."""
    if not row or not any(row):
        return None

    def _str(col):
        return str(row[col]).strip() if len(row) > col and row[col] else ""

    def _float(col):
        if len(row) > col and row[col]:
            try:
                return float(row[col])
            except (ValueError, TypeError):
                return 0.0
        return 0.0

    def _int(col):
        if len(row) > col and row[col]:
            try:
                return int(row[col])
            except (ValueError, TypeError):
                return 0
        return 0

    return {
        "id": _str(RECURRING_COL["ID"]),
        "title": _str(RECURRING_COL["TITLE"]),
        "type": _str(RECURRING_COL["TYPE"]),
        "amount": _float(RECURRING_COL["AMOUNT"]),
        "currency": _str(RECURRING_COL["CURRENCY"]),
        "original_amount": _float(RECURRING_COL["ORIGINAL_AMOUNT"]),
        "original_currency": _str(RECURRING_COL["ORIGINAL_CURRENCY"]),
        "estimated_uah": _float(RECURRING_COL["ESTIMATED_UAH"]),
        "amount_mode": _str(RECURRING_COL["AMOUNT_MODE"]),
        "category": _str(RECURRING_COL["CATEGORY"]),
        "default_account_id": _str(RECURRING_COL["DEFAULT_ACCOUNT_ID"]),
        "default_account_name": _str(RECURRING_COL["DEFAULT_ACCOUNT_NAME"]),
        "payment_options": _str(RECURRING_COL["PAYMENT_OPTIONS"]),
        "frequency": _str(RECURRING_COL["FREQUENCY"]),
        "day_of_month": _int(RECURRING_COL["DAY_OF_MONTH"]),
        "due_day": _int(RECURRING_COL["DUE_DAY"]),
        "grace_until_day": _int(RECURRING_COL["GRACE_UNTIL_DAY"]),
        "next_run_date": _str(RECURRING_COL["NEXT_RUN_DATE"]),
        "last_run_date": _str(RECURRING_COL["LAST_RUN_DATE"]),
        "status": _str(RECURRING_COL["STATUS"]),
        "created_at": _str(RECURRING_COL["CREATED_AT"]),
        "updated_at": _str(RECURRING_COL["UPDATED_AT"]),
        "notes": _str(RECURRING_COL["NOTES"]),
        "last_action": _str(RECURRING_COL["LAST_ACTION"]),
    }


def _recurring_to_row(item: dict) -> list:
    """Convert a recurring item dict to a sheets row."""
    return [
        item.get("id", ""),
        item.get("title", ""),
        item.get("type", "expense"),
        item.get("amount", 0),
        item.get("currency", "UAH"),
        item.get("original_amount", 0),
        item.get("original_currency", ""),
        item.get("estimated_uah", 0),
        item.get("amount_mode", "fixed"),
        item.get("category", ""),
        item.get("default_account_id", ""),
        item.get("default_account_name", ""),
        item.get("payment_options", ""),
        item.get("frequency", "monthly"),
        item.get("day_of_month", 1),
        item.get("due_day", 1),
        item.get("grace_until_day", ""),
        item.get("next_run_date", ""),
        item.get("last_run_date", ""),
        item.get("status", "active"),
        item.get("created_at", ""),
        item.get("updated_at", ""),
        item.get("notes", ""),
        item.get("last_action", ""),
    ]


def _validate_recurring(item: dict) -> list[str]:
    """Validate a recurring item. Returns list of error messages (empty = valid)."""
    errors = []

    if not item.get("title", "").strip():
        errors.append("Title is required")

    item_type = item.get("type", "")
    if item_type not in _VALID_TYPES:
        errors.append(f"Type must be one of: {', '.join(sorted(_VALID_TYPES))}")

    currency = item.get("currency", "")
    if currency not in _VALID_CURRENCIES:
        errors.append(
            f"Currency must be one of: {', '.join(sorted(_VALID_CURRENCIES))}"
        )

    original_currency = item.get("original_currency", "")
    if original_currency and original_currency not in _VALID_CURRENCIES:
        errors.append(
            f"OriginalCurrency must be one of: {', '.join(sorted(_VALID_CURRENCIES))}"
        )

    amount_mode = item.get("amount_mode", "")
    if amount_mode not in _VALID_AMOUNT_MODES:
        errors.append(
            f"AmountMode must be one of: {', '.join(sorted(_VALID_AMOUNT_MODES))}"
        )

    frequency = item.get("frequency", "")
    if frequency not in _VALID_FREQUENCIES:
        errors.append(
            f"Frequency must be one of: {', '.join(sorted(_VALID_FREQUENCIES))}"
        )

    status = item.get("status", "active")
    if status not in _VALID_STATUSES:
        errors.append(f"Status must be one of: {', '.join(sorted(_VALID_STATUSES))}")

    dom = item.get("day_of_month", 0)
    if not isinstance(dom, int) or dom < 1 or dom > 31:
        errors.append("DayOfMonth must be 1-31")

    if amount_mode == "fx":
        if not item.get("original_amount", 0):
            errors.append("fx mode requires OriginalAmount > 0")
        if not item.get("original_currency", ""):
            errors.append("fx mode requires OriginalCurrency")
        if item.get("original_currency", "") == "UAH":
            errors.append("fx mode: OriginalCurrency must not be UAH")

    if amount_mode == "fixed":
        if not item.get("amount", 0):
            errors.append("fixed mode requires Amount > 0")
        if item.get("currency", "UAH") != "UAH":
            errors.append("fixed mode requires Currency = UAH")

    if amount_mode == "variable":
        if item.get("currency", "UAH") != "UAH":
            errors.append("variable mode requires Currency = UAH")

    return errors


def get_recurring_items(status_filter: str | None = "active") -> list[dict]:
    """Read all recurring items, optionally filtered by status.

    Pass None to get all items including deleted.
    """
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return []
    try:
        result = _sheets_api(
            "GET",
            "/values/Recurring!A:X?valueRenderOption=UNFORMATTED_VALUE",
        )
        values = result.get("values", [])
        if len(values) <= 1:
            return []

        items = []
        for row in values[1:]:
            item = _parse_recurring_row(row)
            if item is None:
                continue
            if status_filter is not None and item["status"] != status_filter:
                continue
            items.append(item)
        return items
    except Exception:
        return []


def get_recurring_item(item_id: str) -> dict | None:
    """Get a single recurring item by ID."""
    items = get_recurring_items(status_filter=None)
    item_id_lower = item_id.strip().lower()
    for item in items:
        if item["id"].lower() == item_id_lower:
            return item
    return None


def _find_recurring_row_index(item_id: str) -> int | None:
    """Find the sheets row index (1-based) for a recurring item by ID."""
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return None
    try:
        result = _sheets_api(
            "GET",
            "/values/Recurring!A:X?valueRenderOption=UNFORMATTED_VALUE",
        )
        values = result.get("values", [])
        item_id_lower = item_id.strip().lower()
        for i, row in enumerate(values):
            if i == 0:
                continue
            if not row or not any(row):
                continue
            row_id = str(row[0]).strip() if len(row) > 0 and row[0] else ""
            if row_id.lower() == item_id_lower:
                return i + 1  # 1-based
        return None
    except Exception:
        return None


def add_recurring_item(item: dict) -> str | None:
    """Add a new recurring item. Returns the item ID on success, None on failure."""
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return None

    errors = _validate_recurring(item)
    if errors:
        print(f"Recurring validation errors: {'; '.join(errors)}")
        return None

    try:
        _ensure_sheet("Recurring", RECURRING_HEADERS)

        now_str = datetime.now().strftime("%Y-%m-%d")
        item.setdefault("created_at", now_str)
        item.setdefault("updated_at", now_str)

        # Auto-calculate EstimatedUAH for fixed mode
        if item.get("amount_mode") == "fixed" and not item.get("estimated_uah"):
            item["estimated_uah"] = item.get("amount", 0)

        # Set DueDay = DayOfMonth if not specified
        if not item.get("due_day"):
            item["due_day"] = item.get("day_of_month", 1)

        row = _recurring_to_row(item)
        _sheets_api(
            "POST",
            "/values/Recurring!A:X:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
            {"values": [row]},
        )
        return item.get("id", "")
    except Exception as e:
        print(f"add_recurring_item error: {e}")
        return None


def update_recurring_item(item_id: str, updates: dict) -> bool:
    """Update specific fields of a recurring item."""
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY or not SPREADSHEET_ID:
        return False

    row_idx = _find_recurring_row_index(item_id)
    if row_idx is None:
        return False

    existing = get_recurring_item(item_id)
    if existing is None:
        return False

    merged = dict(existing)
    merged.update(updates)
    merged["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    merged["id"] = existing["id"]  # preserve ID

    errors = _validate_recurring(merged)
    if errors:
        print(f"Recurring validation errors: {'; '.join(errors)}")
        return False

    try:
        row = _recurring_to_row(merged)
        _sheets_api(
            "PUT",
            f"/values/Recurring!A{row_idx}:X{row_idx}?valueInputOption=RAW",
            {"values": [row]},
        )
        return True
    except Exception as e:
        print(f"update_recurring_item error: {e}")
        return False


def _update_recurring_status(item_id: str, new_status: str) -> bool:
    """Internal helper to change status of a recurring item."""
    return update_recurring_item(item_id, {"status": new_status})


def mark_recurring_deleted(item_id: str) -> bool:
    """Soft-delete a recurring item (Status = deleted)."""
    return _update_recurring_status(item_id, "deleted")


def pause_recurring_item(item_id: str) -> bool:
    """Pause a recurring item (Status = paused)."""
    return _update_recurring_status(item_id, "paused")


def resume_recurring_item(item_id: str) -> bool:
    """Resume a paused recurring item (Status = active)."""
    return _update_recurring_status(item_id, "active")


def get_due_recurring_items(today: str | None = None) -> list[dict]:
    """Get active recurring items due on or before today.

    An item is due if:
      - Status = active
      - NextRunDate <= today (or NextRunDate is empty/not set)

    Args:
        today: Date string in YYYY-MM-DD format. Defaults to today.
    """
    if today is None:
        today = datetime.now().strftime("%Y-%m-%d")

    active_items = get_recurring_items(status_filter="active")

    due = []
    for item in active_items:
        next_date = item.get("next_run_date", "")
        if not next_date:
            due.append(item)
        elif next_date <= today:
            due.append(item)

    return due


def calculate_next_run_date(
    current_date: str,
    frequency: str,
    day_of_month: int | None = None,
) -> str:
    """Calculate the next run date based on frequency.

    Args:
        current_date: Starting date as YYYY-MM-DD.
        frequency: 'monthly', 'weekly', or 'daily'.
        day_of_month: For monthly, the target day (1-31).

    Returns:
        Next date as YYYY-MM-DD.
    """
    from calendar import monthrange
    from datetime import timedelta

    try:
        dt = datetime.strptime(current_date, "%Y-%m-%d")
    except ValueError:
        dt = datetime.now()

    if frequency == "daily":
        next_dt = dt + timedelta(days=1)
    elif frequency == "weekly":
        next_dt = dt + timedelta(days=7)
    elif frequency == "monthly":
        target_day = day_of_month or dt.day
        year = dt.year
        month = dt.month + 1
        if month > 12:
            month = 1
            year += 1

        # Clamp day to last day of the target month
        last_day = monthrange(year, month)[1]
        actual_day = min(target_day, last_day)

        next_dt = datetime(year, month, actual_day)
    else:
        next_dt = dt + timedelta(days=1)

    return next_dt.strftime("%Y-%m-%d")


def calculate_initial_next_run_date(
    today: str,
    frequency: str,
    day_of_month: int | None = None,
) -> str:
    """Calculate the first NextRunDate when creating a recurring item.

    Returns the earliest date >= today that matches the frequency pattern.
    For monthly: if target day in current month >= today, use current month;
    otherwise advance to next month. Clamps to last day of month.
    For weekly/daily: today.

    Args:
        today: Today's date as YYYY-MM-DD.
        frequency: 'monthly', 'weekly', or 'daily'.
        day_of_month: Target day for monthly frequency (1-31).

    Returns:
        Initial next run date as YYYY-MM-DD.
    """
    from calendar import monthrange
    from datetime import timedelta

    try:
        dt = datetime.strptime(today, "%Y-%m-%d")
    except ValueError:
        dt = datetime.now()

    if frequency == "daily":
        return today

    if frequency == "weekly":
        return today

    if frequency == "monthly":
        target_day = day_of_month or dt.day

        # Try current month first
        last_day = monthrange(dt.year, dt.month)[1]
        actual_day = min(target_day, last_day)
        candidate = datetime(dt.year, dt.month, actual_day)

        if candidate >= dt:
            return candidate.strftime("%Y-%m-%d")

        # Advance to next month
        year = dt.year
        month = dt.month + 1
        if month > 12:
            month = 1
            year += 1

        last_day = monthrange(year, month)[1]
        actual_day = min(target_day, last_day)
        next_dt = datetime(year, month, actual_day)
        return next_dt.strftime("%Y-%m-%d")

    # Unknown frequency — default to today
    return today


def update_recurring_run_dates(item_id: str, last_run: str, next_run: str) -> bool:
    """Update LastRunDate and NextRunDate after recording a transaction."""
    return update_recurring_item(
        item_id,
        {
            "last_run_date": last_run,
            "next_run_date": next_run,
            "last_action": f"recorded {last_run}",
        },
    )


# Backward compatibility alias
get_or_create_sheet = _ensure_sheet
