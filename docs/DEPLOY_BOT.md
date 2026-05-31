# Деплой бота на fly.io

## Установка flyctl

```bash
# macOS
brew install flyctl

# Или:
curl -L https://fly.io/install.sh | sh
```

## Регистрация и вход

```bash
fly auth signup   # или fly auth login если уже зарегистрирован
```

## Первый деплой

```bash
cd ~/Documents/FinancialTracker

# Создай приложение (fly.toml уже есть, fly launch подхватит настройки)
fly launch --name kesha-finance-bot

# Добавь секреты
fly secrets set BOT_TOKEN=твой_токен
fly secrets set SPREADSHEET_ID=id_таблицы
fly secrets set GOOGLE_SERVICE_ACCOUNT_EMAIL=email
fly secrets set GOOGLE_PRIVATE_KEY="ключ"
fly secrets set MONOBANK_X_TOKEN=токен

# При необходимости — валюта
fly secrets set PRIMARY_CURRENCY=UAH
fly secrets set CURRENCIES="UAH,USD,EUR,USDT"

# Деплой
fly deploy
```

## Обновление после правок

```bash
git push
fly deploy
```

## Полезные команды

```bash
fly logs          # логи в реальном времени
fly status        # статус приложения
fly secrets list  # список переменных (значения скрыты)
fly ssh console   # зайти внутрь VM
fly restart       # перезапустить приложение
```

## Важно

- Бот использует **polling**, а не webhook — внешний порт не нужен
- Сервисный порт 8080 указан в fly.toml для health checks, бот его не слушает
- При старте `load_dotenv()` не найдёт `.env` файл (его нет в Docker-образе) и молча упадёт — `os.getenv()` подхватит переменные из fly secrets
- Бесплатный лимит: 3 shared‑cpu VM по 256 MB RAM
- Регион `ams` (Амстердам) — минимальная задержка для Украины
