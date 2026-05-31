# Аудит безопасности — Kesha Web App

**Дата:** 2026-05-31  
**Версия:** next@14.2.0, googleapis@134.0.0  
**Файлы:** 21 компонент, 2 API-роута, 6 lib-модулей  

---

## Оценка рисков

| Категория | Оценка | Риск |
|-----------|--------|------|
| Утечка secrets в клиент | ✅ Безопасно | — |
| XSS через пользовательские данные | ✅ Безопасно | — |
| Rate limiting API | 🔴 Отсутствует | Высокий |
| Валидация входных данных API | 🟡 Базовая | Средний |
| CSP / Security Headers | 🔴 Отсутствуют | Высокий |
| Зависимости (npm audit) | 🔴 6 уязвимостей | Высокий |
| Service Worker | 🟡 Низкий риск | Низкий |
| Обработка private_key | ✅ Корректно | — |
| Раскрытие данных в ошибках | ✅ Безопасно | — |

---

## 1. Environment Variables

### 1.1 Структура .env файлов

Файлы с секретами (оба в `.gitignore`):
- `/FinancialTracker/.env` — все 7 переменных (используется Python-ботом)
- `/FinancialTracker/web/.env.local` — 4 переменных (дубликат для Next.js)

```
GOOGLE_SERVICE_ACCOUNT_EMAIL ✅
GOOGLE_PRIVATE_KEY         ✅
SPREADSHEET_ID             ✅
MONOBANK_X_TOKEN           ✅ (web-приложение НЕ использует, только бот)
```

### 1.2 `NEXT_PUBLIC_*` переменные

**Отсутствуют.** В коде нет `NEXT_PUBLIC_*` префиксов. ✅

```bash
$ grep -r "NEXT_PUBLIC" FinancialTracker/web/
# No matches found
```

### 1.3 `process.env` в клиентских компонентах

`process.env` используется **только** в `lib/sheets.ts`:

```typescript
// lib/sheets.ts — СЕРВЕРНЫЙ модуль (импортируется только из API routes)
const email = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL;
const key = process.env.GOOGLE_PRIVATE_KEY;
const spreadsheetId = process.env.SPREADSHEET_ID;
```

Все `"use client"` компоненты (21 файл) не используют `process.env`. ✅

**Но:** `sheets.ts` не имеет защиты от случайного импорта в клиентский код.

> ⚠️ **Рекомендация:** Добавить `import "server-only"` в `lib/sheets.ts`, чтобы Next.js гарантированно блокировал импорт в клиентские компоненты.

### 1.4 Private Key в клиентском бандле

**Невозможно** при текущей архитектуре:
- `lib/sheets.ts` импортируется только из `app/api/sheets/[[...segments]]/route.ts` (API route — всегда серверный)
- Все клиентские компоненты используют `fetch("/api/sheets/...")`, а не прямой импорт
- Next.js App Router изолирует серверный код от клиентского

### 1.5 Дублирование .env файлов

`web/.env.local` дублирует секреты из корневого `.env`. Это увеличивает поверхность атаки.

> ⚠️ **Рекомендация:** Удалить `web/.env.local`, загружать переменные через корневой `.env` с `dotenv` или использовать symlink.

---

## 2. API Routes

### 2.1 `app/api/sheets/[[...segments]]/route.ts`

#### ✅ Обработка ошибок
```typescript
catch (error) {
  console.error(`[API] /api/sheets/${action} error:`, error);
  return NextResponse.json(
    { error: "Internal server error" },
    { status: 500 }
  );
}
```
- Не раскрывает стектрейс или внутренние данные — **безопасно**
- Логирует в консоль (серверную, не клиентскую) — **безопасно**

#### ✅ Валидация action
```typescript
case "transactions": ...
case "balance": ...
case "budget": ...
case "limits": ...
default:
  return NextResponse.json(
    { error: `Unknown action: ${action || "empty"}` },
    { status: 400 }
  );
```
- Белый список допустимых действий — **защита от инъекции пути**
- Неизвестные сегменты возвращают 400

#### 🔴 Rate Limiting — ОТСУТСТВУЕТ

