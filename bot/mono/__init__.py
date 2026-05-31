"""Monobank integration for Kesha bot."""

import logging
from datetime import datetime, timezone

from mono.client import _convert_amount, currency_code_to_name
from mono.mcc_categories import categorize_by_mcc

logger = logging.getLogger(__name__)


def build_transaction_row(tx: dict) -> list | None:
    """Преобразовать транзакцию Monobank в строку для Google Sheets.

    Returns список из 9 колонок или None если сумма нулевая.
    """
    amount = tx.get("amount", 0)
    if amount == 0:
        logger.debug("Пропущена транзакция с нулевой суммой: id=%s", tx.get("id"))
        return None

    currency_code = tx.get("currencyCode", 980)
    converted = _convert_amount(amount, currency_code)
    mcc = tx.get("mcc", 0)

    type_str = "expense" if amount < 0 else "income"

    tx_time = tx.get("time", 0)
    dt = datetime.fromtimestamp(tx_time, tz=timezone.utc)
    month_str = dt.strftime("%B")
    date_str = dt.strftime("%d.%m.%Y")

    category = categorize_by_mcc(mcc)
    comment = tx.get("description", "")
    source = f"mono:{tx['id']}"

    amount_uah = converted if currency_code == 980 else ""
    amount_usd = converted if currency_code == 840 else ""
    amount_eur = converted if currency_code == 978 else ""

    if currency_code not in (980, 840, 978):
        amount_uah = converted
        logger.warning(
            "Неизвестный код валюты %s, сумма %s записана в UAH",
            currency_code,
            converted,
        )

    return [
        month_str,
        date_str,
        type_str,
        amount_uah,
        amount_usd,
        amount_eur,
        category,
        comment,
        source,
    ]
