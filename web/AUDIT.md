# Design Audit: Kesha Web App

**Дата:** 2026-05-31
**Методология:** Visual-Companion (5 осей) + Impeccable (4 оси)
**Охват:** 20 файлов (компоненты, страницы, CSS, конфигурация)

---

## Методология

### Visual-Companion (Superpowers)
| Ось | Оценка |
|-----|--------|
| Purpose | 🟡 6/10 |
| Tone | 🟢 8/10 |
| Constraints | 🟢 8/10 |
| Differentiation | 🟡 6/10 |
| UX Laws | 🟡 5/10 |

### Impeccable
| Ось | Оценка |
|-----|--------|
| Consistency | 🔴 2/10 |
| Spacing | 🟡 6/10 |
| Typography | 🟡 5/10 |
| Anti-patterns | 🟡 4/10 |

---

## Результаты

### 🟢 Сильные стороны

**1. Персонаж Кеши — последовательный и живой**
- Header с цитатами (`getRandomQuote`) — сильный брендовый ход
- BalanceCard: «Кеша доволен. Пока.» / «Кеша в шоке. Хомяк, ты серьёзно?»
- BudgetCard: «Кеша живёт одним днём.»
- RecentTransactions: «Кеша живёт интуитивно.»
- PeriodCompare: развёрнутые комментарии с анализом динамики

**2. Mobile-first архитектура**
- `max-w-lg` (512px) на всех страницах
- BottomNav с `pb-safe` для iOS safe-area
- Sticky header с `backdrop-blur`

**3. PWA setup — полный**
- `manifest.json`, `apple-mobile-web-app-capable`, `themeColor`
- ThemeScript в `<head>` предотвращает flash неправильной темы
- Системный шрифт (не Inter) — соответствует anti-pattern рекомендациям

**4. Доступность**
- `focus-visible:ring-2` на интерактивных элементах
- Минимальные touch-targets 44×44px
- `prefers-reduced-motion` в глобальных стилях

**5. DESIGN.md — качественная документация**
- Полная система токенов (цвета, отступы, типографика, скругления)
- Tailwind-классы `kesha-*` правильно зарегистрированы в конфиге
- Механизм тем описан детально

**6. Нет AI-slop**
- Нет rainbow gradients, sparkle-анимаций, «cute» иконок
- Системный шрифт вместо Inter
- Чистый, функциональный дизайн без украшательств

---

### 🟡 Что улучшить

**1. Персонаж Кеши не везде**
- DailyStatsCard, TransactionsPage, AnalyticsPage вообще без комментариев персонажа
- MonthlyChart, CategoryPieChart — чисто технические, нет personality

**2. Слоган нигде не отображается**
- «Трать с умом, хомяк» из DESIGN.md отсутствует в UI
- Предложение: добавить в `<title>` или как подзаголовок в Header

**3. Эмодзи-категории неконсистентны**
- `RecentTransactions` и `TransactionTable` используют разные маппинги эмодзи
- `RecentTransactions`: `categoryEmoji` с 40+ ключами (substring matching)
- `TransactionTable`: `CATEGORY_EMOJI` с 16 ключами (exact matching)
- Ни один не импортирован из общего источника

**4. Форматирование сумм дублируется**
- `formatAmount` определена в BalanceCard, BudgetCard, DailyStatsCard, RecentTransactions
- Должна быть в `@/lib/formatters` и переиспользоваться

**5. Захардкоженные цвета в Recharts**
- MonthlyChart: `stroke="#334155"`, `stroke="#94a3b8"`, фон тултипа `#1e293b`
- CategoryPieChart: `PIE_COLORS` — статический массив без учёта темы
- PeriodCompare: селекты с `bg-slate-800/70`, `border-slate-700/50`
- Не работают в светлой теме

**6. Отсутствует динамический импорт**
- Аналитика (Recharts) грузится сразу, а не лениво
- Тяжёлая библиотека (~120KB gzip) загружается на старте

**7. Баг: мусорный символ в CategoryPieChart**
- Строка: `«Кеша подозревает, что ты或 живёшь за счёт воздуха.»`
- Символ `或` — опечатка/артефакт копирования

**8. Нет анимации для цитат в Header**
- Цитата меняется только при маунте компонента
- Можно добавить ротацию с интервалом или смену при навигации

---

### 🔴 Проблемы

**1. КРИТИЧЕСКАЯ: Цвета захардкожены — светлая тема НЕ РАБОТАЕТ**

Проблема: компоненты используют прямые Tailwind-классы (`slate-800`, `slate-200`, `emerald-400`) вместо `kesha-*` CSS-переменных.

