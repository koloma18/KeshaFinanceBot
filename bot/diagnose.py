import os
import sys

from dotenv import load_dotenv

load_dotenv()

print("=== Проверка .env ===")
token = os.getenv("BOT_TOKEN", "")
print(f"BOT_TOKEN: {'✅ есть' if token else '❌ нет'}")
email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL", "")
print(f"SERVICE_EMAIL: {'✅ ' + email if email else '❌ нет'}")
key = os.getenv("GOOGLE_PRIVATE_KEY", "")
print(f"PRIVATE_KEY: {'✅ есть (' + str(len(key)) + ' символов)' if key else '❌ нет'}")
sheet_id = os.getenv("SPREADSHEET_ID", "")
print(f"SPREADSHEET_ID: {'✅ ' + sheet_id if sheet_id else '❌ нет'}")

print("\n=== Проверка подключения к Google Sheets ===")
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

try:
    formatted_key = key.replace("\\n", "\n")
    creds = service_account.Credentials.from_service_account_info(
        {
            "type": "service_account",
            "client_email": email,
            "private_key": formatted_key,
            "token_uri": "https://oauth2.googleapis.com/token",
        },
        scopes=SCOPES,
    )
    service = build("sheets", "v4", credentials=creds)

    # Try to read the sheet
    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=sheet_id,
            range="Transactions!A1:I1",
        )
        .execute()
    )
    print("✅ Подключение к Sheets API успешно!")
    print(f"   Заголовки: {result.get('values', [['нет данных']])[0]}")

except HttpError as e:
    print(f"❌ Ошибка Google Sheets API: {e}")
    if "not enabled" in str(e) or "has not been used" in str(e):
        print("\n👉 ВКЛЮЧИ GOOGLE SHEETS API:")
        print(
            "   1. Открой: https://console.cloud.google.com/apis/library/sheets.googleapis.com"
        )
        print("   2. Выбери проект: my-ai-497617")
        print("   3. Нажми ENABLE")
    elif "permission" in str(e).lower():
        print("\n👉 Service account не имеет доступа к таблице")
        print("   Добавь в таблицу: Настройки доступа → кеш-financebot@... → Редактор")
except Exception as e:
    print(f"❌ Ошибка: {type(e).__name__}: {e}")