API не имеет никакой защиты от перегрузки:
- Нет `lru-cache` или `rate-limiter-flexible`
- Нет простого счётчика запросов по IP
- Нет `Vercel KV` / `Upstash` rate limiter
- Google Sheets API имеет квоту (60 запросов/мин/пользователь), но клиентский кэш (30 сек) не спасает при параллельных запросах

> 🔴 **Критично:** Отсутствие rate limiting позволяет исчерпать квоту Google Sheets API и привести к отказу в обслуживании.

```typescript
// Пример: простой in-memory rate limiter
import { LRUCache } from 'lru-cache';

const rateLimit = new LRUCache<string, number>({
  max: 500,
  ttl: 60_000,
});

function checkRateLimit(ip: string): boolean {
  const count = rateLimit.get(ip) || 0;
  if (count >= 30) return false;
  rateLimit.set(ip, count + 1);
  return true;
}
```

#### 🟡 Входные параметры

API не принимает query-параметров (только path segments). **Валидация не требуется**, но:
- `segments[0]` проверяется через `switch`, остальные игнорируются — **ок**
- Нет ограничения на длину сегментов

#### ✅ Кэширование

`SimpleCache` с TTL 30 секунд — защищает Google Sheets от частых запросов. Базовая, но достаточная защита.

### 2.2 `app/api/mono/rates/route.ts`

- Публичное API Monobank — **не требует аутентификации**
- `next: { revalidate: 300 }` — встроенный HTTP-кэш Next.js на 5 минут
- Обработка ошибок: возвращает 502 с `{ error: 'Monobank unavailable' }` — **безопасно**

---

## 3. Google Sheets Client (`lib/sheets.ts`)

### 3.1 Обработка private_key

```typescript
return new JWT({
  email,
  key: key.replace(/\\n/g, '\n'),  // Корректная замена \n на реальные переносы
  scopes: SCOPES,
});
```

**Корректно.** `GOOGLE_PRIVATE_KEY` в `.env` хранится с экранированными `\n`, замена происходит на уровне приложения. ✅

### 3.2 Singleton

```typescript
export const sheetsClient = new SheetsClient();
```

Module-level singleton — **корректно**. Экземпляр создаётся один раз при первом импорте. ✅

### 3.3 Lazy-инициализация

```typescript
private getSheets(): sheets_v4.Sheets | null {
  if (this.sheets) return this.sheets;
  const auth = this.getAuth();
  if (!auth) return null;
  this.sheets = google.sheets({ version: 'v4', auth });
  return this.sheets;
}
```

JWT и sheets-клиент создаются лениво при первом вызове — **эффективно**. ✅

### 3.4 Graceful degradation

Все методы возвращают `[]` при ошибке или отсутствии credentials — приложение не падает. ✅

### 3.5 Отсутствие `server-only`

```typescript
// РЕКОМЕНДАЦИЯ: добавить в первую строку
import "server-only";
```

Без этого импорт `sheetsClient` в клиентский компонент **не вызовет ошибку сборки**, хотя и не будет работать (credentials отсутствуют в браузере). Сам факт, что сборка не падает — это упущение.

---

## 4. XSS Protection

### 4.1 `dangerouslySetInnerHTML`

Единственное использование — `app/layout.tsx`:

```tsx
<script dangerouslySetInnerHTML={{ __html: ThemeScript }} />
```

`ThemeScript` — **хардкоженная строка** (определена в `ThemeProvider.tsx`), не содержит пользовательских данных. ✅ Безопасно.

### 4.2 Пользовательские данные в JSX

**Все** пользовательские данные рендерятся через JSX-выражения, которые React автоматически экранирует:

| Компонент | Данные | Защита |
|-----------|--------|--------|
| `TransactionTable` | `tx.category`, `tx.comment`, `tx.source` | JSX auto-escape ✅ |
| `RecentTransactions` | `tx.category`, `tx.comment` | JSX auto-escape ✅ |
| `Badge` | `children` (только строки "Доход"/"Расход") | JSX auto-escape ✅ |
| `EmptyState` | `description` (строковые литералы) | JSX auto-escape ✅ |
| `PeriodCompare` | `stats.comment` (генерируется сервером) | JSX auto-escape ✅ |

