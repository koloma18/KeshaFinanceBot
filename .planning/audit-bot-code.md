# Аудит качества кода бота Kesha

**Дата:** 2026-05-31  
**Вердикт:** 12/14 критических/высоких багов исправлено. 2 низкоприоритетных задокументированы.

---

## 1. Обработка ошибок — ✅ удовлетворительно

| Зона | Статус |
|------|--------|
| `get_all_rows()` → пустой ответ | Все 8+ мест вызова проверяют `if not rows` ✅ |
| `add_row()` → возвращаемое значение | Все вызовы проверяют `ok`/`success` ✅ |
| Sheets API → исключения | `HttpError` + `Exception` catch во всех функций ✅ |
| Monobank 429 (rate limit) | 🔧 Исправлено: ретрай с backoff + Retry-After ⚡ |
| Monobank 401 (неверный токен) | `MonobankError` с сообщением ошибки, передаётся пользователю ✅ |

## 2. Edge Cases — 🔧 1 исправлен, 1 задокументирован

| Кейс | Статус |
|------|--------|
| Google Sheets недоступен | `get_service()` → `None`, все функции проверяют ✅ |
| Лист не существует: Settings | Автосоздание через `get_or_create_sheet` ✅ |
| Лист не существует: Budgets | 🔧 **Исправлено** — добавлен `get_or_create_sheet` в `upsert_budget_row` |
| Лист не существует: Categories | 🔧 **Исправлено** — добавлен `get_or_create_sheet` в `add_custom_category` |
| Пустая база | Все хендлеры проверяют ✅ |
| Большое кол-во записей | ⚠️ `get_all_rows()` читает ВСЕ строки без пагинации. При 5000+ строк возможны таймауты. Рекомендация: добавить `range` фильтрацию или пагинацию в будущем. |
| Категория с пробелами | `strip()` перед валидацией ✅ |

## 3. Типизация и импорты — ✅ удовлетворительно

- **Циклические импорты:** отсутствуют ✅
- **Неиспользуемые импорты/переменные:** 🔧 `DEFAULT_COMMENT`, `TOP_EXPENSES` удалены из `responses.py`
- **Аннотации типов:** 🔧 большинство функций типизированы. Часть хендлеров без аннотаций (минорно)

## 4. Асинхронность — ✅ безопасно

- **BudgetManager** (`_budget_cache`, `_spending_cache`): класс-уровневые переменные. В однопоточном asyncio (все I/O вызовы синхронны) гонки невозможны ✅
- **`categories._custom_cache`**: аналогично, однопоточный asyncio ✅
- **Рекомендация:** при переходе на `run_in_executor` или `asyncio.to_thread` для Sheets API — добавить `asyncio.Lock`

## 5. Persistence — ✅ удовлетворительно

- `user_data` сбрасывается при перезапуске: ✅ но при `/start` подгружается из Sheets
- `expense_step`, `expense_amount` и т.д.: workflow state, ожидаемо теряется при рестарте ✅
- `today_categories` (трекинг повторов): теряется при рестарте — минорно ✅
- Настройки в Sheets: автосоздание Settings sheet + `upsert_setting` ✅

---

## 6. Исправленные баги

### 🔴 Критические

| # | Файл | Проблема | Исправление |
|---|------|----------|-------------|
| 1 | `mono/webhook.py:51-66` | Русские названия месяцев (`Январь`) вместо английских. Расходится со всеми остальными модулями (используют `strftime("%B")` → `January`). Все фильтры по месяцу ломались. | `_format_month()` → `dt.strftime("%B")` |
| 2 | `handlers/stickers.py:134` | `from stickers import STICKER_IDS` — константа `STICKER_IDS` не существует. `ImportError` при нажатии кнопки «Выбрать стикер-пак». | `STICKER_IDS` → `STICKER_POOL` + `bool(STICKER_POOL)` |

### 🟠 Высокие

