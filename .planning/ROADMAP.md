# Roadmap: Financial Tracker

## Phase 1: Core Telegram Bot + Google Sheets ✅

**Цель:** Минимальный бот для записи доходов/расходов, базовой статистики и Google Sheets как хранилище.

**Requirements:** INFRA-01, INFRA-02, INFRA-03, TG-01, TG-02, TG-03, TG-04, CAT-02

**Команды:** /start, /help, /income, /expense, /today, /week, /month, /balance, /categories, /last, /delete_last, /settings

**Кнопки:** Доход, Расход, Статистика, Последние операции, Настройки

**Deliverables:**
- Google Sheets структура (Transactions, Summary, Report)
- Apps Script (цвета, отчёты, меню)
- Telegram Bot v1 (Python, python-telegram-bot)
- Персонаж: бурчливый, мат, эмодзи, разные ответы
- Кнопки и inline-меню

## Phase 2: Budget + Limits + Quotes + Stickers ✅

**Цель:** Бюджетирование, лимиты по категориям, цитаты дня, стикеры.

**Requirements:** BUDG-01, BUDG-02

**Команды:** /budget, /set_limit, /limits, /limit_alerts, /top, /compare, /export, /reminder, /quote, /quote_time, /stickers

**Deliverables:**
- Бюджет на месяц
- Лимиты по категориям с уведомлениями (50%, 80%, превышение)
- Цитаты дня (ежедневно + по запросу)
- Стикеры и эмодзи (настройка частоты)
- Экспорт (CSV, Excel, Google Sheets)
- Ежедневные напоминания

## Phase 3: Web App (PWA) ✅

**Цель:** Веб-приложение с дашбордом и аналитикой.

**Requirements:** WEB-01, WEB-02, WEB-03, WEB-04

**Deliverables:**
- PWA на Next.js
- Дашборд с графиками
- История с фильтрацией
- Установка на телефон

## Phase 4: Monobank Integration ✅

**Цель:** Автоматический импорт транзакций из Monobank.

**Requirements:** MONO-01, MONO-02, CAT-01

**Deliverables:**
- Выписка через Monobank API
- WebHook для реального времени
- Автоматическая категоризация по MCC

## Phase 5: Performance — SQLite Caching 🔄

**Цель:** Мгновенные ответы бота, независимость от Google Sheets latency.

**Requirements:** PERF-01, PERF-02, PERF-03

**Deliverables:**
- SQLite read-through cache между ботом и Sheets
- Запись в Sheets + SQLite одновременно, чтение из SQLite (<1ms)
- Фоновый cron для Monobank sync (раз в 5-10 мин)
- Кеширование /balance, /last, /today, /week, /month
- Web API routes тоже читают из SQLite

## Phase 6: Recurring Payments & Subscriptions

**Цель:** Автоматические напоминания о регулярных платежах и подписках с поддержкой мультивалютных списаний (USD, EUR, UAH).

**Requirements:** RECUR-01, RECUR-02, RECUR-03, RECUR-04, RECUR-05

**Deliverables:**
- Лист Recurring в Google Sheets (24 колонки, три AmountMode: fixed/variable/fx)
- Бот-команды: /recurring_add, /recurring_list, /recurring_due, /recurring_pay, /recurring_pause, /recurring_delete, /recurring_edit
- Due flow с кнопками: запись по фиксированной сумме, ввод фактической UAH для fx, ввод суммы для variable
- Интеграция с Transactions (A:L) — Source = recurring:<ID>, AI Comment = title + original currency
- Apps Script: Recurring sheet + форматтер
- Тесты: fx-подписки, fixed, variable, parser

## Phase 7: Marketing & Monetization

**Цель:** Название, брендинг, возможность платного доступа.

**Requirements:** v2

**Deliverables:**
- Крутое название
- Маркетинговые материалы
- Система платного доступа
