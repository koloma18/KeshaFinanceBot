# SPEC.md — Phase 6: Recurring Payments & Subscriptions

**Phase:** 6
**Project:** Financial Tracker
**Core Value:** Автоматические напоминания о регулярных платежах и подписках с поддержкой мультивалютных списаний (USD, EUR, UAH)
**Requirements:** RECUR-01, RECUR-02, RECUR-03, RECUR-04, RECUR-05
**Depends on:** Phase 1 ✅, Phase 2 ✅, Phase 3 ✅, Phase 4 ✅, Phase 5 🔄

---

## 1. Goal

Добавить учёт регулярных платежей (подписки, аренда, коммунальные) с напоминаниями в день списания. Главная сложность — Monobank списывает подписки в USD/EUR с конвертацией в гривну, поэтому модель должна поддерживать мультивалютность и три режима списания: фиксированный UAH, переменная сумма, конвертация из валюты.

---

## 2. Requirements

### RECUR-01: Multi-Currency Recurring Model

**Current state:** Нет.
**Target state:** Лист `Recurring` в Google Sheets с моделью, поддерживающей три AmountMode.

#### 2.1. Recurring Sheet Headers (24 колонки, A:X)

```
ID                A  — уникальный ID (UUID hex 12)
Title             B  — название (Apple, Аренда, Коммунальные)
Type              C  — expense | income
Amount            D  — сумма в Currency (для fixed/variable, 0 для fx)
Currency          E  — UAH | USD | EUR | USDT
OriginalAmount    F  — сумма в OriginalCurrency (только для fx)
OriginalCurrency  G  — UAH | USD | EUR | USDT (только для fx)
EstimatedUAH      H  — ориентировочная гривневая сумма для планирования
AmountMode        I  — fixed | variable | fx
Category          J  — категория из списка (Подписки, Дом, ...)
DefaultAccountID  K  — ID счёта по умолчанию (из Accounts!A)
DefaultAccountName L — имя счёта (4441...5259, Наличка, ...)
PaymentOptions    M  — JSON-массив: ["cash-uah", "card-office", "card-main"]
Frequency         N  — monthly | weekly | daily
DayOfMonth        O  — день месяца списания (1-31)
DueDay            P  — день напоминания (обычно = DayOfMonth)
GraceUntilDay     Q  — последний день grace-периода (опционально)
NextRunDate       R  — дата следующего списания (YYYY-MM-DD)
LastRunDate       S  — дата последнего списания (YYYY-MM-DD)
Status            T  — active | paused | deleted
CreatedAt         U  — ISO timestamp
UpdatedAt         V  — ISO timestamp
Notes             W  — заметки
Source            X  — manual | monobank (кто создал)
```

#### 2.2. AmountMode Semantics

| Mode | Amount | Currency | Original | EstimatedUAH | Сценарий |
|------|--------|----------|----------|--------------|----------|
| **fixed** | сумма списания | UAH | — | = Amount | WayForPay 102 UAH, Аренда 20000 UAH |
| **variable** | 0 | UAH | — | ориентир | Коммунальные, Boosty.to |
| **fx** | 0 | UAH | сумма в USD/EUR | курс × OriginalAmount | Apple 2.49 USD, OpenAI 23.80 USD |

**fx-режим детальнее:**
- OriginalAmount + OriginalCurrency — фиксированная сумма в валюте подписки
- EstimatedUAH — `OriginalAmount × курс` на момент добавления, для планирования
- При записи транзакции: пользователь может ввести фактическую UAH-сумму после списания (курс меняется), либо использовать EstimatedUAH как приближение
- Пример: Apple списывает 2.49 USD → 2026-05-27 курс 44.4337 → 110.64 UAH. В следующий месяц курс может быть другим.

#### 2.3. Validation Rules

- **Type:** `expense` | `income`
- **Currency:** `UAH` | `USD` | `EUR` | `USDT`
- **OriginalCurrency:** `UAH` | `USD` | `EUR` | `USDT`
- **AmountMode:** `fixed` | `variable` | `fx`
- **Frequency:** `monthly` | `weekly` | `daily`
- **Status:** `active` | `paused` | `deleted` (soft-delete)
- **DayOfMonth:** 1-31
- **Title:** required, непустой
- **EstimatedUAH:** всегда ≥ 0 (для fixed = Amount, для variable — ориентир, для fx = OriginalAmount × курс)
- **Если AmountMode = fx:** OriginalAmount > 0, OriginalCurrency ≠ UAH
- **Если AmountMode = fixed:** Amount > 0, Currency = UAH
- **Если AmountMode = variable:** Currency = UAH

---

### RECUR-02: Bot Commands

#### 2.4. Command Format

**Добавление:**