| # | Файл | Проблема | Исправление |
|---|------|----------|-------------|
| 3 | `handlers/mono_sync.py:28-62` | `_build_row()` — неизвестная валюта (не UAH/USD/EUR) записывалась с пустыми значениями во все колонки. Данные терялись. | Функция вынесена в `mono/__init__.py` как `build_transaction_row()` с обработкой unknown currency. Оба `mono_import` и `mono_sync` теперь используют общую версию. |
| 4 | `handlers/set_currency.py:34` | `/set_currency USD` не сохраняло настройку в Sheets — только в `context.user_data`. После перезапуска валюта сбрасывалась. | Добавлен `persist_setting("currency", currency)` |
| 5 | `handlers/mono_rates.py:45` | `MonobankClient()` создавался без `async with` — `httpx.AsyncClient` никогда не закрывался. Утечка соединений. | `client = MonobankClient()` → `async with MonobankClient() as client` |
| 6 | `sheets.py:128,159` | `delete_row_by_index` и `delete_last_row` использовали хардкод `sheetId=0`. Если Transactions не первый лист — удаление ломало другой лист. | `_get_sheet_id("Transactions")` с fallback на `return False` |
| 7 | `sheets.py:284-340` | `upsert_budget_row` не создавал лист Budgets при первом использовании. `/budget 50000` → молчаливый False. | Добавлен `get_or_create_sheet("Budgets", BUDGET_HEADERS)` |
| 8 | `sheets.py:503-523` | `add_custom_category` не создавал лист Categories. `/add_category expense Книги` → молчаливый False. | Добавлен `get_or_create_sheet("Categories", ["Type", "Name"])` |

### 🟡 Средние

| # | Файл | Проблема | Исправление |
|---|------|----------|-------------|
| 9 | `handlers/mono_import.py:46-87`, `handlers/mono_sync.py:28-62` | Полный дубликат `_build_row()` (42 строки) в двух файлах. | Вынесено в `mono/__init__.py` как `build_transaction_row()` |
| 10 | `handlers/quotes.py:109` | `import datetime as dt` внутри тела функции — код-смрад. | Импорт вынесен на верхний уровень |
| 11 | `handlers/reminder.py:84` | Аналогично — `import datetime as dt` внутри функции. | Импорт вынесен на верхний уровень |
| 12 | `responses.py:197-201,243-246` | Неиспользуемые константы `DEFAULT_COMMENT` (3 строки) и `TOP_EXPENSES` (2 строки). | Удалены |

---

## 7. Неисправленные проблемы (низкий приоритет)

| # | Файл | Проблема | Почему не исправлено |
|---|------|----------|---------------------|
| 1 | `sheets.py`, `handlers/statistics.py`, `handlers/compare.py`, `handlers/export_data.py` | Фильтрация по месяцу только по названию (напр. "June") — смешивает данные разных лет. | Требует изменения схемы: добавить год в колонку Month или фильтровать по дате. Миграция данных. |
| 2 | `handlers/add_category.py` | `import random` внутри тела функции | Косметика, не влияет на работу |

---

## 8. Рекомендации (не баги, но на будущее)

1. **Кэш + многопоточность:** если Sheets API вызовы станут асинхронными (`run_in_executor`) — обернуть `BudgetManager._budget_cache` в `asyncio.Lock`
2. **Пагинация `get_all_rows()`:** при росте базы до 5000+ строк — добавить range-фильтр по дате
3. **Год в месяце:** добавить колонку Year или хранить `YYYY-MM` вместо названия месяца
4. **Логирование:** заменить `print()` в `sheets.py` на `logging.warning/error`
5. **QUOTES_POOL дубликат:** `handlers/quotes.py:QUOTES_POOL` (20 цитат) и `responses.py:QUOTES` (5 цитат) — рассинхронизированы. `get_quote()` из responses возвращает только 5 из 20. Стоит унифицировать.
