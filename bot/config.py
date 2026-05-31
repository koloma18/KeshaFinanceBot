import os

# В Docker/fly.io переменные окружения уже установлены через secrets
# load_dotenv() нужен только для локального запуска с .env файлом
if not os.getenv("FLY_APP_NAME"):
    from dotenv import load_dotenv

    load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_SERVICE_ACCOUNT_EMAIL = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
GOOGLE_PRIVATE_KEY = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
MONOBANK_X_TOKEN = os.getenv("MONOBANK_X_TOKEN")
PRIMARY_CURRENCY = os.getenv("PRIMARY_CURRENCY", "UAH")
CURRENCIES = os.getenv("CURRENCIES", "UAH,USD,EUR,USDT").split(",")
