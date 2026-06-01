# Kesha Finance Tracker — Установка и запуск

> 🚀 **Веб-приложение уже задеплоено на Vercel:** [keshafinancebot.vercel.app](https://keshafinancebot.vercel.app)
> ☁️ **Telegram бот работает 24/7 на fly.io** — локальный запуск только для разработки и тестирования.
>
> Эта инструкция — для локальной разработки. Чтобы задеплоить:
> - Бот → [docs/DEPLOY_BOT.md](DEPLOY_BOT.md) (fly.io)
> - Веб → [docs/DEPLOY.md](DEPLOY.md) (Vercel)

## Требования

| Компонент | Версия | Проверка |
|-----------|--------|----------|
| Python | 3.12+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Google аккаунт | любой | [accounts.google.com](https://accounts.google.com) |
| Telegram | любой | для @BotFather |
| Git | 2+ | `git --version` |

**Опционально:**
- Monobank X-Token — для авто-импорта банковских операций

---

## Шаг 1: Клонирование и `.env`

```bash
cd ~/Documents
git clone git@github.com:koloma18/KeshaFinanceBot.git FinancialTracker
cd FinancialTracker
```

Создай `.env`:

```bash
touch .env
chmod 600 .env
```

Заполни:

```ini
# Telegram
BOT_TOKEN=токен_от_BotFather

# Google Sheets
GOOGLE_SERVICE_ACCOUNT_EMAIL=account@project.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----
SPREADSHEET_ID=id_google_таблицы

# Monobank (опционально)
MONOBANK_X_TOKEN=ваш_monobank_x_token

# Настройки
PRIMARY_CURRENCY=UAH
CURRENCIES=UAH,USD,EUR,USDT
```

> ⚠️ **Важно:** `.env` содержит секреты — никогда не коммить его в git. Файл уже в `.gitignore`.

---

## Шаг 2: Google Sheets + Service Account

### 2.1 Включи Google Sheets API

1. Открой [Google Cloud Console](https://console.cloud.google.com/)
2. Создай проект: **New Project → «Kesha Tracker»**
3. **APIs & Services → Library** → Найди **Google Sheets API** → **Enable**

### 2.2 Создай Service Account

1. **APIs & Services → Credentials → Create Credentials → Service Account**
2. Имя: `kesha-bot`, роль: **Basic → Editor**
3. Нажми на созданный аккаунт → **Keys → Add Key → JSON**
4. Из JSON-файла:
   - `client_email` → `GOOGLE_SERVICE_ACCOUNT_EMAIL`
   - `private_key` → `GOOGLE_PRIVATE_KEY` (одной строкой с `\n`)

### 2.3 Создай Google Таблицу

1. [sheets.google.com](https://sheets.google.com) → **Blank spreadsheet**
2. Из URL скопируй `SPREADSHEET_ID` → в `.env`
3. **Share** → добавь email Service Account как **Editor**

### 2.4 Настрой таблицу через Apps Script

1. В таблице: **Расширения → Apps Script**
2. Скопируй содержимое `scripts/Code.gs`
3. Запусти `setupSheets()` — создаст все листы

**Создаются листы:**
- `Transactions` — все операции (A-I)
- `Budgets` — бюджеты и лимиты
- `Categories` — кастомные категории
- `Settings` — настройки пользователя
- `BankAccounts` — ручные банковские счета

---

## Шаг 3: Telegram бот

### 3.1 Создай бота в BotFather

1. Telegram → [@BotFather](https://t.me/botfather) → `/newbot`
2. Имя: `Kesha Finance Tracker`
3. Username: `kesha_finance_bot` (должен заканчиваться на `bot`)
4. Токен → в `.env` → `BOT_TOKEN`

### 3.2 Установи Python-зависимости

```bash
cd bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Установятся:
- `python-telegram-bot==21.11.1` — фреймворк бота
- `google-auth==2.38.0` — JWT-авторизация Google
- `httpx` — HTTP-клиент (Sheets API + Monobank)
- `python-dotenv` — чтение `.env`

> Бот использует **raw HTTP** для Google Sheets API (через `httpx`), а не `google-api-python-client`. Это экономит ~50MB RAM.

### 3.3 Запуск

```bash
cd ~/Documents/FinancialTracker
./start.sh
```

Бот сам зарегистрирует 37 команд в Telegram при старте. Успешный запуск:

```
🚀 Kesha запущен!
✅ 37 bot commands registered
```

---

## Шаг 4: Веб-приложение (локальная разработка)

> 🌐 Продакшн-версия: [keshafinancebot.vercel.app](https://keshafinancebot.vercel.app)

### 4.1 Установи Node-зависимости

```bash
cd web
npm install
```

Установятся:
- `next@14` + `react@18` — Next.js фреймворк
- `tailwindcss` + `postcss` + `autoprefixer` — стили
- `googleapis` + `google-auth-library` — Google Sheets API

> Графики используют **pure SVG** (не Recharts) — совместимы с iOS Safari.

### 4.2 Переменные окружения

Создай `.env.local` в `web/` (те же переменные, что в корневом `.env`):

```bash
cd web
cat > .env.local << 'EOF'
GOOGLE_SERVICE_ACCOUNT_EMAIL=account@project.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----
SPREADSHEET_ID=id_google_таблицы
MONOBANK_X_TOKEN=ваш_monobank_x_token
EOF
```

### 4.3 Запуск

```bash
cd web
npm run dev        # dev-режим → http://localhost:3000
npm run build && npm start   # production-сборка
```

---

## Шаг 5: Установка PWA на телефон

### iPhone (Safari)
1. Открой сайт в Safari → Share → **Add to Home Screen**
2. Название: `Кеша` → Add

### Android (Chrome)
1. Открой сайт в Chrome → ⋮ → **Add to Home screen**
2. Название: `Кеша` → Add

Приложение работает в полноэкранном режиме с офлайн-поддержкой.

---

## Обновление

```bash
git pull
cd bot && source venv/bin/activate && pip install -r requirements.txt
cd ../web && npm install

# Продакшн:
fly deploy          # бот на fly.io
# веб авто-деплоится через Vercel при git push
```

---

## Структура проекта

```
FinancialTracker/
├── .env                    # Секреты (не коммитится)
├── .env.example            # Шаблон без секретов (коммитится)
├── fly.toml                # Fly.io конфиг бота
├── CLAUDE.md               # Инструкции для AI-агентов
├── bot/
│   ├── main.py             # Точка входа бота (polling)
│   ├── config.py           # Загрузка .env
│   ├── requirements.txt    # Python-зависимости (лёгкие)
│   ├── Dockerfile          # Docker-образ для fly.io
│   ├── categories.py       # Категории (built-in + custom)
│   ├── sheets.py           # Google Sheets API (raw HTTP)
│   ├── budget.py           # Бюджеты и лимиты
│   ├── user_settings.py    # Персистентные настройки
│   ├── stickers.py         # Стикеры (312 шт.)
│   ├── responses.py        # Текстовые ответы (токсичность)
│   ├── register_commands.py # 37 команд бота
│   ├── diagnose.py         # Диагностика
│   ├── handlers/           # Обработчики команд
│   │   ├── start.py, income.py, expense.py
│   │   ├── statistics.py, last.py, delete_command.py
│   │   ├── budget.py, settings.py, quotes.py
│   │   ├── stickers.py, reminder.py, set_currency.py
│   │   ├── export_data.py, compare.py, recategorize.py
│   │   ├── add_category.py, categories.py
│   │   ├── bank.py         # Ручные банковские счета
│   │   ├── mono_import.py  # Импорт выписки Monobank
│   │   ├── mono_sync.py    # Синхронизация Monobank
│   │   ├── mono_rates.py   # Курсы валют Monobank
│   │   ├── mono_info.py    # Счета Monobank
│   │   └── mono_day.py     # Выписка за день
│   └── mono/               # Monobank API
│       ├── client.py       # Async HTTP-клиент с rate limiting
│       ├── mcc_categories.py # 93 MCC кода → 18 категорий
│       └── webhook.py      # Webhook приёмник (заглушка)
├── web/
│   ├── package.json        # Node-зависимости
│   ├── next.config.mjs     # Next.js 14 конфиг
│   ├── tailwind.config.ts  # Tailwind CSS
│   ├── vercel.json         # Vercel деплой конфиг
│   ├── app/                # Next.js App Router
│   │   ├── layout.tsx      # Root layout (PWA meta)
│   │   ├── page.tsx        # Дашборд
│   │   ├── analytics/      # Аналитика (pure SVG charts)
│   │   ├── transactions/   # История транзакций
│   │   └── api/            # API-роуты
│   │       ├── sheets/     # Google Sheets API
│   │       └── mono/       # Monobank (курсы валют)
│   ├── components/         # React-компоненты
│   │   ├── dashboard/      # Карточки дашборда + MonoAccounts
│   │   ├── analytics/      # SVG-графики (не Recharts!)
│   │   ├── transactions/   # Таблица транзакций
│   │   ├── layout/         # Header, BottomNav
│   │   └── ui/             # UI-библиотека
│   ├── lib/                # Бизнес-логика
│   │   ├── sheets.ts       # SheetsClient (googleapis)
│   │   ├── mono.ts         # Monobank API клиент
│   │   └── types.ts        # TypeScript типы
│   └── public/             # Статика (manifest, sw, icons)
├── scripts/
│   └── Code.gs             # Google Apps Script (настройка таблицы)
├── docs/                   # Документация
│   ├── INSTALL.md          # Этот файл
│   ├── DEPLOY.md           # Деплой веба на Vercel
│   ├── DEPLOY_BOT.md       # Деплой бота на fly.io
│   └── USAGE.md            # Руководство пользователя
└── .planning/              # Спецификации и планы
    ├── PROJECT.md          # Описание проекта
    ├── ROADMAP.md          # Дорожная карта
    ├── REQUIREMENTS.md     # Требования
    └── STATE.md            # Текущий статус
```
