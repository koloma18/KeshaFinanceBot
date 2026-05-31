# SPEC.md — Phase 3: PWA Web Application

**Phase:** 3
**Project:** Financial Tracker
**Core Value:** Веб-приложение с дашбордом и аналитикой для управления финансами с телефона
**Requirements:** WEB-01, WEB-02, WEB-03, WEB-04
**Character:** Кеша — саркастичный надзиратель, теперь и в браузере

---

## 1. Goal

Создать PWA веб-приложение на Next.js 14, которое даёт полную картину финансов: дашборд с балансом и графиками, история всех транзакций с фильтрацией, аналитика по периодам. Устанавливается на телефон как родное приложение. Сохраняет стиль и характер Кеши.

---

## 2. Requirements

### REQ-01: Next.js Project Setup

**Current state:** Нет веб-проекта.
**Target state:** Next.js 14 проект с App Router, TypeScript, Tailwind CSS, готовый к деплою на Vercel.

**Acceptance:**
1. Проект запускается через `pnpm dev` и доступен на `localhost:3000`
2. App Router: корневой layout, страницы `/` (dashboard), `/transactions`, `/analytics`
3. TypeScript строгий режим (`strict: true`), eslint без ошибок
4. Tailwind CSS: тёмная тема по умолчанию (`class` strategy), кастомные цвета в `tailwind.config.ts`
5. Адаптивная вёрстка: mobile-first, все страницы корректно отображаются на 375px — 1440px
6. Единый layout с навигацией (Bottom Navigation на мобильных, Sidebar на десктопе)

### REQ-02: Google Sheets API Integration

**Current state:** Google Sheets API используется только в Python-боте.
**Target state:** Next.js API routes (serverless functions) читают и пишут данные в Google Sheets через Service Account.

**Acceptance:**
1. API route `GET /api/sheets/transactions` возвращает все транзакции из Google Sheets (JSON)
2. API route `POST /api/sheets/transaction` добавляет новую транзакцию (прокси для бота), возвращает `{success: true}`
3. API route `GET /api/sheets/summary` возвращает агрегированные данные: баланс, доход/расход за период
4. Service Account авторизован через `GOOGLE_SERVICE_ACCOUNT_JSON` переменную окружения (не хардкод)
5. Rate limiting: 60 запросов/мин, при превышении — `429 Too Many Requests` с `Retry-After`
6. Кэширование: in-memory cache с TTL 30 секунд для повторяющихся запросов (снижение нагрузки на Sheets API)

### REQ-03: Dashboard

**Current state:** Нет дашборда.
**Target state:** Главная страница приложения — полная картина финансов на текущий момент.

**Acceptance:**
1. **Карточки баланса:** UAH, USD, EUR — каждая карточка показывает сумму с цветом (зелёный/красный). Общий баланс сверху
2. **Периоды:** три таба "Сегодня", "Неделя", "Месяц" — переключаются без перезагрузки. Каждый показывает доходы, расходы и разницу
3. **Круговая диаграмма:** распределение расходов по категориям за текущий месяц. Интерактивная (при наведении — категория + сумма)
4. **Линейный график:** динамика доходов/расходов по дням за последние 7/30 дней
5. **Последние 5 операций:** мини-таблица с датой, категорией (иконка), суммой, цветом (доход/расход), комментарием
6. **Прогресс-бар бюджета:** если установлен бюджет (Phase 2 данные), показывает сколько потрачено от лимита. Цвет: зелёный < 50%, жёлтый 50-80%, красный > 80%
7. **Фраза Кеши:** над карточками баланса — случайная фраза на основе текущего состояния (много потратил / хорошо экономишь / баланс на нуле)

### REQ-04: Transactions Page

**Current state:** Транзакции доступны только через Telegram-бота (команды /last, /today, /week, /month).
**Target state:** Полноценная страница с таблицей всех транзакций, фильтрацией и поиском.

**Acceptance:**
1. **Таблица:** колонки Дата, Тип (доход/расход), Сумма (в выбранной валюте), Категория (с иконкой), Комментарий, Источник (бот/Monobank)
2. **Фильтры:**
   - По дате: кастомный DateRangePicker (с — по)
   - По категории: выпадающий список с иконками категорий (доходы и расходы раздельно)
   - По типу: все / доход / расход
   - Все фильтры применяются через URL-параметры (shareable state)
