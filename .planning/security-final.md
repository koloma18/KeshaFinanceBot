# 🔐 Финальный аудит безопасности — Kesha Finance Bot

**Дата:** 2026-05-31  
**Аудитор:** автоматическая проверка  
**Репозиторий:** github.com/koloma18/KeshaFinanceBot  
**Продакшн:** Fly.io (kesha-finance-bot) + Vercel (keshafinancebot.vercel.app)

---

## 1. GitHub — Аудит коммитов

**Проверено коммитов:** 12 (вся история)  
**Метод:** grep по diff каждого коммита на имена секретных переменных + маскинг значений длиннее 30 символов

### Результат: ✅ ЧИСТО

| Коммит | Описание | Вердикт |
|--------|----------|---------|
| `3a28e2a` | Initial commit | Placeholder-ы в `.env.example`, имена переменных в коде |
| `85633c4` | Vercel deploy config | Только имена переменных в документации |
| `1c39554` | Docs update | Только имена переменных в документации |
| `6327d2e` | Fly.io config | `fly secrets set ...=твой_токен` — placeholder |
| `3e5388d` | Docker CMD debug | `bool(os.getenv("BOT_TOKEN"))` — только булево значение |
| `3b61d34` | Skip load_dotenv | Имена переменных в `config.py` |
| `b4bb756` | Suppress httpx token | Комментарий `# BOT_TOKEN` |
| Остальные 5 | Разное | Чисто |

**Ни в одном коммите нет реальных значений секретов.** Все `.env.example` содержат только `your_*` placeholder-ы.

---

## 2. Fly.io — Логирование httpx

**Баг:** httpx на уровне DEBUG/WARNING логировал полный URL вида:  
`https://api.telegram.org/bot<BOT_TOKEN>/sendMessage`

**Исправление:** коммит `b4bb756` — `bot/main.py`, строка ~15:
```python
logging.getLogger("httpx").setLevel(logging.WARNING)
```

### Вердикт: ⚠️ ТРЕБУЕТСЯ РОТАЦИЯ

Старые логи Fly.io могли сохранить URL с BOT_TOKEN. Уровень риска **средний** (токен виден только в логах Fly.io, доступ к которым имеет владелец аккаунта).

### 🔴 Рекомендация: сменить BOT_TOKEN

```bash
# 1. @BotFather → /mybots → Kesha → API Token → Revoke current token
# 2. Установить новый токен:
fly secrets set BOT_TOKEN=<новый_токен> -a kesha-finance-bot
# 3. Обновить локальный .env
# 4. Деплой:
fly deploy -a kesha-finance-bot
```

---

## 3. Google Sheets — Права доступа

**Service account:** `keshafinancebot@my-ai-497617.iam.gserviceaccount.com`  
**Scope:** `https://www.googleapis.com/auth/spreadsheets`

### Проблема: scope даёт доступ ко ВСЕМ таблицам

Сервисный аккаунт с этим scope-ом может читать/писать **любую** Google Sheets таблицу, к которой ему дали доступ. Это стандартное ограничение Google Sheets API — нет scope-а для одной таблицы.

### Вердикт: 🟡 ПРИЕМЛЕМО (с оговорками)

| Аспект | Статус |
|--------|--------|
| Scope | `spreadsheets` (весь Google Sheets) — единственный вариант для записи |
| Доступ к таблицам | Только та, куда приглашён service account |
| Риск компрометации SA | Может читать/писать любую таблицу, куда приглашён |
| Митигация | Не приглашать SA в другие таблицы, мониторить IAM |

### 🔶 Рекомендация

Ограничить на уровне Google Cloud IAM — добавить condition на доступ только к конкретному Spreadsheet ID (если Google Cloud поддерживает resource-based conditions для SA).

---

## 4. Утечки SPREADSHEET_ID

### Найдено: 2 места раскрытия

| Файл | Строка | Что утекает | Кому | Риск |
|------|--------|-------------|------|------|
| `bot/handlers/export_data.py` | 60 | Полный URL с `SPREADSHEET_ID` | Пользователю Telegram | 🟡 Low |
| `bot/diagnose.py` | 15 | Полный `SPREADSHEET_ID` | В stdout (локально) | 🟡 Low |

### Анализ

- `SPREADSHEET_ID` — не секрет уровня токена, но раскрытие упрощает фишинг
- Доступ к таблице всё равно требует аутентификации service account
- `diagnose.py` — локальный инструмент, не на проде

### 🔶 Рекомендация

В `export_data.py` показывать только факт наличия ссылки, без ID в тексте:
```python
# Вариант: использовать именованный диапазон или не показывать ID
url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
# → заменить на общую ссылку или маскировать
```

---

## 5. Vercel — Проверка

| Проверка | Статус |
|----------|--------|
| `NEXT_PUBLIC_*` с секретами | ✅ Нет |
| `vercel.json` | ✅ Чисто |
| `next.config.mjs` CSP | ✅ `connect-src` только `api.monobank.ua` |
| `web/lib/sheets.ts` | ✅ `"server-only"` директива |
| Environment variables | ✅ Только в дашборде Vercel |

---

## 6. Локально — Проверка

| Проверка | Статус |
|----------|--------|
| `.env` в `.gitignore` | ✅ |
| `.env.local` в `.gitignore` | ✅ |
| `.env.production` в `.gitignore` | ✅ |
| `.env` в git-трекинге | ✅ Нет (`git ls-files` пуст) |
| Копии `.env` в проекте | ✅ Только один `.env` в корне |
| `.env.example` | ✅ Только placeholder-ы |
| `Dockerfile` CMD | ✅ Только `bool()` и `len()`, без значений |

---

## 7. Сводная таблица рисков

| # | Уязвимость | Уровень | Статус | Действие |
|---|-----------|---------|--------|----------|
| 1 | BOT_TOKEN в логах Fly.io | 🟡 Medium | Исправлен код, старые логи — риск | **Ротация токена** |
| 2 | SPREADSHEET_ID в export_data | 🟡 Low | В коде | Замаскировать |
| 3 | SPREADSHEET_ID в diagnose.py | 🟡 Low | Локальный инструмент | Замаскировать |
| 4 | SA scope на все таблицы | 🟡 Low | Ограничение API | Ограничить IAM |
| 5 | Секреты в git-истории | 🟢 Clean | — | — |
| 6 | Vercel env vars | 🟢 Clean | — | — |
| 7 | Локальные `.env` | 🟢 Clean | — | — |

---

## 8. План действий (по приоритету)

### 🔴 Срочно
1. **Ротация BOT_TOKEN** — единственная реальная угроза после утечки в логи httpx

### 🟡 Желательно
2. Замаскировать `SPREADSHEET_ID` в `export_data.py` и `diagnose.py`
3. Проверить IAM условия для service account в Google Cloud

### 🟢 Опционально
4. Настроить алерты в Google Cloud на подозрительную активность SA
5. Включить Audit Logs для Google Sheets API

---

## 9. Итоговый вердикт

**🟢 ПРОЕКТ БЕЗОПАСЕН** — критических утечек секретов не обнаружено.

Единственное обязательное действие — **ротация BOT_TOKEN** из-за исторического бага с httpx-логированием. После ротации проект можно считать полностью безопасным с точки зрения хранения и обращения с секретами.

---

*Отчёт сгенерирован автоматически. Все проверки выполнены без логирования реальных значений секретов.*