| Компонент | Хардкод | Должно быть |
|-----------|---------|-------------|
| `page.tsx` ошибка | `bg-slate-800/50 border-slate-700/50` | `bg-kesha-card border-kesha-border` |
| `page.tsx` кнопка обновления | `bg-slate-800/50 border-slate-700/50` | `bg-kesha-card border-kesha-border` |
| `BalanceCard` доход | `text-emerald-400` | `text-kesha-income` |
| `BalanceCard` второстепенный текст | `text-slate-400`, `text-slate-500` | `text-kesha-text-secondary`, `text-kesha-text-tertiary` |
| `DailyStatsCard` весь | `text-slate-400`, `border-slate-700/50` | `text-kesha-text-secondary`, `border-kesha-border` |
| `BudgetCard` весь | `text-slate-400`, `text-slate-500`, `text-emerald-400` | kesha-* эквиваленты |
| `RecentTransactions` весь | `divide-slate-700/30`, `text-slate-200` | `divide-kesha-border`, `text-kesha-text-primary` |
| `TransactionFilters` | `bg-slate-800/70`, `border-slate-700/50` | `bg-kesha-card`, `border-kesha-border` |
| `TransactionTable` мобильные карточки | `bg-slate-800/30`, `border-slate-700/30` | `bg-kesha-card`, `border-kesha-border` |
| `TransactionTable` десктоп | `border-slate-700/50`, `text-slate-300` | kesha-* эквиваленты |
| `Pagination` | `bg-slate-700/50`, `text-slate-400` | `bg-kesha-card-hover`, `text-kesha-text-secondary` |
| `AnalyticsPage` кнопки периода | `bg-slate-800/50`, `text-slate-400`, `bg-amber-400/15` | kesha-* эквиваленты |
| `AnalyticsPage` quick-stats | `bg-slate-800/30` | `bg-kesha-card` |
| `PeriodCompare` селекты | `bg-slate-800/70`, `border-slate-700/50` | kesha-* эквиваленты |
| `PeriodCompare` комментарий | `bg-slate-800/50`, `text-slate-400` | `bg-kesha-card`, `text-kesha-text-secondary` |
| `MonthlyChart` грид, оси | `stroke="#334155"`, `stroke="#94a3b8"` | CSS-переменные через inline style |

**Масштаб:** ~80% компонентов используют хардкоженные цвета. Только `Card`, `Badge`, `ProgressBar`, `Header`, `BottomNav` используют `kesha-*` классы.

**Влияние:** Светлая тема визуально сломана. При включении светлой темы (через `prefers-color-scheme: light`) компоненты остаются тёмными.

**2. СЕРЬЁЗНАЯ: Нарушение 8px grid в Card**

DESIGN.md: Card padding = `p-4` (16px)
Фактически: `px-5 pt-5 pb-3` = 20px / 20px / 12px — ни одно значение не в сетке.

| Компонент | Факт | По DESIGN.md |
|-----------|------|-------------|
| Card (wrapper) | Нет padding | `p-4` |
| CardHeader | `px-5 pt-5 pb-3` | `p-4` |
| CardContent | `px-5 pb-5 pt-1` | `px-4 pb-4 pt-0` |
| Header | `py-3` (12px) | `py-2` или `py-4` (8px или 16px) |
| BottomNav ссылки | `py-2 px-4` | ✅ OK |
| Баланс валюта | `mt-3` (12px) | `mt-2` или `mt-4` |

**3. Типографическая иерархия нарушена**

| Элемент | Факт | По DESIGN.md |
|---------|------|-------------|
| Dashboard H1 | `text-xl` | `text-2xl` (Hero/H1) |
| Баланс | `text-4xl` | `text-3xl` (Balance) |
| Числа | `tabular-nums` без `font-mono` | `tabular-nums font-mono` |
| CardTitle | `text-sm uppercase` | Совпадает с секционным заголовком, но это label-стиль |

**4. Антипаттерн: карточки-в-карточках**

`AnalyticsPage` содержит вложенные `bg-slate-800/30 rounded-lg p-3` внутри `Card` для quick-stats.
Это именно тот anti-pattern, который Impeccable предписывает избегать.

`TransactionTable` (mobile): `rounded-lg border border-slate-700/30 bg-slate-800/30 p-3` — фактически мини-карточка внутри Card.

**5. Income/expense цвета не используют токены**

Вместо `text-kesha-income` используется `text-emerald-400`, вместо `text-kesha-expense` — `text-red-400`. Это делает тему нефункциональной для этих цветов.

**6. CSS-переменные для income/expense-bg НЕ ИСПОЛЬЗУЮТСЯ**

`--color-income-bg`, `--color-expense-bg`, `--color-accent-bg` определены в globals.css и DESIGN.md, но используются только в `Badge`. Skeleton используют `bg-kesha-border` (правильно), но загрузочные состояния на страницах используют хардкод `bg-slate-700/50 animate-pulse`.

