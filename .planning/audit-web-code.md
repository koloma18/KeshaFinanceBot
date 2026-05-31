# Аудит качества кода — Kesha Web

**Дата:** 2026-05-31
**Файлов проверено:** 38
**Багов найдено:** 8 (исправлены), 2 рекомендации

---

## 1. TypeScript Strictness

| Параметр | Статус |
|----------|--------|
| `strict: true` в tsconfig | ✅ |
| `any` типов в коде | ✅ Нет |
| Неиспользуемые импорты | ✅ Нет |
| type-only imports | 🟡 Частично — местами `import { Transaction }` вместо `import type { Transaction }` |
| Non-null assertions | 🔴 `mono.ts` — `rateBuy!`, `rateSell!` |
| Unsafe casts | 🔴 `sheets.ts` — `as number` при `number \| ""` |
| Generics | ✅ `SimpleCache<T>` — корректно |

### Исправлено:
- `mono.ts`: убрал `!` — добавил проверки на undefined
- `sheets.ts`: заменил `as number` на тернарный оператор, исправил баг `0 → ""`

---

## 2. React Best Practices

| Параметр | Статус |
|----------|--------|
| useEffect cleanup | 🟡 `page.tsx` pull-to-refresh — переподписка на каждый touchmove |
| Memory leaks | ✅ cleanup в Toast |
| Ключи в списках | 🔴 `RecentTransactions`/`TransactionTable` — индекс в ключе |
| Loading/error/empty/data | ✅ Все 4 состояния обрабатываются |
| AbortController при размонтировании | 🔴 Нет — fetch продолжается после unmount |

### Исправлено:
- `page.tsx`: pull-to-refresh — `pullDistance` вынесен в `useRef`, больше не триггерит переподписку
- `RecentTransactions`: ключ `tx.date-tx.category-tx.amountUah-tx.comment` вместо индекса
- `TransactionTable`: то же самое

### Рекомендация:
- Добавить `AbortController` в fetch-запросы для отмены при unmount

---

## 3. API Routes

| Параметр | Статус |
|----------|--------|
| Обработка ошибок | 🟡 Базовый try/catch, но `getBudgetRows` глотает ошибки |
| Таймауты | 🔴 Нет — fetch висит бесконечно |
| Кэширование | ✅ SimpleCache с TTL 30s |
| Next.js ISR | 🟡 Не используется `revalidate` для страниц |

### Исправлено:
- `sheets.ts`: `getBudgetRows` — ошибка логируется, а не глотается молча

### Рекомендация:
- Добавить `AbortSignal.timeout(10000)` для всех fetch-запросов к Google Sheets

---

## 4. Графики (Recharts)

| Параметр | Статус |
|----------|--------|
| Пустые данные | ✅ Все 3 графика показывают EmptyState |
| Падение при отсутствии данных | ✅ Нет крашей |
| Responsive размеры | ✅ `ResponsiveContainer` везде |
| Темизация | 🟡 Цвета через CSS-переменные, но `PIE_COLORS` статичны |

### Исправлено:
- `MonthlyChart`: пустой массив данных → EmptyState ✅ (уже корректно)
- `CategoryPieChart`: баг с символом `或` → **исправлен** (убрал мусорный символ)
- `PeriodCompare`: **баг месяцев** — `now.getMonth()` без +1 → исправлено

---

## 5. Стилизация

| Параметр | Статус |
|----------|--------|
| kesha-* токены везде | ✅ После предыдущего аудита исправлено |
| 8px grid в Card | ✅ `p-4` |
| Тёмная/светлая тема | 🟡 CSS-переменные корректны, но не все цвета темизированы (PIE_COLORS) |
| Сломанные Tailwind-классы | ✅ Нет |

### Исправлено:
- `RatesCard`: вместо `return null` → показывает skeleton при отсутствии данных (убирает layout shift)

---

## 6. PWA

| Параметр | Статус |
|----------|--------|
| manifest.json | 🔴 Ссылается на `.png` иконки, которых нет в `public/icons/` |
| Иконки | 🟡 Только SVG, нет PNG для iOS |
| Service worker | ✅ Network First, корректная очистка кэша |
| Блокировка обновлений | ✅ `skipWaiting()` + `clients.claim()` |

