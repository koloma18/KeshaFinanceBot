# Kesha Finance Bot 💰🐿️

Персональный трекер доходов и расходов с характером.

Telegram бот с саркастичным бурундуком Кешей + PWA дашборд для аналитики.

[![Vercel](https://img.shields.io/badge/vercel-deployed-black)](https://keshafinancebot.vercel.app)
[![fly.io](https://img.shields.io/badge/fly.io-deployed-purple)](https://fly.io)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)](https://core.telegram.org/bots)

**Лайв-демо:** [keshafinancebot.vercel.app](https://keshafinancebot.vercel.app)

## Что умеет

### Telegram бот (32+ команды)
- 💰 Быстрый ввод доходов и расходов (текстом или через кнопки)
- 📊 Статистика: сегодня, неделя, месяц, баланс
- 🆘 Интерактивный `/help` — 8 разделов с кнопками и примерами
- 🎯 Бюджет на месяц и лимиты по категориям
- 🔔 Уведомления при превышении лимитов (50%, 80%, 100%)
- 🏦 Авто-импорт из Monobank API
- 💱 Курсы валют
- 🧠 Ежедневные цитаты и напоминания
- 😈 Стикеры и эмодзи
- 📤 Экспорт в CSV
- 🧂 Настраиваемый уровень токсичности (мягкий/бурчливый/жёсткий)
- ☁️ Круглосуточная работа 24/7 на fly.io

### Веб-приложение (PWA)
- 📊 Дашборд с балансом и статистикой
- 💳 История транзакций с фильтрацией и поиском
- 📈 Аналитика с графиками (Recharts)
- 🌓 Тёмная/светлая тема
- 📱 Установка на телефон (PWA)

## Технологии

| Компонент | Технология |
|-----------|-----------|
| Telegram Bot | Python 3.12 + python-telegram-bot v21 |
| Хранилище | Google Sheets API |
| Веб-приложение | Next.js 14 + TypeScript + Tailwind CSS |
| Банк | Monobank API |
| Графики | Recharts |
| PWA | next-pwa + Service Worker |

## Быстрый старт

> ☁️ **Бот уже работает 24/7 на fly.io.** Локальный запуск — только для разработки и тестирования.

### 1. Клонирование
```bash
git clone https://github.com/koloma18/KeshaFinanceBot.git
cd KeshaFinanceBot
```

### 2. Telegram бот (локально)
```bash
cd bot
python3 -m venv venv
source venv/bin/activate  # АКТИВИРОВАТЬ ОБЯЗАТЕЛЬНО! (Windows: venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env        # заполни .env своими токенами
```

**Запуск одной командой:**
```bash
./start.sh    # из корня проекта — сам активирует venv
```

**Или через алиас `kesha` из любого места:**
```bash
echo 'alias kesha="cd ~/Documents/FinancialTracker && ./start.sh"' >> ~/.zshrc
source ~/.zshrc
kesha         # ← одной командой из любого места
```

> ⚠️ **Важно:** без активации venv будет ошибка `TypeError: unsupported operand type(s) for |`.

### Веб-приложение (уже задеплоено на Vercel)
Открой [keshafinancebot.vercel.app](https://keshafinancebot.vercel.app) — готово.

Для локального запуска: см. [docs/INSTALL.md](docs/INSTALL.md)

## Переменные окружения

### `bot/.env`
```
BOT_TOKEN=токен_от_BotFather
SPREADSHEET_ID=id_таблицы_Google_Sheets
GOOGLE_SERVICE_ACCOUNT_EMAIL=email_сервисного_аккаунта
GOOGLE_PRIVATE_KEY=приватный_ключ
MONOBANK_X_TOKEN=токен_monobank  # опционально
```

### `web/.env.local`
```
GOOGLE_SERVICE_ACCOUNT_EMAIL=email_сервисного_аккаунта
GOOGLE_PRIVATE_KEY=приватный_ключ
SPREADSHEET_ID=id_таблицы_Google_Sheets
MONOBANK_X_TOKEN=токен_monobank  # опционально
```

## Структура проекта
```
├── bot/              # Telegram бот
│   ├── main.py
│   ├── handlers/     # Обработчики команд
│   ├── mono/         # Monobank API клиент
│   ├── sheets.py     # Google Sheets API
│   └── responses.py  # Фразы персонажа
├── web/              # PWA веб-приложение
│   ├── app/          # Next.js App Router
│   ├── components/   # React компоненты
│   └── lib/          # Утилиты и API клиенты
├── scripts/          # Apps Script для Google Sheets
├── docs/             # Документация
└── .planning/        # Спецификации и планирование
```

## Документация
- [Установка и запуск](docs/INSTALL.md) — локальная разработка
- [Руководство пользователя](docs/USAGE.md) — все команды и фичи
- [Деплой бота на fly.io](docs/DEPLOY_BOT.md) — продакшн-деплой
- [Деплой веба на Vercel](docs/DEPLOY.md) — веб-приложение
- [Дизайн-система](web/DESIGN.md)

## Лицензия
MIT

---
Сделано с ❤️ и сарказмом.
