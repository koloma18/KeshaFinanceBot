# 🔐 Security Audit Report — Kesha Bot

**Дата:** 31.05.2026  
**Аудитор:** Автоматическая проверка кодовой базы  
**Область:** `/Users/anna/Documents/FinancialTracker/bot/`  
**Вердикт:** 🟡 **Удовлетворительно** — есть несколько важных замечаний

---

## 1. Токены в логах

### Файлы проверены
Все `.py` файлы в `bot/` и `bot/handlers/`, `bot/mono/`.

### Результат: ✅ **Утечек токенов не обнаружено**

| Файл | Строка | Что выводится | Безопасно? |
|------|--------|---------------|------------|
| `handlers/mono_import.py:111` | `f"❌ Ошибка Monobank: {e.message}\n\nПроверь X-Token в настройках."` | `e.message` — сообщение от Monobank API | ✅ API возвращает текст ошибки, не токен |
| `handlers/mono_info.py:66` | `f"❌ Ошибка Monobank: {e.message}\n\nПроверь X-Token в настройках."` | То же самое | ✅ |
| `handlers/export_data.py:61` | `f'📊 <a href="{url}">Открыть Google Sheets</a>'` | `SPREADSHEET_ID` в URL sheets | ⚠️ **См. ниже** |
| `sheets.py:97,101` | `print(f"Google Sheets API error: {e}")` | Вывод в stdout | ✅ Только ошибки API, не токены |
| `diagnose.py:10-16` | `print(f"BOT_TOKEN: ...")` / `print(f"SPREADSHEET_ID: ...")` | `SPREADSHEET_ID` выводится, токены — только «есть/нет» | ⚠️ **См. ниже** |
| `mono/client.py` | Логирование `_request()` | Не логирует токены | ✅ X-Token в заголовке, не в логах |

### ⚠️ Найдено: SPREADSHEET_ID раскрывается
- **`diagnose.py:15-16`** — выводит полный `SPREADSHEET_ID` в stdout.
- **`handlers/export_data.py:61`** — выводит полный URL sheets в ответ пользователю.
- **Риск:** `SPREADSHEET_ID` — менее критичен чем токен, но раскрытие ID таблицы упрощает фишинг (если service account имеет write-доступ).
- **Рекомендация:** Для `diagnose.py` — показывать только `есть/нет` как для токенов. Для `/export sheets` — это фича, но помнить что ID будет в логах Telegram.

### Verdict по токенам: 🟢 БЕЗОПАСНО
Ни в одном логе, `print()`, `logger.`, `reply_text()` или `reply_html()` не выводится `BOT_TOKEN`, `MONOBANK_X_TOKEN`, `GOOGLE_PRIVATE_KEY`.

---

## 2. Google Private Key

### Проверка `config.py`

```python
GOOGLE_PRIVATE_KEY = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
```

- **Источник:** `.env` (через `python-dotenv`) ✅
- **Хардкод:** Отсутствует ✅
- **`replace('\\n', '\n')`:** Корректно обрабатывает экранированные переводы строк из `.env` ✅

### Проверка `diagnose.py`

```python
formatted_key = key.replace("\\n", "\n")
```

- Так же использует `os.getenv` + `replace` ✅
- Выводит только длину ключа: `str(len(key))` ✅

### Проверка `sheets.py`

```python
from config import GOOGLE_PRIVATE_KEY, GOOGLE_SERVICE_ACCOUNT_EMAIL, SPREADSHEET_ID
creds = service_account.Credentials.from_service_account_info(
    {"type": "service_account", ..., "private_key": GOOGLE_PRIVATE_KEY, ...},
    scopes=SCOPES,
)
```

- `private_key` передаётся только в Google SDK ✅
- Нигде не логируется ✅

### Verdict: 🟢 БЕЗОПАСНО

---

## 3. HTML-инъекции

### 3.1 Использование `reply_html()` и `reply_text(parse_mode="HTML")`

