# Requirements: Financial Tracker

**Defined:** 2026-05-30
**Core Value:** Автоматический учёт всех личных финансов без усилий

## v1 Requirements

### Infrastructure
- [ ] **INFRA-01**: Google Sheets таблица как основное хранилище данных (доходы/расходы)
- [ ] **INFRA-02**: Next.js проект с API роутами
- [ ] **INFRA-03**: Telegram bot (python-telegram-bot) как отдельный сервис

### Telegram Bot
- [ ] **TG-01**: Бот принимает сообщение с суммой и описанием расхода
- [ ] **TG-02**: Бот записывает данные в Google Sheets
- [ ] **TG-03**: Бот показывает баланс по запросу
- [ ] **TG-04**: Бот показывает расходы за день/неделю/месяц

### Web App (PWA)
- [ ] **WEB-01**: Дашборд с суммой доходов/расходов за месяц
- [ ] **WEB-02**: График расходов по категориям
- [ ] **WEB-03**: История транзакций с фильтрацией
- [ ] **WEB-04**: PWA установка на телефон

### Monobank
- [ ] **MONO-01**: Импорт выписки через Monobank API (когда будет токен)
- [ ] **MONO-02**: WebHook для получения новых транзакций в реальном времени

### Categories
- [ ] **CAT-01**: Автоматическая категоризация по MCC коду
- [ ] **CAT-02**: Ручная перекатегоризация через Telegram

### Budget
- [ ] **BUDG-01**: Установка бюджетных лимитов по категориям
- [ ] **BUDG-02**: Уведомления о превышении лимита

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
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Pending |
| TG-01 | Phase 1 | Pending |
| TG-02 | Phase 1 | Pending |
| TG-03 | Phase 1 | Pending |
| TG-04 | Phase 1 | Pending |
| WEB-01 | Phase 2 | Pending |
| WEB-02 | Phase 2 | Pending |
| WEB-03 | Phase 2 | Pending |
| WEB-04 | Phase 2 | Pending |
| MONO-01 | Phase 3 | Pending |
| MONO-02 | Phase 3 | Pending |
| CAT-01 | Phase 3 | Pending |
| CAT-02 | Phase 1 | Pending |
| BUDG-01 | Phase 4 | Pending |
| BUDG-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-30*
