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

## Ротация токенов

Если BOT_TOKEN скомпрометирован (утек в логи, git, скриншоты):

```bash
# 1. Сбрось токен в @BotFather: /mybots → выбрать бота → API Token → Revoke
# 2. Обнови секрет на fly.io:
fly secrets set BOT_TOKEN=новый_токен

# 3. Перезапусти бота:
fly restart
```

Бот подхватит новый токен при следующем запуске. Старый токен станет недействительным мгновенно.

## Логи и мониторинг

```bash
# Последние логи
fly logs

# Логи только ошибок (заменяет grep на стороне fly)
fly logs | grep -i error

# Статус и аптайм
fly status

# Потребление ресурсов
fly ssh console -C "free -m && df -h"
```

Рестарт при проблемах:

```bash
fly restart
# Проверить что запустился:
fly logs
```

## Важно

- Бот использует **polling**, а не webhook — внешний порт не нужен
- Сервисный порт 8080 указан в fly.toml для health checks, бот его не слушает
- При старте `load_dotenv()` не найдёт `.env` файл (его нет в Docker-образе) и молча упадёт — `os.getenv()` подхватит переменные из fly secrets
- Бесплатный лимит: 3 shared‑cpu VM по 256 MB RAM
- Регион `ams` (Амстердам) — минимальная задержка для Украины
