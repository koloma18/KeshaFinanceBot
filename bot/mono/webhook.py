"""WebHook обработчик для Monobank API.

REQ-04: Приём транзакций через Monobank WebHook.

Реализован на базовом http.server — без внешних зависимостей.

Формат тела запроса от Monobank:
{
    "type": "StatementItem",
    "data": {
        "account": "account_id",
        "statementItem": {
            "id": "some_unique_id",
            "time": 1234567890,
            "description": "Магазин",
            "mcc": 5411,
            "originalMcc": 5411,
            "amount": -10000,          // в копейках, отрицательное = расход
            "operationAmount": -10000,
            "currencyCode": 980,        // ISO 4217
            "commissionRate": 0,
            "cashbackAmount": 0,
            "balance": 500000,
            "hold": false
        }
    }
}
"""

import json
import logging
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from sheets import COL, add_row, find_row_by_source

from mono.client import MonobankError, _convert_amount, currency_code_to_name
from mono.mcc_categories import categorize_by_mcc

logger = logging.getLogger(__name__)


def _determine_type(amount_minor: int) -> str:
    """Определить тип транзакции: 'expense' или 'income'.

    Отрицательная сумма = расход (списание).
    Положительная = доход (пополнение, кэшбэк, возврат).
    """
    return "expense" if amount_minor < 0 else "income"


def _format_month(dt: datetime) -> str:
    """Форматировать месяц как 'January' (dt.strftime('%B'))."""
    return dt.strftime("%B")


def process_transaction(data: dict) -> bool:
    """Обработать входящую транзакцию из Monobank WebHook.

    Args:
        data: Словарь Monobank StatementItem (из data.statementItem).

    Returns:
        True если транзакция добавлена в таблицу,
        False если дубликат или ошибка.
    """
    try:
        tx_id = data.get("id", "")
        if not tx_id:
            logger.warning("WebHook: транзакция без id — пропущена")
            return False

        # Дедупликация — ищем по источнику mono:{tx_id}
        source_key = f"mono:{tx_id}"
        existing = find_row_by_source(source_key)
        if existing is not None:
            logger.debug("WebHook: дубликат mono:%s — пропущен", tx_id)
            return False

        # Основные поля
        amount_minor = data.get("amount", 0)
        currency_code = data.get("currencyCode", 980)
        mcc = data.get("mcc", 0)
        description = data.get("description", "")
        tx_time = data.get("time", 0)
        hold = data.get("hold", False)

        # Пропускаем холды — обработаем только когда подтверждены
        if hold:
            logger.debug("WebHook: холд mono:%s — пропущен", tx_id)
            return False

        # Определяем тип и категорию
        tx_type = _determine_type(amount_minor)
        category = categorize_by_mcc(mcc)

        # Конвертируем сумму (берём абсолютное значение)
        amount_major = _convert_amount(abs(amount_minor), currency_code)
        currency_name = currency_code_to_name(currency_code)

        # Форматируем дату
        try:
            dt = datetime.fromtimestamp(tx_time, tz=timezone.utc)
        except (OSError, ValueError, OverflowError):
            dt = datetime.now(tz=timezone.utc)
        date_str = dt.strftime("%d.%m.%Y")
        month_str = _format_month(dt)

        # Распределяем сумму по колонкам валют
        amount_uah = amount_major if currency_name == "UAH" else ""
        amount_usd = amount_major if currency_name == "USD" else ""
        amount_eur = amount_major if currency_name == "EUR" else ""

        # Комментарий: описание от Monobank
        comment = description or ""

        # Формируем строку для Sheets
        row = [
            month_str,  # Month
            date_str,  # Date
            tx_type,  # Type
            amount_uah,  # Amount UAH
            amount_usd,  # Amount USD
            amount_eur,  # Amount EUR
            category,  # Category
            comment,  # AI Comment (description from mono)
            source_key,  # Source (mono:{id})
        ]

        if add_row(row):
            logger.info(
                "WebHook: добавлена транзакция mono:%s | %s | %.2f %s | %s",
                tx_id,
                tx_type,
                amount_major,
                currency_name,
                category,
            )
            return True
        else:
            logger.error("WebHook: не удалось записать mono:%s в Sheets", tx_id)
            return False

    except Exception as e:
        logger.exception("WebHook: ошибка обработки транзакции: %s", e)
        return False


class MonobankWebhookHandler(BaseHTTPRequestHandler):
    """HTTP-хендлер для WebHook от Monobank.

    Ожидает POST с JSON-телом. Отвечает 200 OK после обработки
    или 400 Bad Request при неверном формате.
    """

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._respond(400, {"error": "Invalid JSON"})
            return

        # Валидация формата
        event_type = payload.get("type", "")
        event_data = payload.get("data", {})

        if event_type != "StatementItem":
            logger.debug("WebHook: пропущен event type=%s", event_type)
            self._respond(200, {"status": "ignored"})
            return

        statement_item = event_data.get("statementItem", {})
        if not statement_item:
            logger.warning("WebHook: нет statementItem в data")
            self._respond(400, {"error": "Missing statementItem"})
            return

        success = process_transaction(statement_item)
        self._respond(200, {"status": "processed" if success else "skipped"})

    def _respond(self, status_code: int, body: dict):
        """Отправить JSON-ответ."""
        body_bytes = json.dumps(body).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    def log_message(self, fmt: str, *args):
        """Перенаправить логи http.server в наш логгер."""
        logger.debug("WebHook HTTP: %s", fmt % args)


def run_webhook_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Запустить HTTP-сервер для приёма Monobank WebHook.

    Args:
        host: Хост для привязки (0.0.0.0 — все интерфейсы).
        port: Порт (8080 по умолчанию).

    Для деплоя потребуется публичный URL (через ngrok, Cloudflare Tunnel и т.п.)
    и регистрация в Monobank через /personal/webhook.
    """
    server = HTTPServer((host, port), MonobankWebhookHandler)
    logger.info("🌐 Monobank WebHook сервер запущен на %s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("WebHook сервер остановлен")
        server.server_close()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    run_webhook_server()