```
# Fixed UAH
/recurring_add expense 102 UAH Подписки WayForPay monthly 2 карта

# FX (USD/EUR → UAH)
/recurring_add expense 2.49 USD Подписки Apple monthly 27 карта --fx
/recurring_add expense 23.80 USD Подписки OpenAI monthly 12 карта --fx

# Variable
/recurring_add expense variable UAH Подписки Boosty.to monthly 28 карта
/recurring_add expense variable UAH Дом Коммунальные monthly 4 карта
```

**Формат:** `/recurring_add <type> <amount|variable> <currency> <category> <frequency> <day> [account] [--fx] [notes...]`

**Управление:**
```
/recurring_list            — список всех активных подписок
/recurring_list all        — все включая paused
/recurring_edit <ID>       — редактировать (inline-диалог)
/recurring_pause <ID>      — поставить на паузу
/recurring_delete <ID>     — удалить (Status = deleted)
/recurring_due             — что списывается сегодня
/recurring_pay <ID>        — записать транзакцию по recurring шаблону
```

**Параметры recurring_add:**
| # | Параметр | Значение |
|---|----------|----------|
| 1 | type | `expense` или `income` |
| 2 | amount | число, `variable`, или число в валюте для fx |
| 3 | currency | `UAH`, `USD`, `EUR`, `USDT` |
| 4 | category | название категории (можно с пробелами в кавычках или через _) |
| 5 | frequency | `monthly`, `weekly`, `daily` |
| 6 | day | день месяца (1-31) |
| 7 | account | alias счёта (карта, cash, etc.) — опционально |
| — | `--fx` | флаг: сумма в валюте, UAH по курсу |
| — | `--notes` | далее текст заметок (или всё что после аргументов) |

#### 2.5. Parser Logic (bot/recurring_parser.py)

```python
@dataclass
class ParsedRecurring:
    type: str                    # expense | income
    amount: float | None         # None для variable
    currency: str                # UAH | USD | EUR | USDT
    category: str
    frequency: str               # monthly | weekly | daily
    day_of_month: int
    account_id: str | None
    account_name: str | None
    amount_mode: str             # fixed | variable | fx
    original_amount: float | None  # только для fx
    original_currency: str | None  # только для fx
    estimated_uah: float         # всегда заполняется
    notes: str
    payment_options: list[str]   # из Account или []

def parse_recurring_add(args: list[str]) -> ParsedRecurring | None:
    ...
```

**EstimatedUAH calculation:**
- `fixed`: `estimated_uah = amount` (сумма уже в UAH)
- `variable`: `estimated_uah = 0` (пользователь укажет `--est 500`)
- `fx`: `estimated_uah = amount × current_mono_rate(currency)` (если Monobank доступен) или `estimated_uah = 0` (пользователь укажет `--est 110.64`)

Дополнительный флаг `--est <amount>` позволяет вручную задать EstimatedUAH при создании.

#### 2.6. Payment Flow (Due Reminder)

**Daily cron или команда /recurring_due** показывает подписки на сегодня.

**Для fixed UAH:**
```
📱 Подписка: WayForPay
   Сумма: 102 UAH
   Счёт: 4441...5259
[✅ Записать] [✏️ Изменить сумму] [⏭ Пропустить]
```

**Для fx USD/EUR:**
```
📱 Подписка: Apple
   Оригинал: 2.49 USD
   Ориентир: ~110.64 UAH
   Курс может отличаться.
   Счёт: 4441...5259
[✍️ Ввести фактическую сумму UAH]
[✅ Записать по ориентиру]
[⏭ Пропустить]
```

**Для variable:**
```
📱 Подписка: Boosty.to
   Сумма может меняться.
   Счёт: 4441...5259
[✍️ Ввести сумму] [⏭ Пропустить]
```

**Для аренды с PaymentOptions:**
```
🏠 Аренда: 20 000 UAH
   Счёт: выбери способ оплаты
[💳 Карта офисная] [💳 Карта основная] [💵 Наличка] [⏭ Пропустить]
```

**Для коммунальных (variable + PaymentOptions):**
```
🧾 Коммунальные
   Счёт: выбери способ оплаты
[✍️ Сначала ввести сумму]
```

После ввода суммы → выбор способа оплаты → запись в Transactions.

---

### RECUR-03: Integration with Transactions (A:L)

**Transactions sheet НЕ расширяется.** Остаётся A:L.

При записи recurring-транзакции:
- **Amount UAH (D):** фактическая сумма в гривнах (введённая пользователем или EstimatedUAH)
- **Amount USD (E):** 0 (не заполняем)
- **Amount EUR (F):** 0 (не заполняем)
- **Category (G):** категория из recurring (Подписки, Дом)
- **AI Comment (H):** содержит recurring title + original currency info:
  - `Apple · 2.49 USD`
  - `OpenAI · 23.80 USD`
  - `WayForPay · fixed`
  - `Boosty.to · variable`
  - `Аренда · офисная карта`