---

## Приоритизированные рекомендации

### 🔴 P0 — Критические (ломают светлую тему)

1. **Мигрировать все хардкоженные цвета на `kesha-*` токены**
   - Заменить `slate-*`, `emerald-*`, `red-*`, `amber-*` на соответствующие `kesha-*` классы во всех компонентах
   - Особое внимание: `text-emerald-400` → `text-kesha-income`, `text-red-400` → `text-kesha-expense`
   - Заменить `bg-slate-800/50`, `bg-slate-800/30` → `bg-kesha-card`
   - Заменить `border-slate-700/50`, `border-slate-700/30` → `border-kesha-border`

2. **Добавить недостающие Tailwind-классы**
   - `divide-kesha-border` (для разделителей списков)
   - `text-kesha-income`, `text-kesha-expense` — проверить, что они есть в конфиге (уже есть: `kesha.income` и `kesha.expense`)

### 🟡 P1 — Важные (качество и консистентность)

3. **Привести Card-отступы к 8px grid**
   - CardHeader: `px-5 pt-5 pb-3` → `p-4`
   - CardContent: `px-5 pb-5 pt-1` → `px-4 pb-4 pt-0`
   - Или: явно задокументировать отклонение в DESIGN.md

4. **Убрать карточки-в-карточках из AnalyticsPage**
   - Quick-stats оформить как inline-flex элементы с разделителями, а не вложенными контейнерами

5. **Вынести `formatAmount` в `@/lib/formatters`**
   - Убрать дублирование из 4 компонентов
   - Импортировать из одного источника

6. **Унифицировать эмодзи-категорий**
   - Создать `lib/category-emoji.ts` с единым маппингом
   - Использовать его в `RecentTransactions` и `TransactionTable`

7. **Исправить типографию**
   - Dashboard H1: `text-xl` → `text-2xl font-bold tracking-tight`
   - Balance: `text-4xl` → `text-3xl font-bold tabular-nums tracking-tight`
   - Добавить `font-mono` ко всем числовым значениям где нужны `tabular-nums`
   - Проверить, что `font-mono` в tailwind.config указывает на моноширинную систему

### 🟢 P2 — Улучшения (полировка)

8. **Добавить комментарии Кеши на все страницы**
   - DailyStatsCard: реакция на дневной баланс
   - TransactionsPage: приветствие/комментарий при пустом результате фильтрации
   - MonthlyChart: комментарий к тренду

9. **Ленивая загрузка аналитики**
   - `next/dynamic` для `MonthlyChart`, `CategoryPieChart`, `PeriodCompare`

10. **Исправить баг с мусорным символом**
    - CategoryPieChart: убрать `或` из строки

11. **Ротация цитат в Header**
    - Интервал 30 секунд или смена при переходе между страницами

12. **Recharts: темизация через CSS-переменные**
    - Вынести цвета осей/грида/тултипов в `globals.css` как переменные
    - Использовать inline `style` для передачи значений

---

## Файлы, требующие изменений

| Файл | Приоритет | Проблемы |
|------|-----------|----------|
| `app/page.tsx` | P0 | Хардкод цвета, нарушение типографики |
| `components/dashboard/BalanceCard.tsx` | P0 | Хардкод текстовых цветов |
| `components/dashboard/DailyStatsCard.tsx` | P0 | Хардкод всех цветов |
| `components/dashboard/BudgetCard.tsx` | P0 | Хардкод всех цветов |
| `components/dashboard/RecentTransactions.tsx` | P0 | Хардкод цветов, дублирование emoji-map, formatAmount |
| `components/ui/Card.tsx` | P1 | Отступы не в 8px grid |
| `app/analytics/page.tsx` | P0/P1 | Хардкод цветов, карточки-в-карточках |
| `components/analytics/MonthlyChart.tsx` | P1 | Хардкод SVG-цветов |
| `components/analytics/CategoryPieChart.tsx` | P1 | Хардкод SVG-цветов, баг с символом |
| `components/analytics/PeriodCompare.tsx` | P0 | Хардкод цветов |
| `components/transactions/TransactionFilters.tsx` | P0 | Хардкод всех цветов |
| `components/transactions/TransactionTable.tsx` | P0 | Хардкод цветов, дублирование emoji-map, карточки-в-карточках (mobile) |
| `components/transactions/Pagination.tsx` | P0 | Хардкод цветов |
| `app/transactions/page.tsx` | P0 | Хардкод цветов в скелетонах |
| `app/globals.css` | P2 | Добавить переменные для chart-цветов |
| `lib/category-emoji.ts` | P1 | НОВЫЙ ФАЙЛ — единый маппинг эмодзи |