3. **Поиск по комментарию:** текстовое поле, debounce 300ms, поиск без перезагрузки страницы
4. **Пагинация:** 20 строк на страницу, кнопки "Назад/Вперёд", номер текущей страницы
5. **Сортировка:** по клику на заголовок колонки (дата, сумма). Индикатор направления сортировки (▲▼)
6. **Сброс фильтров:** одна кнопка "Сбросить всё" очищает все активные фильтры
7. **Прокси-запись:** inline-кнопка "Добавить" открывает форму для быстрой записи расхода/дохода (отправляется в Sheets через API)

### REQ-05: Analytics Page

**Current state:** Нет аналитики, кроме базовых команд в боте.
**Target state:** Страница с графиками и сравнением периодов для глубокого анализа финансов.

**Acceptance:**
1. **Линейный график расходов по месяцам:** за 12 месяцев. Две линии: доходы и расходы. Пересечение показывает "точку безубыточности"
2. **Топ категорий:** горизонтальная столбчатая диаграмма (или круговая) — Top-10 категорий расходов за выбранный период. Остальное — "Прочее"
3. **Сравнение периодов:** два DateRangePicker — Период А vs Период Б. Показывает:
   - Доходы: А → Б (разница в %)
   - Расходы: А → Б (разница в %)
   - Баланс: А → Б (разница в %)
   - Сравнение топ-5 категорий между периодами
4. **Выбор периода:** три кнопки "Месяц", "Квартал", "Год" — переключают масштаб всех графиков
5. **Средние значения:** средний доход/расход в день за выбранный период

### REQ-06: PWA Features

**Current state:** Нет PWA.
**Target state:** Полноценное PWA с возможностью установки на мобильный телефон и базовым офлайн-режимом.

**Acceptance:**
1. **manifest.json:** сгенерирован и содержит `name: "Kesha Finance Tracker"`, `short_name: "Kesha"`, `theme_color: "#0f172a"` (slate-900), `background_color: "#020617"` (slate-950), `display: "standalone"`, `start_url: "/"`, иконки 192x192 и 512x512
2. **Service Worker:** зарегистрирован через `next-pwa` (или SWC). Кэширует статику (CSS, JS, иконки) по стратегии Cache-First, API-запросы — Network-First с fallback на кэш
3. **Кнопка установки:** на мобильных браузерах (Safari/Chrome) показывается промпт установки или инструкция (iOS: "Поделиться → На экран домой")
4. **Офлайн-режим:** при отсутствии интернета показывает кэшированную версию последних данных + заглушку "Вы офлайн. Данные могут быть неактуальны."
5. **Splash screen:** при запуске с экрана телефона показывается splash screen с иконкой и названием
6. **StatusBar:** настроен на тёмную тему (`"display": "standalone"`, meta viewport)

### REQ-07: Styling & Character

**Current state:** Нет веб-дизайна.
**Target state:** Тёмная тема, адаптивный дизайн, анимации, микро-взаимодействия, фразы Кеши на всех страницах.

**Acceptance:**
1. **Тёмная тема по умолчанию:** фон `slate-950`, карточки `slate-900`, текст `slate-100`, акцент `emerald-500` (доход), `rose-500` (расход)
2. **Фразы Кеши:** на каждой странице в header — контекстная фраза (на дашборде — про траты, на транзакциях — "опять кофе?", на аналитике — про бюджет). Фразы из того же пула, что и в боте
3. **Анимации:** плавный fade-in при загрузке страниц, transition на hover для карточек, микроанимации на графиках (Recharts — built-in transitions)
4. **Иконки категорий:** те же эмодзи, что в боте (🍕, 🚕, 💰 и т.д.), отображаются в таблицах и графиках
5. **Responsive:** на мобильных Bottom Navigation Bar, на десктопе — боковое меню. Графики перестраиваются под ширину экрана
6. **Loading states:** skeleton-загрузка для карточек дашборда вместо спиннеров

---

## 3. Boundaries

### In Scope

