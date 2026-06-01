# Requirements: Financial Tracker

**Defined:** 2026-05-30
**Updated:** 2026-06-01 — added PERF requirements
**Core Value:** Автоматический учёт всех личных финансов без усилий

## v1 Requirements

### Infrastructure
- [x] **INFRA-01**: Google Sheets таблица как основное хранилище данных (доходы/расходы)
- [x] **INFRA-02**: Next.js проект с API роутами
- [x] **INFRA-03**: Telegram bot (python-telegram-bot) как отдельный сервис

### Telegram Bot
- [x] **TG-01**: Бот принимает сообщение с суммой и описанием расхода
- [x] **TG-02**: Бот записывает данные в Google Sheets
- [x] **TG-03**: Бот показывает баланс по запросу
- [x] **TG-04**: Бот показывает расходы за день/неделю/месяц

### Web App (PWA)
- [x] **WEB-01**: Дашборд с суммой доходов/расходов за месяц
- [x] **WEB-02**: График расходов по категориям
- [x] **WEB-03**: История транзакций с фильтрацией
- [x] **WEB-04**: PWA установка на телефон

### Monobank
- [x] **MONO-01**: Импорт выписки через Monobank API
- [ ] **MONO-02**: WebHook для получения новых транзакций в реальном времени (заглушка есть)

### Categories
- [x] **CAT-01**: Автоматическая категоризация по MCC коду
- [x] **CAT-02**: Ручная перекатегоризация через Telegram

### Budget
- [x] **BUDG-01**: Установка бюджетных лимитов по категориям
- [x] **BUDG-02**: Уведомления о превышении лимита

### Performance (NEW — Phase 5)
- [ ] **PERF-01**: SQLite read-through cache — все команды чтения (<1ms вместо ~500ms Sheets API)
- [ ] **PERF-02**: Фоновый Monobank sync (cron 5-10 min) — /balance не ждёт Monobank API
- [ ] **PERF-03**: Web API routes читают SQLite (Sheets как fallback)

## v2 Requirements
- Маркетинг и название, логотип, дизайн
- Возможность платного доступа
- Мультивалютность: украинские гривны, доллары США, евро

## Out of Scope
| Feature | Reason |
|---------|--------|
| Нативное мобильное приложение | PWA достаточно для v1 |
| Поддержка других банков | Только Monobank |
| Мультипользовательский режим | Личный проект |
| Корпоративное Monobank API | Персональный токен достаточен |

## Traceability
| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | ✅ Done |
| INFRA-02 | Phase 1 | ✅ Done |
| INFRA-03 | Phase 1 | ✅ Done |
| TG-01 | Phase 1 | ✅ Done |
| TG-02 | Phase 1 | ✅ Done |
| TG-03 | Phase 1 | ✅ Done |
| TG-04 | Phase 1 | ✅ Done |
| WEB-01 | Phase 3 | ✅ Done |
| WEB-02 | Phase 3 | ✅ Done |
| WEB-03 | Phase 3 | ✅ Done |
| WEB-04 | Phase 3 | ✅ Done |
| MONO-01 | Phase 4 | ✅ Done |
| MONO-02 | Phase 4 | Заглушка |
| CAT-01 | Phase 4 | ✅ Done |
| CAT-02 | Phase 1 | ✅ Done |
| BUDG-01 | Phase 2 | ✅ Done |
| BUDG-02 | Phase 2 | ✅ Done |
| PERF-01 | Phase 5 | 🔄 In Progress |
| PERF-02 | Phase 5 | 🔄 In Progress |
| PERF-03 | Phase 5 | 🔄 In Progress |

**Coverage:**
- v1 requirements: 20 total
- Done: 17
- In Progress: 3
- Not started: 0

---
*Requirements defined: 2026-05-30 | Updated: 2026-06-01*
