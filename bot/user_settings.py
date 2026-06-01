"""Персистентные настройки пользователя через Google Sheets лист 'Settings'.

При старте бота настройки загружаются из Sheets в context.user_data.
При изменении — сохраняются обратно. Поддерживаются str, bool, int, float.

Также отвечает за сброс alert-флагов при начале нового месяца.
"""

import logging
from datetime import datetime

from sheets import (
    _ensure_sheet,
    delete_setting,
    get_settings_rows,
    upsert_setting,
)

logger = logging.getLogger(__name__)

SETTINGS_SHEET = "Settings"
SETTINGS_HEADERS = ["Key", "Value"]

# Ключи настроек, которые сохраняются в Sheets
PERSISTED_KEYS = {
    "toxicity",
    "profanity_enabled",
    "currency",
    "limit_alerts",
    "alert_50",
    "alert_80",
    "alert_exceeded",
    "stickers_enabled",
    "sticker_frequency",
    "emoji_enabled",
    "quote_time",
    "reminder_time",
    "last_alert_reset_month",
}

# Значения по умолчанию при первом запуске
DEFAULTS = {
    "toxicity": "grumpy",
    "profanity_enabled": True,
    "currency": "UAH",
    "alert_50": True,
    "alert_80": True,
    "alert_exceeded": True,
    "stickers_enabled": True,
    "sticker_frequency": "always",
    "emoji_enabled": True,
    "limit_alerts": False,
}


def _ensure_settings_sheet() -> None:
    """Убедиться что лист Settings существует."""
    _ensure_sheet(SETTINGS_SHEET, SETTINGS_HEADERS)


def load_user_settings(user_id: str = "default") -> dict:
    """Загрузить настройки из Settings sheet.

    Возвращает словарь {key: parsed_value}.
    Парсит "True"/"False" → bool, числа → int/float, остальное → str.
    """
    _ensure_settings_sheet()
    rows = get_settings_rows()
    result: dict = {}

    for r in rows:
        if len(r) < 2:
            continue
        key = str(r[0]).strip()
        raw = str(r[1]).strip()

        if raw == "True":
            result[key] = True
        elif raw == "False":
            result[key] = False
        else:
            try:
                result[key] = int(raw)
            except ValueError:
                try:
                    result[key] = float(raw)
                except ValueError:
                    result[key] = raw

    return result


def save_user_settings(settings: dict, user_id: str = "default") -> None:
    """Сохранить настройки в Settings sheet.

    Сохраняет только ключи из PERSISTED_KEYS.
    """
    _ensure_settings_sheet()
    for key, value in settings.items():
        if key in PERSISTED_KEYS:
            upsert_setting(key, str(value))


def persist_setting(key: str, value, user_id: str = "default") -> None:
    """Сохранить одну настройку в Sheets.

    Если value is None — удаляет ключ из Sheets.
    Не бросает исключений — пишет в лог при ошибке.
    """
    if key not in PERSISTED_KEYS:
        return
    try:
        _ensure_settings_sheet()
        if value is None:
            delete_setting(key)
        else:
            upsert_setting(key, str(value))
    except Exception as e:
        logger.warning("Не удалось сохранить настройку %s: %s", key, e)


def should_reset_alerts(user_data: dict) -> bool:
    """Проверить, начался ли новый месяц — сбросить alert_sent флаги.

    Сравнивает сохранённый last_alert_reset_month с текущим месяцем.
    Если не совпадает — обновляет месяц в user_data и Sheets.
    Вызывается при /start.

    Returns True если месяц сменился (алерты сброшены).
    """
    current_month = datetime.now().strftime("%Y-%m")
    last_reset = user_data.get("last_alert_reset_month", "")

    if last_reset != current_month:
        user_data["last_alert_reset_month"] = current_month
        persist_setting("last_alert_reset_month", current_month)
        return True
    return False