**Нет** ни одного случая вставки пользовательских данных через `innerHTML`, `document.write()`, или `eval()`. ✅

### 4.3 Данные из Google Sheets

Все данные приходят как строки через Google Sheets API, преобразуются в `Transaction` объекты, и рендерятся через JSX. React экранирует всё. ✅

---

## 5. CSP & Security Headers

### 5.1 Content-Security-Policy

**Отсутствует.** Ни в `next.config.mjs`, ни в `middleware.ts` (нет файла), ни в заголовках ответа.

> 🔴 **Критично:** CSP — основная защита от XSS. Даже если React экранирует всё, CSP — это defence-in-depth.

**Рекомендуемая конфигурация** для `next.config.mjs`:

```javascript
const nextConfig = {
  reactStrictMode: true,
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob:",
              "font-src 'self'",
              "connect-src 'self' https://api.monobank.ua",
              "manifest-src 'self'",
            ].join('; '),
          },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ];
  },
};
```

### 5.2 CORS

**Не настроен.** Next.js по умолчанию разрешает same-origin запросы. Для API это нормально — все запросы идут с того же домена. ✅

`connect-src 'self' https://api.monobank.ua` в CSP покрывает внешний API.

### 5.3 Отсутствующие заголовки

| Заголовок | Статус |
|-----------|--------|
| `Content-Security-Policy` | 🔴 Отсутствует |
| `X-Content-Type-Options` | 🔴 Отсутствует |
| `X-Frame-Options` | 🔴 Отсутствует |
| `Strict-Transport-Security` | 🔴 Отсутствует |
| `Referrer-Policy` | 🔴 Отсутствует |
| `Permissions-Policy` | 🔴 Отсутствует |

---

## 6. Dependencies

### 6.1 npm audit results

```
6 vulnerabilities (5 moderate, 1 high)
```

| Пакет | Версия | Уязвимость | Severity | Фикс |
|-------|--------|-----------|----------|------|
| **next** | 14.2.0 | 15 CVE (XSS, Request Smuggling, DoS, SSRF, Cache Poisoning) | 🔴 HIGH | 16.2.6 |
| **googleapis** | 134.0.0 | uuid buffer bounds check | 🟡 MODERATE | 173.0.0 |
| **postcss** (transitive) | <8.5.10 | XSS via CSS Stringify | 🟡 MODERATE | bundled with next |
| **uuid** (transitive) | <11.1.1 | Missing buffer bounds check | 🟡 MODERATE | bundled with googleapis |

### 6.2 Критические CVE для Next.js 14.2.0

| CVE | Описание | CVSS |
|-----|----------|------|
| GHSA-gx5p-jg67-6x7h | XSS в beforeInteractive scripts | High |
| GHSA-ffhc-5mcf-pf4q | XSS в App Router с CSP nonces | High |
| GHSA-c4j6-fc7j-m34r | SSRF через WebSocket upgrades | High |
| GHSA-ggv3-7p47-pfv8 | HTTP Request Smuggling в rewrites | High |
| GHSA-h25m-26qc-wcjf | DoS через RSC десериализацию | High |

> 🔴 **Критично:** Next.js 14.2.0 содержит 15 известных уязвимостей. Обновление до 16.2.6 требует breaking changes (React 19, Turbopack, middleware изменения).

### 6.3 Обновление

```bash
# Breaking changes — требует тестирования
npm install next@16.2.6 googleapis@173.0.0
```

> ⚠️ **Предупреждение:** Next.js 16 требует React 19 (breaking). Нужно обновить `react` и `react-dom` до `^19.0.0`, а также проверить совместимость recharts.

---

## 7. Service Worker (`public/sw.js`)

### 7.1 Анализ кэширования

```javascript
// Не кэшируем API/данные
if (event.request.url.includes('/api/') || event.request.method !== 'GET') {
  return;  // Пропускаем — запрос идёт напрямую в сеть
}
```