- Next.js 14 + App Router + TypeScript + Tailwind CSS
- Google Sheets API через Next.js API routes (Service Account)
- PWA: manifest, service worker, офлайн-кэш
- Дашборд с балансом, графики (круговые, линейные), последние операции
- История транзакций с фильтрацией, поиском, пагинацией, сортировкой
- Аналитика: месячные графики, топ категорий, сравнение периодов
- Тёмная тема, адаптивный дизайн, персонаж Кеши
- Деплой на Vercel

### Out of Scope

- Редактирование/удаление транзакций из веба (только просмотр + добавление) — остаётся в Telegram
- Бюджет и лимиты в вебе (управление через бот) — только отображение
- Экспорт из веба — есть в боте (Phase 2)
- Monobank WebHook настройка — Phase 4
- Мультипользовательский режим — личный проект
- Нативное приложение (iOS/Android) — PWA достаточно
- E2E тесты — unit-testing и ручное тестирование
- i18n / локализация — только русский/украинский
- Авторизация и аутентификация — личный проект, данных в Sheets, доступ по ссылке

---

## 4. Constraints

- **Google Sheets API:** 60 запросов/мин, 500 запросов/100 сек. Нужен кэш и rate limiting
- **PWA:** работает только через HTTPS (Vercel предоставляет автоматически)
- **Serverless (Vercel):** cold start до 1 секунды, функция до 10 секунд, 50 MB RAM. Google Sheets запрос может занять 1-3 секунды
- **Service Account:** приватный ключ хранится в переменной окружения (не в репозитории)
- **Next.js 14:** App Router, Server Components vs Client Components — выбор стратегии для каждого компонента
- **Мобильные браузеры:** iOS Safari ограничивает Service Worker (не все офлайн-стратегии работают)
- **Vercel free tier:** 100 GB bandwidth, 100 GB-hours serverless compute — достаточно для личного проекта

---

## 5. Acceptance Criteria (Pass/Fail)

### REQ-01 — Next.js Setup
- [ ] `pnpm dev` запускает проект на `localhost:3000`, страницы `/`, `/transactions`, `/analytics` доступны
- [ ] Bottom Navigation на мобильных (< 768px) и Sidebar на десктопе (>= 768px)
- [ ] `tsconfig.json` содержит `strict: true`, `pnpm lint` без ошибок

### REQ-02 — Google Sheets API
- [ ] `GET /api/sheets/transactions` возвращает массив транзакций (JSON), статус 200
- [ ] `POST /api/sheets/transaction` принимает `{type, amount, category, comment}` и записывает в Sheets, статус 201
- [ ] При 61-м запросе за минуту — ответ `429 Too Many Requests` с `Retry-After`

### REQ-03 — Dashboard
- [ ] Баланс UAH/USD/EUR загружается и отображается в карточках
- [ ] Круговая диаграмма категорий отображается и реагирует на hover
- [ ] Последние 5 операций отображаются с корректными датами, суммами, иконками категорий

### REQ-04 — Transactions Page
- [ ] Таблица отображает все транзакции с пагинацией (20 на страницу)
- [ ] Фильтры по дате + категории + типу работают синхронно (через URL)
- [ ] Поиск по комментарию возвращает результаты с debounce

### REQ-05 — Analytics Page
- [ ] Линейный график за 12 месяцев отображает доходы и расходы двумя линиями
- [ ] Сравнение двух периодов показывает разницу в % по доходам, расходам, балансу
- [ ] Переключение Месяц/Квартал/Год меняет масштаб всех графиков

### REQ-06 — PWA
- [ ] Lighthouse PWA audit: все три чекпоинта пройдены (installable, configured, fast)
- [ ] Service Worker зарегистрирован и кэширует статику (проверка через DevTools → Application → Service Workers)
- [ ] При установке на экран дома на Android/iOS приложение открывается без браузерных элементов (standalone)

### REQ-07 — Styling
- [ ] Тёмная тема: фон `slate-950`, все страницы соответствуют цветовой схеме
- [ ] Фраза Кеши присутствует на каждой странице и меняется при обновлении данных
- [ ] Анимации: fade-in при переходе между страницами, skeleton loading при загрузке данных

---

## 6. Module Map

