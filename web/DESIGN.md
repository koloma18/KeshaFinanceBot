# Kesha Design System

## Brand Identity
- **Название:** Kesha (Кеша)
- **Слоган:** «Трать с умом, хомяк»
- **Персонаж:** Кеша — саркастичный бурундук, следит за финансами и не даёт спускать деньги на ерунду
- **Tone of Voice:** дерзкий, с юмором, но не злой. Русский/украинский суржик. Короткие фразы, иногда с намёком на бурундучьи привычки («Орехи подорожали, ты в курсе?»)

## Logo
- **Файл:** `public/logo.svg`
- **Концепция:** геометрическая буква «K» со скруглёнными углами и элементом жёлудя — отсылка к запасливому бурундуку
- **Стиль:** tech + finance (Stripe, Linear, Raycast) — жирные линии, скругления, без засечек
- **Варианты:** полный логотип (K + жёлудь на фоне), иконка (только K, без фона)

## Colors

Цвета реализованы через CSS-переменные с поддержкой светлой и тёмной темы.
Тема определяется автоматически через `prefers-color-scheme` или сохраняется в `localStorage`.

### Тёмная тема (`.dark` / system auto-dark)

| Token | Hex | CSS Variable | Usage |
|-------|-----|-------------|-------|
| Background | `#020617` | `--color-page` | Фон страницы |
| Surface | `#1e293b` / 50% | `--color-card` | Карточки |
| Accent | `#fbbf24` | `--color-accent` | Кнопки, акценты |
| Income | `#34d399` | `--color-income` | Доходы |
| Expense | `#f87171` | `--color-expense` | Расходы |
| Text Primary | `#f1f5f9` | `--color-text-primary` | Основной текст |
| Text Secondary | `#94a3b8` | `--color-text-secondary` | Второстепенный текст |
| Text Tertiary | `#64748b` | `--color-text-tertiary` | Плейсхолдеры |
| Border | `#334155` / 50% | `--color-border` | Разделители |

### Светлая тема (`:root` default)

| Token | Hex | Usage |
|-------|-----|-------|
| Background | `#f8fafc` (slate-50) | Фон страницы |
| Surface | `#ffffff` | Карточки |
| Accent | `#d97706` (amber-600) | Кнопки, акценты |
| Income | `#059669` (emerald-600) | Доходы |
| Expense | `#dc2626` (red-600) | Расходы |
| Text Primary | `#0f172a` (slate-900) | Основной текст |
| Text Secondary | `#475569` (slate-600) | Второстепенный текст |
| Text Tertiary | `#94a3b8` (slate-400) | Плейсхолдеры |
| Border | `#e2e8f0` (slate-200) | Разделители |

### Tailwind-классы

В компонентах используй `kesha-*` классы из `tailwind.config.ts`:

```
bg-kesha-page          → var(--color-page)
bg-kesha-card          → var(--color-card)
border-kesha-border    → var(--color-border)
text-kesha-accent      → var(--color-accent)
text-kesha-income      → var(--color-income)
text-kesha-expense     → var(--color-expense)
text-kesha-text-primary   → var(--color-text-primary)
text-kesha-text-secondary → var(--color-text-secondary)
text-kesha-text-tertiary  → var(--color-text-tertiary)
bg-kesha-income-bg     → var(--color-income-bg)
bg-kesha-expense-bg    → var(--color-expense-bg)
bg-kesha-accent-bg     → var(--color-accent-bg)
```

### Механизм переключения

1. При загрузке — `ThemeScript` в `<head>` проверяет `localStorage.theme`
2. Если сохранённой темы нет — смотрит `prefers-color-scheme`
3. Ставит класс `dark` или `light` на `<html>`
4. CSS-переменные в `:root`, `.dark` и `@media (prefers-color-scheme: dark)` определяют цвета

## Typography

```
Font Family: system-ui, -apple-system, BlinkMacSystemFont,
             'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif
```

| Role | Classes | Example |
|------|---------|---------|
| Hero / H1 | `text-2xl font-bold tracking-tight` | Сводка |
| Section H2 | `text-lg font-semibold tracking-tight` | Категории |
| H3 | `text-base font-semibold` | Названия карточек |
| Body | `text-sm leading-relaxed` | Основной текст |
| Caption | `text-xs text-slate-400` | Даты, подписи |
| Numbers | `text-sm tabular-nums font-mono` | Суммы в таблицах |
| Balance | `text-3xl font-bold tabular-nums tracking-tight` | Баланс на главной |