| Файл | Метод | Что передаётся | Экранирование |
|------|-------|---------------|---------------|
| `handlers/expense.py` | `reply_text(parse_mode="HTML")` | `category`, `comment` из `context.user_data` | ❌ **НЕТ** |
| `handlers/income.py` | `reply_text()` | Без parse_mode | ✅ Не HTML |
| `handlers/add_category.py` | `reply_html()` | `name` (кастомная категория) | ❌ **НЕТ** |
| `handlers/statistics.py` | `reply_html()` | Данные из Sheets (категории) | ❌ **НЕТ** |
| `handlers/last.py` | `reply_html()` | `category`, `comment` из Sheets | ❌ **НЕТ** |
| `handlers/delete_command.py` | `reply_html()` | `category`, `comment` из Sheets | ❌ **НЕТ** |
| `handlers/recategorize.py` | `reply_html()` | `category`, `comment` из Sheets | ❌ **НЕТ** |
| `handlers/compare.py` | `reply_html()` | Данные из Sheets (категории) | ❌ **НЕТ** |
| `handlers/categories.py` | `reply_html()` | Имена категорий (статические + кастомные) | ❌ **НЕТ** |
| `handlers/budget.py` | `reply_html()` | `category` | ❌ **НЕТ** |
| `handlers/mono_info.py` | `reply_text(parse_mode="HTML")` | `client_name`, `masked_pan` | ⚠️ `client_name` из API |

### 🔴 CRITICAL FINDING: Нигде нет экранирования HTML

**Пользовательские данные, передаваемые в HTML без экранирования:**
- Названия кастомных категорий (`/add_category expense <Название>`)
- Комментарии к транзакциям (`comment`)
- Данные из Google Sheets (категории, комментарии, описания)

**Пример атаки:**
```bash
/add_category expense <script>alert('xss')</script>
```
→ Категория попадёт в `reply_html()` → будет интерпретирована как HTML.

**Аналогично:** Monobank description транзакции (из API) может содержать `&`, `<`, `>` → сломает HTML-разметку/откроет XSS.

### 🔧 Рекомендация

Добавить функцию эскейпинга:
```python
import html

def escape_html(text: str) -> str:
    return html.escape(text, quote=True)
```

И применять ко ВСЕМ данным от пользователя перед передачей в `reply_html()`:
- `category` → `escape_html(category)`
- `comment` → `escape_html(comment)`
- `client_name` → `escape_html(client_name)`

**В идеале:** Создать wrapper `_reply_html(update, text, **kwargs)` который автоматически эскейпит все `{}` подстановки.

### Verdict: 🔴 КРИТИЧНО — требуется экранирование HTML

---

## 4. Rate Limiting

### 4.1 Monobank API

**Реализация в `mono/client.py`:**
```python
REQUEST_INTERVAL = 60  # seconds between requests
```

- Асинхронный `_rate_limit()` через `asyncio.sleep()` ✅
- Учёт ошибки 429 с Retry-After ✅
- Exponential backoff при таймаутах ✅
- **Замечание:** `time.monotonic()` используется для измерения интервалов — корректно ✅

### 4.2 Google Sheets API

- **Защиты нет.** Нет rate limiter'а для Google Sheets.
- **Риск:** При быстром импорте Monobank (много транзакций) идёт много последовательных вызовов `add_row()` → `sheets.values().append()`. Google Sheets бесплатный лимит: 60 запросов/мин на пользователя, 300/мин на проект.
- **В коде:** `mono_import.py` и `mono_sync.py` вызывают `add_row()` в цикле — при 100+ транзакциях могут упереться в квоту.
- **Рекомендация:** Добавить `asyncio.sleep(0.2)` между вызовами `add_row` в цикле импорта, либо батчить аппенды.

### 4.3 Telegram API

- `python-telegram-bot` v21 сам управляет rate limiting ✅
- **Риск зацикливания:** Нет. Бот не отвечает сам себе — только команды пользователя.
- **Потенциальный вектор:** JobQueue (reminder, quote) использует `context.bot.send_message()` — если chat_id невалидный, Telegram вернёт ошибку, бот не зациклится ✅

### Verdict: 🟡 УДОВЛЕТВОРИТЕЛЬНО — Monobank OK, Google Sheets без защиты

---

## 5. Google Sheets API

### 5.1 Права доступа

```python
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
```

- **Scope:** `spreadsheets` (полный доступ) — верно для записи ✅
- **Аутентификация:** Service Account с JSON credentials ✅
- **Приватный ключ:** Из `.env` ✅

### 5.2 Обработка ошибок