```
web/
├── app/                              # Next.js App Router
│   ├── layout.tsx                    # Root layout: theme, fonts, PWA meta
│   ├── page.tsx                      # Dashboard (главная страница)
│   ├── loading.tsx                   # Skeleton loading для dashboard
│   │
│   ├── transactions/
│   │   ├── page.tsx                  # Transactions page (Client Component)
│   │   └── loading.tsx               # Skeleton для таблицы
│   │
│   ├── analytics/
│   │   ├── page.tsx                  # Analytics page (Client Component)
│   │   └── loading.tsx               # Skeleton для графиков
│   │
│   └── api/
│       └── sheets/
│           ├── route.ts              # GET /api/sheets/transactions
│           ├── transaction/
│           │   └── route.ts          # POST /api/sheets/transaction
│           └── summary/
│               └── route.ts          # GET /api/sheets/summary?period=month
│
├── components/
│   ├── layout/
│   │   ├── BottomNav.tsx             # Мобильная нижняя навигация
│   │   ├── Sidebar.tsx               # Десктопный сайдбар
│   │   ├── Header.tsx                # Верхняя панель + фраза Кеши
│   │   └── MobileNav.tsx             # Адаптивный переключатель
│   │
│   ├── dashboard/
│   │   ├── BalanceCards.tsx          # Карточки UAH/USD/EUR баланса
│   │   ├── PeriodTabs.tsx            # Сегодня / Неделя / Месяц
│   │   ├── CategoryPieChart.tsx      # Круговая диаграмма (Recharts)
│   │   ├── DailyLineChart.tsx        # Линейный график (Recharts)
│   │   ├── RecentTransactions.tsx    # Последние 5 операций
│   │   ├── BudgetProgressBar.tsx     # Прогресс-бар бюджета
│   │   └── KeshaQuote.tsx            # Фраза Кеши
│   │
│   ├── transactions/
│   │   ├── TransactionsTable.tsx     # Таблица транзакций
│   │   ├── FiltersBar.tsx            # Фильтры: дата, категория, тип
│   │   ├── SearchInput.tsx           # Поиск по комментарию
│   │   ├── Pagination.tsx            # Пагинация
│   │   ├── SortHeader.tsx            # Заголовок с сортировкой
│   │   └── AddTransactionForm.tsx    # Форма быстрой записи
│   │
│   ├── analytics/
│   │   ├── MonthlyChart.tsx          # Линейный график по месяцам
│   │   ├── TopCategories.tsx         # Топ-10 категорий
│   │   ├── PeriodComparer.tsx        # Сравнение двух периодов
│   │   ├── PeriodSelector.tsx        # Месяц/Квартал/Год
│   │   └── DailyAverages.tsx         # Средние значения
│   │
│   └── ui/
│       ├── Card.tsx                  # Карточка (базовый компонент)
│       ├── Badge.tsx                 # Бейдж дохода/расхода
│       ├── Skeleton.tsx              # Скелетон загрузки
│       ├── DateRangePicker.tsx       # Выбор диапазона дат
│       ├── Select.tsx                # Кастомный select
│       └── Icon.tsx                  # Эмодзи-иконка категории
│
├── lib/
│   ├── sheets.ts                     # Google Sheets API клиент (Service Account)
│   │   ├── getTransactions()         # GET транзакции
│   │   ├── addTransaction(data)      # POST транзакция
│   │   ├── getSummary(period)        # GET агрегированные данные
│   │   └── getRates()                # Курсы валют
│   │
│   ├── cache.ts                      # In-memory cache с TTL
│   │   ├── get(key, fetchFn, ttl)    # Кэшированный запрос
│   │   └── invalidate(key)           # Сброс кэша
│   │
│   ├── rateLimiter.ts                # Rate limiter (sliding window)
│   │   ├── check(key, limit, window) # Проверка лимита
│   │   └── getRemaining(key)         # Оставшиеся запросы
│   │
│   ├── quotes.ts                     # Фразы Кеши для веба
│   │   ├── getQuote(context)         # Фраза по контексту
│   │   └── QUOTES_WEB                # Массив фраз (синхронизирован с ботом)
│   │
│   ├── formatters.ts                 # Форматирование
│   │   ├── formatCurrency(amount, currency)
│   │   ├── formatDate(date, format)
│   │   └── formatPeriodLabel(period)
│   │
│   └── types.ts                      # Общие типы
│       ├── Transaction
│       ├── Summary
│       ├── Category
│       └── Period
│
├── public/
│   ├── icons/
│   │   ├── icon-192x192.png          # PWA иконка 192x192
│   │   ├── icon-512x512.png          # PWA иконка 512x512
│   │   └── maskable-icon.png         # Maskable иконка
│   │
│   └── manifest.json                 # PWA manifest (или через next-pwa)
│
├── tailwind.config.ts                # Кастомные цвета, тёмная тема
├── next.config.ts                    # PWA плагин, headers
├── tsconfig.json                     # strict: true
├── package.json
└── pnpm-lock.yaml
```