- **Source (I):** `recurring:<ID>` (например `recurring:a1b2c3d4e5f6`)
- **Account ID (J):** из recurring.DefaultAccountID или выбранный пользователем
- **Account Name (K):** из recurring.DefaultAccountName или выбранный
- **Transfer ID (L):** пусто

**После успешной записи:** обновить `LastRunDate` и `NextRunDate` в Recurring.

**NextRunDate calculation:**
- monthly: DayOfMonth следующего месяца
- weekly: +7 дней
- daily: +1 день

---

### RECUR-04: Google Sheets & Apps Script

#### 4.1. Sheets API (bot/sheets.py)

```python
RECURRING_HEADERS = [
    "ID", "Title", "Type", "Amount", "Currency",
    "OriginalAmount", "OriginalCurrency", "EstimatedUAH", "AmountMode",
    "Category", "DefaultAccountID", "DefaultAccountName", "PaymentOptions",
    "Frequency", "DayOfMonth", "DueDay", "GraceUntilDay",
    "NextRunDate", "LastRunDate", "Status",
    "CreatedAt", "UpdatedAt", "Notes", "Source",
]

def get_recurring(status: str | None = "active") -> list[dict]: ...
def upsert_recurring(data: dict) -> bool: ...
def delete_recurring(recurring_id: str) -> bool: ...
def get_due_recurring(date_str: str | None = None) -> list[dict]: ...
def update_recurring_run_dates(recurring_id: str, last_run: str, next_run: str) -> bool: ...
```

#### 4.2. Apps Script (scripts/Code.gs)

Добавить лист Recurring в `setupSheetsSafe()`:
```javascript
var RECURRING_HEADERS = [
  'ID', 'Title', 'Type', 'Amount', 'Currency',
  'OriginalAmount', 'OriginalCurrency', 'EstimatedUAH', 'AmountMode',
  'Category', 'DefaultAccountID', 'DefaultAccountName', 'PaymentOptions',
  'Frequency', 'DayOfMonth', 'DueDay', 'GraceUntilDay',
  'NextRunDate', 'LastRunDate', 'Status',
  'CreatedAt', 'UpdatedAt', 'Notes', 'Source'
];

function setupSheetsSafe() {
  // ... existing ...
  ensureRecurringSheet();   // ← добавить
  // ... existing ...
}

function ensureRecurringSheet() {
  var sheet = ensureSheetWithHeaders('Recurring', RECURRING_HEADERS);
  formatRecurringSheet(sheet);
}

function formatRecurringSheet(sheet) {
  formatHeader(sheet, RECURRING_HEADERS.length);
  // Валидация для Type, Currency, AmountMode, Frequency, Status
}
```

**Не трогать:** Transactions, Budgets, Categories, Settings, Rules, Accounts, formatAllCoreSheets, setupSheetsSafe (только добавить ensureRecurringSheet).

---

### RECUR-05: Predefined Subscriptions (для тестов и документации)

Не добавлять автоматически, но поддержать эти сценарии:

| # | Title | Mode | Amount | Currency | Orig | Est UAH | Day | Category |
|---|-------|------|--------|----------|------|---------|-----|----------|
| 1 | Apple | fx | 0 | UAH | 2.49 USD | 110.64 | 27 | Подписки |
| 2 | OpenAI | fx | 0 | UAH | 23.80 USD | 1052.86 | 12 | Подписки |
| 3 | WayForPay | fixed | 102 | UAH | — | 102.00 | 2 | Подписки |
| 4 | Boosty.to | variable | 0 | UAH | — | 493.22 | 28 | Подписки |
| 5 | Google | fixed | 200 | UAH | — | 200.00 | 3 | Подписки |
| 6 | Аренда | fixed | 20000 | UAH | — | 20000.00 | 3 | Дом |
| 7 | Коммунальные | variable | 0 | UAH | — | 3500.00 | 4 | Дом |

**Заметки к тестовым сценариям:**
- Apple и OpenAI — классические fx-подписки, курс плавает
- WayForPay — классический fixed UAH
- Boosty.to — сумма в гривне, но плавает от месяца к месяцу (то ли variable, то ли зависит от внутреннего курса Boosty)
- Google — могут быть разные Google-списания (200 UAH, ~460 UAH), поэтому Notes = "may include different Google charges, verify manually"
- Аренда — fixed UAH с grace-периодом до 4-го числа, PaymentOptions = cash-uah, card-office, card-main
- Коммунальные — variable UAH, нужно ввести сумму, потом выбрать способ оплаты

---

### 3. What NOT to Break

