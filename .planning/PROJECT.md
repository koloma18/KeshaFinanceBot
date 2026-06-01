# Financial Tracker

## What This Is

Персональный трекер денежных приходов и расходов с гибридным вводом: автоматический импорт из Monobank API и ручной ввод через Telegram-бота. Веб-приложение (PWA) для аналитики и управления.

## Core Value

Автоматический учёт всех личных финансов без усилий — Monobank тянет безнал, Telegram для наличных, единая картина в вебе.

## Requirements

### Validated

- ✅ Phase 1-4 реализованы и работают в production

### Active

- [ ] SQLite read-through cache для мгновенных ответов бота
- [ ] Фоновый Monobank sync (cron, раз в 5-10 мин)
- [ ] Web API routes через SQLite (с Sheets fallback)

### Done

- [x] Интеграция с Monobank API (выписка + WebHook)
- [x] Google Sheets как хранилище данных
- [x] Telegram-бот для ручного ввода расходов/доходов
- [x] Автоматическая категоризация по MCC Monobank
- [x] Ручная перекатегоризация через Telegram
- [x] Веб-приложение (Next.js PWA) с дашбордом и графиками
- [x] Бюджетные лимиты по категориям

### Future

- [ ] Крутое название, дизайн, логотип + маркетинг (будущая монетизация)

### Out of Scope

- Мобильное нативное приложение (iOS/Android) — PWA достаточно для v1
- Поддержка других банков — пока только Monobank
- Мультипользовательский режим — личный проект
- Корпоративное Monobank API — персональный токен достаточен

## Context

- Пользователь — клиент Monobank, активный пользователь Telegram
- Monobank API: X-Token, выписка (31 день, 500 транзакций/запрос), WebHook
- Google Sheets — данные доступны напрямую через таблицу
- Tech stack: Next.js 14 + TypeScript + Tailwind CSS (веб), python-telegram-bot (бот)
- Деплой: Fly.io (бот), Vercel (веб)

## Constraints

- **Monobank API**: лимит 1 запрос/60 сек, максимум 31 день за запрос
- **Google Sheets**: лимит 60 запросов/мин, ~300-800ms latency per request
- **Fly.io**: 3GB persistent volume для SQLite кеша
- **Персональный проект**: минимальные затраты на хостинг
- **WebHook**: нужен публичный HTTPS URL (Vercel подходит)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Google Sheets как БД | Прозрачность данных, можно править руками | Done ✅ | 2026-05-30 |
| PWA вместо нативного | Быстрее, дешевле, достаточно для v1 | Done ✅ | 2026-05-30 |
| Гибридный ввод (API + Telegram) | Полный охват транзакций | Done ✅ | 2026-05-30 |
| SQLite read-through cache | Мгновенные ответы, защита от Sheets latency | In Progress | 2026-06-01 |
| Monobank cron sync | Убрать блокирующий API из user-facing команд | Planned | 2026-06-01 |

---
*Last updated: 2026-06-01 — SQLite caching phase started*
