# Roadmap: Financial Tracker

## Phase 1: Core Telegram Bot + Google Sheets

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

## Phase 2: Budget + Limits + Quotes + Stickers

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

## Phase 3: Web App (PWA)

**Цель:** Веб-приложение с дашбордом и аналитикой.

**Requirements:** WEB-01, WEB-02, WEB-03, WEB-04

**Deliverables:**
- PWA на Next.js
- Дашборд с графиками
- История с фильтрацией
- Установка на телефон

## Phase 4: Monobank Integration

**Цель:** Автоматический импорт транзакций из Monobank.

**Requirements:** MONO-01, MONO-02, CAT-01

**Deliverables:**
- Выписка через Monobank API
- WebHook для реального времени
- Автоматическая категоризация по MCC

## Phase 5: Marketing & Monetization

**Цель:** Название, брендинг, возможность платного доступа.

**Requirements:** v2

**Deliverables:**
- Крутое название
- Маркетинговые материалы
- Система платного доступа
