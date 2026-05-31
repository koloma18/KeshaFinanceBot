# Деплой на Vercel

> 🌐 **Текущий деплой:** [keshafinancebot.vercel.app](https://keshafinancebot.vercel.app)
>
> Репозиторий: [github.com/koloma18/KeshaFinanceBot](https://github.com/koloma18/KeshaFinanceBot)

## Шаг 1: Импорт репозитория

1. Зайди на [vercel.com](https://vercel.com)
2. **Add New → Project**
3. Выбери `koloma18/KeshaFinanceBot`
4. Vercel автоматически определит, что это Next.js

## Шаг 2: Настройка Root Directory

Приложение находится в поддиректории `web/` (монорепо: `bot/` + `web/`).

В настройках проекта укажи:
- **Framework Preset:** Next.js (автоопределится)
- **Root Directory:** `web`

> Конфиг `web/vercel.json` уже есть в репозитории — Vercel подхватит его автоматически.

## Шаг 3: Environment Variables

Project → Settings → Environment Variables. Добавь следующие переменные:

| Name | Value | Обязательно |
|------|-------|:----------:|
| `GOOGLE_SERVICE_ACCOUNT_EMAIL` | email сервисного аккаунта Google Cloud | ✅ |
| `GOOGLE_PRIVATE_KEY` | приватный ключ сервисного аккаунта | ✅ |
| `SPREADSHEET_ID` | ID Google Sheets таблицы | ✅ |
| `MONOBANK_X_TOKEN` | X-Token персональный Monobank | ❌ (опционально) |
| `CACHE_TTL_MS` | время кеша в мс (по умолчанию 30000) | ❌ |

### Важно: формат `GOOGLE_PRIVATE_KEY`

Ключ должен быть **в точности** как в JSON-файле сервисного аккаунта, включая `\n`:

```
-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC...\n-----END PRIVATE KEY-----\n
```

Не заменяй `\n` на реальные переносы строк в интерфейсе Vercel — вставляй как есть, одной строкой с `\n`.

Если ключ обёрнут в двойные кавычки в JSON — **убери внешние кавычки**, сам `\n` оставь.

## Шаг 4: Deploy

Нажми **Deploy**. Vercel:
- Установит зависимости (`npm install`)
- Соберёт Next.js (`next build`)
- Зальёт на CDN

Первый деплой займёт 1–2 минуты.

## Что ты получишь

- URL вида `https://kesha-finance-bot.vercel.app` (можно сменить в Settings → Domains). Текущий: [keshafinancebot.vercel.app](https://keshafinancebot.vercel.app)
- Авто-деплой при каждом `git push` в `main`
- Бесплатный HTTPS (автоматически)
- PWA из коробки (`manifest.json` + service worker уже настроены)

## Проверка деплоя

### 1. Health check
Открой `https://<твой-домен>.vercel.app/api/health` — должен вернуть:

```json
{
  "status": "ok",
  "timestamp": 1717000000000,
  "env": {
    "hasSheets": true,
    "hasGoogleEmail": true,
    "hasGoogleKey": true,
    "hasMono": true
  }
}
```

- `hasSheets: false` → `SPREADSHEET_ID` не указан или неверный
- `hasGoogleEmail: false` → `GOOGLE_SERVICE_ACCOUNT_EMAIL` не указан
- `hasGoogleKey: false` → `GOOGLE_PRIVATE_KEY` не подхватился (частая ошибка — неправильный формат `\n`)
- `hasMono: false` → нормально, если Monobank не подключён

### 2. Дашборд
Открой главную страницу — должен отобразиться дашборд с данными из Google Sheets.

### 3. PWA
На мобильном устройстве открой сайт в Chrome/Safari → «Добавить на главный экран». Должно установиться как приложение.

## Локальный деплой (для теста)

```bash
cd web
npm install
npm run build
npm start
```

Открой `http://localhost:3000`.

## Troubleshooting

| Проблема | Вероятная причина | Решение |
|----------|-------------------|---------|
| 500 на дашборде | `GOOGLE_PRIVATE_KEY` неверный | Проверь `\n` в ключе, убери внешние кавычки |
| 500 на дашборде | `SPREADSHEET_ID` не указан | Проверь переменную в Vercel |
| Белый экран | Ошибка сборки | Смотри логи во вкладке Deployments |
| PWA не устанавливается | `manifest.json` не найден | Проверь что `web/public/manifest.json` существует |
| CORS ошибки | CSP блокирует запросы | `connect-src` в `next.config.mjs` уже включает `api.monobank.ua` |
