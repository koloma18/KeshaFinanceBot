"""Цитаты дня. /quote — случайная цитата. /quote_time HH:MM — установка времени."""

import datetime as dt
import logging
from datetime import datetime
from random import choice

from telegram import Update
from telegram.ext import ContextTypes
from user_settings import persist_setting

logger = logging.getLogger(__name__)

# 20 цитат в характере Кеши — саркастичные, о деньгах и жизни
QUOTES_POOL = [
    "«Деньги любят учёт. А импульсивные покупки любят делать вид, что их не было.»",
    "«Бюджет не ограничивает свободу. Он показывает, где ты сама себе враг.»",
    "«Самая дорогая категория расходов — „да ладно, один раз живём“»",
    "«Скидка не экономит деньги, если ты вообще не собиралась это покупать.»",
    "«Если покупка кажется срочной, подожди 24 часа. Если всё ещё нужна — покупай.»",
    "«Кофе — это не расход, это инвестиция в способность функционировать.»",
    "«Тратить меньше, чем зарабатываешь — звучит скучно, но работает.»",
    "«Финансовая подушка — это когда ты можешь послать начальника и не умереть с голоду.»",
    "«Копейка рубль бережёт. А потом приходит маркетплейс и забирает всё.»",
    "«Богатые тоже платят. Просто у них остаётся больше.»",
    "«Самая опасная фраза в финансах: „Ой, да это же мелочь“»",
    "«Отложить деньги — это купить спокойствие в рассрочку у самого себя.»",
    "«Кредитка — это как одолжить деньги у будущего себя, который будет зол.»",
    "«Бюджет — это не клетка. Это карта, которая показывает где ямы.»",
    "«Если ты не знаешь куда уходят деньги — они уходят на херню.»",
    "«Счастье не в деньгах. Но на такси и кофе их почему-то всегда жалко.»",
    "«Подушка безопасности — это не та, на которой ты спишь.»",
    "«Расходы имеют привычку расти, чтобы заполнить любой доход.»",
    "«Инвестиция в себя — это хорошо. Но чек почему-то всегда приходит на карту.»",
    "«Деньги — это инструмент. А инструмент должен быть в порядке, а не валяться где попало.»",
]


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать случайную цитату дня."""
    quote = choice(QUOTES_POOL)
    await update.message.reply_text(f"💬 {quote}")


async def quote_time_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Установить время ежедневной цитаты.

    /quote_time — показать текущее время
    /quote_time 09:00 — установить на 9:00
    /quote_time off — отключить

    Хранит в context.user_data['quote_time'] в формате "HH:MM" или None.
    """
    user_data = context.user_data
    args = context.args

    if not args:
        current = user_data.get("quote_time")
        if current:
            await update.message.reply_text(
                f"⏰ Ежедневная цитата запланирована на <b>{current}</b>.\n"
                f"Чтобы изменить: /quote_time HH:MM\n"
                f"Чтобы отключить: /quote_time off",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                "⏰ Ежедневная цитата отключена.\n"
                "Чтобы включить: /quote_time HH:MM\n"
                "Например: /quote_time 09:00"
            )
        return

    arg = args[0].lower()

    if arg == "off":
        if "quote_time" in user_data:
            del user_data["quote_time"]
        persist_setting("quote_time", None)
        # Удаляем джобу
        chat_id = update.effective_chat.id
        job_name = f"quote_{chat_id}"
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        for j in current_jobs:
            j.schedule_removal()
        await update.message.reply_text(
            "⏰ Ежедневная цитата отключена. Буду молчать до команды."
        )
        return

    # Проверяем формат HH:MM
    try:
        datetime.strptime(arg, "%H:%M")
    except ValueError:
        await update.message.reply_text(
            "❌ Неправильный формат. Используй HH:MM, например: /quote_time 09:00"
        )
        return

    user_data["quote_time"] = arg
    persist_setting("quote_time", arg)

    # Удаляем старую джобу и создаём новую
    chat_id = update.effective_chat.id
    job_name = f"quote_{chat_id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for j in current_jobs:
        j.schedule_removal()

    hour, minute = map(int, arg.split(":"))

    context.job_queue.run_daily(
        send_daily_quote_job,
        time=dt.time(hour=hour, minute=minute),
        data={"chat_id": chat_id},
        name=job_name,
    )

    await update.message.reply_text(
        f"✅ Ежедневная цитата установлена на <b>{arg}</b>.\n"
        f"Буду напоминать о финансах каждый день в это время.",
        parse_mode="HTML",
    )


async def send_daily_quote_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback для JobQueue. Отправляет цитату всем активным пользователям.

    context.job.data = {'chat_id': chat_id}
    Если у пользователя есть quote_time — отправляет цитату.
    """
    job = context.job
    if not job or not job.data:
        return

    chat_id = job.data.get("chat_id")
    if not chat_id:
        return

    # Проверяем, что у пользователя включены ежедневные цитаты
    # user_data недоступна напрямую из job callback — chat_data используется
    # Отправляем цитату, а фильтрацию по quote_time делает тот, кто создаёт job
    quote = choice(QUOTES_POOL)
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"💬 <b>Цитата дня</b>\n\n{quote}",
        parse_mode="HTML",
    )