- ✅ **Transactions A:L** — не менять схему
- ✅ **Accounts** — только читать (DefaultAccountID/Name)
- ✅ **/banks** — не трогать
- ✅ **Transfers** — не трогать
- ✅ **Account aliases** — использовать существующие
- ✅ **Rules** — не трогать
- ✅ **setupSheetsSafe** — добавить ensureRecurringSheet, ничего не удалять
- ✅ **PWA auth** — не трогать
- ✅ **Зарплата** — остаётся ручной, не добавлять в recurring

---

### 4. Tests (bot/tests/test_recurring.py)

```python
# --- Model validation ---
def test_apple_fx_recurring_model():
    """Apple: fx mode, 2.49 USD, EstimatedUAH 110.64"""
    ...

def test_openai_fx_recurring_model():
    """OpenAI: fx mode, 23.80 USD, EstimatedUAH 1052.86"""
    ...

def test_wayforpay_fixed_recurring_model():
    """WayForPay: fixed 102 UAH"""
    ...

def test_boosty_variable_recurring_model():
    """Boosty.to: variable, asks for actual amount"""
    ...

# --- FX flow ---
def test_fx_subscription_asks_for_actual_uah():
    """FX subscription due: offers 'enter actual UAH' and 'use estimated'"""
    ...

def test_fx_subscription_allows_estimated_uah():
    """FX subscription: user can record with EstimatedUAH"""
    ...

# --- Transaction comment ---
def test_transaction_comment_includes_original_currency():
    """Transaction from fx recurring has comment like 'Apple · 2.49 USD'"""
    ...

def test_transaction_source_is_recurring_id():
    """Transaction Source = recurring:<ID>"""
    ...

# --- Transactions schema ---
def test_transactions_stays_A_L():
    """Recurring transaction uses only A-L columns, no extra columns"""
    ...

# --- Existing features remain ---
def test_rent_fixed_remains_working():
    """Аренда 20000 UAH fixed monthly"""
    ...

def test_utilities_variable_remains_working():
    """Коммунальные variable monthly"""
    ...

def test_accounts_unchanged():
    """Accounts sheet not modified by recurring"""
    ...

def test_banks_unchanged():
    """/banks still works"""
    ...

# --- Parser ---
def test_parse_fx_recurring_add():
    """/recurring_add expense 2.49 USD Подписки Apple monthly 27 карта --fx"""
    ...

def test_parse_fixed_recurring_add():
    """/recurring_add expense 102 UAH Подписки WayForPay monthly 2 карта"""
    ...

def test_parse_variable_recurring_add():
    """/recurring_add expense variable UAH Дом Коммунальные monthly 4 карта"""
    ...
```

---

### 5. Implementation Order

| Step | What | Files |
|------|------|-------|
| 1 | Recurring sheet headers + `_ensure_sheet` в sheets.py | `bot/sheets.py` |
| 2 | CRUD функции для Recurring (get/upsert/delete/due) | `bot/sheets.py` |
| 3 | ParsedRecurring + parse_recurring_add | `bot/recurring_parser.py` |
| 4 | Handler: /recurring_add | `bot/handlers/recurring.py` |
| 5 | Handler: /recurring_list, /recurring_due | `bot/handlers/recurring.py` |
| 6 | Handler: /recurring_pay (due flow с кнопками) | `bot/handlers/recurring.py` |
| 7 | Handler: /recurring_pause, /recurring_delete, /recurring_edit | `bot/handlers/recurring.py` |
| 8 | Интеграция: recurring_pay → add_row в Transactions | `bot/handlers/recurring.py` |
| 9 | Apps Script: Recurring sheet + форматтер | `scripts/Code.gs` |
| 10 | Тесты: test_recurring.py | `bot/tests/test_recurring.py` |
| 11 | Регистрация handler'ов в register_commands.py | `bot/register_commands.py` |

---

### 6. Open Decisions

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Нужен ли cron для `/recurring_due` или только ручной вызов? | a) Cron на Fly.io раз в день b) Только `/recurring_due` вручную | **a)** Cron每天早上 — пассивное напоминание |
| 2 | Кешировать recurring в SQLite или всегда читать из Sheets? | a) SQLite cache b) Sheets напрямую | **a)** Вписать в Phase 5 SQLite-кеш |
| 3 | `/recurring_due` — показывать overdue (пропущенные) подписки? | a) Только сегодня b) Сегодня + overdue | **b)** Показывать overdue чтобы не забыть |
| 4 | Нужен ли импорт recurring из Monobank (авто-детект подписок)? | a) Да, определять повторяющиеся b) Нет, только ручное создание | **b)** Пока ручное — детект сложный, легко ошибиться |

---
*Created: 2026-06-02 | Spec version: 1.0*
