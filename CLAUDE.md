# Project Instructions

## Knowledge Base

Use LLM Wiki from ~/Brain (/Users/anna/Documents/brain/) for:
- Technical concepts
- Best practices
- Previous solutions
- Tools and libraries
- Personal facts about the user

Before answering questions, check wiki first.

## Project Context

- **User:** Anna — личный проект
- **Goal:** Трекер денежных приходов и расходов
- **Tech stack preferences:** Telegram (основной мессенджер), Monobank (клиент)
- **Deploy:** Bot on Fly.io, Web on Vercel (keshafinancebot.vercel.app)
- **Vercel account:** personal (anna-kolom-s-projects/kesha-finance-bot), not team (coinpostnews)

## Communication

- Язык коммуникации: русский (Ukrainian/Russian hybrid)
- User предпочитает прямые, конкретные ответы

## Memory & Context

- Используй claude-memory-compiler из ~/Brain при старте каждой новой сессии
- Сохраняй важные решения и факты в wiki (/Users/anna/Documents/brain/wiki/)
- Обновляй personal_facts.md при получении новой информации о пользователе

## Development

### GSD Workflow
- Следуй GSD workflow для всех изменений
- Используй Jcodemunch для экономии токенов
- Используй GStack skills для мульти-агентной разработки

### Design Skills
- Impeccable — аудит/полишинг UI (/impeccable audit|polish|critique|craft)
- Visual Companion — визуальный компаньон в браузере (/visual-companion)
- Оба установлены в `.agents/skills/`, синхронизированы с `~/.agents/skills/`

### Critical: React Rules of Hooks
- **ВСЕ хуки (useState, useMemo, useEffect) ДОЛЖНЫ быть до любого условного return.**
- Нарушение порядка хуков вызывает "Application error: client-side exception" в production-сборке
- При дебаггинге ошибок на Vercel: если ошибка только в production, первым делом проверяй порядок хуков

### Testing Protocol
- Деплой после КАЖДОГО изменения. Тест проходит → следующее изменение
- При ошибке: откатить последнее изменение, подтвердить что работает, затем искать корневую причину
- Никогда не добавлять несколько изменений за раз без промежуточного теста

### Stale Build Cache
- После массовых изменений: `rm -rf web/.next && cd web && npm run dev`
- Битый кеш вызывает "Cannot find module './NNN.js'" — не ошибка в коде

## Architecture Decisions

### Analytics Charts: Pure SVG, NOT Recharts
- ❌ Recharts (~120KB) — несовместим с iOS Safari, ResponsiveContainer ломает рендеринг
- ❌ `var(--css-var)` в SVG-атрибутах (stroke, fill) крашит iOS Safari
- ✅ Pure SVG с `viewBox` — 6KB, работает везде, темнеет/светлеет через CSS-переменные
- CSS-переменные в SVG-атрибутах работают в Chrome/Desktop, но НЕ в iOS Safari. Использовать `getComputedStyle` + хук для резолва в hex

### Theme Toggle
- Три состояния: system → dark → light (цикл)
- localStorage для сохранения, ThemeScript в `<head>` для предотвращения flash
- CSS-переменные в `:root` (light), `.dark` (manual), `@media prefers-color-scheme: dark` (system)

### Mobile Safe Area
- `viewportFit: "cover"` в метатеге + CSS `env(safe-area-inset-*)` через `@layer utilities` Tailwind
- `.pt-safe`, `.pb-safe` — утилитарные классы для Header и BottomNav

### Monobank Integration
- Public API: `/bank/currency` (rates, no auth needed)
- Personal API: `/personal/client-info` + `/personal/statement/{id}` (X-Token header)
- Amounts in kopecks/cents → divide by 100
- Web: API routes → lib/mono.ts functions → React components
- Bot: async MonobankClient with rate limiting, retries, /mono_import + /mono_sync commands

## Project Structure
```
├── bot/              # Telegram bot (Python 3.12 + python-telegram-bot)
│   ├── handlers/     # 20+ command handlers
│   ├── mono/         # Monobank API client + webhook
│   └── sheets.py     # Google Sheets integration
├── web/              # Next.js 14 PWA
│   ├── app/          # App Router pages + API routes
│   ├── components/   # React components (dashboard, analytics, ui, layout, transactions)
│   └── lib/          # Shared utilities (sheets, mono, formatters, quotes, cache)
├── docs/             # Documentation
└── .planning/        # Specs, audits, plans
```

## Environment Variables (both bot + web)
```
GOOGLE_SERVICE_ACCOUNT_EMAIL  # Google Sheets service account
GOOGLE_PRIVATE_KEY            # with \n replaced to real newlines
SPREADSHEET_ID                # Google Sheets spreadsheet ID
MONOBANK_X_TOKEN              # Monobank personal API token (optional)
BOT_TOKEN                     # Telegram bot token (bot only)
```