- `return` без `event.respondWith()` означает, что браузер обрабатывает запрос самостоятельно — **API-запросы не кэшируются** ✅
- Не-GET запросы пропускаются — **безопасно** ✅

### 7.2 Кэширование страниц

Страницы (`/`, `/transactions`, `/analytics`) precache-ятся при установке SW и обновляются через Network First стратегию.

**Риск:** Закэшированные страницы могут содержать финансовые данные в HTML (если страница рендерится на сервере). Но:
- Все страницы — `"use client"` компоненты, данные загружаются через API
- HTML содержит только скелетоны и статический контент
- Финансовые данные НЕ попадают в кэш SW

### 7.3 Precached URLs

```javascript
const PRECACHE_URLS = [
  '/', '/transactions', '/analytics',
  '/manifest.json',
  '/icons/icon-192x192.svg', '/icons/icon-512x512.svg',
];
```

Только статические маршруты — **безопасно** ✅

---

## 8. Дополнительные находки

### 8.1 Отсутствие CORS на API

API routes не имеют CORS-заголовков, но это ок для same-origin приложения. Однако если в будущем понадобится доступ из PWA на другом домене — нужно будет добавить.

### 8.2 Аутентификация API

API routes `/api/sheets/*` — **публичные** (нет проверки токена/сессии). Любой, кто знает URL, может читать финансовые данные.

> 🟡 **Средний риск:** Для персонального трекера, развёрнутого локально или за VPN — приемлемо. При деплое в открытый интернет — критично.

**Рекомендация:** Добавить `Authorization` header с shared secret или простой API-ключ.

```typescript
// middleware.ts
import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  if (request.nextUrl.pathname.startsWith('/api/')) {
    const auth = request.headers.get('authorization');
    if (auth !== `Bearer ${process.env.API_SECRET}`) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
  }
}

export const config = { matcher: '/api/:path*' };
```

### 8.3 Информация в ответах API

API ответы содержат финансовые данные, но не раскрывают:
- Структуру базы данных ✅
- Учётные данные ✅
- Внутренние пути/конфигурацию ✅

Ошибки возвращают generic `"Internal server error"` — **безопасно** ✅

---

## Сводка рекомендаций

### 🔴 P0 — Критические (немедленно)

| # | Проблема | Действие | Файл |
|---|----------|----------|------|
| 1 | Next.js 14.2.0 — 15 CVE | Обновить до 16.2.6 (+ React 19) | `package.json` |
| 2 | Отсутствует rate limiting API | Добавить `lru-cache` rate limiter | `api/sheets/route.ts` |
| 3 | Отсутствует CSP и security headers | Добавить `headers()` в next.config | `next.config.mjs` |

### 🟡 P1 — Важные (в ближайшее время)

| # | Проблема | Действие | Файл |
|---|----------|----------|------|
| 4 | `sheets.ts` без `server-only` | Добавить `import "server-only"` | `lib/sheets.ts` |
| 5 | API без аутентификации | Добавить middleware с API key | `middleware.ts` (новый) |
| 6 | Дублирование .env файлов | Удалить `web/.env.local` | `web/.env.local` |
| 7 | googleapis 134.0.0 — uuid CVE | Обновить до 173.0.0 | `package.json` |

### 🟢 P2 — Улучшения

| # | Проблема | Действие | Файл |
|---|----------|----------|------|
| 8 | Нет `Strict-Transport-Security` | Добавить HSTS-заголовок | `next.config.mjs` |
| 9 | Нет `Permissions-Policy` | Добавить заголовок | `next.config.mjs` |
| 10 | Service Worker без хэша версии | Добавить content-hash в CACHE_VERSION | `public/sw.js` |

---

## Итог

Приложение **не содержит критических уязвимостей в коде** (XSS, утечка секретов, инъекции). Основные риски сосредоточены в:

1. **Устаревшие зависимости** — Next.js 14.2.0 с 15 известными CVE
2. **Инфраструктурные пробелы** — отсутствие CSP, security headers, rate limiting
3. **Публичный доступ к API** — при деплое в интернет потребуется аутентификация

Рекомендуемый порядок действий: обновление Next.js → CSP + rate limiting → API-аутентификация.
