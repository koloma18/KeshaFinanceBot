# Project State

## Current Status

**Phase:** Phase 4 — Performance Optimization (SQLite Caching)
**Last Action:** Диагностика медленного /balance, планирование кеширования
**Blockers:** —

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-01)

**Core value:** Автоматический учёт всех личных финансов без усилий
**Current focus:** Phase 4 — SQLite read-through cache для мгновенных ответов бота

## Active Decisions

| # | Decision | Status | Date |
|---|----------|--------|------|
| 1 | Google Sheets как БД | Done ✅ | 2026-05-30 |
| 2 | PWA вместо нативного | Done ✅ | 2026-05-30 |
| 3 | Гибридный ввод (API + TG) | Done ✅ | 2026-05-30 |
| 4 | Без Monobank до получения токена | Done ✅ | 2026-05-30 → 2026-05-31 |
| 5 | Monobank интеграция | Done ✅ | 2026-05-31 |
| 6 | WebHook (заглушка) | Done | 2026-05-31 |
| 7 | Phase 2: Budget + Limits + Quotes + Export | Done ✅ | 2026-05-31 |
| 8 | Phase 3: PWA Web App (Next.js + Tailwind) | Done ✅ | 2026-05-31 |
| 9 | SQLite read-through cache для бота | In Progress | 2026-06-01 |

## Open Questions

- Фоновый cron для Monobank — на Fly.io или отдельно?
- Нужна ли LiteFS для шаринга SQLite между ботом и вебом?

## Completed

- ✅ Phase 1: Core Telegram Bot + Google Sheets
- ✅ Phase 2: Budget + Limits + Quotes + Export
- ✅ Phase 3: PWA Web App (Next.js + Tailwind)
- ✅ Phase 4: Monobank Integration (импорт, синк, webhook)

## Current Focus

- 🔄 Phase 4 (new): Performance — SQLite caching, async Monobank, fast /balance
