# Kesha Finance Tracker — Установка и запуск

> 🚀 **Веб-приложение уже задеплоено на Vercel:** [keshafinancebot.vercel.app](https://keshafinancebot.vercel.app)
>
> Эта инструкция — для локальной разработки. Если хочешь задеплоить свою версию, см. [docs/DEPLOY.md](DEPLOY.md).

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
- ngrok или публичный сервер — для Monobank webhook

---

## Шаг 1: Клонирование и `.env`

```bash
cd ~/Documents
cd FinancialTracker
```

Скопируй шаблон переменных окружения (создай вручную, если файла ещё нет):

```bash
touch .env
chmod 600 .env
```

Открой `.env` в редакторе и заполни:

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
2. Создай проект (или выбери существующий): **New Project → «Kesha Tracker»**
3. В боковом меню: **APIs & Services → Library**
4. Найди **Google Sheets API** → **Enable**

### 2.2 Создай Service Account

1. **APIs & Services → Credentials → Create Credentials → Service Account**
2. Имя: `kesha-bot`
3. Роль: **Basic → Editor** (достаточно для Sheets)
4. Нажми на созданный аккаунт → **Keys → Add Key → JSON**
5. Скачается JSON-файл — из него нам нужны:
   - `client_email` → скопируй в `.env` как `GOOGLE_SERVICE_ACCOUNT_EMAIL`
   - `private_key` → скопируй в `.env` как `GOOGLE_PRIVATE_KEY`
     - **Важно:** в `.env` ключ должен быть в одной строке с `\n` между строками
     - Пример: `GOOGLE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n`

### 2.3 Создай Google Таблицу

1. Открой [sheets.google.com](https://sheets.google.com) → **Blank spreadsheet**
2. Назови таблицу (например: `Kesha Finances`)
3. Из URL скопируй `SPREADSHEET_ID`:
   ```
   https://docs.google.com/spreadsheets/d/ЭТО_SPREADSHEET_ID/edit
   ```
4. Вставь в `.env` → `SPREADSHEET_ID=этот_id`

### 2.4 Дай доступ Service Account

1. В созданной таблице нажми **Share**
2. Добавь email Service Account (тот самый `client_email`) как **Editor**
3. Сними галку «Notify people» → **Send**

**Бот сам создаст нужные листы при первом запуске:**
- `Transactions` — все операции
- `Categories` — кастомные категории
- `Budgets` — бюджеты и лимиты
- `Settings` — настройки пользователя

---

## Шаг 3: Telegram бот

### 3.1 Создай бота в BotFather

1. Открой Telegram → найди [@BotFather](https://t.me/botfather)
2. Отправь команду `/newbot`
3. Введи имя: `Kesha Finance Tracker`
4. Введи username: `kesha_finance_bot` (должен заканчиваться на `bot`)
5. BotFather выдаст токен — скопируй его в `.env` → `BOT_TOKEN`
6. Настрой бота (опционально):
   - `/setdescription` — описание профиля
   - `/setabouttext` — текст «About»
   - `/setuserpic` — аватарку хомяка
   - `/setcommands` — список команд (бот сам зарегистрирует команды при старте)

### 3.2 Установи Python-зависимости

```bash
cd bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Установятся пакеты:
- `python-telegram-bot==21.11.1` — фреймворк бота
- `google-api-python-client` — Google Sheets API
- `google-auth` + `google-auth-oauthlib` — авторизация Google
- `python-dotenv` — чтение `.env`
- `httpx` + `aiohttp` — HTTP-клиенты для Monobank API

### 3.3 Зарегистрируй команды

После первого запуска бот автоматически зарегистрирует 32 команды в Telegram.
Можно также запустить регистрацию вручную:

```bash
cd bot
source venv/bin/activate
python3 register_commands.py
```

---

## Шаг 4: Веб-приложение (локальная разработка)

> 🌐 Продакшн-версия уже доступна на [keshafinancebot.vercel.app](https://keshafinancebot.vercel.app).
> Локальный запуск нужен только для разработки и тестирования.

### 4.1 Установи Node-зависимости

```bash
cd web
npm install
```

Установятся:
- `next@14` + `react@18` — Next.js фреймворк
- `tailwindcss` + `postcss` + `autoprefixer` — стили
- `googleapis` + `google-auth-library` — Google Sheets для веба
- `recharts` — графики аналитики

### 4.2 Переменные окружения для веба

Создай `.env.local` в папке `web/` (веб читает те же переменные, что и бот):

```bash
cd web
cat > .env.local << 'EOF'
GOOGLE_SERVICE_ACCOUNT_EMAIL=account@project.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----
SPREADSHEET_ID=id_google_таблицы
MONOBANK_X_TOKEN=ваш_monobank_x_token
EOF
```

> `.env.local` уже в `.gitignore`.

---

## Шаг 5: Запуск (ВНИМАНИЕ: сначала активировать venv!)

> ⚠️ **Каждый раз перед запуском:** сначала `source venv/bin/activate`, потом `python3 main.py`. Без venv — ошибка `TypeError`.
### Бот

```bash
cd ~/Documents/FinancialTracker/bot
source venv/bin/activate
python3 main.py
```

Успешный запуск:

```
🚀 Kesha запущен!
```

Бот начинает polling — можно писать ему в Telegram.

### Веб-приложение (dev-режим)

```bash
cd ~/Documents/FinancialTracker/web
npm run dev
```

Откроется на [http://localhost:3000](http://localhost:3000).

### Production-сборка веба

```bash
cd web
npm run build
npm start
```

Откроется на порту 3000.

### Для постоянной работы

Чтобы бот работал 24/7, запускай в фоне. **Варианты:**

**Вариант A — macOS (launchd):**
Создай plist-файл для автозапуска бота как фонового сервиса.

**Вариант B — screen/tmux:**
```bash
screen -S kesha
cd ~/Documents/FinancialTracker/bot && source venv/bin/activate && python3 main.py
# Ctrl+A, D — отключиться от сессии
# screen -r kesha — вернуться
```

**Вариант C — Raspberry Pi / VPS:**
Скопируй проект на сервер, установи systemd-сервис.

---

## Установка PWA на телефон

### iPhone (Safari)

1. Открой Safari → перейди на `http://твой-ip:3000` (или домен)
2. Нажми кнопку **Share** (квадрат со стрелкой вверх) в нижней панели
3. Пролистай → **Add to Home Screen** (На экран «Домой»)
4. Название: `Кеша` → **Add**
5. На домашнем экране появится иконка — открывай как отдельное приложение

### Android (Chrome)

1. Открой Chrome → перейди на веб-приложение
2. Нажми ⋮ (меню) → **Add to Home screen** (Добавить на главный экран)
3. Название: `Кеша` → **Add**

После установки приложение работает в полноэкранном режиме, как нативное. Service Worker кэширует страницы — работает офлайн для просмотра ранее загруженных данных.

---

## Обновление

```bash
# Обнови код
git pull

# Обнови Python-зависимости
cd bot
source venv/bin/activate
pip install -r requirements.txt

# Обнови веб-зависимости
cd ../web
npm install

# Перезапусти бота
# (останови текущий процесс, запусти заново)
```

Если менялась структура данных Google Sheets — новые листы создадутся автоматически при первом запуске бота.

---

## Структура проекта

```
FinancialTracker/
├── .env                    # Секреты (не коммитится)
├── bot/
│   ├── main.py             # Точка входа бота
│   ├── config.py           # Загрузка .env
│   ├── requirements.txt    # Python-зависимости
│   ├── categories.py       # Справочник категорий
│   ├── sheets.py           # Google Sheets API
│   ├── budget.py           # Бюджеты и лимиты
│   ├── user_settings.py    # Настройки пользователя
│   ├── stickers.py         # Стикеры (312 шт.)
│   ├── register_commands.py # Регистрация команд в Telegram
│   ├── diagnose.py         # Диагностика
│   ├── fetch_stickers.py   # Получение стикеров
│   ├── responses.py        # Текстовые ответы (токсичность)
│   ├── handlers/           # Обработчики команд
│   │   ├── start.py, income.py, expense.py
│   │   ├── statistics.py, last.py, delete_command.py
│   │   ├── budget.py, settings.py, quotes.py
│   │   ├── stickers.py, reminder.py, set_currency.py
│   │   ├── export_data.py, compare.py, recategorize.py
│   │   └── add_category.py, categories.py
│   └── mono/               # Monobank API
│       ├── client.py       # HTTP-клиент
│       ├── mcc_categories.py # MCC → категория
│       └── webhook.py      # Webhook приёмник
├── web/
│   ├── package.json        # Node-зависимости
│   ├── next.config.mjs     # Next.js конфиг
│   ├── tailwind.config.ts  # Tailwind CSS конфиг
│   ├── app/                # Next.js App Router
│   │   ├── layout.tsx      # Root layout (PWA meta)
│   │   ├── page.tsx        # Dashboard
│   │   ├── analytics/      # Страница аналитики
│   │   ├── transactions/   # История транзакций
│   │   └── api/            # API-роуты
│   │       ├── sheets/     # Google Sheets API
│   │       └── mono/       # Monobank (курсы валют)
│   ├── components/         # React-компоненты
│   │   ├── dashboard/      # Карточки дашборда
│   │   ├── analytics/      # Графики
│   │   ├── transactions/   # Таблица транзакций
│   │   ├── layout/         # Header, BottomNav
│   │   └── ui/             # UI-библиотека
│   ├── lib/                # Бизнес-логика
│   │   ├── sheets.ts       # Sheets клиент
│   │   ├── mono.ts         # Monobank клиент
│   │   ├── types.ts        # Типы TypeScript
│   │   └── ...
│   └── public/             # Статика
│       ├── manifest.json   # PWA манифест
│       ├── sw.js           # Service Worker
│       └── icons/          # Иконки PWA
└── docs/                   # Документация
    ├── INSTALL.md          # Этот файл
    └── USAGE.md            # Руководство пользователя
```