### Порядок реализации модулей (рекомендуемый)

| Шаг | Модуль | Зависимости | Описание |
|-----|--------|-------------|----------|
| 1 | `next.config.ts`, `tsconfig.json`, `tailwind.config.ts` | — | Инициализация проекта |
| 2 | `lib/types.ts`, `lib/formatters.ts` | — | База: типы и форматтеры |
| 3 | `lib/sheets.ts`, `lib/cache.ts`, `lib/rateLimiter.ts` | types.ts | Google Sheets API клиент |
| 4 | `app/api/sheets/*/route.ts` | sheets.ts, cache.ts | API routes |
| 5 | `components/ui/*` | — | UI-кит (Card, Skeleton, Badge, etc.) |
| 6 | `components/dashboard/*` | ui, api | Компоненты дашборда |
| 7 | `app/page.tsx` | dashboard/* | Главная страница |
| 8 | `components/transactions/*` | ui, api | Компоненты транзакций |
| 9 | `app/transactions/page.tsx` | transactions/* | Страница транзакций |
| 10 | `components/analytics/*` | ui, api | Компоненты аналитики |
| 11 | `app/analytics/page.tsx` | analytics/* | Страница аналитики |
| 12 | `components/layout/*` | все компоненты | Layout: BottomNav, Sidebar, Header |
| 13 | `app/layout.tsx` | layout/* | Root layout + PWA meta |
| 14 | `public/manifest.json`, `public/icons/*` | — | PWA assets |
| 15 | `next.config.ts` (PWA) | manifest | Service Worker + PWA настройка |
| 16 | `lib/quotes.ts` | — | Фразы Кеши для веба |
| 17 | Deploy на Vercel | всё | CI/CD, env variables |

---

## 7. Open Questions

1. **Дизайн — откуда брать?** Нужен ли полноценный дизайн-макет (Figma) или достаточно описания в SPEC и реализации на глаз? Для PWA better-safe: можно взять shadcn/ui как базовый UI-кит (стилизовать под Кешу).
2. **Графики — библиотека?** Recharts (проверенная, React-native) или Tremor (дашборд-специфичная)? Recharts более гибкая для кастомных стилей. Tremor даёт готовые дашборд-компоненты. Рекомендация: Recharts + кастомная стилизация.
3. **Monobank данные в вебе?** Phase 4 ещё не завершена. На момент Phase 3 в Sheets только данные из бота. Monobank-транзакции появятся в вебе после Phase 4. Показывать заглушку "Monobank интеграция скоро" или просто не упоминать?
4. **Офлайн-режим — насколько глубокий?** Просто показывать "Вы офлайн" с кэшированными данными или реализовать полноценную IndexedDB синхронизацию для добавления транзакций офлайн? Для v1 достаточно read-only офлайн.
5. **Next.js — Server vs Client Components?** Dashboard/Transactions/Analytics — почти 100% интерактив (графики, фильтры, поиск). Всё делать Client Components или выносить статические части в Server Components? Рекомендация: страницы — Client Components (use client), layout — Server Component, API routes — Serverless Functions.
6. **Прокси-запись транзакций из веба — нужна ли синхронизация с ботом?** Если пользователь добавил транзакцию через веб, должен ли бот подтвердить? Или просто записываем в Sheets и готово? Логичнее: запись в Sheets без подтверждения бота.
7. **Мобильная навигация — Bottom Navigation на всех страницах или скрывать на аналитике?** Стандарт: Bottom Nav на всех основных страницах. Аналитика — тоже основная страница.

---

*SPEC.md generated: 2026-05-31*
*Requirements locked: 7*
*Estimated acceptance criteria: 25*