## Spacing Scale

| Token | Value | Tailwind |
|-------|-------|----------|
| xs | 4px | `p-1` / `gap-1` |
| sm | 8px | `p-2` / `gap-2` |
| md | 16px | `p-4` / `gap-4` |
| lg | 24px | `p-6` / `gap-6` |
| xl | 32px | `p-8` / `gap-8` |

### Layout
- **Page padding:** `px-4` (16px)
- **Content max-width:** `max-w-lg` (512px — мобильный first)
- **Bottom nav height:** 56px + `pb-safe` (safe-area для iOS)
- **Header height:** 48px

## Border Radius

| Token | Value | Tailwind | Usage |
|-------|-------|----------|-------|
| btn | 8px | `rounded-lg` | Кнопки, inputs |
| card | 12px | `rounded-xl` | Карточки, модалки |
| pill | 9999px | `rounded-full` | Бейджи, чипсы, аватар Кеши |

## Shadows

Карточки используют тонкую обводку вместо теней (flat design). Тени — только для модалок и попапов:

- **Modal:** `shadow-2xl shadow-black/40`
- **Toast:** `shadow-lg shadow-black/30`

## Components

### Card
```
bg-kesha-card border border-kesha-border rounded-xl p-4
```

### Button Primary
```
bg-kesha-accent text-white rounded-lg px-4 py-2.5 font-semibold
hover:opacity-90 active:scale-[0.98] transition-all
```

### Button Secondary
```
bg-kesha-card border border-kesha-border text-kesha-text-primary rounded-lg px-4 py-2.5
hover:bg-kesha-card-hover active:scale-[0.98] transition-all
```

### Input
```
bg-kesha-card border border-kesha-border rounded-lg px-3 py-2 text-sm
focus:border-amber-400/50 focus:ring-1 focus:ring-amber-400/20 outline-none
placeholder:text-kesha-text-tertiary
```

### Progress Bar
Полоса прогресса бюджета: заполненная часть — `bg-kesha-accent`, пустая — `bg-kesha-border`.
```
<div class="h-2 rounded-full bg-kesha-border overflow-hidden">
  <div class="h-full bg-kesha-accent rounded-full" style="width: 65%"/>
</div>
```

### Badge / Chip
```
bg-kesha-income-bg text-kesha-income border-kesha-income-border  // доход
bg-kesha-expense-bg text-kesha-expense border-kesha-expense-border  // расход
bg-kesha-accent-bg text-kesha-accent border-kesha-accent-border  // предупреждение
inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium
```

### Transaction Item
```
flex items-center justify-between py-3 border-b border-kesha-border last:border-0
```

## Icons

- **Библиотека:** Lucide React (`lucide-react`)
- **Эмодзи:** для категорий (🍔 Еда, 🚗 Транспорт, 🎮 Развлечения)
- **PWA-иконки:** `public/icons/icon-{size}.svg`

### Emoji-категории
| Категория | Emoji |
|-----------|-------|
| Еда | 🍔 |
| Транспорт | 🚗 |
| Жильё | 🏠 |
| Развлечения | 🎮 |
| Здоровье | 💊 |
| Одежда | 👕 |
| Зарплата | 💰 |
| Подарки | 🎁 |
| Подработка | 💼 |
| Инвестиции | 📈 |

## States

### Loading
- Skeleton: `bg-kesha-border animate-pulse rounded-lg`
- Spinner: Lucide `Loader2` с `animate-spin`

### Empty
- Иконка 48px + текст вторым цветом + кнопка действия
- Текст: «Пока пусто. Кеша ждёт первую транзакцию 🐿️»

### Error
- Карточка с `border-red-400/30 bg-red-400/5`
- Текст ошибки + кнопка «Повторить»

## Motion

| Элемент | Анимация |
|---------|----------|
| Появление карточек | `animate-in fade-in slide-in-from-bottom-2 duration-300` |
| Навигация между страницами | мгновенно (без анимации) |
| Кнопки | `active:scale-[0.98] transition-transform duration-100` |
| Toast | `animate-in slide-in-from-top-2 fade-in duration-200` |

## Accessibility
- Все interactive-элементы имеют `focus-visible:ring-2 focus-visible:ring-amber-400`
- Минимальный размер touch-target: 44×44px
- Цветовой контраст: AA (4.5:1 для текста)
- `prefers-reduced-motion` отключает анимации