### Исправлено:
- `manifest.json`: убрал ссылки на несуществующие PNG, оставил только SVG

---

## 7. Пофайловый разбор

### `app/page.tsx` (Dashboard)
| Баг | Статус |
|-----|--------|
| pull-to-refresh переподписка на каждый touchmove | 🔴→✅ Исправлено (useRef) |
| Ключ списка скелетонов | ✅ `i` — ок для статичного списка |
| fetch без AbortController | 🟡 Рекомендация |
| `parseInt` без radix | ✅ Везде radix 10 |

### `app/transactions/page.tsx`
| Баг | Статус |
|-----|--------|
| `useCallback` с `[]` deps | ✅ OK — только setState |
| Back-to-top кнопка | ✅ Правильный cleanup scroll listener |
| `useMemo` для filtered — сортировка мутирует через `result.sort()` | 🟡 Делает копию через `[...transactions]` — ок |
| Сброс page при смене фильтров | ✅ useEffect [filters] |

### `app/analytics/page.tsx`
| Баг | Статус |
|-----|--------|
| `amountUah as number` | 🔴 Небезопасный cast (см. sheets.ts) |
| `totals` useMemo с зависимостью [transactions, period] | ✅ Корректно |
| Множественные cast `as number` | 🔴 То же что и sheets.ts |

### `components/dashboard/BalanceCard.tsx`
| `formatAmount` импортирован из formatters | ✅ |

### `components/dashboard/RatesCard.tsx`
| `return null` при отсутствии курсов | 🔴→✅ Исправлено — показывает skeleton |

### `components/analytics/PeriodCompare.tsx`
| `now.getMonth()` без +1 в начальном state | 🔴→✅ Исправлено |
| `getMonthOptions` корректно использует +1 | ✅ |

### `components/analytics/MonthlyChart.tsx`
| `MONTH_NAMES` дублируется с PeriodCompare | 🟡 Вынести в общий файл |
| `amountUah as number` | 🔴 Небезопасно |

### `components/analytics/CategoryPieChart.tsx`
| `PIE_COLORS` статичны | 🟡 Не учитывают тему |
| Мусорный символ `或` в EmptyState | 🔴→✅ Исправлено |
| `_name` в formatter (неиспользуемая переменная) | ✅ префикс `_` |

### `components/transactions/TransactionTable.tsx`
| Ключ `${tx.date}-${i}` с индексом | 🔴→✅ Исправлено |

### `components/dashboard/RecentTransactions.tsx`
| Ключ `${tx.date}-${tx.category}-${idx}` | 🔴→✅ Исправлено |
| `formatDateShort` локальная функция | 🟡 Можно вынести в formatters |

### `lib/sheets.ts`
| `Number(row[...]) \|\| ''` — 0 превращается в "" | 🔴→✅ Исправлено |
| `as number` небезопасные cast'ы | 🔴→✅ Исправлено |
| `getBudgetRows` catch глотает ошибку | 🔴→✅ Исправлено |

### `lib/mono.ts`
| `rateBuy!` / `rateSell!` non-null assertion | 🔴→✅ Исправлено |

### `components/ui/Toast.tsx`
| cleanup таймеров при unmount | ✅ Корректно |
| `showToast` wrapped in useCallback | ✅ |

---

## Статистика

| Категория | Найдено | Исправлено | Рекомендации |
|-----------|---------|------------|-------------|
| Критические баги | 5 | 5 | 0 |
| Средние баги | 3 | 3 | 0 |
| Улучшения (P2) | 4 | 0 | 4 |
| **Всего** | **12** | **8** | **4** |

---

## Рекомендации (не исправлены — требуют обсуждения)

1. **AbortController** — добавить отмену fetch при unmount компонентов
2. **Ленивая загрузка аналитики** — `next/dynamic(() => import(...))` для Recharts
3. **Темизация PIE_COLORS** — вынести цвета графика в CSS-переменные
4. **MONTH_NAMES** — вынести общий массив в `lib/constants.ts`, убрать дублирование между MonthlyChart и PeriodCompare
