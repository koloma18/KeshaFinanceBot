"""Ежедневные напоминания. /reminder — настройка времени."""

import datetime as dt
import logging
from datetime import datetime

from handlers.statistics import _filter_today, _format_cat_top, _summarize
from responses import get_quote
from sheets import get_all_rows
from telegram import Update
from telegram.ext import ContextTypes
from user_settings import persist_setting

logger = logging.getLogger(__name__)


async def reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Настройка ежедневного напоминания.

    /reminder — показать текущее время
    /reminder 21:00 — установить на 21:00
    /reminder off — отключить

    Хранит в context.user_data['reminder_time'].
    """
    user_data = context.user_data
    args = context.args

    if not args:
        current = user_data.get("reminder_time")
        if current:
            await update.message.reply_text(
                f"⏰ Ежедневное напоминание запланировано на <b>{current}</b>.\n"
                f"Я буду присылать итог дня и цитату.\n\n"
                f"Чтобы изменить: /reminder HH:MM\n"
                f"Чтобы отключить: /reminder off",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                "⏰ Ежедневное напоминание отключено.\n"
                "Я могу присылать итог дня и цитату каждый вечер.\n\n"
                "Чтобы включить: /reminder HH:MM\n"
                "Например: /reminder 21:00"
            )
        return

    arg = args[0].lower()

    if arg == "off":
        if "reminder_time" in user_data:
            del user_data["reminder_time"]
        persist_setting("reminder_time", None)
        # Удаляем джобу
        chat_id = update.effective_chat.id
        job_name = f"reminder_{chat_id}"
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        for j in current_jobs:
            j.schedule_removal()
        await update.message.reply_text(
            "⏰ Ежедневное напоминание отключено. Буду молчать до команды."
        )
        return

    # Проверяем формат HH:MM
    try:
        datetime.strptime(arg, "%H:%M")
    except ValueError:
        await update.message.reply_text(
            "❌ Неправильный формат. Используй HH:MM, например: /reminder 21:00"
        )
        return

    user_data["reminder_time"] = arg
    persist_setting("reminder_time", arg)

    # Удаляем старую джобу и создаём новую
    chat_id = update.effective_chat.id
    job_name = f"reminder_{chat_id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for j in current_jobs:
        j.schedule_removal()

    hour, minute = map(int, arg.split(":"))

    context.job_queue.run_daily(
        send_daily_reminder_job,
        time=dt.time(hour=hour, minute=minute),
        data={"chat_id": chat_id},
        name=job_name,
    )

    await update.message.reply_text(
        f"✅ Ежедневное напоминание установлено на <b>{arg}</b>.\n"
        f"Каждый день в это время буду присылать итог и цитату.",
        parse_mode="HTML",
    )


async def send_daily_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback для JobQueue. Отправляет итог дня + цитату.

    context.job.data = {'chat_id': chat_id}
    Берёт today rows, считает income/expense, добавляет цитату.
    """
    job = context.job
    if not job or not job.data:
        return

    chat_id = job.data.get("chat_id")
    if not chat_id:
        return

    try:
        rows = get_all_rows()
        today_rows = _filter_today(rows)
        income, expense, cat_expense = _summarize(today_rows)
        cat_block = _format_cat_top(cat_expense)
        quote = get_quote()

        lines = [
            "📅 <b>Итог дня</b>",
            "",
            f"💰 Доход: +{income:.0f} UAH",
            f"💸 Расход: -{expense:.0f} UAH",
            f"📊 Итого: {income - expense:+.0f} UAH",
        ]

        if cat_block:
            lines.append("")
            lines.append("<b>Топ трат:</b>")
            lines.append(cat_block)

        lines.append("")
        lines.append(f"💬 {quote}")
        lines.append("")
        lines.append("✌️ Спокойной ночи. Завтра новый день — новые траты.")

        await context.bot.send_message(
            chat_id=chat_id,
            text="\n".join(lines),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка в send_daily_reminder_job для chat_id %s: %s", chat_id, e)