| Функция | try/except | Возврат |
|---------|-----------|---------|
| `get_all_rows()` | ✅ `HttpError` + generic | `[]` |
| `add_row()` | ✅ `HttpError` + generic | `False` |
| `delete_row_by_index()` | ✅ `HttpError` + generic | `False` |
| `find_row_by_source()` | ✅ generic | `None` |
| `get_budget_rows()` | ✅ generic | `[]` |
| `upsert_budget_row()` | ✅ `HttpError` + generic | `False` |
| `get_categories_spending()` | Нет try/except, но вызывает `get_all_rows()` (который ловит) | `{}` |
| `get_balance()` | Нет try/except, но вызывает `get_all_rows()` | `dict с нулями` |

- **Все критические операции** (запись, удаление) имеют try/except ✅
- Некоторые read-only функции полагаются на обработку в вызываемых функциях — приемлемо ✅
- **Замечание:** `get_service()` глушит ВСЕ исключения (`except Exception: return None`) — хорошо для продакшена, но усложняет отладку.

### Verdict: 🟢 БЕЗОПАСНО

---

## 6. Input Validation

### 6.1 Суммы

| Место | Валидация | Отрицательные | Максимум |
|-------|-----------|---------------|----------|
| `expense_command.py` | `float(parts[1])` | ❌ Принимает отрицательные | ❌ Без上限а |
| `income_command.py` | `float(parts[1])` | ❌ Принимает отрицательные | ❌ Без上限а |
| `expense_text()` | `float(text)` | ❌ | ❌ |
| `income_text()` | `float(text)` | ❌ | ❌ |
| `budget.py:_parse_amount()` | `Decimal(cleaned)` | ✅ `<= 0` → reject | ❌ |

- **Проблема:** Пользователь может ввести `-500` как расход — в `_save_expense()` сумма инвертируется (`-amount` → `+500`), записывается как expense с положительной суммой. Логика не ломается, но UX странный.
- **Рекомендация:** Добавить `amount = abs(float(text))` для расходов и `amount > 0` проверку для доходов.

### 6.2 Категории

- **Встроенные:** Жёсткий список ✅
- **Кастомные:** `/add_category` проверяет `len(name) >= 2`, capitalizes, проверяет дубликаты ✅
- **НО:** Нет проверки на спецсимволы (HTML-теги в названии — см. раздел 3) ❌
- **НО:** Нет ограничения длины названия ❌

### 6.3 Аргументы команд

| Команда | Валидация | Безопасно? |
|---------|-----------|------------|
| `/delete N` | `int(parts[1])` + проверка диапазона | ✅ |
| `/mono_import N` | `isdigit()` + `1 <= N <= 31` | ✅ |
| `/budget N` | `_parse_amount()` + `<= 0` check | ✅ |
| `/set_limit Cat N` | `_parse_amount()` + нормализация категории | ✅ |
| `/export csv N` | `isdigit()` или `"month"` | ✅ |
| `/quote_time HH:MM` | `datetime.strptime(arg, "%H:%M")` | ✅ |
| `/recategorize Cat` | `normalize_category()` | ✅ |

### 6.4 Monobank webhook данные

```python
amount_minor = data.get("amount", 0)
mcc = data.get("mcc", 0)
description = data.get("description", "")
```

- `amount` и `mcc` — целые числа, безопасны ✅
- **`description` — строка от Monobank, записывается в Sheets и потом отображается в HTML без эскейпинга!** 🔴

### Verdict: 🟡 УДОВЛЕТВОРИТЕЛЬНО — требуется валидация спецсимволов в названиях/описаниях

---

## 7. Webhook Endpoint (`bot/mono/webhook.py`)

### 7.1 Валидация входящего JSON

```python
def do_POST(self):
    content_length = int(self.headers.get("Content-Length", 0))
    body = self.rfile.read(content_length)
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        self._respond(400, {"error": "Invalid JSON"})
        return
```

- **Валидация JSON:** ✅ Проверяет `json.JSONDecodeError`
- **Content-Length:** ❌ Нет проверки на максимальный размер тела → потенциальный memory exhaustion

### 7.2 Валидация формата транзакции

```python
event_type = payload.get("type", "")
if event_type != "StatementItem":
    self._respond(200, {"status": "ignored"})  # ✅ Не 200 OK на невалидные?
    return

statement_item = event_data.get("statementItem", {})
if not statement_item:
    self._respond(400, {"error": "Missing statementItem"})
    return
```

- Проверяет наличие `type` и `data.statementItem` ✅
- **НО:** Не проверяет обязательные поля внутри `statementItem` (`id`, `time`, `amount`). `process_transaction()` обрабатывает отсутствующие поля через `.get()` с дефолтами ✅

### 7.3 HTTP ответы

| Сценарий | Код ответа |
|----------|-----------|
| Невалидный JSON | 400 ✅ |
| Тип не `StatementItem` | 200 `{"status": "ignored"}` ✅ |
| Нет `statementItem` | 400 ✅ |
| Транзакция обработана | 200 ✅ |
| Дубликат/ошибка | 200 `{"status": "skipped"}` ✅ |

- **Правильное поведение:** Monobank ожидает 200 OK для подтверждения доставки ✅
- **Замечание:** Нет логирования IP-адреса источника запроса — рекомендую добавить для аудита

### 7.4 Дедупликация

```python
source_key = f"mono:{tx_id}"
existing = find_row_by_source(source_key)
```

- Идемпотентность через поиск в Sheets ✅
- Пропуск холдов (`hold: true`) ✅

### 7.5 Безопасность сервера

- Использует `http.server.HTTPServer` — без TLS ⚠️
- **Рекомендация:** В продакшене ставить за nginx/caddy с HTTPS, либо ngrok для разработки.

### Verdict: 🟢 БЕЗОПАСНО — с замечанием по Content-Length

---

## 8. Дополнительные находки

### 8.1 Fetch Stickers — `BOT_TOKEN` в URL

```python
# fetch_stickers.py:22
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
```

Бот-токен в URL — стандартная практика Telegram API ✅. Но файл лежит в репозитории. Сам токен из `.env` → `.gitignore` ✅.

### 8.2 `.gitignore`

```
.env
.env.local
.env.production
```

- `.env` в `.gitignore` ✅
- `__pycache__/`, `venv/` — в игноре ✅

### 8.3 Отсутствует requirements.txt проверка версий

```text
python-telegram-bot[job-queue]
google-auth google-auth-oauthlib google-auth-httplib2
google-api-python-client
python-dotenv
httpx
```

- Версии не зафиксированы — `pip freeze` при деплое рекомендуется ⚠️

---

## Сводная таблица

| # | Проверка | Вердикт | Критичность |
|---|----------|---------|-------------|
| 1 | Токены в логах | 🟢 OK | — |
| 1 | SPREADSHEET_ID раскрытие | 🟡 OK с оговоркой | Low |
| 2 | Google Private Key | 🟢 OK | — |
| 3 | HTML-инъекции | 🔴 ТРЕБУЕТ ИСПРАВЛЕНИЯ | **HIGH** |
| 4 | Monobank rate limit | 🟢 OK | — |
| 4 | Sheets rate limit | 🟡 Нет защиты | Medium |
| 5 | Sheets API доступ | 🟢 OK | — |
| 5 | Sheets обработка ошибок | 🟢 OK | — |
| 6 | Валидация сумм | 🟡 Нет abs/limit | Low |
| 6 | Валидация категорий | 🔴 Нет HTML-эскейпинга | **HIGH** |
| 7 | Webhook JSON | 🟢 OK | — |
| 7 | Webhook Content-Length | 🟡 Нет上限а | Medium |

---

## Приоритеты исправлений

### 🔴 HIGH — сделать немедленно
1. **HTML-эскейпинг:** Добавить `html.escape()` для всех пользовательских данных перед `reply_html()` / `reply_text(parse_mode="HTML")`.

### 🟡 MEDIUM — сделать до продакшена
2. **Rate limit Google Sheets:** Добавить `asyncio.sleep(0.2)` в циклы импорта.
3. **Webhook Content-Length:** Добавить `if content_length > 100_000: self._respond(413, ...)`.
4. **Валидация сумм:** `abs()` для расходов, `> 0` для доходов.

### 🟢 LOW — по желанию
5. **SPREADSHEET_ID в diagnose.py:** Показывать только факт наличия.
6. **Фиксация версий:** `pip freeze > requirements.txt`.
7. **Логирование IP webhook:** Добавить `self.client_address` в логи.
